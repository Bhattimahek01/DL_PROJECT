import React, { useState, useEffect, useCallback, useMemo } from 'react';
import LiveCamera from './components/LiveCamera';
import AlertPanel from './components/AlertPanel';
import StatusDashboard from './components/StatusDashboard';
import CheatingLogs from './components/CheatingLogs';
import RegistrationForm from './components/RegistrationForm';
import { ShieldAlert, User, Clock, Monitor } from 'lucide-react';

const MAX_ALERTS = 50;

function App() {
  const [alerts, setAlerts] = useState([]);
  const [videoFrame, setVideoFrame] = useState(null);
  const [status, setStatus] = useState({ status: 'normal', description: 'No cheating detected' });
  const [isSuspended, setIsSuspended] = useState(false);
  const [sessionActive, setSessionActive] = useState(false);
  const [examConfig, setExamConfig] = useState(null);
  const [remainingSeconds, setRemainingSeconds] = useState(0);
  const [localStream, setLocalStream] = useState(null);

  const [suspensionReason, setSuspensionReason] = useState('');
  
  // Memoized alert handler to be used in visibility change listener
  const handleNewAlert = useCallback((alert) => {
    setAlerts((prev) => {
      const newAlerts = [alert, ...prev];
      
      // IMMEDIATE TERMINATION for camera off violations
      if (alert.type === 'camera_off') {
        setIsSuspended(true);
        setSuspensionReason('EXAM TERMINATED: Camera tampering detected. Exam session ended immediately.');
        setStatus({ status: 'terminated', description: 'Exam terminated due to camera violation' });
        // Close WebSocket connections to stop monitoring
        return newAlerts;
      }
      
      // Suspension after 8 general violations (Previously rule 1 was immediate termination for side-look)
      if (newAlerts.length >= MAX_ALERTS) {
          setIsSuspended(true);
          setSuspensionReason(`Terminated: ${MAX_ALERTS} violations reached.`);
          setStatus({ status: 'suspended', description: 'Exam suspended' });
      } else {
          setStatus({ status: 'alert', description: alert.description });
      }
      return newAlerts;
    });
  }, []);

  // WebSockets and Media Streaming setup
  useEffect(() => {
    if (!sessionActive || isSuspended) return;

    const rawBase = import.meta.env.VITE_API_BASE_URL || '127.0.0.1:8000';
    // Clean the base URL: remove protocols and trailing slashes
    const API_BASE = rawBase.replace(/^https?:\/\//, '').replace(/\/$/, '');
    const WS_PROTOCOL = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    
    console.log(`Connecting to Video WS: ${WS_PROTOCOL}//${API_BASE}/ws/video`);
    const videoWs = new WebSocket(`${WS_PROTOCOL}//${API_BASE}/ws/video`);
    const audioWs = new WebSocket(`${WS_PROTOCOL}//${API_BASE}/ws/audio`);

    videoWs.onerror = (err) => console.error("Video WebSocket Error:", err);
    audioWs.onerror = (err) => console.error("Audio WebSocket Error:", err);

    let stream = null;
    let videoInterval = null;
    let audioProcessor = null;
    let audioContext = null;

    const startStreaming = async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ 
            video: { width: 640, height: 480, frameRate: 10 }, 
            audio: true 
        });
        setLocalStream(stream);

        // --- Video Streaming ---
        const video = document.createElement('video');
        video.srcObject = stream;
        video.play();

        const canvas = document.createElement('canvas');
        canvas.width = 640;
        canvas.height = 480;
        const ctx = canvas.getContext('2d');

        videoInterval = setInterval(() => {
          if (videoWs.readyState === WebSocket.OPEN) {
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            const base64Frame = canvas.toDataURL('image/jpeg', 0.5).split(',')[1];
            videoWs.send(JSON.stringify({ type: 'frame', data: base64Frame }));
          }
        }, 200); // 5 FPS

        // --- Audio Streaming ---
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const source = audioContext.createMediaStreamSource(stream);
        audioProcessor = audioContext.createScriptProcessor(4096, 1, 1);

        source.connect(audioProcessor);
        audioProcessor.connect(audioContext.destination);

        audioProcessor.onaudioprocess = (e) => {
          if (audioWs.readyState === WebSocket.OPEN) {
            const inputData = e.inputBuffer.getChannelData(0);
            
            // Safer way to convert float32 array to base64
            // Avoids stack overflow for large buffers
            const uint8Array = new Uint8Array(inputData.buffer);
            let binary = '';
            for (let i = 0; i < uint8Array.byteLength; i++) {
                binary += String.fromCharCode(uint8Array[i]);
            }
            const base64Audio = btoa(binary);
            audioWs.send(JSON.stringify({ type: 'audio', data: base64Audio }));
          }
        };

      } catch (err) {
        console.error("Error accessing media devices:", err);
        alert("Please allow camera and microphone access to continue the exam.");
        setIsSuspended(true);
        setSuspensionReason("Media access denied.");
      }
    };

    videoWs.onopen = () => {
        console.log("Video WebSocket connected");
        startStreaming();
    };

    videoWs.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'frame') {
          setVideoFrame(`data:image/jpeg;base64,${data.data}`);
        } else if (data.type === 'alert') {
          handleNewAlert(data.data);
        } else if (data.type === 'termination') {
          setIsSuspended(true);
          setSuspensionReason(`EXAM TERMINATED: ${data.message}`);
          setStatus({ status: 'terminated', description: 'Exam terminated due to critical violation' });
          videoWs.close();
          audioWs.close();
        }
      } catch (e) {
        console.error("Frame processing error", e);
      }
    };

    audioWs.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'alert') {
          handleNewAlert(data.data);
        }
      } catch (e) {
        console.error("Audio processing error", e);
      }
    };

    return () => {
      if (videoInterval) clearInterval(videoInterval);
      if (audioProcessor) audioProcessor.disconnect();
      if (audioContext) audioContext.close();
      if (stream) stream.getTracks().forEach(track => track.stop());
      setLocalStream(null);
      videoWs.close();
      audioWs.close();
    };
  }, [sessionActive, isSuspended, handleNewAlert]);

  // Tab & Keyboard Monitoring
  useEffect(() => {
    if (!sessionActive || isSuspended) return;

    const handleVisibilityChange = () => {
      if (document.hidden) {
        const tabAlert = {
            id: Date.now(),
            timestamp: new Date().toISOString(),
            type: 'tab_switch',
            description: 'Tab switch or window minimization detected'
        };
        handleNewAlert(tabAlert);
      }
    };

    const handleKeyDown = (e) => {
        // PrintScreen detection
        if (e.key === 'PrintScreen') {
          const screenAlert = {
              id: Date.now(),
              timestamp: new Date().toISOString(),
              type: 'screenshot',
              description: 'WARNING: Trying to take a screenshot!'
          };
          handleNewAlert(screenAlert);
          alert("SECURITY ALERT: Screenshotting is prohibited! This incident has been logged.");
        }
        
        // Prevent F12, Ctrl+Shift+I, etc.
        if (e.key === 'F12' || (e.ctrlKey && e.shiftKey && e.key === 'I')) {
            e.preventDefault();
            const devAlert = {
              id: Date.now(),
              timestamp: new Date().toISOString(),
              type: 'dev_tools',
              description: 'Unauthorized access to Developer Tools attempt'
          };
          handleNewAlert(devAlert);
        }

        // Ctrl+P (Print) detection
        if (e.ctrlKey && (e.key === 'p' || e.key === 'P')) {
            e.preventDefault();
            const printAlert = {
                id: Date.now(),
                timestamp: new Date().toISOString(),
                type: 'printing',
                description: 'SECURITY ALERT: Unauthorized attempt to print the page!'
            };
            handleNewAlert(printAlert);
            alert("SECURITY ALERT: Printing is strictly prohibited! This event has been logged.");
        }
    };

    const handleCopy = (e) => {
        const copyAlert = {
            id: Date.now(),
            timestamp: new Date().toISOString(),
            type: 'copy_paste',
            description: 'Unauthorized content copy detected'
        };
        handleNewAlert(copyAlert);
        alert("SECURITY ALERT: Copying content is prohibited!");
    };

    const handlePaste = (e) => {
        e.preventDefault();
        const pasteAlert = {
            id: Date.now(),
            timestamp: new Date().toISOString(),
            type: 'copy_paste',
            description: 'Unauthorized content paste attempt'
        };
        handleNewAlert(pasteAlert);
        alert("SECURITY ALERT: Pasting content is not allowed!");
    };

    const handleContextMenu = (e) => {
        e.preventDefault();
        return false;
    };

    const handleBlur = () => {
        const blurAlert = {
            id: Date.now(),
            timestamp: new Date().toISOString(),
            type: 'tab_switch',
            description: 'Security Warning: Browser focus lost'
        };
        handleNewAlert(blurAlert);
    };

    const handleDragStart = (e) => {
        e.preventDefault();
        return false;
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('copy', handleCopy);
    window.addEventListener('paste', handlePaste);
    window.addEventListener('contextmenu', handleContextMenu);
    window.addEventListener('blur', handleBlur);
    window.addEventListener('dragstart', handleDragStart);
    
    return () => {
        document.removeEventListener('visibilitychange', handleVisibilityChange);
        window.removeEventListener('keydown', handleKeyDown);
        window.removeEventListener('copy', handleCopy);
        window.removeEventListener('paste', handlePaste);
        window.removeEventListener('contextmenu', handleContextMenu);
        window.removeEventListener('blur', handleBlur);
        window.removeEventListener('dragstart', handleDragStart);
    };
  }, [sessionActive, isSuspended, handleNewAlert]);

  // Timer logic
  useEffect(() => {
    if (!sessionActive || remainingSeconds <= 0 || isSuspended) return;
    const interval = setInterval(() => {
      setRemainingSeconds((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, [sessionActive, remainingSeconds, isSuspended]);

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  };

  const handleStartSession = async (config) => {
    const rawBase = import.meta.env.VITE_API_BASE_URL || '127.0.0.1:8000';
    const API_BASE = rawBase.replace(/^https?:\/\//, '').replace(/\/$/, '');
    const HTTP_PROTOCOL = window.location.protocol === 'https:' ? 'https:' : 'http:';

    console.log(`Starting session at: ${HTTP_PROTOCOL}//${API_BASE}/api/session/start`);
    try {
      await fetch(`${HTTP_PROTOCOL}//${API_BASE}/api/session/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      setExamConfig(config);
      setRemainingSeconds(config.durationMinutes * 60);
      setSessionActive(true);
      setAlerts([]);
      setIsSuspended(false);
      setSuspensionReason('');
      setStatus({ status: 'normal', description: 'No cheating detected' });
    } catch (e) {
      console.error("Failed to start session on backend", e);
      alert("Backend not reachable. Start the FastAPI server first.");
    }
  };

  const resetExam = () => {
    setAlerts([]);
    setIsSuspended(false);
    setSuspensionReason('');
    setSessionActive(false);
    setExamConfig(null);
    resetStatusOnBackend(); // Notify backend to reset
    setStatus({ status: 'normal', description: 'No cheating detected' });
    setVideoFrame(null);
    setLocalStream(null);
  };

  const resetStatusOnBackend = async () => {
    const rawBase = import.meta.env.VITE_API_BASE_URL || '127.0.0.1:8000';
    const API_BASE = rawBase.replace(/^https?:\/\//, '').replace(/\/$/, '');
    const HTTP_PROTOCOL = window.location.protocol === 'https:' ? 'https:' : 'http:';
    try {
        await fetch(`${HTTP_PROTOCOL}//${API_BASE}/api/reset`, { method: 'POST' });
    } catch (e) { console.error("Failed to reset backend", e); }
  };

  const downloadReport = async () => {
    const rawBase = import.meta.env.VITE_API_BASE_URL || '127.0.0.1:8000';
    const API_BASE = rawBase.replace(/^https?:\/\//, '').replace(/\/$/, '');
    const HTTP_PROTOCOL = window.location.protocol === 'https:' ? 'https:' : 'http:';
    
    try {
      const response = await fetch(`${HTTP_PROTOCOL}//${API_BASE}/api/report/download`);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Proctoring_Report_${examConfig?.candidateId || 'Session'}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      } else {
        alert("Report not available yet or session not found.");
      }
    } catch (e) {
      console.error("Failed to download report", e);
      alert("Error downloading report.");
    }
  };

  if (isSuspended) {
    const isTerminated = status.status === 'terminated';
    return (
      <div className="min-h-screen bg-slate-900 text-slate-100 flex items-center justify-center p-6">
        <div className={`border-2 p-12 rounded-2xl shadow-2xl max-w-2xl w-full text-center flex flex-col items-center gap-6 animate-in fade-in zoom-in duration-300 ${
          isTerminated ? 'bg-red-900/20 border-red-500/50' : 'bg-slate-800 border-red-500/30'
        }`}>
           <div className={`p-6 rounded-full ${isTerminated ? 'bg-red-600/30' : 'bg-red-500/20'}`}>
            <ShieldAlert className={`w-20 h-20 ${isTerminated ? 'text-red-400' : 'text-red-500'}`} />
           </div>
           <h1 className={`text-4xl font-bold ${isTerminated ? 'text-red-300' : 'text-white'}`}>
             {isTerminated ? 'Exam Terminated' : 'Exam Suspended'}
           </h1>
           <p className="text-xl text-red-400 font-semibold">{suspensionReason}</p>
           <p className="text-slate-300 leading-relaxed">
             {isTerminated 
               ? 'This exam session has been permanently terminated due to critical violations. All activities were recorded and reported.'
               : 'This session has been suspended. Contact your proctor for further instructions.'
             }
           </p>
           <div className="w-full bg-slate-900/50 p-4 rounded-lg text-left border border-slate-700 mt-4">
              <p className="text-sm text-slate-400 uppercase tracking-wider font-bold mb-2">Student Record</p>
              <p className="text-white"><strong>Name:</strong> {examConfig?.candidateName}</p>
              <p className="text-white"><strong>ID:</strong> {examConfig?.candidateId}</p>
              <p className="text-white"><strong>Exam:</strong> {examConfig?.examTitle} ({examConfig?.examCode})</p>
           </div>
            <div className="flex flex-col sm:flex-row gap-4 mt-8 w-full justify-center">
               <button 
                 onClick={resetExam}
                 className="px-8 py-3 bg-slate-700 hover:bg-slate-600 transition-all font-bold rounded-lg shadow-lg flex items-center justify-center gap-2"
               >
                 Request New Session
               </button>
               <button 
                 onClick={downloadReport}
                 className="px-8 py-3 bg-blue-600 hover:bg-blue-700 transition-all font-bold rounded-lg shadow-lg shadow-blue-500/20 flex items-center justify-center gap-2"
               >
                 <ShieldAlert className="w-5 h-5" /> Download Proctoring Report
               </button>
            </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col font-sans">
      <header className="bg-slate-800 p-4 shadow-md flex justify-between items-center px-8 border-b border-slate-700">
        <div className="flex items-center gap-6">
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
            <span className="bg-blue-600 font-black text-white px-2 py-1 rounded-md text-sm">AI</span>
            SmartProctor AI
          </h1>
          {sessionActive && (
            <div className="hidden md:flex items-center gap-4 text-sm text-slate-400 border-l border-slate-700 pl-6">
              <span className="flex items-center gap-1"><User className="w-4 h-4" /> {examConfig.candidateName}</span>
              <span className="flex items-center gap-1"><Monitor className="w-4 h-4" /> {examConfig.examTitle}</span>
              <span className="flex items-center gap-1 font-mono text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded"><Clock className="w-4 h-4" /> {formatTime(remainingSeconds)}</span>
            </div>
          )}
        </div>
        {sessionActive ? (
          <StatusDashboard status={status} onReset={resetExam} />
        ) : (
          <div className="text-sm text-slate-400 italic">Waiting for orientation...</div>
        )}
      </header>
      
      {!sessionActive ? (
        <RegistrationForm onStart={handleStartSession} />
      ) : (
        <main className="flex-1 grid grid-cols-1 xl:grid-cols-3 gap-6 p-6 lg:p-8 max-w-[1600px] w-full mx-auto">
          <div className="xl:col-span-2 flex flex-col gap-6">
            <LiveCamera frame={videoFrame} localStream={localStream} />
            <CheatingLogs alerts={alerts} />
          </div>
          <div className="xl:col-span-1 h-[calc(100vh-140px)]">
            <AlertPanel alerts={alerts} />
          </div>
        </main>
      )}
    </div>
  );
}

export default App;
