import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { formatHebrewDate } from '../../utils/format';
import { ChevronRight } from 'lucide-react';
import NotificationBell from '../layout/NotificationBell';

export default function PortalTopBar({ title, onBack }) {
  const { user } = useAuth();
  const today = new Date();
  const hebrewDate = formatHebrewDate(today.getFullYear() + '-' + String(today.getMonth() + 1).padStart(2, '0'));

  return (
    <div className="fixed top-0 left-0 right-0 w-screen h-20 bg-gradient-to-r from-slate-700 via-slate-800 to-slate-900 border-b border-slate-900 flex items-center justify-between px-6 shadow-lg z-40">
      {/* Right: Back button + Title */}
      <div className="flex items-center gap-4">
        {onBack && (
          <button
            onClick={onBack}
            className="text-slate-300 hover:text-white transition"
          >
            <ChevronRight size={24} />
          </button>
        )}
        <h1 className="text-2xl font-hebrew font-bold text-white">{title}</h1>
      </div>

      {/* Left: Bell + Municipality + Date */}
      <div className="flex items-center gap-4 text-right text-slate-200 text-sm font-hebrew">
        <NotificationBell />
        <span className="text-slate-100">{hebrewDate}</span>
        <span className="font-medium text-white">{user?.municipality_name}</span>
      </div>
    </div>
  );
}
