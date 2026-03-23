import sounddevice as sd
import numpy as np
import asyncio
from utils.alerts import add_alert

# Configuration
THRESHOLD = 3.0 # Required volume to trigger an alert
SAMPLING_RATE = 16000
BLOCK_SIZE = 8000 # 0.5 seconds of audio buffer

class AudioMonitor:
    def __init__(self, loop, queue):
        self.loop = loop
        self.queue = queue

    def callback(self, indata, frames, time, status):
        if status:
            print(f"Audio status: {status}")
            
        volume_norm = np.linalg.norm(indata) * 10
        if volume_norm > THRESHOLD:
            if not self.loop.is_closed():
                # Schedule queue update on asyncio thread
                self.loop.call_soon_threadsafe(self.queue.put_nowait, {
                    "type": "audio",
                    "volume": float(volume_norm)
                })

async def process_audio_feed(websocket):
    loop = asyncio.get_running_loop()
    audio_queue = asyncio.Queue()
    monitor = AudioMonitor(loop, audio_queue)
    
    stream = sd.InputStream(callback=monitor.callback, channels=1, samplerate=SAMPLING_RATE, blocksize=BLOCK_SIZE)
    with stream:
        try:
            while True:
                # This explicitly blocks until there's an alert
                alert_data = await audio_queue.get()
                alert = add_alert("talking", f"Suspicious talking/noise detected. Vol: {alert_data['volume']:.1f}")
                
                try:
                    await websocket.send_json({"type": "alert", "data": alert})
                except Exception:
                    break # Websocket disconnected
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Audio processing error: {e}")
