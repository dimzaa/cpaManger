import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Home, Upload, BarChart3, LogOut, CheckCircle, AlertCircle, Briefcase, FileDown, Bell, BookOpen } from 'lucide-react';
import { usePendingSuggestionsCount } from '../../hooks/usePendingSuggestionsCount';
import { useRejectedSuggestionsCount } from '../../hooks/useRejectedSuggestionsCount';

export default function Sidebar() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const { count: pendingCount } = usePendingSuggestionsCount();
  const { count: rejectedCount } = useRejectedSuggestionsCount();

  const isActive = (path) => location.pathname === path;

  const navItems = [
    { label: 'לוח בקרה', path: '/dashboard', icon: Home },
    { label: 'העלאת קבצים', path: '/upload', icon: Upload },
    { label: 'דוחות ומסמכים', path: '/admin/reports', icon: FileDown },
    { label: 'השוואת חודשים', path: '/compare', icon: BarChart3 },
  ];

  const adminItems = user?.role === 'admin' ? [
    { label: 'אישורים', path: '/admin/approvals', icon: CheckCircle, badge: pendingCount > 0 ? pendingCount : null },
    { label: 'ניתוח משרות', path: '/admin/positions', icon: Briefcase, badge: null },
    { label: 'ניתוח ומגמות', path: '/admin/analytics', icon: BarChart3, badge: null },
    { label: 'תזכורות ומועדים', path: '/admin/reminders', icon: Bell, badge: null },
    { label: 'משרד החינוך', path: '/admin/ministry', icon: BookOpen, badge: null },
  ] : [];

  const employeeItems = user?.role === 'employee' ? [
    { label: 'הצעות שנדחו', path: '/portal/rejected', icon: AlertCircle, badge: rejectedCount > 0 ? rejectedCount : null },
  ] : [];

  return (
    <div className="w-sidebar bg-gradient-to-b from-slate-800 to-slate-900 text-white h-screen fixed right-0 top-0 flex flex-col shadow-lg p-6">
      {/* Logo */}
      <div className="mb-10">
        <h1 className="text-2xl font-hebrew font-bold">SmartHub</h1>
        <p className="text-xs text-primary-200 mt-2">פלטפורמה לניהול תקציב</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = isActive(item.path);
          
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-colors justify-between ${
                active
                  ? 'bg-slate-600 text-white shadow-md'
                  : 'text-slate-300 hover:text-white hover:bg-slate-700'
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon size={20} />
                <span className="text-sm font-medium">{item.label}</span>
              </div>
            </Link>
          );
        })}

        {/* Admin Items */}
        {adminItems.length > 0 && (
          <>
            <div className="border-t border-slate-700 my-2 pt-2">
              <p className="text-xs text-slate-500 font-hebrew px-4 mb-2">ניהול</p>
            </div>
            {adminItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.path);
              
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-colors justify-between ${
                    active
                      ? 'bg-slate-600 text-white shadow-md'
                      : 'text-slate-300 hover:text-white hover:bg-slate-700'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon size={20} />
                    <span className="text-sm font-medium">{item.label}</span>
                  </div>
                  {item.badge && (
                    <span className="inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-white bg-red-600 rounded-full">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </>
        )}

        {/* Employee Items */}
        {employeeItems.length > 0 && (
          <>
            <div className="border-t border-slate-700 my-2 pt-2">
              <p className="text-xs text-slate-500 font-hebrew px-4 mb-2">הצעות</p>
            </div>
            {employeeItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.path);
              
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-colors justify-between ${
                    active
                      ? 'bg-slate-600 text-white shadow-md'
                      : 'text-slate-300 hover:text-white hover:bg-slate-700'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon size={20} />
                    <span className="text-sm font-medium">{item.label}</span>
                  </div>
                  {item.badge && (
                    <span className="inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-white bg-red-600 rounded-full">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </>
        )}
      </nav>

      {/* User Profile and Logout */}
      <div className="border-t border-slate-700 pt-4">
        <div className="text-sm text-slate-300 mb-4">
          <span className="block font-medium text-white">שלום,</span>
          <span className="block truncate text-slate-400">{user?.first_name} {user?.last_name}</span>
        </div>
        <button
          onClick={logout}
          className="w-full flex items-center gap-2 px-4 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors font-medium"
        >
          <LogOut size={16} />
          <span>התנתקות</span>
        </button>
      </div>
    </div>
  );
}
