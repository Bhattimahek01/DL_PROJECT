from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from datetime import datetime

from services.video_processing import process_video_feed
from services.audio_processing import process_audio_feed
from utils.alerts import get_logs, get_status, reset_status, start_session, get_session

app = FastAPI(title="SmartProctor AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/status")
def status():
    return get_status()

@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/api/logs")
def logs():
    return {"logs": get_logs()}

@app.post("/api/session/start")
def session_start(data: dict):
    return start_session(data)

@app.get("/api/session")
def session_get():
    return get_session()

@app.post("/api/reset")
def reset():
    reset_status()
    # Also clear reports
    import os
    if os.path.exists("reports"):
        for f in os.listdir("reports"):
            try:
                os.remove(os.path.join("reports", f))
            except: pass
    return {"message": "Status reset locally."}

@app.get("/api/report/download")
def download_report():
    from fastapi.responses import FileResponse
    from utils.report_generator import generate_pdf_report
    import os
    
    session = get_session()
    logs = get_logs()
    
    if not session:
        return {"error": "No active session found"}
    
    # Create report filename
    report_filename = f"report_{session.get('candidateId', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    report_path = os.path.join("reports", report_filename)
    
    try:
        generate_pdf_report(session, logs, report_path)
        return FileResponse(path=report_path, filename=report_filename, media_type='application/pdf')
    except Exception as e:
        return {"error": f"Failed to generate report: {str(e)}"}

@app.websocket("/ws/video")
async def websocket_video(websocket: WebSocket):
    await websocket.accept()
    print("Video WebSocket connected")
    try:
        await process_video_feed(websocket)
    except WebSocketDisconnect:
        print("Video WebSocket disconnected")
    except Exception as e:
        print(f"Error in video feed: {e}")

@app.websocket("/ws/audio")
async def websocket_audio(websocket: WebSocket):
    await websocket.accept()
    print("Audio WebSocket connected")
    try:
        await process_audio_feed(websocket)
    except WebSocketDisconnect:
        print("Audio WebSocket disconnected")
    except Exception as e:
        print(f"Error in audio feed: {e}")
