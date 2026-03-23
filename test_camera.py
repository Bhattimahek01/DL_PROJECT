import cv2
import time

print("Testing camera behavior when turned off...")

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Camera not available")
    exit()

print("Camera opened successfully. Reading frames...")

for i in range(20):
    success, frame = cap.read()
    current_time = time.time()

    if frame is not None:
        print(f"Frame {i}: success={success}, shape={frame.shape}, size={frame.size}")
    else:
        print(f"Frame {i}: success={success}, frame=None")

    time.sleep(0.1)

print("Test complete. Now turn off camera and run again.")
cap.release()