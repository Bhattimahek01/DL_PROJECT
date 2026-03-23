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

    # Get identity baseline from session
    from utils.alerts import get_session
    session = get_session()
    
    try:
        while True:
            # Receive frame from frontend via WebSocket
            data = await websocket.receive_json()
            if data['type'] != 'frame':
                continue
                
            frame_base64 = data['data']
            frame_bytes = base64.b64decode(frame_base64)
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is None:
                continue

            current_time = time.time()
            img_h, img_w, _ = frame.shape
            
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
                    buffer["last_seen"] = current_time
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
                    if buffer["last_seen"] and current_time - buffer["last_seen"] > GRACE_PERIOD:
                        buffer["start_time"] = None
                        buffer["active"] = False

            # Encode and send proccessed frame back (optional, for debugging/feedback)
            _, processed_buffer = cv2.imencode('.jpg', frame)
            processed_base64 = base64.b64encode(processed_buffer).decode('utf-8')
            
            try:
                await websocket.send_json({"type": "frame", "data": processed_base64})
            except Exception:
                break

    except Exception as e:
        print(f"Video processing error: {e}")
