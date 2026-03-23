# SmartProctor AI – Intelligent Exam Hall Monitoring System

SmartProctor AI is a full-stack project designed to monitor exam halls and detect cheating behaviors using computer vision and audio analysis. The system uses a Python (FastAPI + YOLOv8) backend for real-time inference and a React (Vite + Tailwind CSS) frontend for live monitoring.

## Features
- **Computer Vision**: Detects multiple persons and mobile phones using YOLOv8.
- **Audio Analysis**: Monitors ambient noise through the microphone to spot suspicious talking behaviors.
- **Live Dashboard**: A premium, real-time React dashboard streaming webcam data and alerts via WebSockets.
- **Cheating Logs**: Keeps a history of anomalous events detected during the exam session.

---

## 🚀 Setup Instructions

### 1. Prerequisites
- Python 3.9+
- Node.js 18+
- Active Webcam & Microphone connected to the host machine.

### 2. Backend Setup
1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment (recommended):
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the FastAPI server:
   ```bash
   uvicorn main:app --reload
   ```
   > The server will start on `http://127.0.0.1:8000`. By default, YOLOv8 (`yolov8n.pt`) may be downloaded on the first run. The system will immediately attempt to access your default webcam and microphone.

### 3. Frontend Setup
1. Open a new terminal and navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   > The React app will usually be available at `http://localhost:5173`. Open this URL in your browser to view the Live Proctoring feed!

---

## 🛠️ Tech Stack
- **Backend API**: FastAPI, Uvicorn, Python
- **AI Models**: Ultralytics YOLOv8 (PyTorch)
- **Computer Vision**: OpenCV
- **Audio Processing**: SoundDevice, NumPy
- **Frontend App**: React, Vite, Tailwind CSS, Lucide Icons

## 📝 License
This project is open source and available for educational purposes.
