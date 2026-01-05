'use client';

import { useState, useEffect, useRef } from 'react';
import { Satellite, MissionPhase } from '../../types/mission';
import { AnomalyEvent } from '../../types/anomalies';
import missionData from '../../mocks/mission.json';
import anomalyData from '../../mocks/anomalies.json';
import { SatelliteCard } from './SatelliteCard';
import { PhaseTimeline } from './PhaseTimeline';
import { OrbitMap } from './OrbitMap';
import { AnomalyFeed } from './AnomalyFeed';

const cycleTasks: Record<string, string[]> = {
  'sat-001': ['Data Dump', 'Status Check', 'Calibration'],
  'sat-002': ['Orbit Adjust', 'Drift Correction', 'Standby'],
  'sat-003': ['Imaging', 'Data Capture', 'Processing'],
  'sat-004': ['Standby', 'Monitoring', 'Idle'],
  'sat-005': ['Offline', 'Offline', 'Offline'],
  'sat-006': ['Telemetry', 'Signal Boost', 'Transmission'],
};

export const MissionPanel: React.FC<{ onSelectSatellite?: (satId: string) => void }> = ({ onSelectSatellite }) => {
  const [satellites, setSatellites] = useState<Satellite[]>(missionData.satellites as Satellite[]);
  const [phases, setPhases] = useState<MissionPhase[]>(missionData.phases as MissionPhase[]);
  const [selectedSatId, setSelectedSatId] = useState<string | null>(null);
  const [anomalies, setAnomalies] = useState<AnomalyEvent[]>([]);
  const [selectedAnomaly, setSelectedAnomaly] = useState<AnomalyEvent | null>(null);
  const taskIndicesRef = useRef<Record<string, number>>({});

  const selectedSat = satellites.find((s) => s.id === selectedSatId) || null;
  const anomalyTemplates = anomalyData.templates;

  useEffect(() => {
    missionData.satellites.forEach((sat) => {
      taskIndicesRef.current[sat.id] = 0;
    });
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setSatellites((prev) =>
        prev.map((sat) => {
          const tasks = cycleTasks[sat.id] || ['Data Dump'];
          taskIndicesRef.current[sat.id] = ((taskIndicesRef.current[sat.id] || 0) + 1) % tasks.length;
          return {
            ...sat,
            task: tasks[taskIndicesRef.current[sat.id]],
            latency:
              sat.latency === 0 ? 0 : Math.max(20, sat.latency + (Math.random() - 0.5) * 20),
          };
        })
      );

      setPhases((prev) => {
        const activeIdx = prev.findIndex((p) => p.isActive);
        const nextIdx = (activeIdx + 1) % prev.length;
        return prev.map((phase, i) => ({
          ...phase,
          isActive: i === nextIdx,
          progress:
            i === nextIdx && phase.progress < 100 ? Math.min(100, phase.progress + 2) : phase.progress,
        }));
      });
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  // 15s anomaly generator
  useEffect(() => {
    const interval = setInterval(() => {
      const template = anomalyTemplates[Math.floor(Math.random() * anomalyTemplates.length)];
      setAnomalies((prev) => [
        {
          id: `evt-${Date.now()}`,
          satellite: template.satellite,
          severity: template.severity as 'Critical' | 'Warning' | 'Info',
          metric: template.metric,
          value: template.value,
          timestamp: new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          acknowledged: false,
        },
        ...prev.slice(0, 19),
      ]);
    }, 15000);

    return () => clearInterval(interval);
  }, [anomalyTemplates]);

  const handleAcknowledgeAnomaly = (id: string) => {
    setAnomalies((prev) =>
      prev.map((a) => (a.id === id ? { ...a, acknowledged: true } : a))
    );
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Top: Satellite Tracker from #87 */}
      <section className="glow-teal/50">
        <h2 className="text-2xl font-bold mb-6 text-teal-400 glow-teal flex items-center">
          Satellite Status{' '}
          <span className="ml-2 text-sm bg-teal-500/20 px-3 py-1 rounded-full">
            {satellites.filter((s) => s.status === 'Nominal').length}/6 Nominal
          </span>
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          {satellites.map((sat) => (
            <SatelliteCard
              key={sat.id}
              {...sat}
              isSelected={selectedSatId === sat.id}
              onClick={() => {
                setSelectedSatId(sat.id);
                onSelectSatellite?.(sat.orbitSlot);
              }}
            />
          ))}
        </div>
      </section>

      {/* 3-Column Layout: Map (2x) + Feed (1x) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Map Section (2x width) */}
        <section className="lg:col-span-2 glow-teal rounded-2xl border border-teal-500/30 p-4 bg-black/50 backdrop-blur-xl">
          <h3 className="text-lg font-bold text-teal-400 mb-4 glow-teal">Orbit Visualization</h3>
          <OrbitMap
            satellites={satellites}
            selectedSat={selectedSat}
            onSatClick={(sat) => {
              setSelectedSatId(sat.id);
              onSelectSatellite?.(sat.orbitSlot);
            }}
            anomalies={anomalies.filter((a) => !a.acknowledged)}
          />
        </section>

        {/* Anomaly Feed (1x width) */}
        <section className="glow-magenta rounded-2xl border border-magenta-500/30 p-0">
          <AnomalyFeed
            anomalies={anomalies}
            onAcknowledge={handleAcknowledgeAnomaly}
            onSelect={setSelectedAnomaly}
            selectedSat={selectedSat?.orbitSlot || null}
          />
        </section>
      </div>

      {/* Selected Items Debug Panel */}
      {(selectedSat || selectedAnomaly) && (
        <div className="p-4 bg-black/70 backdrop-blur-xl rounded-xl border border-teal-500/50 glow-teal grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          {selectedSat && (
            <div>
              <h4 className="font-bold text-teal-400 mb-2">Selected Satellite</h4>
              <div className="space-y-1 font-mono text-gray-300">
                <div>LEO-{selectedSat.orbitSlot} · {selectedSat.status}</div>
                <div className="text-xs opacity-75">{selectedSat.task} · {Math.round(selectedSat.latency)}ms</div>
              </div>
            </div>
          )}
          {selectedAnomaly && (
            <div>
              <h4 className="font-bold text-magenta-400 mb-2">Selected Anomaly</h4>
              <div className="space-y-1 font-mono text-gray-300">
                <div>{selectedAnomaly.satellite}</div>
                <div className="text-xs opacity-75">{selectedAnomaly.metric} · {selectedAnomaly.value}</div>
              </div>
            </div>
          )}
        </div>
      )}

      <PhaseTimeline phases={phases} />
    </div>
  );
};
