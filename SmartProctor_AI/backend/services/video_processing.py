import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import asyncio
import base64
import numpy as np
import os
import time
import hashlib
from utils.alerts import add_alert

# --- 3D Model Points (Standard Face Model in mm) ---
MODEL_POINTS = np.array([
    (0.0, 0.0, 0.0),             # Nose tip
    (0.0, -330.0, -65.0),        # Chin
    (-225.0, 170.0, -135.0),     # Left eye left corner
    (225.0, 170.0, -135.0),      # Right eye right corner
    (-150.0, -150.0, -125.0),    # Left Mouth corner
    (150.0, -150.0, -125.0)      # Right mouth corner
], dtype=np.float64)

def draw_3d_axes(image, center, axes_points):
    p_nose = tuple(map(int, center))
    p_x = tuple(map(int, axes_points[0].ravel()))
    p_y = tuple(map(int, axes_points[1].ravel()))
    p_z = tuple(map(int, axes_points[2].ravel()))
    
    cv2.line(image, p_nose, p_x, (0, 0, 255), 2) # X - Red
    cv2.line(image, p_nose, p_y, (0, 255, 0), 2) # Y - Green
    cv2.line(image, p_nose, p_z, (255, 0, 0), 2) # Z - Blue
    cv2.circle(image, p_nose, 4, (0, 255, 255), -1)

async def process_video_feed(websocket):
    if not os.path.exists(MODEL_PATH):
        print(f"Warning: {MODEL_PATH} not found. Head pose detection will be disabled.")
        detector = None
    else:
        try:
            detector = setup_face_landmarker()
        except Exception as e:
            print(f"Error setting up Face Landmarker: {e}")
            detector = None

    # Threshold constants
    YAW_THRESHOLD = 18
    PITCH_THRESHOLD = 15

    # Smoothing state
    smooth_yaw, smooth_pitch = 0, 0
    alpha = 0.3 # Smoothing factor (lower = smoother)
    
    # Get identity baseline from session
    from utils.alerts import get_session
    session = get_session()
    
    if detector is None:
        logger.error("MediaPipe Detector is None! Head pose detection will not work.")
    if yolo_model is None:
        logger.error("YOLO Model is None! Object detection will not work.")

    frame_count = 0
    try:
        while True:
            # Receive frame from frontend via WebSocket
            data = await websocket.receive_json()
            if data['type'] != 'frame':
                continue
            
            frame_count += 1
            frame_base64 = data['data']
            frame_bytes = base64.b64decode(frame_base64)
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is None:
                continue

            current_time = time.time()
            img_h, img_w, _ = frame.shape
            
            # --- 0. Define ROI (Central Framing Box) ---
            roi_w, roi_h = int(img_w * 0.45), int(img_h * 0.55)
            roi_x1, roi_y1 = (img_w - roi_w) // 2, (img_h - roi_h) // 2
            roi_x2, roi_y2 = roi_x1 + roi_w, roi_y1 + roi_h

            detections_this_frame = {
                "looking_side_to_side": False,
                "multiple_persons": False,
                "mobile_phone": False,
                "prohibited_object": False
            }

            face_in_roi = False
            face_size_ok = False
            faces_detected = 0
            
            # --- 1. Mediapipe Face Processing ---
            if detector:
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                detection_result = detector.detect(mp_image)
                
                faces_detected = len(detection_result.face_landmarks) if detection_result.face_landmarks else 0
                
                if faces_detected > 0:
                    # 1.1 solvePnP Head Pose Estimation (First face)
                    lms = detection_result.face_landmarks[0]
                    
                    # 2D Image Points for solvePnP
                    image_points = np.array([
                        (lms[1].x * img_w, lms[1].y * img_h),     # Nose tip
                        (lms[152].x * img_w, lms[152].y * img_h), # Chin
                        (lms[33].x * img_w, lms[33].y * img_h),   # Left eye left corner
                        (lms[263].x * img_w, lms[263].y * img_h), # Right eye right corner
                        (lms[61].x * img_w, lms[61].y * img_h),   # Left mouth corner
                        (lms[291].x * img_w, lms[291].y * img_h)  # Right mouth corner
                    ], dtype=np.float64)

                    # Camera Matrix
                    focal_length = img_w
                    center = (img_w / 2, img_h / 2)
                    camera_matrix = np.array([[focal_length, 0, center[0]], [0, focal_length, center[1]], [0, 0, 1]], dtype="double")
                    dist_coeffs = np.zeros((4, 1))

                    success, rot_vec, trans_vec = cv2.solvePnP(MODEL_POINTS, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE)
                    
                    # Decompose rotation vector to Euler angles
                    rmat, _ = cv2.Rodrigues(rot_vec)
                    angles, _, _, _, _, _ = cv2.decomposeProjectionMatrix(np.hstack((rmat, trans_vec)))
                    p_raw, y_raw = angles[0].item(), angles[1].item()
                    
                    # Apply Mirroring Compensation and Smoothing
                    curr_pitch = np.clip(-p_raw, -90, 90)
                    curr_yaw = np.clip(-y_raw, -90, 90) # Flipped for mirrored frame consistency
                    
                    smooth_pitch = alpha * curr_pitch + (1 - alpha) * smooth_pitch
                    smooth_yaw = alpha * curr_yaw + (1 - alpha) * smooth_yaw
                    pitch, yaw = smooth_pitch, smooth_yaw

                    # 1.2 Framing & Distance Logic
                    nose = lms[1]
                    nx, ny = int(nose.x * img_w), int(nose.y * img_h)
                    if roi_x1 < nx < roi_x2 and roi_y1 < ny < roi_y2: face_in_roi = True
                    
                    # Eye distance check
                    eye_l, eye_r = lms[33], lms[263]
                    dist_px = np.sqrt((eye_l.x - eye_r.x)**2 + (eye_l.y - eye_r.y)**2) * img_w
                    if 45 < dist_px < 120: face_size_ok = True
                    else:
                        label_d = "TOO FAR" if dist_px <= 45 else "TOO CLOSE"
                        cv2.putText(frame, f"DIST: {label_d}", (roi_x1, roi_y2 + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

                    # 1.3 Orientation Violations (Yaw/Pitch)
                    if abs(yaw) > YAW_THRESHOLD or abs(pitch) > PITCH_THRESHOLD or not face_in_roi:
                        detections_this_frame["looking_side_to_side"] = True
                        reason = "SIDE LOOK" if abs(yaw) > YAW_THRESHOLD else ("PITCH" if abs(pitch) > PITCH_THRESHOLD else "OUT OF BOX")
                        cv2.putText(frame, f"VIOLATION: {reason}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

                    # 1.4 Visualization (3D Axes & HUD)
                    cv2.putText(frame, f"Yaw/Pitch: {int(yaw)}/{int(pitch)} deg", (img_w - 220, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                    
                    # Project 3D axes
                    axis_len = 200
                    (axes_2d, _) = cv2.projectPoints(np.array([(axis_len, 0, 0), (0, axis_len, 0), (0, 0, axis_len)], dtype=np.float64), rot_vec, trans_vec, camera_matrix, dist_coeffs)
                    draw_3d_axes(frame, image_points[0], axes_2d)
                    
                    # Direction Line
                    p1 = tuple(map(int, image_points[0]))
                    p2 = tuple(map(int, axes_2d[2].ravel())) # Z axis
                    cv2.arrowedLine(frame, p1, p2, (255, 255, 255), 2)

                if faces_detected > 1:
                    detections_this_frame["multiple_persons"] = True
                    cv2.putText(frame, f"MULTIPLE FACES ({faces_detected})", (50, 130), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

            # --- 2. YOLO processing ---
            results_yolo = yolo_model(frame, stream=True, verbose=False)
            person_count = 0
            for r in results_yolo:
                for box in r.boxes:
                    conf = float(box.conf[0])
                    if conf > 0.4:
                        cls = int(box.cls[0])
                        class_name = yolo_model.names[cls]
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        if class_name == 'person':
                            person_count += 1
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        elif class_name == 'cell phone':
                            detections_this_frame["mobile_phone"] = True
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                        elif class_name in ['book', 'laptop']:
                            detections_this_frame["prohibited_object"] = True
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 165, 0), 2)

            if person_count > 1:
                detections_this_frame["multiple_persons"] = True
                cv2.putText(frame, "MULTIPLE PERSONS (YOLO)", (50, 170), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

            # --- 3. Screen Alerts & Overlay Logic ---
            box_color = (0, 255, 0) if (face_in_roi and face_size_ok and faces_detected == 1) else (0, 0, 255)
            cv2.rectangle(frame, (roi_x1, roi_y1), (roi_x2, roi_y2), box_color, 2)
            lbl = "FRAME OK" if box_color == (0, 255, 0) else "RE-CENTER FACE"
            cv2.putText(frame, lbl, (roi_x1, roi_y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, box_color, 2)

            if faces_detected == 0:
                overlay = frame.copy()
                cv2.rectangle(overlay, (0,0), (img_w, img_h), (0,0,255), -1)
                frame = cv2.addWeighted(overlay, 0.2, frame, 0.8, 0)
                cv2.putText(frame, "NO FACE DETECTED", (img_w//2-140, img_h//2), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3)

            # --- 4. WebSocket Sync & Alerts ---
            active_violations = []
            GRACE_PERIOD = 1.0
            for alert_key, is_detected in detections_this_frame.items():
                buffer = alert_buffers[alert_key]
                if is_detected:
                    buffer["last_seen"] = current_time
                    if buffer["start_time"] is None: buffer["start_time"] = current_time
                    elif current_time - buffer["start_time"] >= 0.5:
                        if not buffer["active"]:
                            desc = {
                                "looking_side_to_side": "Candidate looking side to side or tilted",
                                "multiple_persons": "Multiple persons detected in frame",
                                "mobile_phone": "Mobile phone detected",
                                "prohibited_object": "Prohibited object detected"
                            }.get(alert_key, "Cheating violation detected")
                            alert = add_alert(alert_key, desc)
                            await websocket.send_json({"type": "alert", "data": alert})
                            buffer["active"] = True
                else:
                    if buffer["last_seen"] and current_time - buffer["last_seen"] > GRACE_PERIOD:
                        buffer["start_time"] = None
                        buffer["active"] = False
                if buffer["active"]: active_violations.append(alert_key)

            # --- 5. Final Encode and Send ---
            _, processed_buffer = cv2.imencode('.jpg', frame)
            processed_base64 = base64.b64encode(processed_buffer).decode('utf-8')
            
            try:
                await websocket.send_json({
                    "type": "frame", 
                    "data": processed_base64,
                    "active_violations": active_violations
                })
            except Exception: break

    except Exception as e:
        import traceback
        logger.error(f"Video processing error: {e}")
        logger.error(traceback.format_exc())
