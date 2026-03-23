import sounddevice as sd
import numpy as np

print("Testing Audio Input...")
print("Available Devices:")
print(sd.query_devices())

def callback(indata, frames, time, status):
    volume_norm = np.linalg.norm(indata) * 10
    if volume_norm > 0:
        print(f"Volume: {volume_norm:.2f}")

try:
    with sd.InputStream(callback=callback, channels=1, samplerate=16000, blocksize=8000):
        print("Recording for 5 seconds... (make some noise!)")
        sd.sleep(5000)
except Exception as e:
    print(f"Audio error: {e}")
