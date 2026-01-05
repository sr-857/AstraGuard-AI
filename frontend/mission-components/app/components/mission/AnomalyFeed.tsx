'use client';

import { AnomalyEvent } from '../../types/anomalies';

interface Props {
  anomalies: AnomalyEvent[];
  onAcknowledge: (id: string) => void;
  onSelect: (anomaly: AnomalyEvent) => void;
  selectedSat?: string | null;
}

export const AnomalyFeed: React.FC<Props> = ({ anomalies, onAcknowledge, onSelect, selectedSat }) => {
  const severityConfig = {
    Critical: { color: 'red', icon: '🔴', pulse: 'animate-pulse glow-red', borderColor: 'border-red-500/30', bgColor: 'bg-red-500/10' },
    Warning: { color: 'amber', icon: '🟡', pulse: 'glow-amber', borderColor: 'border-amber-500/30', bgColor: 'bg-amber-500/10' },
    Info: { color: 'cyan', icon: '🟢', pulse: '', borderColor: 'border-cyan-500/30', bgColor: 'bg-cyan-500/10' },
  };

  const unackedCount = anomalies.filter((a) => !a.acknowledged).length;

  return (
    <div className="h-full flex flex-col bg-black/70 backdrop-blur-xl rounded-2xl border-2 border-magenta-500/30 glow-magenta p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 pb-4 border-b border-magenta-500/20">
        <h3 className="text-lg font-bold text-magenta-400 glow-magenta flex items-center">
          <span className="mr-2 text-xl">🚨</span> Anomaly Feed
        </h3>
        <span className={`text-xs font-mono font-bold px-2 py-1 rounded-full transition-all ${
          unackedCount > 0 
            ? 'bg-magenta-500/30 text-magenta-300 glow-magenta' 
            : 'bg-green-500/20 text-green-400'
        }`}>
          {unackedCount} unacked
        </span>
      </div>

      {/* Anomaly List */}
      <div className="flex-1 overflow-auto space-y-2 pr-2 scrollbar-thin scrollbar-thumb-magenta-500/50">
        {anomalies.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-8">
            <div className="text-4xl mb-2 animate-bounce">🟢</div>
            <div className="text-sm font-mono text-green-400">All systems nominal</div>
            <div className="text-xs text-gray-500 mt-2">No anomalies detected</div>
          </div>
        ) : (
          anomalies.slice(0, 10).map((anomaly) => {
            const config = severityConfig[anomaly.severity];
            const isSelected = selectedSat === anomaly.satellite;

            return (
              <div
                key={anomaly.id}
                className={`group p-3 rounded-lg border cursor-pointer transition-all hover:scale-[1.02] hover:shadow-2xl ${
                  anomaly.acknowledged
                    ? 'border-gray-700/50 bg-gray-900/50 opacity-50'
                    : `${config.borderColor} ${config.bgColor}`
                } ${isSelected ? 'ring-2 ring-teal-400/50' : ''}`}
                onClick={() => !anomaly.acknowledged && onSelect(anomaly)}
              >
                <div className="flex items-start gap-3">
                  {/* Severity Icon */}
                  <span className={`text-xl flex-shrink-0 ${config.pulse}`}>
                    {config.icon}
                  </span>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    {/* Satellite + Time */}
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono text-sm font-bold text-gray-200">
                        {anomaly.satellite}
                      </span>
                      <span className="text-xs opacity-60 font-mono text-gray-400">
                        {anomaly.timestamp}
                      </span>
                    </div>

                    {/* Metric */}
                    <div className={`text-base font-bold truncate ${
                      anomaly.acknowledged ? 'line-through text-gray-500' : 'text-white'
                    }`}>
                      {anomaly.metric}
                    </div>

                    {/* Value */}
                    <div className="text-xs opacity-75 font-mono text-gray-300">
                      {anomaly.value}
                    </div>
                  </div>

                  {/* ACK Button */}
                  {!anomaly.acknowledged && (
                    <button
                      className="ml-2 px-2 py-1 rounded-md hover:bg-teal-500/20 hover:text-teal-400 text-gray-400 transition-all flex-shrink-0 font-mono text-sm glow-teal"
                      onClick={(e) => {
                        e.stopPropagation();
                        onAcknowledge(anomaly.id);
                      }}
                      title="Acknowledge anomaly"
                    >
                      ✓
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Footer Stats */}
      {anomalies.length > 0 && (
        <div className="mt-4 pt-4 border-t border-magenta-500/20 text-xs space-y-1 text-gray-400">
          <div className="flex justify-between">
            <span>Total Events:</span>
            <span className="font-mono text-magenta-400">{anomalies.length}</span>
          </div>
          <div className="flex justify-between">
            <span>Critical:</span>
            <span className="font-mono text-red-400">{anomalies.filter((a) => a.severity === 'Critical').length}</span>
          </div>
          <div className="flex justify-between">
            <span>Acknowledged:</span>
            <span className="font-mono text-cyan-400">{anomalies.filter((a) => a.acknowledged).length}</span>
          </div>
        </div>
      )}
    </div>
  );
};
