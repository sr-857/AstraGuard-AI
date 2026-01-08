'use client';

import { createContext, useContext, ReactNode, useState, useEffect } from 'react';
import { TelemetryState, WSMessage } from '../types/websocket';
import { useDashboardWebSocket } from '../hooks/useDashboardWebSocket';
import { GroundStation, RemediationScript, RemediationStep, AICognitiveState } from '../types/dashboard';

export interface Annotation {
    id: string;
    targetId: string; // ID of anomaly or metric
    text: string;
    author: string;
    timestamp: string;
}

export interface Operator {
    id: string;
    name: string;
    avatar: string;
    activePanel: string;
}

interface ContextValue {
    state: TelemetryState;
    isConnected: boolean;
    send: (msg: WSMessage) => void;
    dispatch: any;
    isReplayMode: boolean;
    toggleReplayMode: () => void;
    replayProgress: number;
    setReplayProgress: (p: any) => void;
    isPlaying: boolean;
    togglePlay: () => void;
    isBattleMode: boolean;
    setBattleMode: (active: boolean) => void;
    // Collaboration
    annotations: Annotation[];
    addAnnotation: (note: Omit<Annotation, 'id' | 'timestamp'>) => void;
    removeAnnotation: (id: string) => void;
    presence: Operator[];
    // Remediation
    activeRemediation: RemediationScript | null;
    proposeRemediation: (anomalyId: string) => void;
    authorizeRemediation: (id: string) => void;
    cancelRemediation: () => void;
    // Ground Stations
    groundStations: GroundStation[];
    // AI Health
    aiHealth: AICognitiveState;
}

const DashboardContext = createContext<ContextValue | undefined>(undefined);

export const DashboardProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const ws = useDashboardWebSocket();
    const [isBattleMode, setBattleMode] = useState(false);
    const [annotations, setAnnotations] = useState<Annotation[]>([]);
    const [presence] = useState<Operator[]>([
        { id: '1', name: 'SIGMA', avatar: 'Σ', activePanel: 'Mission Control' },
        { id: '2', name: 'ALPHA', avatar: 'A', activePanel: 'Systems' },
        { id: '3', name: 'KAPPA', avatar: 'K', activePanel: 'Chaos Engine' },
    ]);
    const [activeRemediation, setActiveRemediation] = useState<RemediationScript | null>(null);
    const [groundStations] = useState<GroundStation[]>([
        { id: 'gs-1', name: 'Svalbard-A', lat: 78.22, lng: 15.65, weather: 'Clear', signalQuality: 0.98, connectedSatelliteId: 'SAT-01' },
        { id: 'gs-2', name: 'Kourou-Prime', lat: 5.16, lng: -52.64, weather: 'Rain', signalQuality: 0.65, connectedSatelliteId: 'SAT-02' },
        { id: 'gs-3', name: 'Canberra-Deep', lat: -35.28, lng: 149.13, weather: 'Clear', signalQuality: 0.95, connectedSatelliteId: 'SAT-03' },
        { id: 'gs-4', name: 'Haruna-Station', lat: 36.47, lng: 138.92, weather: 'Storm', signalQuality: 0.42, connectedSatelliteId: 'SAT-01' },
    ]);
    const [aiHealth, setAiHealth] = useState<AICognitiveState>({
        load: 12,
        synapticThroughput: 1450,
        attentionFocus: 'Orbit Optimization',
        confidence: 0.99,
        activeNeurons: 4200
    });

    // Simulate AI Cognitive Fluctuations
    useEffect(() => {
        const interval = setInterval(() => {
            setAiHealth((prev: AICognitiveState) => ({
                ...prev,
                load: Math.max(10, Math.min(95, prev.load + (Math.random() - 0.5) * 5)),
                synapticThroughput: 1400 + Math.floor(Math.random() * 200),
                confidence: 0.95 + Math.random() * 0.05
            }));
        }, 3000);
        return () => clearInterval(interval);
    }, []);

    // Add Annotation
    const addAnnotation = (note: Omit<Annotation, 'id' | 'timestamp'>) => {
        const newNote: Annotation = {
            ...note,
            id: Math.random().toString(36).substr(2, 9),
            timestamp: new Date().toLocaleTimeString(),
        };
        setAnnotations(prev => [newNote, ...prev]);
    };

    // Remove Annotation
    const removeAnnotation = (id: string) => {
        setAnnotations(prev => prev.filter(a => a.id !== id));
    };

    // Propose Remediation (Mock logic)
    const proposeRemediation = (anomalyId: string) => {
        const steps: RemediationStep[] = [
            { id: 's1', command: 'REBOOT_TRANSCEIVER_01', description: 'Hard reset on signal transceiver primary loop', status: 'pending' },
            { id: 's2', command: 'RECALIBRATE_PHASE_ARRAY', description: 'Adjusting phase array to ±0.04° alignment', status: 'pending' },
            { id: 's3', command: 'CLEAR_CACHE_MCR', description: 'Clearing local MCR mission persistent cache', status: 'pending' }
        ];

        setActiveRemediation({
            id: Math.random().toString(36).substr(2, 9),
            anomalyId,
            steps,
            status: 'proposed',
            createdAt: new Date().toLocaleTimeString()
        });
    };

    // Authorize Remediation
    const authorizeRemediation = (id: string) => {
        if (!activeRemediation || activeRemediation.id !== id) return;

        setActiveRemediation(prev => prev ? { ...prev, status: 'authorized' } : null);

        // Mock execution sequence
        setTimeout(() => {
            setActiveRemediation(prev => {
                if (!prev) return null;
                const newSteps = [...prev.steps];
                newSteps[0].status = 'executing';
                return { ...prev, status: 'executing', steps: newSteps };
            });
        }, 1000);

        setTimeout(() => {
            setActiveRemediation(prev => {
                if (!prev) return null;
                const newSteps = [...prev.steps];
                newSteps[0].status = 'completed';
                newSteps[1].status = 'executing';
                return { ...prev, steps: newSteps };
            });
        }, 3000);

        setTimeout(() => {
            setActiveRemediation(prev => {
                if (!prev) return null;
                const newSteps = [...prev.steps];
                newSteps[1].status = 'completed';
                newSteps[2].status = 'completed';
                return { ...prev, status: 'completed', steps: newSteps };
            });
        }, 6000);
    };

    const cancelRemediation = () => {
        setActiveRemediation(null);
    };

    // Auto-trigger Battle Mode on Critical Anomalies
    useEffect(() => {
        if (ws.state.mission?.anomalies) {
            const hasCritical = ws.state.mission.anomalies.some((a: any) => a.severity === 'Critical');
            if (hasCritical && !isBattleMode) {
                setBattleMode(true);
            }
        }
    }, [ws.state.mission?.anomalies, isBattleMode]);

    const value = {
        ...ws,
        isBattleMode,
        setBattleMode,
        annotations,
        addAnnotation,
        removeAnnotation,
        presence,
        activeRemediation,
        proposeRemediation,
        authorizeRemediation,
        cancelRemediation,
        groundStations,
        aiHealth
    };

    return (
        <DashboardContext.Provider value={value}>
            {children}
        </DashboardContext.Provider>
    );
};

export const useDashboard = () => {
    const context = useContext(DashboardContext);
    if (!context) throw new Error('useDashboard must be used within DashboardProvider');
    return context;
};
