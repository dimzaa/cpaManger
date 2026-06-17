import React, { useState, useEffect } from 'react';
import { Eye, EyeOff } from 'lucide-react';

/**
 * DevModeToggle — Allows admins to show/hide test data
 * 
 * Stores preference in localStorage so it persists across sessions.
 * Only visible to admin users.
 */
export default function DevModeToggle({ isAdmin = false }) {
  const [devMode, setDevMode] = useState(false);

  // Load dev mode preference from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem('dev_mode_enabled');
    if (stored) {
      setDevMode(JSON.parse(stored));
    }
  }, []);

  // Update localStorage and propagate to API queries
  const handleToggle = () => {
    const newState = !devMode;
    setDevMode(newState);
    localStorage.setItem('dev_mode_enabled', JSON.stringify(newState));
    
    // Optionally dispatch custom event to notify other components
    window.dispatchEvent(
      new CustomEvent('devModeChanged', { detail: { enabled: newState } })
    );
  };

  if (!isAdmin) return null;

  return (
    <button
      onClick={handleToggle}
      title={devMode ? 'Showing test data' : 'Hiding test data (click to show)'}
      className={`
        inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium
        transition-all duration-200
        ${devMode
          ? 'bg-purple-100 text-purple-700 border border-purple-300'
          : 'bg-slate-100 text-slate-600 border border-slate-200'
        }
      `}
    >
      {devMode ? (
        <>
          <Eye size={14} />
          <span className="font-hebrew">Dev Mode: ON</span>
        </>
      ) : (
        <>
          <EyeOff size={14} />
          <span className="font-hebrew">Dev Mode: OFF</span>
        </>
      )}
    </button>
  );
}
