from datetime import datetime

cheating_logs = []
current_session = None
current_status = {"status": "normal", "description": "No cheating detected"}

def add_alert(alert_type: str, description: str):
    global current_status
    log_entry = {
        "id": len(cheating_logs) + 1,
        "timestamp": datetime.now().isoformat(),
        "type": alert_type,
        "description": description
    }
    cheating_logs.append(log_entry)
    current_status = {"status": "alert", "description": description}
    return log_entry

def get_logs():
    return cheating_logs

def get_status():
    return current_status

def reset_status():
    global current_status, current_session, cheating_logs
    current_status = {"status": "normal", "description": "No cheating detected"}
    current_session = None
    cheating_logs = []

def start_session(session_data: dict):
    global current_session, cheating_logs
    current_session = session_data
    cheating_logs = [] # Clear logs for new session
    return {"message": "Session started", "session": current_session}

def get_session():
    return current_session
