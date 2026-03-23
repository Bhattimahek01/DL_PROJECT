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

# Mediapipe Face Landmarker setup
# We'll need the task file. I'll download it if it doesn't exist.
MODEL_PATH = 'face_landmarker.task'

# Note: In a real environment, you'd download this from:
# https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task

def setup_face_landmarker():
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        output_face_blendshapes=True,
        output_facial_transformation_matrixes=True,
        num_faces=1)
    detector = vision.FaceLandmarker.create_from_options(options)
    return detector

def get_head_pose_from_matrix(matrix):
    # The transformation matrix provides the 4x4 matrix
    # We can extract Euler angles from it
    # For now, let's simplify and use the rotation components
    # matrix is 4x4
    rmat = matrix[:3, :3]
    
    # Calculate euler angles
    sy = np.sqrt(rmat[0,0] * rmat[0,0] +  rmat[1,0] * rmat[1,0])
    singular = sy < 1e-6

    if not singular:
        x = np.arctan2(rmat[2,1], rmat[2,2])
        y = np.arctan2(-rmat[2,0], sy)
        z = np.arctan2(rmat[1,0], rmat[0,0])
    else:
        x = np.arctan2(-rmat[1,2], rmat[1,1])
        y = np.arctan2(-rmat[2,0], sy)
        z = 0

    # Convert to degrees
    return np.rad2deg(x), np.rad2deg(y), np.rad2deg(z)

def is_blurry(image, threshold=50):
    """
    Detects if the image is blurry using Laplacian variance.
    Lower threshold means more sensitive (detects even slight blur).
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    fm = cv2.Laplacian(gray, cv2.CV_64F).var()
    return fm < threshold, fm

import time

# Thresholds for smoothing (seconds)
DETECTION_THRESHOLD_SEC = 2.0 

# State for temporal smoothing
alert_buffers = {
    "looking_side_to_side": {"start_time": None, "active": False, "last_seen": 0},
    "multiple_persons": {"start_time": None, "active": False},
    "mobile_phone": {"start_time": None, "active": False},
    "prohibited_object": {"start_time": None, "active": False},
    "camera_off": {"start_time": None, "active": False}
}

async def process_video_feed(websocket):
    from ultralytics import YOLO
    yolo_model = YOLO('yolov8n.pt')
    
    if not os.path.exists(MODEL_PATH):
        print(f"Warning: {MODEL_PATH} not found. Head pose detection will be disabled.")
        detector = None
    else:
        try:
            detector = setup_face_landmarker()
        except Exception as e:
            print(f"Error setting up Face Landmarker: {e}")
            detector = None

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    # Camera status tracking
    last_frame_time = time.time()
    camera_off_start_time = None
    consecutive_failures = 0
    MAX_CONSECUTIVE_FAILURES = 3  # Reduced threshold for faster detection
    last_camera_check = time.time()
    CAMERA_CHECK_INTERVAL = 1.0  # Check more frequently
    last_frame_hash = None
    identical_frame_count = 0
    MAX_IDENTICAL_FRAMES = 5  # If we get 5 identical frames, camera might be off

    # Get identity baseline from session
    from utils.alerts import get_session
    session = get_session()
    
    try:
        while True:
            current_time = time.time()
            
            # Periodic camera health check
            if current_time - last_camera_check >= CAMERA_CHECK_INTERVAL:
                if not cap.isOpened():
                    print("Camera connection lost - attempting reconnection...")
                    cap.release()
                    cap = cv2.VideoCapture(0)
                    if not cap.isOpened():
                        print("Failed to reconnect camera")
                last_camera_check = current_time
            
            success, frame = cap.read()
            
            # Debug: Print frame info
            if frame is not None:
                print(f"Frame received: success={success}, shape={frame.shape if hasattr(frame, 'shape') else 'no shape'}, size={frame.size if hasattr(frame, 'size') else 'no size'}")
            else:
                print(f"Frame received: success={success}, frame=None")
            
            # Check if frame is valid and not identical to previous frames
            frame_is_valid = True
            if not success or frame is None or frame.size == 0 or (hasattr(frame, 'shape') and (frame.shape[0] == 0 or frame.shape[1] == 0)):
                frame_is_valid = False
                consecutive_failures += 1
                print(f"Warning: Could not read valid frame from webcam (failure {consecutive_failures}/{MAX_CONSECUTIVE_FAILURES})")
            else:
                # Check if frame is all black (camera covered or off)
                if frame is not None:
                    # Check if frame is mostly black (camera covered/off)
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    mean_brightness = cv2.mean(gray)[0]
                    variance = np.var(gray)
                    
                    if mean_brightness < 15 or variance < 5:  # Catch dark or flat frames
                        frame_is_valid = False
                        consecutive_failures += 1
                        print(f"CRITICAL: Low health frame (Bright: {mean_brightness:.2f}, Var: {variance:.2f})")
                    
                    # Check for blur
                    blurry, focus_measure = is_blurry(frame)
                    if blurry and frame_is_valid: # Only check blur if not already dark
                        frame_is_valid = False
                        consecutive_failures += 1
                        print(f"CRITICAL: Camera is all blur (focus: {focus_measure:.2f})")

                    # Check for identical frames (camera frozen)
                    frame_hash = hashlib.md5(frame.tobytes()).hexdigest()
                    if last_frame_hash == frame_hash:
                        identical_frame_count += 1
                        if identical_frame_count >= MAX_IDENTICAL_FRAMES:
                            frame_is_valid = False
                            consecutive_failures += 1
                            print(f"CRITICAL: Identical frames detected ({identical_frame_count} times) - camera frozen")
                    else:
                        if frame_is_valid: # Only reset if frame is truly healthy
                            identical_frame_count = 0
                            last_frame_hash = frame_hash
                            consecutive_failures = 0 
            
            if not frame_is_valid and consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                # Camera is considered off
                if camera_off_start_time is None:
                    camera_off_start_time = current_time
                    print(f"Camera off detection started at {current_time}")
                elif current_time - camera_off_start_time >= DETECTION_THRESHOLD_SEC:
                    buffer = alert_buffers["camera_off"]
                    if not buffer["active"]:
                        print("TRIGGERING CAMERA OFF ALERT!")
                        alert = add_alert("camera_off", "CRITICAL VIOLATION: Camera tampering detected - exam terminated")
                        print(f"Alert created: {alert}")
                        await websocket.send_json({"type": "alert", "data": alert})
                        # Send termination signal
                        await websocket.send_json({"type": "termination", "reason": "camera_off", "message": "Exam terminated due to camera tampering"})
                        print("Termination signal sent via WebSocket")
                        buffer["active"] = True
                        buffer["start_time"] = current_time
                    
                    # Send a black frame to indicate camera is off
                    black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(black_frame, "CAMERA OFF", (180, 220), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
                    cv2.putText(black_frame, "Please check camera connection", (120, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
                    _, buffer = cv2.imencode('.jpg', black_frame)
                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                    
                    try:
                        await websocket.send_json({"type": "frame", "data": frame_base64})
                    except Exception:
                        break
                    
                    await asyncio.sleep(0.1)
                    continue
            else:
                # Camera is working - reset all failure counters and camera off status
                consecutive_failures = 0
                identical_frame_count = 0
                camera_off_start_time = None
                alert_buffers["camera_off"]["start_time"] = None
                alert_buffers["camera_off"]["active"] = False
                last_frame_time = current_time
                last_camera_check = current_time

            img_h, img_w, _ = frame.shape
            current_time = time.time()
            
            # Reset frame-level detection flags
            detections_this_frame = {
                "looking_side_to_side": False,
                "multiple_persons": False,
                "mobile_phone": False,
                "prohibited_object": False
            }

            # 1. Mediapipe Head Pose
            if detector:
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                detection_result = detector.detect(mp_image)
                
                if detection_result.facial_transformation_matrixes:
                    for i, matrix in enumerate(detection_result.facial_transformation_matrixes):
                        pitch, yaw, roll = get_head_pose_from_matrix(matrix)
                        
                        # Looking side to side (Yaw focus)
                        if abs(yaw) > 20:
                            detections_this_frame["looking_side_to_side"] = True
                            cv2.putText(frame, "Looking Side!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

                # Background Person Detection
                if len(detection_result.face_landmarks) > 1:
                    detections_this_frame["multiple_persons"] = True
                    cv2.putText(frame, "MULTIPLE FACES!", (50, 130), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

            # 2. YOLOv8 inference
            results_yolo = yolo_model(frame, stream=True, verbose=False)
            
            person_count = 0
            for r in results_yolo:
                boxes = r.boxes
                for box in boxes:
                    conf = float(box.conf[0])
                    cls = int(box.cls[0])
                    class_name = yolo_model.names[cls]
                    
                    if conf > 0.4:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        
                        if class_name == 'person':
                            person_count += 1
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        elif class_name == 'cell phone':
                            detections_this_frame["mobile_phone"] = True
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                        elif class_name in ['book', 'laptop']:
                            detections_this_frame["prohibited_object"] = True
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 165, 0), 2)
                        
                        cv2.putText(frame, f'{class_name} {conf:.2f}', (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

            if person_count > 1:
                detections_this_frame["multiple_persons"] = True

            # 3. Temporal Smoothing and Alert logic
            GRACE_PERIOD = 0.5 # seconds
            for alert_key, is_detected in detections_this_frame.items():
                buffer = alert_buffers[alert_key]
                
                if is_detected:
                    buffer["last_seen"] = current_time if "last_seen" in buffer else 0
                    if buffer["start_time"] is None:
                        buffer["start_time"] = current_time # Start the timer
                    elif current_time - buffer["start_time"] >= (1.5 if alert_key == "looking_side_to_side" else DETECTION_THRESHOLD_SEC):
                        if not buffer["active"]:
                            # TRIGGER ALERT
                            description = {
                                "looking_side_to_side": "Candidate frequently looking side to side",
                                "multiple_persons": "Multiple persons/faces detected in frame",
                                "mobile_phone": "Mobile phone detected in frame",
                                "prohibited_object": "Prohibited object detected"
                            }[alert_key]
                            
                            print(f"TRIGGERING ALERT: {alert_key}")
                            alert = add_alert(alert_key, description)
                            await websocket.send_json({"type": "alert", "data": alert})
                            buffer["active"] = True
                else:
                    # Only reset if we haven't seen the violation for more than the grace period
                    if "last_seen" in buffer:
                        if current_time - buffer["last_seen"] > GRACE_PERIOD:
                            buffer["start_time"] = None
                            buffer["active"] = False
                    else:
                        buffer["start_time"] = None
                        buffer["active"] = False

            # Encode and send frame
            _, buffer = cv2.imencode('.jpg', frame)
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            try:
                await websocket.send_json({"type": "frame", "data": frame_base64})
            except Exception:
                break
            
            await asyncio.sleep(0.05)

    except Exception as e:
        print(f"Video processing error: {e}")
    finally:
        cap.release()
