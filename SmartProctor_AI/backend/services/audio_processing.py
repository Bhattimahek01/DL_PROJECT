import base64
import numpy as np
import asyncio
from utils.alerts import add_alert

# Configuration
THRESHOLD = 3.0 # Required volume to trigger an alert
SAMPLING_RATE = 16000
BLOCK_SIZE = 8000 # 0.5 seconds of audio buffer

async def process_audio_feed(websocket):
    try:
        while True:
            # Receive audio chunk from frontend via WebSocket
            data = await websocket.receive_json()
            if data['type'] != 'audio':
                continue
            
            # Assuming frontend sends audio as base64 encoded float32 array
            audio_base64 = data['data']
            audio_bytes = base64.b64decode(audio_base64)
            audio_chunk = np.frombuffer(audio_bytes, dtype=np.float32)

            if len(audio_chunk) == 0:
                continue
            
            volume_norm = np.linalg.norm(audio_chunk) * 10
            if volume_norm > THRESHOLD:
                alert = add_alert("talking", f"Suspicious talking/noise detected. Vol: {volume_norm:.1f}")
                try:
                    await websocket.send_json({"type": "alert", "data": alert})
                except Exception:
                    break # Websocket disconnected

    except Exception as e:
        print(f"Audio processing error: {e}")
