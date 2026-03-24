import React, { useEffect, useRef } from 'react';
import { Camera, AlertCircle } from 'lucide-react';

const LiveCamera = ({ frame, localStream }) => {
  const localVideoRef = useRef(null);

  useEffect(() => {
    if (localVideoRef.current && localStream && !frame) {
      localVideoRef.current.srcObject = localStream;
    }
  }, [localStream, frame]);

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden shadow-lg flex flex-col">
      <div className="p-4 border-b border-slate-700 flex justify-between items-center bg-slate-800/50">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Camera className="w-5 h-5 text-blue-400" />
          Live Proctoring Feed
        </h2>
        <div className="flex items-center gap-2">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
            </span>
            <span className="text-sm text-slate-400 font-medium">Recording</span>
        </div>
      </div>
      <div className="relative aspect-video bg-black flex items-center justify-center">
        {frame ? (
          <img src={frame} alt="Live feed" className="w-full h-full object-cover" />
        ) : localStream ? (
          <video 
            ref={localVideoRef} 
            autoPlay 
            muted 
            playsInline 
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="flex flex-col items-center text-slate-500 gap-3">
            <Camera className="w-12 h-12 opacity-20" />
            <p>Waiting for video stream...</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default LiveCamera;
