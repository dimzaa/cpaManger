import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Bell, X, Check, CheckCheck, ChevronLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { notificationsAPI } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

const TYPE_ICON = {
  deadline_reminder: '🔔',
  budget_updated: '📊',
  suggestion_approved: '✅',
  suggestion_rejected: '❌',
  large_discrepancy: '⚠️',
  new_report: '📄',
};

const TYPE_COLOR = {
  deadline_reminder: 'bg-amber-50 border-amber-200',
  budget_updated: 'bg-blue-50 border-blue-200',
  suggestion_approved: 'bg-green-50 border-green-200',
  suggestion_rejected: 'bg-red-50 border-red-200',
  large_discrepancy: 'bg-orange-50 border-orange-200',
  new_report: 'bg-purple-50 border-purple-200',
};

export default function NotificationBell() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const panelRef = useRef(null);
  const intervalRef = useRef(null);

  const municipalityId = user?.municipality_id;

  // Don't render if no municipality context
  if (!municipalityId) return null;

  const fetchCount = useCallback(async () => {
    try {
      const res = await notificationsAPI.getUnreadCount(municipalityId);
      setUnreadCount(res.data?.count ?? 0);
    } catch {
      // silent
    }
  }, [municipalityId]);

  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const res = await notificationsAPI.getAll(municipalityId, 15);
      setNotifications(res.data || []);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [municipalityId]);

  // Initial + periodic count refresh
  useEffect(() => {
    fetchCount();
    intervalRef.current = setInterval(fetchCount, 60000);
    return () => clearInterval(intervalRef.current);
  }, [fetchCount]);

  // Fetch notifications when opening the panel
  useEffect(() => {
    if (open) fetchNotifications();
  }, [open, fetchNotifications]);

  // Close on outside click
  useEffect(() => {
    const handleClick = (e) => {
      if (panelRef.current && !panelRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    if (open) document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  const handleMarkRead = async (id) => {
    try {
      await notificationsAPI.markRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch {
      // silent
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationsAPI.markAllRead(municipalityId);
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch {
      // silent
    }
  };

  const handleAction = (notif) => {
    handleMarkRead(notif.id);
    setOpen(false);
    if (notif.action_url) navigate(notif.action_url);
  };

  return (
    <div className="relative" ref={panelRef}>
      {/* Bell button */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="relative p-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-600 transition-colors"
        title="התראות"
      >
        <Bell size={22} />
        {unreadCount > 0 && (
          <span className="absolute top-0.5 right-0.5 min-w-[18px] h-[18px] rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center px-1 leading-none">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown panel */}
      {open && (
        <div
          className="absolute left-0 top-12 w-96 max-h-[520px] bg-white rounded-2xl shadow-2xl border border-slate-200 flex flex-col z-50"
          dir="rtl"
          style={{ minWidth: '360px' }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
            <h3 className="font-hebrew font-semibold text-slate-800 text-base">
              התראות
              {unreadCount > 0 && (
                <span className="mr-2 text-xs bg-red-100 text-red-600 rounded-full px-2 py-0.5">
                  {unreadCount} חדשות
                </span>
              )}
            </h3>
            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1 font-hebrew"
                  title="סמן הכל כנקרא"
                >
                  <CheckCheck size={14} />
                  סמן הכל כנקרא
                </button>
              )}
              <button
                onClick={() => setOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* List */}
          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center py-12 text-slate-400 font-hebrew text-sm">
                טוען...
              </div>
            ) : notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-slate-400">
                <Bell size={32} className="mb-2 opacity-30" />
                <p className="font-hebrew text-sm">אין התראות חדשות</p>
              </div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  className={`px-4 py-3 border-b border-slate-50 transition-colors ${
                    n.is_read ? 'bg-slate-50' : 'bg-white'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <span className="text-lg flex-shrink-0 mt-0.5">
                      {TYPE_ICON[n.type] || '🔔'}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p
                        className={`font-hebrew text-sm font-semibold leading-snug ${
                          n.is_read ? 'text-slate-500' : 'text-slate-800'
                        }`}
                      >
                        {n.title}
                      </p>
                      {n.message && (
                        <p className="font-hebrew text-xs text-slate-500 mt-0.5 leading-relaxed">
                          {n.message}
                        </p>
                      )}
                      <div className="flex items-center gap-3 mt-2">
                        {n.action_url && n.action_text && (
                          <button
                            onClick={() => handleAction(n)}
                            className="text-xs text-blue-600 hover:text-blue-800 font-hebrew font-medium flex items-center gap-1"
                          >
                            {n.action_text}
                            <ChevronLeft size={12} />
                          </button>
                        )}
                        <span className="text-xs text-slate-400 font-hebrew mr-auto">
                          {n.time_ago}
                        </span>
                        {!n.is_read && (
                          <button
                            onClick={() => handleMarkRead(n.id)}
                            className="text-xs text-slate-400 hover:text-slate-600 flex items-center gap-1"
                            title="סמן כנקרא"
                          >
                            <Check size={12} />
                          </button>
                        )}
                      </div>
                    </div>
                    {!n.is_read && (
                      <div className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0 mt-2" />
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          <div className="border-t border-slate-100 p-3">
            <button
              onClick={() => { setOpen(false); navigate('/portal/deadlines'); }}
              className="w-full text-center text-sm text-blue-600 hover:text-blue-800 font-hebrew font-medium py-1"
            >
              ראה כל ההתראות ←
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
