import React from 'react';
import { ChevronRight } from 'lucide-react';
import NotificationBell from './NotificationBell';

export default function TopBar({ title, backPath = null }) {
  const handleBack = () => {
    if (backPath) {
      window.history.back();
    }
  };

  return (
    <div className="h-topbar bg-gradient-to-r from-slate-700 via-slate-800 to-slate-900 border-b border-slate-900 fixed top-0 left-0 right-0 w-screen flex items-center justify-between px-8 shadow-lg z-40">
      <div className="flex items-center gap-4">
        {backPath && (
          <button
            onClick={handleBack}
            className="p-2 hover:bg-slate-600 rounded-lg transition-colors"
          >
            <ChevronRight size={24} className="text-white" />
          </button>
        )}
        <h1 className="text-2xl font-hebrew font-bold text-white">
          {title}
        </h1>
      </div>
      <div className="flex items-center">
        <NotificationBell />
      </div>
    </div>
  );
}
