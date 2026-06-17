import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import PortalWrapper from '../components/portal/PortalWrapper';
import { analyticsAPI } from '../services/api';
import { formatShekel as formatShekelByMode, getRoundingDisclosureText, resolveConcreteMode, ROUNDING_MODES } from '../utils/formatShekel';
import { useRoundingMode } from '../utils/roundingMode';
import RoundingModeToggle from '../components/common/RoundingModeToggle';
import RoundingDisclosureBanner from '../components/common/RoundingDisclosureBanner';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine,
} from 'recharts';

// ────────────────────────────────────────────────────────────
// Constants
// ────────────────────────────────────────────────────────────
const CODE_COLORS = {
  '3':  '#10B981',
  '19': '#F59E0B',
  '33': '#EF4444',
  '5':  '#8B5CF6',
  '45': '#8B5CF6',
  total: '#3B82F6',
  forecast: '#8B5CF6',
};

const SEVERITY_STYLES = {
  high:   { border: 'border-red-500',   bg: 'bg-red-50',   badge: 'bg-red-100 text-red-800',   label: 'גבוהה', icon: '🔴' },
  medium: { border: 'border-amber-500', bg: 'bg-amber-50', badge: 'bg-amber-100 text-amber-800', label: 'בינונית', icon: '🟡' },
  low:    { border: 'border-blue-400',  bg: 'bg-blue-50',  badge: 'bg-blue-100 text-blue-800',   label: 'נמוכה', icon: '🔵' },
};

const CONFIDENCE_STYLES = {
  high:   { bg: 'bg-green-50',  border: 'border-green-400', text: 'text-green-800', label: 'דיוק גבוה',  icon: '✅' },
  medium: { bg: 'bg-amber-50',  border: 'border-amber-400', text: 'text-amber-800', label: 'דיוק סביר', icon: '⚠️' },
  low:    { bg: 'bg-red-50',    border: 'border-red-400',   text: 'text-red-800',   label: 'דיוק נמוך',  icon: '❗' },
  none:   { bg: 'bg-gray-50',   border: 'border-gray-300',  text: 'text-gray-700',  label: 'אין נתונים', icon: '—' },
};

const TABS = [
  { id: 'trends',   label: '📈 מגמות' },
  { id: 'forecast', label: '📅 תחזית' },
  { id: 'anomalies', label: '🚨 חריגות' },
  { id: 'retro',    label: '⏳ רטרו ישן' },
];

let activeRoundingMode = ROUNDING_MODES.EXACT;

function extractNumericValues(value, output = []) {
  if (Array.isArray(value)) {
    value.forEach((item) => extractNumericValues(item, output));
    return output;
  }
  if (value && typeof value === 'object') {
    Object.values(value).forEach((item) => extractNumericValues(item, output));
    return output;
  }
  if (typeof value === 'number' && Number.isFinite(value)) {
    output.push(value);
  }
  return output;
}

// ────────────────────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────────────────────
function getLast12Months() {
  const options = [];
  const now = new Date();
  for (let i = 0; i < 12; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    options.push({ value, label: value });
  }
  return options;
}

function formatShekel(n) {
  if (n === null || n === undefined) return '—';
  return formatShekelByMode(n, { mode: activeRoundingMode });
}

function trendArrow(dir) {
  if (dir === 'up')   return '↑';
  if (dir === 'down') return '↓';
  return '→';
}

// ────────────────────────────────────────────────────────────
// Custom recharts tooltip (right-to-left)
// ────────────────────────────────────────────────────────────
function HebTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-lg p-3 text-sm font-hebrew" dir="rtl">
      <p className="font-bold text-gray-700 mb-2">{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }}>
          {p.name}: {formatShekel(p.value)}
        </p>
      ))}
    </div>
  );
}

// ────────────────────────────────────────────────────────────
// Tab: Trends
// ────────────────────────────────────────────────────────────
function TrendsTab({ municipalityId, roundingMode, onModeResolved }) {
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState(null);

  useEffect(() => {
    setLoading(true);
    analyticsAPI.getTrends(municipalityId)
      .then(r => setData(r.data))
      .catch(e => setError(e.response?.data?.detail || 'שגיאה בטעינת מגמות'))
      .finally(() => setLoading(false));
  }, [municipalityId]);

  if (loading) return <Spinner />;
  if (error)   return <ErrorBox msg={error} />;
  if (!data || !data.months_available?.length) return <EmptyState msg="אין נתונים היסטוריים עדיין" />;

  const concreteRoundingMode = resolveConcreteMode(roundingMode, extractNumericValues(data));
  activeRoundingMode = concreteRoundingMode;

  useEffect(() => {
    onModeResolved?.(concreteRoundingMode);
  }, [concreteRoundingMode, onModeResolved]);

  const { trends, total_budget_trend, months_available } = data;

  // Format total budget trend for recharts
  const totalChartData = total_budget_trend.map(m => ({
    name: m.month_display,
    סה_כ: m.total,
  }));

  return (
    <div className="space-y-8">
      {/* Total budget trend */}
      <Section title="סה״כ תקציב לאורך זמן">
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={totalChartData} margin={{ top: 10, right: 20, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis dataKey="name" tick={{ fontSize: 11, fontFamily: 'inherit' }} />
            <YAxis tickFormatter={v => `₪${(v/1000).toFixed(0)}K`} tick={{ fontSize: 11 }} />
            <Tooltip content={<HebTooltip />} />
            <Line type="monotone" dataKey="סה_כ" name="סה״כ" stroke={CODE_COLORS.total} strokeWidth={2.5} dot={{ r: 4 }} />
          </LineChart>
        </ResponsiveContainer>
      </Section>

      {/* Per-code trends */}
      {Object.entries(trends).map(([code, t]) => {
        const chartData = t.data.map(d => ({
          name: d.month_display,
          total: d.total,
          retro: d.retro_total,
          regular: d.regular_total,
        }));

        return (
          <Section key={code} title={`${t.name} (קוד ${code})`}>
            <div className="grid grid-cols-3 gap-3 mb-4 text-center">
              <StatPill label="ממוצע" value={formatShekel(t.average)} color="blue" />
              <StatPill label="שינוי מצטבר" value={`${t.change_percent > 0 ? '+' : ''}${t.change_percent}%`} color={t.trend_direction === 'up' ? 'green' : t.trend_direction === 'down' ? 'red' : 'gray'} />
              <StatPill label="מגמה" value={`${trendArrow(t.trend_direction)} ${t.trend_direction === 'up' ? 'עלייה' : t.trend_direction === 'down' ? 'ירידה' : 'יציב'}`} color="gray" />
            </div>

            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={chartData} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis dataKey="name" tick={{ fontSize: 11, fontFamily: 'inherit' }} />
                <YAxis tickFormatter={v => `₪${(v/1000).toFixed(0)}K`} tick={{ fontSize: 11 }} />
                <Tooltip content={<HebTooltip />} />
                <Line type="monotone" dataKey="total" name="סה״כ" stroke={CODE_COLORS[code] || '#6B7280'} strokeWidth={2.5} dot={{ r: 4 }} />
                <Line type="monotone" dataKey="regular" name="רגיל" stroke={CODE_COLORS[code] || '#6B7280'} strokeWidth={1.5} strokeDasharray="5 3" dot={false} opacity={0.7} />
              </LineChart>
            </ResponsiveContainer>

            {/* Children count (code 3 only) */}
            {code === '3' && t.data.some(d => d.children_count > 0) && (
              <div className="mt-4">
                <p className="text-sm text-gray-500 font-hebrew mb-2">הערכת מספר ילדים</p>
                <ResponsiveContainer width="100%" height={150}>
                  <BarChart data={t.data.map(d => ({ name: d.month_display, ילדים: d.children_count }))} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                    <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} />
                    <Tooltip content={<HebTooltip />} />
                    <Bar dataKey="ילדים" name="ילדים" fill="#10B981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </Section>
        );
      })}
    </div>
  );
}

// ────────────────────────────────────────────────────────────
// Tab: Forecast
// ────────────────────────────────────────────────────────────
function ForecastTab({ municipalityId, roundingMode, onModeResolved }) {
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState(null);

  useEffect(() => {
    setLoading(true);
    analyticsAPI.getForecast(municipalityId)
      .then(r => setData(r.data))
      .catch(e => setError(e.response?.data?.detail || 'שגיאה בטעינת תחזית'))
      .finally(() => setLoading(false));
  }, [municipalityId]);

  if (loading) return <Spinner />;
  if (error)   return <ErrorBox msg={error} />;
  if (!data?.predicted_total) return <EmptyState msg="אין מספיק נתונים לחישוב תחזית" />;

  const concreteRoundingMode = resolveConcreteMode(roundingMode, extractNumericValues(data));
  activeRoundingMode = concreteRoundingMode;

  useEffect(() => {
    onModeResolved?.(concreteRoundingMode);
  }, [concreteRoundingMode, onModeResolved]);

  const conf = CONFIDENCE_STYLES[data.confidence] || CONFIDENCE_STYLES.none;

  // Build chart — historical + forecast point (dashed)
  const historicalData = (data.based_on_months || []).map((m, i) => ({
    name: m,
    actual: data.based_on_totals?.[i] ?? 0,
    forecast: null,
  }));

  const forecastPoint = {
    name: data.forecast_month,
    actual: null,
    forecast: data.predicted_total,
  };

  // Connect last real point to forecast with both keys
  const chartData = [
    ...historicalData.slice(0, -1),
    { ...historicalData[historicalData.length - 1], forecast: historicalData[historicalData.length - 1]?.actual },
    forecastPoint,
  ];

  return (
    <div className="space-y-6">
      {/* Confidence banner */}
      <div className={`rounded-xl border-2 ${conf.border} ${conf.bg} p-4 flex items-center gap-3`} dir="rtl">
        <span className="text-2xl">{conf.icon}</span>
        <div>
          <p className={`font-bold font-hebrew ${conf.text}`}>{conf.label}</p>
          <p className={`text-sm font-hebrew ${conf.text}`}>{data.confidence_reason}</p>
        </div>
      </div>

      {/* Forecast total */}
      <Section title={`תחזית לחודש ${data.forecast_month_display}`}>
        <div className="flex flex-col items-center py-4 gap-2">
          <p className="text-5xl font-bold text-purple-700">{formatShekel(data.predicted_total)}</p>
          <p className={`text-lg font-hebrew font-semibold ${data.change_from_last >= 0 ? 'text-red-600' : 'text-green-600'}`}>
            {data.change_from_last >= 0 ? '↑' : '↓'} {formatShekel(Math.abs(data.change_from_last))}
            &nbsp;({data.change_percent > 0 ? '+' : ''}{data.change_percent}%) מהחודש הנוכחי
          </p>
        </div>

        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={chartData} margin={{ top: 10, right: 20, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis dataKey="name" tick={{ fontSize: 11, fontFamily: 'inherit' }} />
            <YAxis tickFormatter={v => `₪${(v/1000).toFixed(0)}K`} tick={{ fontSize: 11 }} />
            <Tooltip content={<HebTooltip />} />
            <Line type="monotone" dataKey="actual" name="בפועל" stroke={CODE_COLORS.total} strokeWidth={2.5} dot={{ r: 4 }} connectNulls={false} />
            <Line type="monotone" dataKey="forecast" name="תחזית" stroke={CODE_COLORS.forecast} strokeWidth={2.5} strokeDasharray="8 4" dot={{ r: 6, fill: '#8B5CF6' }} connectNulls />
          </LineChart>
        </ResponsiveContainer>
      </Section>

      {/* Per-code forecast */}
      {Object.keys(data.by_code || {}).length > 0 && (
        <Section title="תחזית לפי קוד תקציב">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {Object.entries(data.by_code).map(([code, fc]) => (
              <div key={code} className="bg-white rounded-xl border border-gray-200 p-4 text-center shadow-sm">
                <p className="text-xs text-gray-500 font-hebrew mb-1">קוד {code}</p>
                <p className="font-bold text-gray-800 font-hebrew text-sm mb-2">{fc.name}</p>
                <p className="text-2xl font-bold" style={{ color: CODE_COLORS[code] || '#6B7280' }}>
                  {formatShekel(fc.predicted)}
                </p>
                <p className="text-xs text-gray-500 font-hebrew mt-1">
                  {trendArrow(fc.trend)} {fc.trend === 'up' ? 'עלייה' : fc.trend === 'down' ? 'ירידה' : 'יציב'}
                </p>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Disclaimer */}
      <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 text-xs text-gray-500 font-hebrew" dir="rtl">
        {data.disclaimer}
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────
// Tab: Anomalies
// ────────────────────────────────────────────────────────────
function AnomaliesTab({ municipalityId, selectedMonth, roundingMode, onModeResolved }) {
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState(null);

  useEffect(() => {
    if (!selectedMonth) return;
    setLoading(true);
    analyticsAPI.getAnomalies(municipalityId, selectedMonth)
      .then(r => setData(r.data))
      .catch(e => setError(e.response?.data?.detail || 'שגיאה בטעינת חריגות'))
      .finally(() => setLoading(false));
  }, [municipalityId, selectedMonth]);

  if (loading) return <Spinner />;
  if (error)   return <ErrorBox msg={error} />;
  if (!data)   return null;

  const concreteRoundingMode = resolveConcreteMode(roundingMode, extractNumericValues(data));
  activeRoundingMode = concreteRoundingMode;

  useEffect(() => {
    onModeResolved?.(concreteRoundingMode);
  }, [concreteRoundingMode, onModeResolved]);

  const { anomalies, total_anomalies, high_severity, medium_severity, low_severity } = data;

  return (
    <div className="space-y-6" dir="rtl">
      {/* Summary badges */}
      <div className="grid grid-cols-3 gap-4">
        <SeverityBadge count={high_severity}   label="חריגות גבוהות"  color="red" />
        <SeverityBadge count={medium_severity} label="חריגות בינוניות" color="amber" />
        <SeverityBadge count={low_severity}    label="חריגות נמוכות"  color="blue" />
      </div>

      {total_anomalies === 0 ? (
        <div className="bg-green-50 border border-green-200 rounded-xl p-8 text-center">
          <p className="text-4xl mb-3">✅</p>
          <p className="text-green-800 font-bold font-hebrew text-lg">לא נמצאו חריגות</p>
          <p className="text-green-600 text-sm font-hebrew mt-1">הנתונים לחודש {data.month_display} תקינים</p>
        </div>
      ) : (
        <div className="space-y-4">
          {['high', 'medium', 'low'].map(sev =>
            anomalies.filter(a => a.severity === sev).map(a => (
              <AnomalyCard key={a.id} anomaly={a} />
            ))
          )}
        </div>
      )}
    </div>
  );
}

function SeverityBadge({ count, label, color }) {
  const colors = {
    red:   'bg-red-50 border-red-300 text-red-800',
    amber: 'bg-amber-50 border-amber-300 text-amber-800',
    blue:  'bg-blue-50 border-blue-300 text-blue-800',
  };
  return (
    <div className={`rounded-xl border p-4 text-center ${colors[color]}`}>
      <p className="text-3xl font-bold">{count}</p>
      <p className="text-xs font-hebrew mt-1">{label}</p>
    </div>
  );
}

function AnomalyCard({ anomaly }) {
  const sev = SEVERITY_STYLES[anomaly.severity] || SEVERITY_STYLES.low;
  return (
    <div className={`bg-white rounded-xl border-r-4 ${sev.border} border border-gray-200 shadow-sm p-5`} dir="rtl">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium font-hebrew ${sev.badge} mb-2`}>
            {sev.icon} {sev.label}
          </span>
          <h3 className="font-bold text-gray-800 font-hebrew">{anomaly.title}</h3>
        </div>
        {anomaly.budget_code && (
          <span className="text-xs text-gray-500 font-hebrew bg-gray-100 px-2 py-1 rounded-lg whitespace-nowrap">
            קוד {anomaly.budget_code}
          </span>
        )}
      </div>
      <p className="text-sm text-gray-600 font-hebrew mb-3">{anomaly.description}</p>
      {anomaly.previous_amount !== undefined && (
        <div className="flex gap-4 text-sm mb-3 flex-wrap">
          {anomaly.previous_amount !== undefined && <KV label="קודם" value={formatShekel(anomaly.previous_amount)} />}
          {anomaly.current_amount !== undefined && <KV label="כעת" value={formatShekel(anomaly.current_amount)} />}
          {anomaly.change_percent !== undefined && <KV label="שינוי" value={`${anomaly.change_percent}%`} />}
          {anomaly.drop_percent !== undefined && <KV label="ירידה" value={`${anomaly.drop_percent}%`} />}
        </div>
      )}
      {anomaly.recommendation && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <p className="text-xs font-hebrew text-blue-800">💡 {anomaly.recommendation}</p>
        </div>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────────────────
// Tab: Retro Aging
// ────────────────────────────────────────────────────────────
function RetroAgingTab({ municipalityId, selectedMonth, roundingMode, onModeResolved }) {
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState(null);
  const [sortDir, setSortDir] = useState('desc'); // 'desc' = oldest first

  useEffect(() => {
    if (!selectedMonth) return;
    setLoading(true);
    analyticsAPI.getRetroAging(municipalityId, selectedMonth)
      .then(r => setData(r.data))
      .catch(e => setError(e.response?.data?.detail || 'שגיאה בטעינת נתוני רטרו'))
      .finally(() => setLoading(false));
  }, [municipalityId, selectedMonth]);

  if (loading) return <Spinner />;
  if (error)   return <ErrorBox msg={error} />;
  if (!data)   return null;

  const concreteRoundingMode = resolveConcreteMode(roundingMode, extractNumericValues(data));
  activeRoundingMode = concreteRoundingMode;

  useEffect(() => {
    onModeResolved?.(concreteRoundingMode);
  }, [concreteRoundingMode, onModeResolved]);

  const { retro_lines, aging_summary, total_retro_amount } = data;

  if (!retro_lines?.length) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-xl p-8 text-center" dir="rtl">
        <p className="text-4xl mb-3">✅</p>
        <p className="text-green-800 font-bold font-hebrew text-lg">אין תשלומי רטרו</p>
        <p className="text-green-600 text-sm font-hebrew mt-1">כל התשלומים בחודש זה הם עדכניים</p>
      </div>
    );
  }

  const sorted = [...retro_lines].sort((a, b) => 
    sortDir === 'desc' ? b.months_old - a.months_old : a.months_old - b.months_old
  );

  const agingBarData = [
    { name: 'רגיל (0-3)', count: aging_summary.normal_0_3.count, amount: aging_summary.normal_0_3.amount, fill: '#10B981' },
    { name: 'ישן (4-6)',   count: aging_summary.old_4_6.count,   amount: aging_summary.old_4_6.amount,   fill: '#F59E0B' },
    { name: 'ישן מאוד (7+)',count:aging_summary.very_old_7_plus.count, amount: aging_summary.very_old_7_plus.amount, fill: '#EF4444' },
  ];

  const hasVeryOld = aging_summary.very_old_7_plus.count > 0;

  return (
    <div className="space-y-6" dir="rtl">
      {/* Alert for very old retro */}
      {hasVeryOld && (
        <div className="bg-red-50 border-2 border-red-400 rounded-xl p-4 flex items-start gap-3">
          <span className="text-2xl">⚠️</span>
          <div>
            <p className="font-bold text-red-800 font-hebrew">נמצאו תשלומי רטרו ישנים מאוד</p>
            <p className="text-sm text-red-700 font-hebrew">
              {aging_summary.very_old_7_plus.count} תשלומים ממתינים יותר מ-6 חודשים — {formatShekel(aging_summary.very_old_7_plus.amount)}
            </p>
          </div>
        </div>
      )}

      {/* Total */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500 font-hebrew">סה״כ תשלומי רטרו</p>
          <p className="text-3xl font-bold text-gray-800">{formatShekel(total_retro_amount)}</p>
        </div>
        <p className="text-4xl">🔄</p>
      </div>

      {/* Aging bar chart */}
      <Section title="פיזור לפי גיל תשלום">
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={agingBarData} margin={{ top: 10, right: 20, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis dataKey="name" tick={{ fontSize: 11, fontFamily: 'inherit' }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip
              formatter={(v, name) => [name === 'count' ? v : formatShekel(v), name === 'count' ? 'מספר שורות' : 'סכום']}
            />
            <Bar dataKey="count" name="מספר שורות" radius={[4, 4, 0, 0]}>
              {agingBarData.map((d, i) => (
                <rect key={i} fill={d.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Section>

      {/* Table */}
      <Section title="פירוט שורות רטרו">
        <div className="flex justify-end mb-3">
          <button
            onClick={() => setSortDir(d => d === 'desc' ? 'asc' : 'desc')}
            className="text-xs text-blue-600 font-hebrew border border-blue-300 rounded-lg px-3 py-1.5 hover:bg-blue-50"
          >
            מיין לפי גיל {sortDir === 'desc' ? '↑ ישן→חדש' : '↓ חדש→ישן'}
          </button>
        </div>
        <div className="overflow-x-auto rounded-xl border border-gray-200">
          <table className="w-full text-sm font-hebrew" dir="rtl">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-right text-gray-600">קוד</th>
                <th className="px-4 py-3 text-right text-gray-600">נושא</th>
                <th className="px-4 py-3 text-right text-gray-600">עבור חודש</th>
                <th className="px-4 py-3 text-right text-gray-600">גיל</th>
                <th className="px-4 py-3 text-right text-gray-600">סכום</th>
                <th className="px-4 py-3 text-right text-gray-600">סטטוס</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((line, i) => {
                const ageBg = line.age_color === 'red' ? 'bg-red-50' : line.age_color === 'amber' ? 'bg-amber-50' : '';
                const ageTxt = line.age_color === 'red' ? 'text-red-700' : line.age_color === 'amber' ? 'text-amber-700' : 'text-green-700';
                return (
                  <tr key={line.id || i} className={`border-t border-gray-100 ${ageBg}`}>
                    <td className="px-4 py-3 text-gray-600">{line.code}</td>
                    <td className="px-4 py-3 text-gray-800 max-w-[200px] truncate" title={line.topic}>{line.topic}</td>
                    <td className="px-4 py-3 text-gray-700">{line.period_display}</td>
                    <td className={`px-4 py-3 font-bold ${ageTxt}`}>{line.months_old} חודשים</td>
                    <td className="px-4 py-3 text-gray-800 font-medium">{formatShekel(line.amount)}</td>
                    <td className={`px-4 py-3 font-bold ${ageTxt}`}>{line.age_category}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Section>
    </div>
  );
}

// ────────────────────────────────────────────────────────────
// Shared UI components
// ────────────────────────────────────────────────────────────
function Section({ title, children }) {
  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
      <h3 className="font-bold text-gray-700 font-hebrew text-base mb-4 border-b border-gray-100 pb-2">{title}</h3>
      {children}
    </div>
  );
}

function StatPill({ label, value, color }) {
  const colors = {
    blue:  'bg-blue-50 text-blue-800',
    green: 'bg-green-50 text-green-800',
    red:   'bg-red-50 text-red-800',
    gray:  'bg-gray-50 text-gray-700',
  };
  return (
    <div className={`rounded-xl p-3 ${colors[color] || colors.gray}`}>
      <p className="text-xs text-current opacity-70 font-hebrew mb-1">{label}</p>
      <p className="font-bold text-sm">{value}</p>
    </div>
  );
}

function KV({ label, value }) {
  return (
    <div className="bg-gray-50 rounded-lg px-3 py-1">
      <span className="text-gray-500 font-hebrew text-xs">{label}: </span>
      <span className="font-semibold text-gray-800 text-xs">{value}</span>
    </div>
  );
}

function Spinner() {
  return (
    <div className="flex justify-center py-16">
      <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

function ErrorBox({ msg }) {
  return (
    <div className="bg-red-50 border border-red-300 rounded-xl p-4 text-red-700 font-hebrew" dir="rtl">
      ⚠️ {msg}
    </div>
  );
}

function EmptyState({ msg }) {
  return (
    <div className="bg-gray-50 border border-gray-200 rounded-xl p-10 text-center font-hebrew text-gray-500" dir="rtl">
      <p className="text-3xl mb-3">📊</p>
      <p>{msg}</p>
    </div>
  );
}

// ────────────────────────────────────────────────────────────
// Main page
// ────────────────────────────────────────────────────────────
export default function PortalAnalyticsPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const municipalityId = user?.municipality_id;

  const months = getLast12Months();
  const [activeTab, setActiveTab] = useState('trends');
  const [selectedMonth, setSelectedMonth] = useState(months[0]?.value || '');
  const [roundingMode, setRoundingMode] = useRoundingMode();
  const [resolvedModeForBanner, setResolvedModeForBanner] = useState(ROUNDING_MODES.EXACT);
  const analyticsDisclosureText = getRoundingDisclosureText(resolvedModeForBanner);

  if (!municipalityId) {
    return (
      <PortalWrapper title="ניתוח ומגמות" onBack={() => navigate('/portal')}>
        <ErrorBox msg="לא נמצא מזהה רשות מקומית" />
      </PortalWrapper>
    );
  }

  const needsMonth = activeTab === 'anomalies' || activeTab === 'retro';

  return (
    <PortalWrapper title="ניתוח ומגמות" onBack={() => navigate('/portal')}>
      <div dir="rtl" className="space-y-6">
        {/* Header */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
          <div className="flex items-start justify-between flex-wrap gap-4">
            <div>
              <h1 className="text-2xl font-bold font-hebrew text-gray-800 flex items-center gap-2">
                📊 ניתוח ומגמות
              </h1>
              <p className="text-sm text-gray-500 font-hebrew mt-1">
                ניתוח תקציבי, מגמות לאורך זמן, חריגות ותחזיות
              </p>
            </div>

            <RoundingModeToggle mode={roundingMode} onChange={setRoundingMode} />

            {/* Month selector (only for tabs that need it) */}
            {needsMonth && (
              <select
                value={selectedMonth}
                onChange={e => setSelectedMonth(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm font-hebrew bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                dir="rtl"
              >
                <option value="">בחר חודש</option>
                {months.map(m => (
                  <option key={m.value} value={m.value}>{m.value}</option>
                ))}
              </select>
            )}
          </div>
        </div>

        <RoundingDisclosureBanner text={analyticsDisclosureText} />

        {/* Tabs */}
        <div className="flex gap-2 flex-wrap">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 rounded-xl text-sm font-medium font-hebrew transition-colors ${
                activeTab === tab.id
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {activeTab === 'trends'    && <TrendsTab municipalityId={municipalityId} roundingMode={roundingMode} onModeResolved={setResolvedModeForBanner} />}
        {activeTab === 'forecast'  && <ForecastTab municipalityId={municipalityId} roundingMode={roundingMode} onModeResolved={setResolvedModeForBanner} />}
        {activeTab === 'anomalies' && <AnomaliesTab municipalityId={municipalityId} selectedMonth={selectedMonth} roundingMode={roundingMode} onModeResolved={setResolvedModeForBanner} />}
        {activeTab === 'retro'     && <RetroAgingTab municipalityId={municipalityId} selectedMonth={selectedMonth} roundingMode={roundingMode} onModeResolved={setResolvedModeForBanner} />}
      </div>
    </PortalWrapper>
  );
}
