import React, { useEffect, useState, useRef, useMemo } from 'react';
import dynamic from 'next/dynamic';
import { Satellite, AnomalyEvent } from '../../types/dashboard';
import { getSatellitePosition, SatellitePoint } from '../../utils/orbital';

// Dynamically import Globe to avoid SSR issues with WebGL
const Globe = dynamic(() => import('react-globe.gl'), { ssr: false });

interface Props {
  satellites: Satellite[];
  selectedSat?: Satellite | null;
  onSatClick: (sat: Satellite) => void;
  anomalies: AnomalyEvent[];
}


// Ground Station Coordinates
const GROUND_STATIONS = [
  { id: 'GS-HOU', name: 'HOUSTON', lat: 29.7604, lng: -95.3698, color: '#06b6d4' },
  { id: 'GS-LON', name: 'LONDON', lat: 51.5074, lng: -0.1278, color: '#06b6d4' },
  { id: 'GS-TOK', name: 'TOKYO', lat: 35.6762, lng: 139.6503, color: '#06b6d4' },
  { id: 'GS-CAN', name: 'CANBERRA', lat: -35.2809, lng: 149.1300, color: '#06b6d4' },
];

export const OrbitMap: React.FC<Props> = ({ satellites, selectedSat, onSatClick, anomalies }) => {
  const globeEl = useRef<any>(null);
  const [points, setPoints] = useState<any[]>([]);
  const [arcs, setArcs] = useState<any[]>([]);

  // Calculate satellite positions (animation loop)
  useEffect(() => {
    const updatePositions = () => {
      const satPoints = satellites.map(getSatellitePosition);

      // Merge satellites with static ground stations for point rendering
      const stationPoints = GROUND_STATIONS.map(gs => ({
        ...gs,
        alt: 0.01,
        type: 'STATION',
        status: 'ONLINE'
      }));

      // Calculate Links (Arcs)
      const newArcs = satPoints.map(sat => {
        // Find nearest ground station (simple euclidean approx for visual speed)
        let nearest = GROUND_STATIONS[0];
        let minDist = 9999;

        GROUND_STATIONS.forEach(gs => {
          const dist = Math.sqrt(Math.pow(sat.lat - gs.lat, 2) + Math.pow(sat.lng - gs.lng, 2));
          if (dist < minDist) {
            minDist = dist;
            nearest = gs;
          }
        });

        // Determine signal quality based on distance (mock horizon)
        const isConnected = minDist < 60; // Approximate approx

        return {
          startLat: sat.lat,
          startLng: sat.lng,
          endLat: nearest.lat,
          endLng: nearest.lng,
          color: isConnected ? ['#22c55e', '#22c55e'] : ['#ef444400', '#ef444400'], // Green or Transparent
          dashLength: 0.4,
          dashGap: 0.2,
          dashAnimateTime: 2000,
          stroke: isConnected ? 0.3 : 0
        };
      });

      setPoints([...satPoints, ...stationPoints]);
      setArcs(newArcs);
    };

    const interval = setInterval(updatePositions, 50);
    return () => clearInterval(interval);
  }, [satellites]);

  // Initial focus
  useEffect(() => {
    if (selectedSat && globeEl.current) {
      const satPoint = getSatellitePosition(selectedSat);
      // globeEl.current.pointOfView({ lat: satPoint.lat, lng: satPoint.lng, altitude: satPoint.alt + 0.5 }, 1000);
    }
  }, [selectedSat]);

  // Auto-rotate
  useEffect(() => {
    if (globeEl.current) {
      globeEl.current.controls().autoRotate = true;
      globeEl.current.controls().autoRotateSpeed = 0.5;
    }
  }, []);

  const ringsData = useMemo(() => {
    // Anomaly Rings
    const anomalyRings = anomalies.map(anomaly => {
      const sat = satellites.find(s => s.orbitSlot === anomaly.satellite.split('-')[1]);
      if (!sat) return null;
      const pos = getSatellitePosition(sat);
      return {
        lat: pos.lat,
        lng: pos.lng,
        alt: pos.alt,
        maxR: 5,
        propagationSpeed: 5,
        repeatPeriod: 1000,
        color: () => '#ef4444'
      }
    }).filter(Boolean);

    // Ground Station Coverage Zones
    const stationRings = GROUND_STATIONS.map(gs => ({
      lat: gs.lat,
      lng: gs.lng,
      alt: 0,
      maxR: 15, // Coverage radius
      propagationSpeed: 0.5,
      repeatPeriod: 2000,
      color: () => '#06b6d4'
    }));

    return [...anomalyRings, ...stationRings];
  }, [anomalies, satellites]);

  return (
    <div className="relative w-full h-full bg-slate-950 rounded-sm border border-slate-900 overflow-hidden flex items-center justify-center">
      <Globe
        ref={globeEl}
        width={800}
        height={400}
        globeImageUrl="//unpkg.com/three-globe/example/img/earth-night.jpg"
        backgroundImageUrl="//unpkg.com/three-globe/example/img/night-sky.png"
        pointsData={points}
        pointAltitude="alt"
        pointColor="color"
        pointRadius={(d: any) => d.type === 'STATION' ? 0.8 : 0.5}
        pointLabel={(d: any) => `
            <div style="background: rgba(15, 23, 42, 0.9); padding: 8px; border: 1px solid #334155; border-radius: 4px; color: white;">
                <div style="font-weight: bold; color: ${d.color}">${d.name}</div>
                <div style="font-size: 11px;">${d.type === 'STATION' ? 'GROUND UPLINK' : 'SAT_ID: ' + d.id}</div>
                <div style="font-size: 11px;">Status: ${d.status}</div>
            </div>
        `}
        onPointClick={(point: any) => {
          if (point.type !== 'STATION') {
            const originalSat = satellites.find(s => s.id === point.id);
            if (originalSat) onSatClick(originalSat);
          }
        }}

        arcsData={arcs}
        arcColor="color"
        arcDashLength="dashLength"
        arcDashGap="dashGap"
        arcDashAnimateTime="dashAnimateTime"
        arcStroke="stroke"

        ringsData={ringsData}
        ringColor="color"
        ringMaxRadius="maxR"
        ringPropagationSpeed="propagationSpeed"
        ringRepeatPeriod="repeatPeriod"
        atmosphereColor="#3b82f6"
        atmosphereAltitude={0.15}

        labelsData={GROUND_STATIONS}
        labelLat="lat"
        labelLng="lng"
        labelText="name"
        labelSize={1.5}
        labelDotRadius={0.5}
        labelColor={() => '#06b6d4'}
      />

      {/* Overlay UI */}
      <div className="absolute top-4 right-4 bg-slate-900/80 backdrop-blur border border-slate-700 p-2 rounded text-xs text-slate-300">
        <div>Total Satellites: {satellites.length}</div>
        <div>Active Anomalies: {anomalies.length}</div>
        <div>Ground Stations: {GROUND_STATIONS.length}</div>
      </div>
    </div>
  );
};
