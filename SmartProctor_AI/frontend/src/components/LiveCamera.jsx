import React, { useEffect, useRef } from 'react';
import { Camera, AlertCircle } from 'lucide-react';

const LiveCamera = ({ frame, localStream, alerts = [], activeViolations = [] }) => {
  const localVideoRef = useRef(null);
  
  // Check if multiple persons are currently detected OR were detected recently in logs
  const isMultiplePersons = activeViolations.includes('multiple_persons') || (
    alerts.length > 0 && 
    alerts[0].type === 'multiple_persons' && 
    (new Date() - new Date(alerts[0].timestamp)) < 5000
  );

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

        {/* Warning Overlay for Multiple Persons */}
        {isMultiplePersons && (
          <div className="absolute inset-0 bg-red-600/20 border-4 border-red-500 animate-pulse flex items-center justify-center z-10 pointer-events-none">
            <div className="bg-red-600 text-white px-6 py-3 rounded-lg shadow-2xl flex items-center gap-3 scale-110">
              <AlertCircle className="w-8 h-8" />
              <div className="text-left">
                <p className="font-black text-xl leading-none">SECURITY ALERT</p>
                <p className="text-sm font-bold opacity-90">MULTIPLE PERSONS DETECTED</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default LiveCamera;
