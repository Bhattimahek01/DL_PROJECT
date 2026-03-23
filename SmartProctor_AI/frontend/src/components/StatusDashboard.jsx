import React from 'react';
import { CheckCircle, AlertTriangle, ShieldAlert } from 'lucide-react';

const StatusDashboard = ({ status, onReset }) => {
  const isAlert = status.status === 'alert';
  const isSuspended = status.status === 'suspended';
  const isTerminated = status.status === 'terminated';

  return (
    <div className="flex items-center gap-4">
      <div className={`flex items-center gap-2 px-4 py-2 rounded-full border transition-all duration-300 ${
        isTerminated 
          ? 'bg-red-700 border-red-600 text-white shadow-lg shadow-red-600/30' 
          : isSuspended 
            ? 'bg-red-600 border-red-500 text-white shadow-lg shadow-red-500/20' 
            : isAlert 
              ? 'bg-red-500/10 border-red-500/30 text-red-400' 
              : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
      }`}>
        {isTerminated ? <ShieldAlert className="w-4 h-4" /> : isSuspended ? <ShieldAlert className="w-4 h-4" /> : isAlert ? <AlertTriangle className="w-4 h-4" /> : <CheckCircle className="w-4 h-4" />}
        <span className="text-sm font-semibold uppercase tracking-wider">
          {isTerminated ? 'Exam Terminated' : isSuspended ? 'Exam Suspended' : isAlert ? 'Cheating Detected' : 'Monitoring Active'}
        </span>
      </div>
      
      {(isAlert || isSuspended) && (
          <button 
            onClick={onReset}
            className="text-xs bg-slate-700 hover:bg-slate-600 transition-colors px-3 py-1.5 rounded-md text-slate-200 font-medium"
          >
            {isSuspended ? 'Restart Session' : 'Acknowledge & Reset'}
          </button>
      )}
    </div>
  );
};

export default StatusDashboard;
