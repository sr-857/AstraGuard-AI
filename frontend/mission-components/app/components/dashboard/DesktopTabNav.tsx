import React from 'react';

interface DesktopTabNavProps {
    activeTab: 'mission' | 'systems' | 'chaos';
    onTabChange: (tab: 'mission' | 'systems' | 'chaos') => void;
}

export const DesktopTabNav: React.FC<DesktopTabNavProps> = ({ activeTab, onTabChange }) => {
    return (
        <div className="hidden md:flex gap-2 pt-4">
            <button
                id="mission-tab"
                data-tab="mission"
                className={`px-6 py-3 rounded-t-lg font-mono text-lg font-semibold transition-all duration-300 ${activeTab === 'mission'
                    ? 'tab-active-teal bg-teal-500/10 border-b-2 border-teal-400 text-teal-300 glow-teal'
                    : 'text-gray-400 hover:text-teal-300 hover:bg-teal-500/5'
                    }`}
                onClick={() => onTabChange('mission')}
            >
                Mission
            </button>

            <button
                id="systems-tab"
                data-tab="systems"
                className={`ml-2 px-6 py-3 rounded-t-lg font-mono text-lg font-semibold transition-all duration-300 ${activeTab === 'systems'
                    ? 'tab-active-magenta bg-fuchsia-500/10 border-b-2 border-fuchsia-400 text-fuchsia-300 glow-magenta'
                    : 'text-gray-400 hover:text-fuchsia-300 hover:bg-fuchsia-500/5'
                    }`}
                onClick={() => onTabChange('systems')}
            >
                Systems
            </button>

            <button
                id="chaos-tab"
                data-tab="chaos"
                className={`ml-2 px-6 py-3 rounded-t-lg font-mono text-lg font-semibold transition-all duration-300 ${activeTab === 'chaos'
                    ? 'tab-active-amber bg-amber-500/10 border-b-2 border-amber-400 text-amber-300 glow-amber'
                    : 'text-gray-400 hover:text-amber-300 hover:bg-amber-500/5'
                    }`}
                onClick={() => onTabChange('chaos')}
            >
                Chaos
            </button>
        </div>
    );
};
