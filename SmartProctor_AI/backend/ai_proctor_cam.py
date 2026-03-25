import cv2
import mediapipe as mp
import time
from datetime import datetime
import numpy as np

# --- CONFIGURATION & THRESHOLDS ---
YAW_RATIO_THRESHOLD = 0.25  # Side-look threshold (closer to 0 or 1 means side look)
FACE_SIZE_TOO_FAR = 45      # Min eye-to-eye distance (pixels)
FACE_SIZE_TOO_CLOSE = 110   # Max eye-to-eye distance (pixels)
GRACE_PERIOD_SEC = 1.0      # Persistence for alerts
LOG_FILE = "proctoring_alerts.log"

# Initialize MediaPipe
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=5,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

class AIProctor:
    def __init__(self):
        self.logs = []
        self.active_alerts = {}  # {type: start_time}
        self.last_alert_time = {} # {type: timestamp}
        
    def log_alert(self, alert_type):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {alert_type}"
        print(f"ALERT: {entry}")
        self.logs.append(entry)
        with open(LOG_FILE, "a") as f:
            f.write(entry + "\n")

    def get_face_metrics(self, face_landmarks, img_w, img_h):
        # 478-point mesh mapping:
        # 1: Nose Tip
        # 33: Left Eye Inner
        # 263: Right Eye Inner
        # 10, 152: Face Boundary Top/Bottom
        
        nose = face_landmarks.landmark[1]
        eye_l = face_landmarks.landmark[33]
        eye_r = face_landmarks.landmark[263]
        
        # 1. Yaw Ratio (Side Look)
        # Ratio of distance from nose to eyes horizontally
        # In centered face: (nose.x - eye_l.x) / (eye_r.x - eye_l.x) is approx 0.5
        denom = (eye_r.x - eye_l.x)
        yaw_ratio = (nose.x - eye_l.x) / denom if denom != 0 else 0.5
        
        # 2. Distance Proxy (Eye-to-Eye pixels)
        eye_dist = np.sqrt((eye_l.x - eye_r.x)**2 + (eye_l.y - eye_r.y)**2) * img_w
        
        # Bounding Box coordinates
        xs = [lm.x for lm in face_landmarks.landmark]
        ys = [lm.y for lm in face_landmarks.landmark]
        x_min, x_max = int(min(xs) * img_w), int(max(xs) * img_w)
        y_min, y_max = int(min(ys) * img_h), int(max(ys) * img_h)
        
        return yaw_ratio, eye_dist, (x_min, y_min, x_max, y_max)

    def run(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Error: Could not open webcam.")
            return

        print(f"AI Proctoring System Started. Logging to {LOG_FILE}")
        
        prev_time = time.time()
        
        while cap.isOpened():
            success, image = cap.read()
            if not success: break
            
            image = cv2.flip(image, 1)
            img_h, img_w, _ = image.shape
            curr_time = time.time()
            fps = 1 / (curr_time - prev_time)
            prev_time = curr_time
            
            # Process frame
            results = face_mesh.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            
            faces_detected = 0
            if results.multi_face_landmarks:
                faces_detected = len(results.multi_face_landmarks)
            
            # --- Violations Check ---
            violations = []
            
            if faces_detected == 0:
                violations.append("NO FACE DETECTED")
            elif faces_detected > 1:
                violations.append("MULTIPLE PERSONS DETECTED")
            else:
                # Single face logic
                face_lms = results.multi_face_landmarks[0]
                yaw, dist, bbox = self.get_face_metrics(face_lms, img_w, img_h)
                
                # Rule: Side Look
                if yaw < YAW_RATIO_THRESHOLD or yaw > (1 - YAW_RATIO_THRESHOLD):
                    violations.append("SIDE LOOK DETECTED")
                
                # Rule: Distance
                status_box = "FRAME OK"
                box_color = (0, 255, 0) # Normal: Green
                
                if dist < FACE_SIZE_TOO_FAR:
                    violations.append("TOO FAR FROM CAMERA")
                elif dist > FACE_SIZE_TOO_CLOSE:
                    violations.append("TOO CLOSE TO CAMERA")
                
                # Draw Primary Face UI
                if violations:
                    box_color = (0, 0, 255) # Violation: Red
                
                cv2.rectangle(image, (bbox[0], bbox[1]), (bbox[2], bbox[3]), box_color, 2)
                
                # Draw "FRAME OK" or Distance Status
                label = "FRAME OK" if not any(v in violations for v in ["TOO FAR FROM CAMERA", "TOO CLOSE TO CAMERA"]) else violations[0]
                cv2.putText(image, label, (bbox[0], bbox[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, box_color, 2)

            # --- UI Rendering for Screen-level Alerts ---
            # Pulse Red Screen for Multiple Persons or NO Face
            if "MULTIPLE PERSONS DETECTED" in violations or "NO FACE DETECTED" in violations:
                overlay = image.copy()
                cv2.rectangle(overlay, (0, 0), (img_w, img_h), (0, 0, 255), -1)
                alpha = 0.2 + 0.1 * np.sin(curr_time * 10) # Simple pulse
                image = cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0)
                
                banner_text = "SECURITY ALERT: " + violations[0]
                cv2.rectangle(image, (0, 0), (img_w, 60), (0, 0, 255), -1)
                cv2.putText(image, banner_text, (50, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3)

            # General Violations Text (Side look, distance, etc.)
            for i, v in enumerate(violations):
                # Log violation if it's new
                if v not in self.active_alerts:
                    self.log_alert(v)
                    self.active_alerts[v] = curr_time
                
                if v == "SIDE LOOK DETECTED":
                    cv2.putText(image, v, (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

            # Cleanup expired active alerts (for logging persistence)
            keys_to_remove = []
            for k in self.active_alerts:
                if k not in violations:
                    keys_to_remove.append(k)
            for k in keys_to_remove:
                del self.active_alerts[k]

            # Display FPS
            cv2.putText(image, f"FPS: {int(fps)}", (img_w - 120, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            
            # Show final frame
            cv2.imshow('AI Proctor Monitoring', image)
            
            if cv2.waitKey(5) & 0xFF == 27: # ESC to exit
                break
                
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    proctor = AIProctor()
    proctor.run()
