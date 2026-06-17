import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Home, FileText, Briefcase, LogOut, Clock, CheckCircle, XCircle, TrendingUp, Calendar, BookOpen } from 'lucide-react';
import { usePositionsAttentionCount } from '../../hooks/usePositionsAttentionCount';
import { useEmployeeSuggestionCounts } from '../../hooks/useEmployeeSuggestionCounts';

export default function PortalSidebar({ onLogout }) {
  const location = useLocation();
  const { user } = useAuth();
  const { count: positionsCount } = usePositionsAttentionCount();
  const suggestionCounts = useEmployeeSuggestionCounts();

  const isEmployee = user?.role === 'employee';
  const isActive = (path) => location.pathname === path || location.pathname.startsWith(path + '/');

  return (
    <div className="fixed right-0 top-0 w-64 h-screen bg-gradient-to-b from-slate-800 to-slate-900 text-white flex flex-col shadow-2xl">
      {/* Logo & Municipality Name */}
      <div className="p-6 border-b border-slate-700">
        <div className="text-xl font-hebrew font-bold mb-2 text-white">💰 SmartHub</div>
        <div className="text-sm text-slate-300 font-hebrew">{user?.municipality_name || 'ניהול תקציב'}</div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 py-6 px-4 space-y-2">
        <Link
          to="/portal"
          className={`flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition text-right ${
            isActive('/portal') && location.pathname === '/portal'
              ? 'bg-slate-600 text-white shadow-md'
              : 'text-slate-300 hover:bg-slate-700'
          }`}
        >
          <Home size={20} />
          <span className="font-hebrew">סטטוס חודשי</span>
        </Link>

        <Link
          to="/portal/budget"
          className={`flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition text-right ${
            isActive('/portal/budget')
              ? 'bg-slate-600 text-white shadow-md'
              : 'text-slate-300 hover:bg-slate-700'
          }`}
        >
          <FileText size={20} />
          <span className="font-hebrew">פירוט תקציב</span>
        </Link>

        <Link
          to="/portal/positions"
          className={`flex items-center justify-between px-4 py-3 rounded-xl font-medium transition ${
            isActive('/portal/positions')
              ? 'bg-slate-600 text-white shadow-md'
              : 'text-slate-300 hover:bg-slate-700'
          }`}
        >
          <div className="flex items-center gap-3">
            <Briefcase size={20} />
            <span className="font-hebrew">משרות ותקנים</span>
          </div>
          {positionsCount > 0 && (
            <span className="inline-flex items-center justify-center min-w-[20px] px-1.5 py-0.5 text-xs font-bold leading-none text-white bg-amber-500 rounded-full">
              {positionsCount}
            </span>
          )}
        </Link>

        <Link
          to="/portal/analytics"
          className={`flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition text-right ${
            isActive('/portal/analytics')
              ? 'bg-slate-600 text-white shadow-md'
              : 'text-slate-300 hover:bg-slate-700'
          }`}
        >
          <TrendingUp size={20} />
          <span className="font-hebrew">ניתוח ומגמות</span>
        </Link>

        <Link
          to="/portal/reports"
          className={`flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition text-right ${
            isActive('/portal/reports')
              ? 'bg-slate-600 text-white shadow-md'
              : 'text-slate-300 hover:bg-slate-700'
          }`}
        >
          <FileText size={20} />
          <span className="font-hebrew">דוחות ומסמכים</span>
        </Link>

        <Link
          to="/portal/deadlines"
          className={`flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition text-right ${
            isActive('/portal/deadlines')
              ? 'bg-slate-600 text-white shadow-md'
              : 'text-slate-300 hover:bg-slate-700'
          }`}
        >
          <Calendar size={20} />
          <span className="font-hebrew">מועדים חשובים</span>
        </Link>

        <Link
          to="/portal/ministry"
          className={`flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition text-right ${
            isActive('/portal/ministry')
              ? 'bg-slate-600 text-white shadow-md'
              : 'text-slate-300 hover:bg-slate-700'
          }`}
        >
          <BookOpen size={20} />
          <span className="font-hebrew">משרד החינוך</span>
        </Link>

        {/* Employee-only: Suggestions tabs */}
        {isEmployee && (
          <>
            <div className="border-t border-slate-700 my-3 pt-1">
              <p className="px-4 text-xs text-slate-500 font-hebrew mb-2">ההצעות שלי</p>
            </div>

            {/* Pending suggestions */}
            <Link
              to="/portal/suggestions?tab=pending"
              className={`flex items-center justify-between px-4 py-3 rounded-xl font-medium transition ${
                location.pathname === '/portal/suggestions'
                  ? 'bg-slate-600 text-white shadow-md'
                  : 'text-slate-300 hover:bg-slate-700'
              }`}
            >
              <div className="flex items-center gap-3">
                <Clock size={20} />
                <span className="font-hebrew">ממתינות לאישור</span>
              </div>
              {suggestionCounts.pending > 0 && (
                <span className="inline-flex items-center justify-center min-w-[20px] px-1.5 py-0.5 text-xs font-bold leading-none text-white bg-red-500 rounded-full">
                  {suggestionCounts.pending}
                </span>
              )}
            </Link>

            {/* Approved suggestions */}
            <Link
              to="/portal/suggestions?tab=approved"
              className={`flex items-center justify-between px-4 py-3 rounded-xl font-medium transition text-slate-300 hover:bg-slate-700`}
            >
              <div className="flex items-center gap-3">
                <CheckCircle size={20} />
                <span className="font-hebrew">הצעות שאושרו</span>
              </div>
              {suggestionCounts.approved > 0 && (
                <span className="inline-flex items-center justify-center min-w-[20px] px-1.5 py-0.5 text-xs font-bold leading-none text-white bg-green-600 rounded-full">
                  {suggestionCounts.approved}
                </span>
              )}
            </Link>

            {/* Rejected suggestions */}
            <Link
              to="/portal/suggestions?tab=rejected"
              className={`flex items-center justify-between px-4 py-3 rounded-xl font-medium transition text-slate-300 hover:bg-slate-700`}
            >
              <div className="flex items-center gap-3">
                <XCircle size={20} />
                <span className="font-hebrew">הצעות שנדחו</span>
              </div>
              {suggestionCounts.rejected > 0 && (
                <span className="inline-flex items-center justify-center min-w-[20px] px-1.5 py-0.5 text-xs font-bold leading-none text-white bg-red-500 rounded-full">
                  {suggestionCounts.rejected}
                </span>
              )}
            </Link>
          </>
        )}
      </nav>

      {/* User Info & Logout */}
      <div className="p-6 border-t border-slate-700 space-y-3">
        <div className="text-sm text-slate-300">
          <div className="font-hebrew mb-2 text-white font-semibold">משתמש:</div>
          <div className="font-medium text-right text-slate-200">
            {user?.first_name} {user?.last_name}
          </div>
        </div>
        <button
          onClick={onLogout}
          className="w-full flex items-center justify-end gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 rounded-xl text-sm font-medium transition shadow-md"
        >
          <span className="font-hebrew">התנתקות</span>
          <LogOut size={18} />
        </button>
      </div>
    </div>
  );
}
