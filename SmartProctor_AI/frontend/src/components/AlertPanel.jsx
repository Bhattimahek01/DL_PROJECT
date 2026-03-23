import { Bell, ShieldAlert, UserX, Smartphone, EyeOff, Layout, CameraOff } from 'lucide-react';

const getIcon = (type) => {
    switch(type) {
        case 'multiple_persons': return <UserX className="w-5 h-5 text-orange-400" />;
        case 'mobile_phone': return <Smartphone className="w-5 h-5 text-red-400" />;
        case 'talking': return <Bell className="w-5 h-5 text-yellow-400" />;
        case 'looking_away': 
        case 'looking_side_to_side': return <EyeOff className="w-5 h-5 text-purple-400" />;
        case 'tab_switch': return <Layout className="w-5 h-5 text-pink-400" />;
        case 'camera_off': return <CameraOff className="w-5 h-5 text-red-500" />;
        case 'printing': return <Layout className="w-5 h-5 text-blue-500" />;
        default: return <ShieldAlert className="w-5 h-5 text-blue-400" />;
    }
}

const AlertPanel = ({ alerts }) => {
  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden shadow-lg flex flex-col h-full">
      <div className="p-4 border-b border-slate-700 bg-slate-800/50 flex items-center justify-between">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-red-400" />
          Real-time Alerts
        </h2>
        <span className="bg-red-500/10 text-red-400 px-2 py-1 rounded text-xs font-bold">
            {alerts.length} ALERTS
        </span>
      </div>
      <div className="p-4 flex-1 overflow-y-auto flex flex-col gap-3 custom-scrollbar">
        {alerts.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-500">
            <ShieldAlert className="w-12 h-12 opacity-20 mb-3" />
            <p>No anomalous behavior detected.</p>
          </div>
        ) : (
          alerts.map((alert, index) => (
            <div 
              key={index} 
              className="bg-slate-900/50 border border-slate-700/50 p-4 rounded-lg flex gap-4 animate-in slide-in-from-right fade-in duration-300"
            >
              <div className="mt-1">
                {getIcon(alert.type)}
              </div>
              <div>
                <div className="text-slate-200 font-medium">{alert.description}</div>
                <div className="text-slate-500 text-xs mt-1">
                  {new Date(alert.timestamp).toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default AlertPanel;
