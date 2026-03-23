import React from 'react';
import { History } from 'lucide-react';

const CheatingLogs = ({ alerts }) => {
  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden shadow-lg flex flex-col flex-1 min-h-[300px]">
      <div className="p-4 border-b border-slate-700 bg-slate-800/50">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <History className="w-5 h-5 text-emerald-400" />
          Detailed Event Logs
        </h2>
      </div>
      <div className="p-0 overflow-x-auto">
        <table className="w-full text-left text-sm text-slate-400">
          <thead className="text-xs text-slate-300 uppercase bg-slate-900/50 border-b border-slate-700/50">
            <tr>
              <th className="px-6 py-3 font-medium">Time</th>
              <th className="px-6 py-3 font-medium">Event Type</th>
              <th className="px-6 py-3 font-medium">Description</th>
            </tr>
          </thead>
          <tbody>
            {alerts.length === 0 ? (
                <tr>
                    <td colSpan="3" className="px-6 py-8 text-center text-slate-500">
                        No recent events recorded in the log.
                    </td>
                </tr>
            ) : (
                alerts.map((alert, index) => (
                <tr key={index} className="border-b border-slate-700/50 hover:bg-slate-700/20 transition-colors">
                    <td className="px-6 py-3 font-medium text-slate-300">
                      {new Date(alert.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </td>
                    <td className="px-6 py-3">
                      <span className="px-2 py-1 rounded bg-slate-900 border border-slate-700 text-xs capitalize text-slate-300">
                        {alert.type.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-slate-300">{alert.description}</td>
                </tr>
                ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default CheatingLogs;
