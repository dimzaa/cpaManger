import React, { useState, useEffect, useCallback } from 'react';
import PortalWrapper from '../components/portal/PortalWrapper';
import { useAuth } from '../context/AuthContext';
import { remindersAPI, notificationsAPI } from '../services/api';
import { Calendar, Clock, ChevronDown, ChevronUp, X, CheckCircle, Bell, BellOff, BookOpen, AlertCircle } from 'lucide-react';

const MONTH_NAMES = {
  1: 'ינואר', 2: 'פברואר', 3: 'מרץ', 4: 'אפריל',
  5: 'מאי', 6: 'יוני', 7: 'יולי', 8: 'אוגוסט',
  9: 'ספטמבר', 10: 'אוקטובר', 11: 'נובמבר', 12: 'דצמבר',
};

function urgencyConfig(urgency) {
  switch (urgency) {
    case 'critical': return { bg: 'bg-red-50', border: 'border-red-400', text: 'text-red-700', badge: 'bg-red-100 text-red-700', icon: '🚨', label: 'דחוף מאוד' };
    case 'high':     return { bg: 'bg-amber-50', border: 'border-amber-400', text: 'text-amber-700', badge: 'bg-amber-100 text-amber-700', icon: '⚠️', label: 'דחוף' };
    case 'medium':   return { bg: 'bg-blue-50', border: 'border-blue-400', text: 'text-blue-700', badge: 'bg-blue-100 text-blue-700', icon: '📋', label: 'בינוני' };
    default:         return { bg: 'bg-slate-50', border: 'border-slate-300', text: 'text-slate-600', badge: 'bg-slate-100 text-slate-600', icon: '🔔', label: 'רגיל' };
  }
}

function daysLabel(days) {
  if (days === null || days === undefined) return '—';
  if (days === 0) return 'היום!';
  if (days === 1) return 'מחר';
  if (days < 0) return 'עבר';
  return `${days} ימים`;
}

// ─── DEADLINE DETAIL MODAL ────────────────────────────────────────────────────
function DeadlineModal({ deadline, upcoming, onClose, onDismiss }) {
  if (!deadline) return null;
  const cfg = urgencyConfig(deadline.urgency);

  // Get reminder dates for this deadline from upcoming list
  const myReminders = upcoming.filter(r => r.deadline_id === deadline.id);

  const nextDate = deadline.next_deadline_date
    ? new Date(deadline.next_deadline_date)
    : null;
  const nextDateStr = nextDate
    ? `${nextDate.getDate()} ${MONTH_NAMES[nextDate.getMonth() + 1]} ${nextDate.getFullYear()}`
    : '—';

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" dir="rtl">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className={`p-6 border-b border-slate-100 ${cfg.bg}`}>
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-xl font-hebrew font-bold text-slate-800 leading-snug">
                {cfg.icon} {deadline.title}
              </h2>
              <p className="text-sm text-slate-500 font-hebrew mt-1">{deadline.deadline_type === 'quarterly' ? 'רבעוני' : 'שנתי'}</p>
            </div>
            <button onClick={onClose} className="p-2 hover:bg-white/60 rounded-lg transition">
              <X size={20} className="text-slate-500" />
            </button>
          </div>
        </div>

        <div className="p-6 space-y-5" dir="rtl">
          {/* Dates */}
          <div className="flex gap-4">
            <div className="flex-1 bg-slate-50 rounded-xl p-4 text-center">
              <p className="text-xs font-hebrew text-slate-500 mb-1">מועד אחרון</p>
              <p className="font-hebrew font-bold text-slate-800 text-sm">{nextDateStr}</p>
            </div>
            <div className={`flex-1 rounded-xl p-4 text-center ${cfg.bg}`}>
              <p className="text-xs font-hebrew text-slate-500 mb-1">ימים שנותרו</p>
              <p className={`font-hebrew font-bold text-lg ${cfg.text}`}>
                {daysLabel(deadline.days_until)}
              </p>
            </div>
          </div>

          {/* Description */}
          {deadline.description && (
            <div>
              <h4 className="font-hebrew font-semibold text-slate-700 mb-2">📝 פרטים</h4>
              <p className="font-hebrew text-sm text-slate-600 leading-relaxed">{deadline.description}</p>
            </div>
          )}

          {/* Reminders schedule */}
          {myReminders.length > 0 && (
            <div>
              <h4 className="font-hebrew font-semibold text-slate-700 mb-3">🔔 תזכורות אוטומטיות:</h4>
              <div className="space-y-2">
                {myReminders.map(r => {
                  const rDate = new Date(r.reminder_date);
                  const rDateStr = `${rDate.getDate()} ${MONTH_NAMES[rDate.getMonth() + 1]}`;
                  const isPast = r.days_until_reminder < 0;
                  const isSent = r.status === 'sent';
                  return (
                    <div key={r.id} className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        {isSent ? (
                          <CheckCircle size={16} className="text-green-500" />
                        ) : isPast ? (
                          <div className="w-4 h-4 rounded-full border-2 border-slate-300" />
                        ) : (
                          <div className="w-4 h-4 rounded-full border-2 border-blue-400" />
                        )}
                        <span className="font-hebrew text-sm text-slate-700">
                          {r.days_before} ימים לפני — {rDateStr}
                        </span>
                      </div>
                      <span className={`text-xs font-hebrew px-2 py-0.5 rounded-full ${
                        isSent ? 'bg-green-100 text-green-700' :
                        r.status === 'dismissed' ? 'bg-slate-100 text-slate-500' :
                        'bg-blue-100 text-blue-700'
                      }`}>
                        {isSent ? '✅ נשלחה' : r.status === 'dismissed' ? 'בוטלה' : '⏳ ממתין'}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Action required */}
          {deadline.action_required && (
            <div className="bg-blue-50 rounded-xl p-4">
              <h4 className="font-hebrew font-semibold text-blue-800 mb-2">📋 מה צריך לעשות:</h4>
              <p className="font-hebrew text-sm text-blue-700 leading-relaxed">{deadline.action_required}</p>
            </div>
          )}

          {/* Ministry reference */}
          {deadline.ministry_reference && (
            <div className="flex items-center gap-2 text-slate-400">
              <BookOpen size={14} />
              <span className="font-hebrew text-xs">מקור: {deadline.ministry_reference}</span>
            </div>
          )}

          {/* Topic codes */}
          {deadline.topic_codes && deadline.topic_codes.length > 0 && !deadline.topic_codes.includes('all') && (
            <div className="flex items-center gap-2">
              <span className="font-hebrew text-xs text-slate-500">קודי נושא:</span>
              {deadline.topic_codes.map(tc => (
                <span key={tc} className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full font-mono">{tc}</span>
              ))}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-2 border-t border-slate-100">
            <button
              onClick={onClose}
              className="flex-1 py-2.5 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-hebrew text-sm font-medium transition"
            >
              סגור
            </button>
            {myReminders.some(r => r.status === 'pending') && (
              <button
                onClick={() => { onDismiss(myReminders.filter(r => r.status === 'pending').map(r => r.id)); onClose(); }}
                className="flex-1 py-2.5 px-4 bg-red-50 hover:bg-red-100 text-red-700 rounded-xl font-hebrew text-sm font-medium transition flex items-center justify-center gap-2"
              >
                <BellOff size={15} />
                בטל תזכורת
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── TIMELINE ITEM ────────────────────────────────────────────────────────────
function TimelineItem({ item, onClick }) {
  const cfg = urgencyConfig(item.urgency);
  const rDate = new Date(item.reminder_date);
  const dateStr = `${rDate.getDate()} ${MONTH_NAMES[rDate.getMonth() + 1]}`;

  return (
    <div
      className={`relative mr-6 mb-3 p-4 rounded-xl border-r-4 cursor-pointer transition hover:shadow-md ${cfg.bg} ${cfg.border}`}
      onClick={onClick}
    >
      <div className="absolute -right-7 top-4 w-4 h-4 rounded-full bg-white border-2 border-current" style={{ borderColor: cfg.border.replace('border-', '') }} />
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-base">{cfg.icon}</span>
            <span className="font-hebrew font-semibold text-slate-800 text-sm">{item.deadline_title}</span>
          </div>
          <p className="font-hebrew text-xs text-slate-500">
            תזכורת: {dateStr} | מועד אחרון: {item.deadline_date ? new Date(item.deadline_date).toLocaleDateString('he-IL') : '—'}
          </p>
          {item.action_required && (
            <p className="font-hebrew text-xs text-slate-600 mt-1 truncate">{item.action_required}</p>
          )}
        </div>
        <div className="text-right flex-shrink-0">
          <div className={`text-xs font-hebrew font-bold px-2 py-1 rounded-full ${cfg.badge}`}>
            {daysLabel(item.days_until_deadline)}
          </div>
          {item.status === 'dismissed' && (
            <div className="text-xs text-slate-400 font-hebrew mt-1">בוטל</div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── MAIN PAGE ────────────────────────────────────────────────────────────────
export default function PortalDeadlinesPage() {
  const { user } = useAuth();
  const municipalityId = user?.municipality_id;

  const [deadlines, setDeadlines] = useState([]);
  const [upcoming, setUpcoming] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDeadline, setSelectedDeadline] = useState(null);
  const [expandedRows, setExpandedRows] = useState(new Set());
  const [dismissing, setDismissing] = useState(false);

  const load = useCallback(async () => {
    if (!municipalityId) return;
    setLoading(true);
    try {
      const [dRes, uRes] = await Promise.all([
        remindersAPI.getDeadlines(),
        remindersAPI.getUpcoming(municipalityId),
      ]);
      setDeadlines(dRes.data || []);
      setUpcoming(uRes.data || []);
    } catch (e) {
      console.error('Failed to load deadlines:', e);
    } finally {
      setLoading(false);
    }
  }, [municipalityId]);

  useEffect(() => { load(); }, [load]);

  const handleDismiss = async (reminderIds) => {
    setDismissing(true);
    try {
      await Promise.all(reminderIds.map(id => remindersAPI.dismiss(id)));
      await load();
    } finally {
      setDismissing(false);
    }
  };

  const toggleRow = (id) => {
    setExpandedRows(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  // Group upcoming by month
  const upcomingByMonth = {};
  upcoming.forEach(u => {
    const d = new Date(u.reminder_date);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    const label = `${MONTH_NAMES[d.getMonth() + 1]} ${d.getFullYear()}`;
    if (!upcomingByMonth[key]) upcomingByMonth[key] = { label, items: [] };
    upcomingByMonth[key].items.push(u);
  });

  // Count urgent (≤30 days)
  const urgentCount = upcoming.filter(u => (u.days_until_deadline ?? 999) <= 30).length;

  const openModal = (deadlineId) => {
    const dl = deadlines.find(d => d.id === deadlineId);
    if (dl) setSelectedDeadline(dl);
  };

  return (
    <PortalWrapper title="מועדים חשובים">
      <div dir="rtl" className="max-w-5xl mx-auto space-y-8">

        {/* Header */}
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-2xl font-hebrew font-bold text-slate-800 flex items-center gap-3">
              <Calendar size={28} className="text-blue-600" />
              מועדים חשובים
            </h1>
            <p className="text-slate-500 font-hebrew text-sm mt-1">
              תזכורות אוטומטיות למועדי הגשה של משרד החינוך
            </p>
          </div>
          {urgentCount > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-2 flex items-center gap-2">
              <AlertCircle size={16} className="text-amber-600" />
              <span className="font-hebrew text-sm text-amber-700 font-semibold">
                {urgentCount} מועדים בחודש הקרוב
              </span>
            </div>
          )}
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20 text-slate-400">
            <div className="w-8 h-8 border-2 border-blue-400 border-t-transparent rounded-full animate-spin mr-3" />
            <span className="font-hebrew">טוען...</span>
          </div>
        ) : (
          <>
            {/* ── UPCOMING TIMELINE ── */}
            {Object.keys(upcomingByMonth).length > 0 && (
              <section>
                <h2 className="font-hebrew font-bold text-slate-700 text-lg mb-4 flex items-center gap-2">
                  <Clock size={20} className="text-blue-500" />
                  הקרובים ביותר
                  <span className="text-sm font-normal text-slate-400">(90 ימים הבאים)</span>
                </h2>

                <div className="space-y-6">
                  {Object.entries(upcomingByMonth).map(([key, { label, items }]) => (
                    <div key={key}>
                      <div className="font-hebrew font-semibold text-slate-500 text-sm mb-3 pb-1 border-b border-slate-200">
                        {label}
                      </div>
                      <div className="border-r-2 border-slate-200 pr-4">
                        {items.map(item => (
                          <TimelineItem
                            key={item.id}
                            item={item}
                            onClick={() => openModal(item.deadline_id)}
                          />
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {upcoming.length === 0 && (
              <div className="bg-green-50 border border-green-200 rounded-2xl p-8 text-center">
                <CheckCircle size={32} className="text-green-500 mx-auto mb-3" />
                <p className="font-hebrew font-semibold text-green-800 text-lg">אין מועדים דחופים בחודשיים הקרובים</p>
                <p className="font-hebrew text-green-600 text-sm mt-1">ניתן לראות את כל המועדים בטבלה למטה</p>
              </div>
            )}

            {/* ── ALL DEADLINES TABLE ── */}
            <section>
              <h2 className="font-hebrew font-bold text-slate-700 text-lg mb-4 flex items-center gap-2">
                <Bell size={20} className="text-blue-500" />
                כל מועדי ההגשה
              </h2>

              <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
                <table className="w-full">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200">
                      <th className="text-right font-hebrew text-xs font-semibold text-slate-500 px-4 py-3">נושא</th>
                      <th className="text-right font-hebrew text-xs font-semibold text-slate-500 px-4 py-3">מועד הגשה</th>
                      <th className="text-right font-hebrew text-xs font-semibold text-slate-500 px-4 py-3">ימים שנותרו</th>
                      <th className="text-right font-hebrew text-xs font-semibold text-slate-500 px-4 py-3">קוד</th>
                      <th className="px-4 py-3" />
                    </tr>
                  </thead>
                  <tbody>
                    {deadlines.map(dl => {
                      const cfg = urgencyConfig(dl.urgency);
                      const isExpanded = expandedRows.has(dl.id);
                      const nextDate = dl.next_deadline_date ? new Date(dl.next_deadline_date) : null;
                      const nextStr = nextDate
                        ? `${nextDate.getDate()} ${MONTH_NAMES[nextDate.getMonth() + 1]} ${nextDate.getFullYear()}`
                        : '—';

                      return (
                        <React.Fragment key={dl.id}>
                          <tr className="border-b border-slate-100 hover:bg-slate-50 transition">
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-2">
                                <span>{cfg.icon}</span>
                                <span className="font-hebrew font-medium text-slate-800 text-sm">{dl.title}</span>
                              </div>
                            </td>
                            <td className="px-4 py-3 font-hebrew text-sm text-slate-600">{nextStr}</td>
                            <td className="px-4 py-3">
                              <span className={`font-hebrew text-xs font-bold px-2 py-1 rounded-full ${cfg.badge}`}>
                                {daysLabel(dl.days_until)}
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              {dl.topic_codes && !dl.topic_codes.includes('all') && (
                                <div className="flex flex-wrap gap-1">
                                  {dl.topic_codes.map(tc => (
                                    <span key={tc} className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono">{tc}</span>
                                  ))}
                                </div>
                              )}
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-2">
                                <button
                                  onClick={() => setSelectedDeadline(dl)}
                                  className="text-xs font-hebrew text-blue-600 hover:text-blue-800 font-medium px-2 py-1 rounded hover:bg-blue-50"
                                >
                                  פרטים
                                </button>
                                <button
                                  onClick={() => toggleRow(dl.id)}
                                  className="p-1 text-slate-400 hover:text-slate-600"
                                >
                                  {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                                </button>
                              </div>
                            </td>
                          </tr>
                          {isExpanded && (
                            <tr className={`${cfg.bg}`}>
                              <td colSpan={5} className="px-6 py-4 border-b border-slate-100">
                                <div className="space-y-3" dir="rtl">
                                  {dl.description && (
                                    <p className="font-hebrew text-sm text-slate-700">{dl.description}</p>
                                  )}
                                  {dl.action_required && (
                                    <div className="bg-white/60 rounded-xl p-3">
                                      <p className="font-hebrew text-xs font-semibold text-slate-600 mb-1">📋 מה צריך לעשות:</p>
                                      <p className="font-hebrew text-sm text-slate-700">{dl.action_required}</p>
                                    </div>
                                  )}
                                  {dl.ministry_reference && (
                                    <p className="font-hebrew text-xs text-slate-400 flex items-center gap-1">
                                      <BookOpen size={12} />
                                      מקור: {dl.ministry_reference}
                                    </p>
                                  )}
                                </div>
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
      </div>

      {/* Detail modal */}
      {selectedDeadline && (
        <DeadlineModal
          deadline={selectedDeadline}
          upcoming={upcoming}
          onClose={() => setSelectedDeadline(null)}
          onDismiss={handleDismiss}
        />
      )}
    </PortalWrapper>
  );
}
