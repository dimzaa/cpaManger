import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import PortalWrapper from '../components/portal/PortalWrapper';
import { useAuth } from '../context/AuthContext';
import { positionsAPI, deadlinesAPI } from '../services/api';
import { formatShekel, getLast12Months, formatHebrewDate } from '../utils/format';

// ─── Severity helpers ────────────────────────────────────────────────────────
const SEVERITY_CONFIG = {
  critical: {
    border: 'border-red-400',
    bg: 'bg-red-50',
    badge: 'bg-red-100 text-red-700 border border-red-300',
    icon: '🔴',
  },
  attention: {
    border: 'border-amber-400',
    bg: 'bg-amber-50',
    badge: 'bg-amber-100 text-amber-700 border border-amber-300',
    icon: '🟡',
  },
  ok: {
    border: 'border-green-400',
    bg: 'bg-green-50',
    badge: 'bg-green-100 text-green-700 border border-green-300',
    icon: '🟢',
  },
  surplus: {
    border: 'border-blue-400',
    bg: 'bg-blue-50',
    badge: 'bg-blue-100 text-blue-700 border border-blue-300',
    icon: '🔵',
  },
  none: {
    border: 'border-gray-300',
    bg: 'bg-gray-50',
    badge: 'bg-gray-100 text-gray-600 border border-gray-200',
    icon: '⚪',
  },
  routine: {
    border: 'border-orange-300',
    bg: 'bg-orange-50',
    badge: 'bg-orange-100 text-orange-700 border border-orange-200',
    icon: '🟠',
  },
};

function getSeverityConfig(severity) {
  return SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.none;
}

// ─── Formula section (collapsible) ───────────────────────────────────────────
function FormulaSection({ position }) {
  const [open, setOpen] = useState(false);
  const fp = position.formula_parts || {};
  const divisor = fp.divisor;

  return (
    <div className="border-t border-gray-100 pt-3">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 font-medium font-hebrew transition-colors"
      >
        <span>📐 איך חושב?</span>
        <span className={`transition-transform ${open ? 'rotate-180' : ''}`}>▼</span>
      </button>

      {open && (
        <div
          className="mt-3 bg-blue-50 border border-blue-100 rounded-lg p-4 text-right font-hebrew text-sm space-y-2"
          dir="rtl"
        >
          {fp.total_children != null && (
            <div className="flex items-start gap-2">
              <span className="text-blue-400 font-bold">•</span>
              <span>
                <strong>סך ילדים מתוקצבים:</strong> {fp.total_children.toLocaleString()} ילדים
              </span>
            </div>
          )}

          {divisor != null && (
            <div className="flex items-start gap-2">
              <span className="text-blue-400 font-bold">•</span>
              <span>
                <strong>קבוע חישוב:</strong>{' '}
                <span
                  title={`קבוע של משרד החינוך: ${divisor} ילדים לגן עבור רשויות ${divisor === 31 ? 'המקבלות מענק איזון' : 'שאינן מקבלות מענק'}`}
                  className="inline-block font-bold text-red-600 border-b border-dotted border-red-400 cursor-help"
                >
                  [{divisor}]
                </span>{' '}
                ילדים לגן
              </span>
            </div>
          )}

          {fp.kindergartens != null && (
            <div className="flex items-start gap-2">
              <span className="text-blue-400 font-bold">•</span>
              <span>
                {fp.total_children} ÷ [{divisor}] = <strong>{fp.kindergartens}</strong> גני ילדים
              </span>
            </div>
          )}

          {fp.positions != null && (
            <div className="flex items-start gap-2">
              <span className="text-blue-400 font-bold">•</span>
              <span>
                {fp.kindergartens} גנים × 1 עוזרת לגן = <strong>{fp.positions}</strong> משרות
              </span>
            </div>
          )}

          {fp.formula_text && (
            <div className="mt-2 bg-white rounded p-3 border border-blue-200 text-blue-900 font-mono text-xs leading-relaxed">
              {fp.formula_text}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Email button ─────────────────────────────────────────────────────────────
function EmailButton({ subject, body }) {
  const [copied, setCopied] = useState(false);

  const handleEmail = () => {
    const mailto = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    window.open(mailto, '_blank');
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(`נושא: ${subject}\n\n${body}`);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  };

  return (
    <div className="flex gap-2 flex-wrap">
      <button
        onClick={handleEmail}
        className="flex items-center gap-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium font-hebrew transition-colors"
      >
        <span>📧 שלח מייל לרשות</span>
      </button>
      <button
        onClick={handleCopy}
        className="flex items-center gap-1 px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm font-medium font-hebrew transition-colors"
      >
        <span>{copied ? '✅' : '📋'}</span>
        <span>{copied ? 'הועתק!' : 'העתק פרטים'}</span>
      </button>
    </div>
  );
}

// ─── Position card ────────────────────────────────────────────────────────────
function PositionCard({ position }) {
  const cfg = getSeverityConfig(position.severity);
  const hasMissingGap = position.gap > 0 && position.gap_direction === 'missing';
  const hasSurplus = position.gap_direction === 'surplus';

  return (
    <div
      className={`bg-white rounded-2xl border-2 ${cfg.border} shadow-sm overflow-hidden`}
      dir="rtl"
    >
      {/* Card Header */}
      <div className={`${cfg.bg} px-6 py-4 flex items-center justify-between flex-wrap gap-3`}>
        <div className="flex items-center gap-3">
          <span className="text-2xl">{position.icon}</span>
          <div>
            <h3 className="font-hebrew font-bold text-lg text-gray-800">
              {position.type}
            </h3>
            <span className="text-xs text-gray-500 font-hebrew">קוד {position.code}</span>
          </div>
        </div>
        <span className={`px-3 py-1 rounded-full text-sm font-medium font-hebrew ${cfg.badge}`}>
          {cfg.icon} {position.status}
          {hasMissingGap ? ` — חסר ${position.gap}` : ''}
          {hasSurplus ? ` — עודף ${Math.abs(position.gap)}` : ''}
        </span>
      </div>

      <div className="px-6 py-5 space-y-5">
        {/* Current vs. Entitled (only when not "none" severity) */}
        {position.severity !== 'none' && (
          <div className="flex items-center justify-center gap-6 py-2">
            <div className="text-center">
              <div className="text-3xl font-bold text-gray-700">{position.current}</div>
              <div className="text-xs text-gray-500 font-hebrew mt-1">קיים כרגע</div>
            </div>
            <div className="flex flex-col items-center gap-1">
              <div className="text-2xl text-gray-400">→</div>
              {hasMissingGap && (
                <span className="text-xs text-red-600 font-hebrew font-semibold">
                  ❌ חסר {position.gap}
                </span>
              )}
              {hasSurplus && (
                <span className="text-xs text-blue-600 font-hebrew font-semibold">
                  ➕ עודף {Math.abs(position.gap)}
                </span>
              )}
              {position.gap_direction === 'ok' && (
                <span className="text-xs text-green-600 font-hebrew font-semibold">✅ תקין</span>
              )}
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-blue-700">{position.entitled}</div>
              <div className="text-xs text-gray-500 font-hebrew mt-1">מגיע לך</div>
            </div>
          </div>
        )}

        {/* Formula (collapsible) */}
        {position.formula_parts?.formula_text && (
          <FormulaSection position={position} />
        )}

        {/* Financial value */}
        {position.annual_gap_value > 0 && (
          <div className="border-t border-gray-100 pt-3">
            <p className="text-sm text-gray-500 font-hebrew mb-2">💰 שווי כספי אפשרי:</p>
            <div className="bg-green-50 border border-green-200 rounded-lg p-3">
              <p className="font-bold text-green-800 font-hebrew text-right">
                {formatShekel(position.annual_gap_value)} לשנה
              </p>
              {position.monthly_gap_value > 0 && (
                <p className="text-sm text-green-600 font-hebrew text-right mt-1">
                  ({formatShekel(position.monthly_gap_value)} לחודש)
                </p>
              )}
            </div>
          </div>
        )}

        {/* What to do */}
        {position.what_to_do?.length > 0 && position.gap > 0 && (
          <div className="border-t border-gray-100 pt-3">
            <p className="text-sm text-gray-500 font-hebrew mb-2">📋 מה לעשות:</p>
            <ul className="space-y-1">
              {position.what_to_do.map((item, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-700 font-hebrew">
                  <span className="text-green-500 mt-0.5 flex-shrink-0">✓</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Ministry reference */}
        {position.ministry_reference && (
          <div className="border-t border-gray-100 pt-3 flex items-center justify-between flex-wrap gap-3">
            <span className="text-xs text-gray-400 font-hebrew">
              📖 מקור: {position.ministry_reference}
            </span>
            {position.gap > 0 && (
              <EmailButton
                subject={position.email_subject}
                body={position.email_body}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Summary card ─────────────────────────────────────────────────────────────
function SummaryCard({ icon, label, value, colorClass }) {
  return (
    <div className={`bg-white rounded-xl border shadow-sm p-4 text-center ${colorClass}`}>
      <div className="text-2xl mb-1">{icon}</div>
      <div className="text-2xl font-bold text-gray-800">{value}</div>
      <div className="text-xs text-gray-500 font-hebrew mt-1">{label}</div>
    </div>
  );
}

const BUDGET_CODES_GUIDE = [
  { code: '3', name: 'שכל"מ גני ילדים', what: 'תקציב גני ילדים (עיקרי)', formula: 'ילדים × תעריף × אחוז השתתפות' },
  { code: '19', name: 'עוזרות לגננות', what: 'עוזרת אחת לכל גן', formula: 'מספר גנים × טבלת שכר × 90%' },
  { code: '33', name: 'גננות עובדות מדינה', what: 'קיזוז גננות עובדות מדינה', formula: 'מספר גננות × שכר (שורת זיכוי שלילית)' },
  { code: '5/45', name: 'קב"ס', what: 'קצין ביקור סדיר', formula: 'שכר קב"ס × 75%' },
  { code: '50', name: 'הסעות', what: 'השתתפות בהסעות', formula: 'מסלולים × תעריף למסלול' },
  { code: '47', name: 'שירותים פסיכולוגיים', what: 'הקצאה לשירות פסיכולוגי', formula: 'הקצאה לפי גודל הרשות' },
];

function BudgetCodesGuide() {
  const [open, setOpen] = useState(false);

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden" dir="rtl">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full px-6 py-4 flex items-center justify-between text-right"
      >
        <span className="font-hebrew font-bold text-gray-800">📘 קודי תקצוב מרכזיים (חוברת סגולה)</span>
        <span className="text-gray-500">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="px-6 pb-5">
          <div className="overflow-x-auto border border-gray-100 rounded-lg">
            <table className="w-full text-sm">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-3 py-2 text-right font-hebrew">קוד</th>
                  <th className="px-3 py-2 text-right font-hebrew">שם</th>
                  <th className="px-3 py-2 text-right font-hebrew">מה זה</th>
                  <th className="px-3 py-2 text-right font-hebrew">נוסחת בדיקה</th>
                </tr>
              </thead>
              <tbody>
                {BUDGET_CODES_GUIDE.map((item) => (
                  <tr key={item.code} className="border-t border-gray-100">
                    <td className="px-3 py-2 font-semibold text-gray-800">{item.code}</td>
                    <td className="px-3 py-2 text-gray-700">{item.name}</td>
                    <td className="px-3 py-2 text-gray-600">{item.what}</td>
                    <td className="px-3 py-2 text-gray-600">{item.formula}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Urgency + Status constants ──────────────────────────────────────────────
const URGENCY_STYLES = {
  overdue:   { bg: 'bg-red-50',    border: 'border-red-400',    badge: 'bg-red-100 text-red-800',       label: 'עבר המועד' },
  critical:  { bg: 'bg-red-50',    border: 'border-red-400',    badge: 'bg-red-100 text-red-800',       label: 'דחוף מאוד' },
  urgent:    { bg: 'bg-orange-50', border: 'border-orange-400', badge: 'bg-orange-100 text-orange-800', label: 'דחוף' },
  attention: { bg: 'bg-amber-50',  border: 'border-amber-400',  badge: 'bg-amber-100 text-amber-800',   label: 'מתקרב' },
  upcoming:  { bg: 'bg-blue-50',   border: 'border-blue-400',   badge: 'bg-blue-100 text-blue-800',     label: 'בקרוב' },
  future:    { bg: 'bg-gray-50',   border: 'border-gray-200',   badge: 'bg-gray-100 text-gray-600',     label: 'עתידי' },
};

const STATUS_LABELS = {
  not_started:  { label: 'לא התחיל',   icon: '⚪', color: 'gray' },
  in_progress:  { label: 'בתהליך',     icon: '🔄', color: 'blue' },
  submitted:    { label: 'הוגש',       icon: '📤', color: 'indigo' },
  approved:     { label: 'אושר',       icon: '✅', color: 'green' },
  rejected:     { label: 'נדחה',       icon: '❌', color: 'red' },
  not_relevant: { label: 'לא רלוונטי', icon: '—',  color: 'gray' },
};

// ─── Deadlines tab ────────────────────────────────────────────────────────────
function DeadlinesTab({ municipalityId }) {
  const [deadlines, setDeadlines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => {
    if (!municipalityId) return;
    setLoading(true);
    deadlinesAPI.getDeadlines(municipalityId)
      .then(res => setDeadlines(res.data?.deadlines || []))
      .catch(() => setError('שגיאה בטעינת המועדים'))
      .finally(() => setLoading(false));
  }, [municipalityId]);

  if (loading) return (
    <div className="flex justify-center py-16">
      <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );
  if (error) return (
    <div className="bg-red-50 border border-red-200 rounded-xl p-5 text-center">
      <p className="text-red-700 font-hebrew">{error}</p>
    </div>
  );
  if (!deadlines.length) return (
    <div className="text-center py-16 text-gray-500 font-hebrew">אין מועדים להצגה</div>
  );

  const URGENCY_ORDER = ['overdue', 'critical', 'urgent', 'attention', 'upcoming', 'future'];
  const grouped = URGENCY_ORDER.reduce((acc, u) => {
    const items = deadlines.filter(d => d.urgency === u);
    if (items.length) acc[u] = items;
    return acc;
  }, {});

  return (
    <div className="space-y-6" dir="rtl">
      {Object.entries(grouped).map(([urgency, items]) => {
        const gStyle = URGENCY_STYLES[urgency] || URGENCY_STYLES.future;
        return (
          <div key={urgency}>
            <h3 className="font-bold font-hebrew text-gray-700 mb-3 flex items-center gap-2">
              <span className={`px-2 py-0.5 rounded-full text-xs ${gStyle.badge}`}>{gStyle.label}</span>
              <span className="text-sm text-gray-400">({items.length})</span>
            </h3>
            <div className="space-y-3">
              {items.map(d => {
                const dStyle = URGENCY_STYLES[d.urgency] || URGENCY_STYLES.future;
                const isExpanded = expandedId === d.id;
                const appCfg = STATUS_LABELS[d.application?.status] || STATUS_LABELS.not_started;
                const steps = (d.how_to_submit || '').split('\n').filter(s => s.trim());
                const colorMap = { green: 'border-green-300 text-green-700', blue: 'border-blue-300 text-blue-700', red: 'border-red-300 text-red-700', indigo: 'border-indigo-300 text-indigo-700' };
                return (
                  <div key={d.id} className={`rounded-xl border-2 ${dStyle.border} ${dStyle.bg} overflow-hidden`}>
                    <button
                      className="w-full px-5 py-4 flex items-center justify-between text-right"
                      onClick={() => setExpandedId(isExpanded ? null : d.id)}
                    >
                      <div className="flex items-center gap-2 flex-wrap">
                        {d.days_until != null && (
                          <span className="text-xs text-gray-500 font-hebrew">
                            {d.days_until < 0
                              ? `עבר לפני ${Math.abs(d.days_until)} יום`
                              : d.days_until === 0 ? 'היום!'
                              : `${d.days_until} ימים`}
                          </span>
                        )}
                        <span className={`text-xs px-2 py-0.5 rounded-full border bg-white font-hebrew ${colorMap[appCfg.color] || 'border-gray-300 text-gray-500'}`}>
                          {appCfg.icon} {appCfg.label}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="text-right">
                          <p className="font-bold font-hebrew text-gray-800">{d.title}</p>
                          <p className="text-xs text-gray-500 font-hebrew">{d.deadline_display}</p>
                        </div>
                        <span className="text-gray-400 text-sm">{isExpanded ? '▲' : '▼'}</span>
                      </div>
                    </button>
                    {isExpanded && (
                      <div className="px-5 pb-5 space-y-4 border-t border-inherit bg-white/70">
                        {d.description && (
                          <p className="text-sm text-gray-700 font-hebrew pt-3">{d.description}</p>
                        )}
                        {d.consequence && (
                          <div className="bg-red-50 rounded-lg p-3 border border-red-200">
                            <p className="text-xs font-bold text-red-700 font-hebrew mb-1">⚠️ השלכות אי-עמידה:</p>
                            <p className="text-sm text-red-600 font-hebrew">{d.consequence}</p>
                          </div>
                        )}
                        {steps.length > 0 && (
                          <div>
                            <p className="text-xs font-bold text-gray-600 font-hebrew mb-2">📋 שלבי הגשה:</p>
                            <ol className="space-y-1">
                              {steps.map((step, i) => (
                                <li key={i} className="text-sm text-gray-700 font-hebrew">{step}</li>
                              ))}
                            </ol>
                          </div>
                        )}
                        {d.requires_documents?.length > 0 && (
                          <div>
                            <p className="text-xs font-bold text-gray-600 font-hebrew mb-2">📎 מסמכים נדרשים:</p>
                            <ul className="space-y-1">
                              {d.requires_documents.map((doc, i) => (
                                <li key={i} className="flex items-start gap-2 text-sm text-gray-700 font-hebrew">
                                  <span className="text-blue-500 flex-shrink-0">□</span>
                                  <span>{doc}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {d.ministry_system_display && (
                          <p className="text-xs text-gray-500 font-hebrew">
                            🔗 אמצעי הגשה: {d.ministry_system_display}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Tracking tab ─────────────────────────────────────────────────────────────
function TrackingTab({ municipalityId }) {
  const [deadlines, setDeadlines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [formData, setFormData] = useState({});
  const [saving, setSaving] = useState({});
  const [saved, setSaved] = useState({});

  useEffect(() => {
    if (!municipalityId) return;
    deadlinesAPI.getDeadlines(municipalityId)
      .then(res => {
        const dl = res.data?.deadlines || [];
        setDeadlines(dl);
        const init = {};
        dl.forEach(d => {
          init[d.id] = {
            status: d.application?.status || 'not_started',
            submitted_date: d.application?.submitted_date || '',
            reference_number: d.application?.reference_number || '',
            notes: d.application?.notes || '',
          };
        });
        setFormData(init);
      })
      .finally(() => setLoading(false));
  }, [municipalityId]);

  const updateField = (deadlineId, field, value) =>
    setFormData(f => ({ ...f, [deadlineId]: { ...f[deadlineId], [field]: value } }));

  const handleSave = async (deadlineId) => {
    setSaving(s => ({ ...s, [deadlineId]: true }));
    try {
      await deadlinesAPI.updateApplication(municipalityId, deadlineId, formData[deadlineId]);
      setSaved(s => ({ ...s, [deadlineId]: true }));
      setTimeout(() => setSaved(s => ({ ...s, [deadlineId]: false })), 2500);
    } catch {
      // silent — user can retry
    } finally {
      setSaving(s => ({ ...s, [deadlineId]: false }));
    }
  };

  if (loading) return (
    <div className="flex justify-center py-16">
      <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  const doneCount = deadlines.filter(d => ['submitted', 'approved'].includes(formData[d.id]?.status)).length;
  const progressPct = deadlines.length ? Math.round((doneCount / deadlines.length) * 100) : 0;

  return (
    <div className="space-y-6" dir="rtl">
      {/* Progress bar */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
        <div className="flex items-center justify-between mb-2">
          <span className="font-bold font-hebrew text-gray-700">התקדמות הגשות</span>
          <span className="font-bold text-blue-700">{doneCount} / {deadlines.length}</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className="bg-blue-500 h-3 rounded-full transition-all duration-500"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <p className="text-xs text-gray-500 font-hebrew mt-2">{progressPct}% מהבקשות הוגשו או אושרו</p>
        <div className="flex flex-wrap gap-2 mt-3">
          {Object.entries(STATUS_LABELS).map(([status, cfg]) => {
            const count = deadlines.filter(d => formData[d.id]?.status === status).length;
            if (!count) return null;
            return (
              <span key={status} className="text-xs px-2 py-1 bg-gray-100 rounded-full text-gray-600 font-hebrew">
                {cfg.icon} {cfg.label}: {count}
              </span>
            );
          })}
        </div>
      </div>

      {/* Per-deadline tracking cards */}
      {deadlines.map(d => {
        const urgStyle = URGENCY_STYLES[d.urgency] || URGENCY_STYLES.future;
        const form = formData[d.id] || {};
        return (
          <div key={d.id} className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <div className={`px-5 py-3 ${urgStyle.bg} border-b ${urgStyle.border} flex items-center justify-between flex-wrap gap-2`}>
              <div>
                <p className="font-bold font-hebrew text-gray-800">{d.title}</p>
                <p className="text-xs text-gray-500 font-hebrew">{d.deadline_display}</p>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded-full font-hebrew ${urgStyle.badge}`}>
                {urgStyle.label}
              </span>
            </div>
            <div className="p-5 space-y-4">
              {/* Status buttons */}
              <div>
                <label className="block text-xs font-bold text-gray-600 font-hebrew mb-2">סטטוס בקשה:</label>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(STATUS_LABELS).map(([status, cfg]) => (
                    <button
                      key={status}
                      onClick={() => updateField(d.id, 'status', status)}
                      className={`text-xs px-3 py-1.5 rounded-full border transition-colors font-hebrew ${
                        form.status === status
                          ? 'bg-blue-600 text-white border-blue-600'
                          : 'bg-white text-gray-600 border-gray-300 hover:border-blue-300'
                      }`}
                    >
                      {cfg.icon} {cfg.label}
                    </button>
                  ))}
                </div>
              </div>
              {/* Date + reference */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-gray-600 font-hebrew mb-1">תאריך הגשה:</label>
                  <input
                    type="date"
                    value={form.submitted_date || ''}
                    onChange={e => updateField(d.id, 'submitted_date', e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-600 font-hebrew mb-1">מספר אסמכתא:</label>
                  <input
                    type="text"
                    value={form.reference_number || ''}
                    onChange={e => updateField(d.id, 'reference_number', e.target.value)}
                    placeholder="למשל: 2024-1234"
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-hebrew focus:outline-none focus:ring-2 focus:ring-blue-400"
                    dir="ltr"
                  />
                </div>
              </div>
              {/* Notes */}
              <div>
                <label className="block text-xs font-bold text-gray-600 font-hebrew mb-1">הערות:</label>
                <textarea
                  value={form.notes || ''}
                  onChange={e => updateField(d.id, 'notes', e.target.value)}
                  rows={2}
                  placeholder="הערות נוספות..."
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-hebrew focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none"
                  dir="rtl"
                />
              </div>
              {/* Save */}
              <button
                onClick={() => handleSave(d.id)}
                disabled={saving[d.id]}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-lg text-sm font-hebrew transition-colors"
              >
                {saving[d.id] ? '⏳ שומר...' : saved[d.id] ? '✅ נשמר!' : '💾 שמור'}
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Priority tab ─────────────────────────────────────────────────────────────
function PriorityTab({ municipalityId, selectedMonth }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showFormula, setShowFormula] = useState(false);

  useEffect(() => {
    if (!municipalityId || !selectedMonth) return;
    setLoading(true);
    deadlinesAPI.getPriority(municipalityId, selectedMonth)
      .then(res => setData(res.data))
      .catch(() => setError('שגיאה בטעינת נתוני העדיפות'))
      .finally(() => setLoading(false));
  }, [municipalityId, selectedMonth]);

  if (loading) return (
    <div className="flex justify-center py-16">
      <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );
  if (error) return (
    <div className="bg-red-50 border border-red-200 rounded-xl p-5 text-center">
      <p className="text-red-700 font-hebrew">{error}</p>
    </div>
  );

  const priorities = data?.priorities || [];
  const summary = data?.summary;

  if (!priorities.length) return (
    <div className="text-center py-16 text-gray-500 font-hebrew">אין פערים לדירוג בחודש זה 🎉</div>
  );

  const PRIORITY_BADGE = {
    red:   'bg-red-100 text-red-800 border-red-300',
    amber: 'bg-orange-100 text-orange-800 border-orange-300',
    blue:  'bg-blue-100 text-blue-800 border-blue-300',
    gray:  'bg-gray-100 text-gray-600 border-gray-300',
  };

  return (
    <div className="space-y-5" dir="rtl">
      {/* Formula explanation */}
      <div className="bg-blue-50 rounded-xl border border-blue-200 overflow-hidden">
        <button
          className="w-full px-5 py-3 flex items-center justify-between text-right"
          onClick={() => setShowFormula(f => !f)}
        >
          <span className="font-bold font-hebrew text-blue-800">📐 איך מחושב ציון העדיפות?</span>
          <span className="text-blue-500">{showFormula ? '▲' : '▼'}</span>
        </button>
        {showFormula && (
          <div className="px-5 pb-4 text-sm font-hebrew text-blue-900 space-y-1 border-t border-blue-200">
            <p className="pt-3"><strong>ציון = שווי שנתי × מכפיל דחיפות × מכפיל רצף</strong></p>
            <p><strong>מכפיל דחיפות:</strong> עבר המועד ← 0.5 | פחות מ-30 יום ← 3.0 | פחות מ-60 יום ← 2.0 | פחות מ-90 יום ← 1.5 | אחר ← 1.0</p>
            <p><strong>מכפיל רצף:</strong> חודש 1 ← 1.0 | 2 חודשים ← 1.3 | 3 חודשים ← 1.6 | 4+ ← 2.0</p>
          </div>
        )}
      </div>

      {/* Priority list */}
      {priorities.map((item, idx) => {
        const badgeClass = PRIORITY_BADGE[item.priority_color] || PRIORITY_BADGE.gray;
        return (
          <div key={item.position_type} className="bg-white rounded-xl border-2 border-gray-200 shadow-sm hover:border-blue-200 transition-colors">
            <div className="px-5 py-4 flex items-start gap-4">
              <div className="flex-shrink-0 w-9 h-9 rounded-full bg-gray-100 flex items-center justify-center font-bold text-gray-600 text-sm mt-0.5">
                {idx + 1}
              </div>
              <div className="flex-1 space-y-2">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div>
                    <p className="font-bold font-hebrew text-gray-800">{item.position_name}</p>
                    {item.deadline_display && (
                      <p className="text-xs text-gray-500 font-hebrew">מועד הגשה: {item.deadline_display}</p>
                    )}
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full border font-medium font-hebrew ${badgeClass}`}>
                    {item.priority_label}
                  </span>
                </div>
                <div className="flex flex-wrap gap-3 text-sm">
                  {item.annual_value > 0 && (
                    <span className="font-hebrew text-green-700 font-semibold">{formatShekel(item.annual_value)} שנתי</span>
                  )}
                  {item.days_to_deadline != null && (
                    <span className="font-hebrew text-gray-500">
                      {item.days_to_deadline < 0
                        ? `מועד עבר לפני ${Math.abs(item.days_to_deadline)} יום`
                        : `${item.days_to_deadline} ימים למועד`}
                    </span>
                  )}
                  {item.consecutive_months > 1 && (
                    <span className="font-hebrew text-orange-600">⚠️ {item.consecutive_months} חודשים ברצף</span>
                  )}
                </div>
                {item.why_high_priority?.length > 0 && (
                  <ul className="space-y-0.5">
                    {item.why_high_priority.map((r, i) => (
                      <li key={i} className="text-xs text-gray-600 font-hebrew flex items-start gap-1">
                        <span className="text-gray-400 flex-shrink-0">•</span>
                        <span>{r}</span>
                      </li>
                    ))}
                  </ul>
                )}
                {item.recommended_action && (
                  <div className="bg-blue-50 rounded-lg p-3 border border-blue-100">
                    <p className="text-sm text-blue-800 font-hebrew font-medium">✅ {item.recommended_action}</p>
                    {item.recommended_by && (
                      <p className="text-xs text-blue-600 font-hebrew mt-1">עד: {item.recommended_by}</p>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })}

      {/* Summary */}
      {summary && (
        <div className="bg-green-50 border-2 border-green-300 rounded-xl p-5 text-right" dir="rtl">
          <p className="font-bold font-hebrew text-green-800 text-lg">
            💰 סה"כ פוטנציאל: {formatShekel(summary.total_annual_value)} לשנה
          </p>
          {summary.total_lost_so_far > 0 && (
            <p className="text-sm text-red-700 font-hebrew mt-1">
              📉 הפסד מצטבר עד כה: {formatShekel(summary.total_lost_so_far)}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function PortalPositionsPage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const params = new URLSearchParams(window.location.search);
  const municipalityFromUrl = params.get('municipality')
    ? parseInt(params.get('municipality'))
    : null;
  const monthFromUrl = params.get('month');

  const months = getLast12Months();
  const defaultMonth = months[0]?.value || '';

  const [selectedMonth, setSelectedMonth] = useState(monthFromUrl || defaultMonth);
  const [selectedMunicipality, setSelectedMunicipality] = useState(
    municipalityFromUrl || user?.municipality_id || null
  );
  const [activeTab, setActiveTab] = useState('analysis');
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadAnalysis = useCallback(async () => {
    if (!selectedMunicipality || !selectedMonth) return;
    setLoading(true);
    setError(null);
    try {
      const res = await positionsAPI.getAnalysis(selectedMunicipality, selectedMonth);
      setAnalysis(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'שגיאה בטעינת הנתונים');
    } finally {
      setLoading(false);
    }
  }, [selectedMunicipality, selectedMonth]);

  useEffect(() => {
    if (municipalityFromUrl) setSelectedMunicipality(municipalityFromUrl);
    else if (user?.municipality_id) setSelectedMunicipality(user.municipality_id);
  }, [municipalityFromUrl, user?.municipality_id]);

  useEffect(() => {
    loadAnalysis();
  }, [loadAnalysis]);

  const summary = analysis?.summary;
  const positions = analysis?.positions || [];
  const hasUrgent = summary && (summary.positions_missing > 0 || summary.urgent_count > 0);
  const annualPotential = summary?.total_potential_value || 0;
  const monthlyPotential = annualPotential / 12;

  const handleExportExcel = useCallback(() => {
    if (!positions.length) return;
    const header = ['Position Type', 'Entitled', 'Actual', 'Gap', 'Monthly Value', 'Annual Value'];
    const rows = [header];

    positions.forEach((position) => {
      rows.push([
        position.type || '',
        String(position.entitled ?? 0),
        String(position.current ?? 0),
        String(position.gap ?? 0),
        String(Math.round(position.monthly_gap_value || 0)),
        String(Math.round(position.annual_gap_value || 0)),
      ]);
    });

    const csv = rows.map((r) => r.map((v) => `"${String(v).replaceAll('"', '""')}"`).join(',')).join('\n');
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `positions_gap_${selectedMonth || 'month'}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  }, [positions, selectedMonth]);

  return (
    <PortalWrapper title="משרות ותקנים" onBack={() => navigate('/portal')}>
      <div dir="rtl" className="space-y-6">

        {/* ── Header ─────────────────────────────────────────────────── */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
          <div className="flex items-start justify-between flex-wrap gap-4">
            <div>
              <h1 className="text-2xl font-bold font-hebrew text-gray-800 flex items-center gap-2">
                💼 משרות ותקנים
              </h1>
              <p className="text-sm text-gray-500 font-hebrew mt-1">
                בדיקת זכאות למשרות ותקנים נוספים על פי חוברת התקצוב
              </p>
              <p className="text-sm text-indigo-700 font-hebrew mt-1">
                דף זה מציג את הפער בין מה שהרשות זכאית לקבל לבין מה שקיבלה בפועל, על פי חוברת התקצוב.
              </p>
              {analysis && (
                <p className="text-sm text-blue-700 font-hebrew font-semibold mt-2">
                  {analysis.municipality_name} — {formatHebrewDate(selectedMonth)}
                </p>
              )}
            </div>

            {/* Month selector */}
            <select
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm font-hebrew bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              dir="rtl"
            >
              <option value="">בחר חודש</option>
              {months.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
            <button
              onClick={handleExportExcel}
              disabled={!analysis?.has_data || !positions.length}
              className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-hebrew hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              הורד Excel
            </button>
          </div>

          {/* Grant status */}
          {analysis && !loading && (
            <div className="flex items-center gap-3 mt-4 flex-wrap">
              <span className="text-sm font-hebrew text-gray-600">מצב מענק:</span>
              <span
                className={`px-3 py-1 rounded-full text-sm font-medium font-hebrew ${
                  analysis.divisor === 31
                    ? 'bg-green-100 text-green-700'
                    : 'bg-gray-100 text-gray-600'
                }`}
              >
                {analysis.divisor === 31 ? '🟢' : '⚪'} {analysis.grant_status}
              </span>
              <span
                className="px-3 py-1 bg-blue-50 rounded-full text-sm font-medium font-hebrew text-blue-700 border border-blue-200 cursor-help"
                title={`קבוע חישוב של משרד החינוך: ${analysis.divisor} ילדים לגן עבור רשויות ${analysis.divisor === 31 ? 'המקבלות' : 'שאינן מקבלות'} מענק איזון`}
              >
                קבוע: [{analysis.divisor}] ילדים לגן
              </span>
              {analysis.total_children > 0 && (
                <span className="px-3 py-1 bg-purple-50 rounded-full text-sm font-medium font-hebrew text-purple-700 border border-purple-200">
                  👶 {analysis.total_children.toLocaleString()} ילדים
                </span>
              )}
            </div>
          )}
        </div>

        {/* ── Tab bar ────────────────────────────────────────────────── */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="flex overflow-x-auto" dir="rtl">
            {[
              { id: 'analysis',  label: '📊 ניתוח משרות' },
              { id: 'deadlines', label: '📅 יומן מועדים' },
              { id: 'tracking',  label: '📋 מעקב בקשות' },
              { id: 'priority',  label: '🏆 סדר עדיפויות' },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-shrink-0 px-5 py-3 text-sm font-medium font-hebrew border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-600 text-blue-700 bg-blue-50'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* ── Loading ────────────────────────────────────────────────── */}
        {activeTab === 'analysis' && loading && (
          <div className="flex flex-col items-center justify-center py-16 gap-4">
            <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-gray-600 font-hebrew text-lg">🔍 מנתח נתוני תקציב...</p>
          </div>
        )}

        {/* ── Error ─────────────────────────────────────────────────── */}
        {activeTab === 'analysis' && error && !loading && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-5 text-center">
            <p className="text-red-700 font-hebrew font-semibold text-lg">שגיאה בטעינת הנתונים</p>
            <p className="text-red-600 font-hebrew text-sm mt-1">{error}</p>
            <button
              onClick={loadAnalysis}
              className="mt-3 px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-hebrew hover:bg-red-700 transition-colors"
            >
              נסה שוב
            </button>
          </div>
        )}

        {/* ── No data ───────────────────────────────────────────────── */}
        {activeTab === 'analysis' && analysis && !loading && !analysis.has_data && (
          <div className="bg-gray-50 border border-gray-200 rounded-xl p-10 text-center">
            <p className="text-4xl mb-4">📭</p>
            <p className="text-gray-700 font-hebrew font-semibold text-lg">
              אין נתוני תקציב לחודש זה
            </p>
            <p className="text-gray-500 font-hebrew text-sm mt-2">
              בחר חודש עם נתונים לקבלת ניתוח משרות ותקנים
            </p>
          </div>
        )}

        {/* ── Results ───────────────────────────────────────────────── */}
        {activeTab === 'analysis' && analysis && !loading && analysis.has_data && summary && (
          <>
            <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4" dir="rtl">
              <p className="font-hebrew text-indigo-900">
                המערכת חוסכת עבודה ידנית ומבצעת דברים שאקסל לא עושה לבד: מעקב רב־רשויות, זיהוי תשלומי רטרו, חישוב זכאויות אוטומטי, ויצירת מכתבי PDF מקצועיים.
              </p>
            </div>

            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-emerald-800 font-hebrew">
              <span className="font-semibold">פוטנציאל החזר:</span> {formatShekel(monthlyPotential)} לחודש / {formatShekel(annualPotential)} לשנה
            </div>

            <BudgetCodesGuide />

            {/* Summary cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <SummaryCard
                icon="📊"
                label="נושאים נבדקו"
                value={summary.total_positions_analyzed}
                colorClass="border-gray-200"
              />
              <SummaryCard
                icon="⚠️"
                label="חסרים"
                value={summary.positions_missing}
                colorClass={summary.positions_missing > 0 ? 'border-amber-300' : 'border-gray-200'}
              />
              <SummaryCard
                icon="✅"
                label="תקין"
                value={summary.positions_ok}
                colorClass="border-green-200"
              />
              <SummaryCard
                icon="💰"
                label="פוטנציאל שנתי"
                value={formatShekel(summary.total_potential_value)}
                colorClass={summary.total_potential_value > 0 ? 'border-green-300' : 'border-gray-200'}
              />
            </div>

            {/* Urgent alert */}
            {hasUrgent && (
              <div className="bg-red-50 border-2 border-red-300 rounded-2xl p-5" dir="rtl">
                <div className="flex items-start gap-3">
                  <span className="text-2xl flex-shrink-0">🚨</span>
                  <div>
                    <p className="font-bold font-hebrew text-red-800 text-lg">
                      נמצאו {summary.positions_missing} נושאים הדורשים פעולה
                    </p>
                    {summary.total_potential_value > 0 && (
                      <p className="text-red-700 font-hebrew mt-1">
                        ייתכן שהרשות מפסידה עד{' '}
                        <strong>{formatShekel(summary.total_potential_value)}</strong> בשנה
                      </p>
                    )}
                    <p className="text-red-600 font-hebrew text-sm mt-2">
                      פנה לרואה החשבון לטיפול בנושאים המפורטים למטה
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Position cards */}
            <div className="space-y-4">
              {positions.map((position) => (
                <PositionCard key={position.id} position={position} />
              ))}
            </div>

            {/* Footer disclaimer */}
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-5 mt-4" dir="rtl">
              <div className="flex items-start gap-3">
                <span className="text-lg flex-shrink-0">⚠️</span>
                <div>
                  <p className="font-semibold font-hebrew text-gray-700 text-sm">הערה חשובה</p>
                  <p className="text-gray-500 font-hebrew text-sm mt-1 leading-relaxed">
                    ניתוח זה מבוסס על נתוני התקציב החודשי ועל חוברת התקצוב של משרד החינוך.
                    הנתונים הם הערכה בלבד ומיועדים לסיוע בזיהוי פערים אפשריים.
                    לאישור סופי וטיפול יש לפנות לרואה החשבון.
                  </p>
                </div>
              </div>
            </div>
          </>
        )}

        {/* ── Deadlines tab ─────────────────────────────────────────── */}
        {activeTab === 'deadlines' && (
          selectedMunicipality
            ? <DeadlinesTab municipalityId={selectedMunicipality} />
            : <div className="text-center py-16 text-gray-500 font-hebrew">נא לבחור רשות לצפייה במועדים</div>
        )}

        {/* ── Tracking tab ──────────────────────────────────────────── */}
        {activeTab === 'tracking' && (
          selectedMunicipality
            ? <TrackingTab municipalityId={selectedMunicipality} />
            : <div className="text-center py-16 text-gray-500 font-hebrew">נא לבחור רשות לצפייה במעקב</div>
        )}

        {/* ── Priority tab ──────────────────────────────────────────── */}
        {activeTab === 'priority' && (
          selectedMunicipality
            ? <PriorityTab municipalityId={selectedMunicipality} selectedMonth={selectedMonth} />
            : <div className="text-center py-16 text-gray-500 font-hebrew">נא לבחור רשות לצפייה בעדיפויות</div>
        )}
      </div>
    </PortalWrapper>
  );
}
