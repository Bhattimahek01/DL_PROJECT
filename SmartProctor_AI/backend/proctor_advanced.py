import cv2
import mediapipe as mp
import numpy as np
import time
from datetime import datetime

# --- CONFIGURATION & THRESHOLDS ---
YAW_THRESHOLD = 18       # Left/Right rotation in degrees
PITCH_THRESHOLD = 15     # Up/Down rotation in degrees
LOG_FILE = "proctor_advanced_logs.txt"

# MediaPipe Initialization
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=5,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5)

class AdvancedProctor:
    def __init__(self):
        self.logs = []
        # Standard 3D model points for face (in world coordinates)
        self.model_points = np.array([
            (0.0, 0.0, 0.0),             # Nose tip
            (0.0, -330.0, -65.0),        # Chin
            (-225.0, 170.0, -135.0),     # Left eye left corner
            (225.0, 170.0, -135.0),      # Right eye right corner
            (-150.0, -150.0, -125.0),    # Left Mouth corner
            (150.0, -150.0, -125.0)      # Right mouth corner
        ], dtype=np.float64)
        
        self.last_log_time = {} # For throttling log entries

    def log_event(self, event_type):
        now = time.time()
        # Only log once every 5 seconds for same type
        if event_type in self.last_log_time and now - self.last_log_time[event_type] < 5:
            return
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {event_type}"
        print(f"ALARM: {entry}")
        self.logs.append(entry)
        self.last_log_time[event_type] = now
        with open(LOG_FILE, "a") as f:
            f.write(entry + "\n")

    def get_head_pose(self, face_landmarks, img_w, img_h):
        # 2D Image mapping
        image_points = np.array([
            (face_landmarks.landmark[1].x * img_w, face_landmarks.landmark[1].y * img_h),     # Nose tip
            (face_landmarks.landmark[152].x * img_w, face_landmarks.landmark[152].y * img_h), # Chin
            (face_landmarks.landmark[33].x * img_w, face_landmarks.landmark[33].y * img_h),   # Left eye left corner
            (face_landmarks.landmark[263].x * img_w, face_landmarks.landmark[263].y * img_h), # Right eye right corner
            (face_landmarks.landmark[61].x * img_w, face_landmarks.landmark[61].y * img_h),   # Left mouth corner
            (face_landmarks.landmark[291].x * img_w, face_landmarks.landmark[291].y * img_h)  # Right mouth corner
        ], dtype=np.float64)

        # Camera matrix
        focal_length = img_w
        center = (img_w/2, img_h/2)
        camera_matrix = np.array(
            [[focal_length, 0, center[0]],
             [0, focal_length, center[1]],
             [0, 0, 1]], dtype=np.float64
        )

        dist_coeffs = np.zeros((4, 1)) # Assuming no lens distortion
        success, rotation_vector, translation_vector = cv2.solvePnP(self.model_points, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE)

        # Draw 3D axes
        axis_len = 200
        (nose_end_point2D, _) = cv2.projectPoints(np.array([(axis_len, 0, 0), (0, axis_len, 0), (0, 0, axis_len)], dtype=np.float64), rotation_vector, translation_vector, camera_matrix, dist_coeffs)
        
        # Get rotation matrix and Euler angles
        rmat, _ = cv2.Rodrigues(rotation_vector)
        angles, _, _, _, _, _ = cv2.decomposeProjectionMatrix(np.hstack((rmat, translation_vector)))
        
        # Convert to degrees
        pitch, yaw, roll = angles[0], angles[1], angles[2]
        
        # Mapping to intuitive directions
        pitch = np.clip(-pitch, -90, 90) # Up/Down
        yaw = np.clip(yaw, -90, 90)      # Left/Right
        
        return pitch, yaw, roll, image_points[0], nose_end_point2D

    def draw_3d_axes(self, image, center, axes_points):
        p_nose = tuple(map(int, center))
        p_x = tuple(map(int, axes_points[0].ravel()))
        p_y = tuple(map(int, axes_points[1].ravel()))
        p_z = tuple(map(int, axes_points[2].ravel()))
        
        cv2.line(image, p_nose, p_x, (0, 0, 255), 2) # X - Red
        cv2.line(image, p_nose, p_y, (0, 255, 0), 2) # Y - Green
        cv2.line(image, p_nose, p_z, (255, 0, 0), 2) # Z - Blue
        cv2.circle(image, p_nose, 4, (0, 255, 255), -1)

    def run(self):
        cap = cv2.VideoCapture(0)
        
        print(f"SmartProctor_AI Advanced 3D System Started. Logs: {LOG_FILE}")
        
        while cap.isOpened():
            success, image = cap.read()
            if not success: break
            
            image = cv2.flip(image, 1)
            img_h, img_w, _ = image.shape
            
            results = face_mesh.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            
            faces = len(results.multi_face_landmarks) if results.multi_face_landmarks else 0
            
            # --- Detection Logic ---
            violations = []
            
            if faces == 0:
                violations.append("NO FACE DETECTED")
                # Red overlay
                overlay = image.copy()
                cv2.rectangle(overlay, (0,0), (img_w, img_h), (0,0,255), -1)
                image = cv2.addWeighted(overlay, 0.3, image, 0.7, 0)
                cv2.putText(image, "NO FACE DETECTED", (img_w//2-150, img_h//2), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3)

            elif faces > 1:
                violations.append("MULTIPLE PERSONS DETECTED")
                # Pulsing red screen
                pulse = 0.2 + 0.2 * np.sin(time.time() * 10)
                overlay = image.copy()
                cv2.rectangle(overlay, (0,0), (img_w, img_h), (0,0,255), -1)
                image = cv2.addWeighted(overlay, pulse, image, 1-pulse, 0)
                cv2.putText(image, "!!!! WARNING: MULTIPLE PEOPLE !!!!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 4)

            else:
                lms = results.multi_face_landmarks[0]
                pitch, yaw, roll, nose_2d, axes_2d = self.get_head_pose(lms, img_w, img_h)
                
                # Rules
                status = "FOCUSED / FRAME OK"
                box_color = (0, 255, 0) # Green
                
                # Check Side Look (Yaw)
                if yaw > YAW_THRESHOLD:
                    status = "LOOKING LEFT"
                    violations.append("SIDE LOOK DETECTED")
                    box_color = (0, 0, 255)
                elif yaw < -YAW_THRESHOLD:
                    status = "LOOKING RIGHT"
                    violations.append("SIDE LOOK DETECTED")
                    box_color = (0, 0, 255)
                    
                # Check Up/Down (Pitch)
                if pitch > PITCH_THRESHOLD:
                    status = "LOOKING UP"
                    violations.append("PITCH VIOLATION")
                elif pitch < -PITCH_THRESHOLD:
                    status = "LOOKING DOWN"
                    violations.append("PITCH VIOLATION")

                # Distance Estimate (based on bounding box)
                xs = [lm.x for lm in lms.landmark]
                ys = [lm.y for lm in lms.landmark]
                x1, y1, x2, y2 = int(min(xs)*img_w), int(min(ys)*img_h), int(max(xs)*img_w), int(max(ys)*img_h)
                face_width = x2 - x1
                
                dist_label = "OPTIMAL DISTANCE"
                if face_width < 120: dist_label = "TOO FAR"; violations.append("DIST VIOLATION")
                elif face_width > 280: dist_label = "TOO CLOSE"; violations.append("DIST VIOLATION")
                
                # DRAW UI
                cv2.rectangle(image, (x1, y1), (x2, y2), box_color, 2)
                cv2.putText(image, f"{status} | {dist_label}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, box_color, 2)
                
                # Show Angles
                cv2.putText(image, f"Yaw: {int(yaw)} deg", (img_w-180, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                cv2.putText(image, f"Pitch: {int(pitch)} deg", (img_w-180, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                cv2.putText(image, f"Roll: {int(roll)} deg", (img_w-180, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

                # Visual 3D helpers
                self.draw_3d_axes(image, nose_2d, axes_2d)
                
                # Direction line
                p1 = tuple(map(int, nose_2d))
                p2 = tuple(map(int, axes_2d[2].ravel())) # Z axis is forward
                cv2.arrowedLine(image, p1, p2, (255, 255, 255), 2)

            # Log any active violations
            for v in violations:
                self.log_event(v)

            # Final rendering
            cv2.imshow('SmartProctor_AI - Advanced 3D Monitoring', image)
            if cv2.waitKey(5) & 0xFF == 27: break
                
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    proctor = AdvancedProctor()
    proctor.run()
