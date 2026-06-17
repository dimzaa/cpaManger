import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { analyticsAPI, municipalityAPI } from '../services/api';
import PageWrapper from '../components/layout/PageWrapper';
import { formatShekel as formatShekelByMode, getRoundingDisclosureText, resolveConcreteMode, ROUNDING_MODES } from '../utils/formatShekel';
import { useRoundingMode } from '../utils/roundingMode';
import RoundingModeToggle from '../components/common/RoundingModeToggle';
import RoundingDisclosureBanner from '../components/common/RoundingDisclosureBanner';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
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

const MUNI_COLORS = [
  '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
  '#06B6D4', '#84CC16', '#F97316', '#EC4899', '#6366F1',
];

const SEVERITY_STYLES = {
  high:   { border: 'border-red-500',   bg: 'bg-red-50',   badge: 'bg-red-100 text-red-800',    label: 'גבוהה',   icon: '🔴' },
  medium: { border: 'border-amber-500', bg: 'bg-amber-50', badge: 'bg-amber-100 text-amber-800', label: 'בינונית', icon: '🟡' },
  low:    { border: 'border-blue-400',  bg: 'bg-blue-50',  badge: 'bg-blue-100 text-blue-800',   label: 'נמוכה',   icon: '🔵' },
};

const CONFIDENCE_STYLES = {
  high:   { bg: 'bg-green-50',  border: 'border-green-400', text: 'text-green-800', label: 'דיוק גבוה',  icon: '✅' },
  medium: { bg: 'bg-amber-50',  border: 'border-amber-400', text: 'text-amber-800', label: 'דיוק סביר', icon: '⚠️' },
  low:    { bg: 'bg-red-50',    border: 'border-red-400',   text: 'text-red-800',   label: 'דיוק נמוך',  icon: '❗' },
  none:   { bg: 'bg-gray-50',   border: 'border-gray-300',  text: 'text-gray-700',  label: 'אין נתונים', icon: '—' },
};

const TABS = [
  { id: 'overview',  label: '🗺️ סקירה כללית' },
  { id: 'trends',    label: '📈 מגמות' },
  { id: 'forecast',  label: '📅 תחזית' },
  { id: 'anomalies', label: '🚨 חריגות' },
  { id: 'retro',     label: '⏳ רטרו ישן' },
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

function formatMonthDisplay(month) {
  if (!month || !/^\d{4}-\d{2}$/.test(month)) return month || '—';
  const [year, mon] = month.split('-');
  const map = {
    '01': 'ינואר', '02': 'פברואר', '03': 'מרץ', '04': 'אפריל',
    '05': 'מאי', '06': 'יוני', '07': 'יולי', '08': 'אוגוסט',
    '09': 'ספטמבר', '10': 'אוקטובר', '11': 'נובמבר', '12': 'דצמבר',
  };
  return `${map[mon] || mon} ${year}`;
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
// Custom tooltip
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
// Tab: Admin Overview
// ────────────────────────────────────────────────────────────
function OverviewTab({ selectedMonth, roundingMode, onModeResolved }) {
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState(null);

  useEffect(() => {
    if (!selectedMonth) return;

    let ignore = false;
    setLoading(true);

    analyticsAPI.getAdminOverview(selectedMonth)
      .then(r => {
        if (!ignore) setData(r.data);
      })
      .catch(e => {
        if (!ignore) setError(e.response?.data?.detail || 'שגיאה בטעינת סקירה');
      })
      .finally(() => {
        if (!ignore) setLoading(false);
      });

    return () => {
      ignore = true;
    };
  }, [selectedMonth]);

  if (loading) return <Spinner />;
  if (error)   return <ErrorBox msg={error} />;
  if (!data?.municipalities?.length) return <EmptyState msg="אין נתונים לחודש זה" />;

  const concreteRoundingMode = resolveConcreteMode(roundingMode, extractNumericValues(data));
  activeRoundingMode = concreteRoundingMode;

  useEffect(() => {
    onModeResolved?.(concreteRoundingMode);
  }, [concreteRoundingMode, onModeResolved]);

  const byMunicipality = data.municipalities;

  // Bar chart — total per municipality
  const barData = byMunicipality
    .filter(m => m.has_data)
    .map((m, i) => ({
      name: m.municipality_name,
      total: m.total,
      fill: MUNI_COLORS[i % MUNI_COLORS.length],
    }));

  return (
    <div className="space-y-8" dir="rtl">
      <Section title={`סקירת רשויות — ${data.month_display}`}>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={barData} margin={{ top: 10, right: 20, left: 20, bottom: 80 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 11, fontFamily: 'inherit' }}
              angle={-30}
              textAnchor="end"
              interval={0}
            />
            <YAxis tickFormatter={v => `₪${(v / 1000).toFixed(0)}K`} tick={{ fontSize: 11 }} />
            <Tooltip content={<HebTooltip />} />
            <Bar dataKey="total" name="סה״כ תקציב" radius={[6, 6, 0, 0]} fill="#3B82F6" />
          </BarChart>
        </ResponsiveContainer>
      </Section>

      {/* Per-municipality table */}
      <Section title="פירוט לפי רשות">
        <div className="overflow-x-auto rounded-xl border border-gray-200">
          <table className="w-full text-sm font-hebrew" dir="rtl">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-right text-gray-600">רשות</th>
                <th className="px-4 py-3 text-right text-gray-600">
                  <div className="leading-tight">
                    <div>סה״כ תקציב</div>
                    <div className="text-xs text-gray-400 font-normal mt-1">מצטבר שנתי</div>
                  </div>
                </th>
                <th className="px-4 py-3 text-right text-gray-600">
                  <div className="leading-tight">
                    <div>מגיע</div>
                    <div className="text-xs text-gray-400 font-normal mt-1">לחודש הנבחר</div>
                  </div>
                </th>
                <th className="px-4 py-3 text-right text-gray-600">
                  <div className="leading-tight">
                    <div>שולם</div>
                    <div className="text-xs text-gray-400 font-normal mt-1">לחודש הנבחר</div>
                  </div>
                </th>
                <th className="px-4 py-3 text-right text-gray-600">
                  <div className="leading-tight">
                    <div>פער</div>
                    <div className="text-xs text-gray-400 font-normal mt-1">לחודש הנבחר</div>
                  </div>
                </th>
                <th className="px-4 py-3 text-right text-gray-600">
                  <div className="leading-tight">
                    <div>קוד 3 — גני ילדים</div>
                    <div className="text-xs text-gray-400 font-normal mt-1">מצטבר שנתי</div>
                  </div>
                </th>
                <th className="px-4 py-3 text-right text-gray-600">
                  <div className="leading-tight">
                    <div>קוד 19 — עוזרות</div>
                    <div className="text-xs text-gray-400 font-normal mt-1">מצטבר שנתי</div>
                  </div>
                </th>
                <th className="px-4 py-3 text-right text-gray-600">
                  <div className="leading-tight">
                    <div>קוד 33 — גננות מדינה</div>
                    <div className="text-xs text-gray-400 font-normal mt-1">מצטבר שנתי</div>
                  </div>
                </th>
              </tr>
            </thead>
            <tbody>
              {byMunicipality.map((m, i) => (
                <tr key={m.municipality_id} className={`border-t border-gray-100 ${!m.has_data ? 'opacity-50' : ''}`}>
                  <td className="px-4 py-3 font-medium text-gray-800">{m.municipality_name}</td>
                  <td className="px-4 py-3 font-bold text-blue-700">{formatShekel(m.total)}</td>
                  <td className="px-4 py-3 text-slate-700">{formatShekel(m.due_amount)}</td>
                  <td className="px-4 py-3 text-green-700">{formatShekel(m.paid_amount)}</td>
                  <td className={`px-4 py-3 font-semibold ${Number(m.gap_amount || 0) < 0 ? 'text-red-700' : 'text-indigo-700'}`}>
                    {formatShekel(m.gap_amount)}
                  </td>
                  <td className="px-4 py-3 text-green-700">{formatShekel(m.by_code?.['3'])}</td>
                  <td className="px-4 py-3 text-amber-700">{formatShekel(m.by_code?.['19'])}</td>
                  <td className="px-4 py-3 text-red-700">{formatShekel(m.by_code?.['33'])}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
    </div>
  );
}

// ────────────────────────────────────────────────────────────
// Tab: Trends (admin view — requires municipality selection)
// ────────────────────────────────────────────────────────────
function AdminTrendsTab({ municipalityId, roundingMode, onModeResolved }) {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);

  useEffect(() => {
    if (!municipalityId) return;
    setLoading(true);
    analyticsAPI.getTrends(municipalityId)
      .then(r => setData(r.data))
      .catch(e => setError(e.response?.data?.detail || 'שגיאה בטעינת מגמות'))
      .finally(() => setLoading(false));
  }, [municipalityId]);

  if (!municipalityId) return <EmptyState msg="בחר רשות מקומית להצגת מגמות" />;
  if (loading) return <Spinner />;
  if (error)   return <ErrorBox msg={error} />;
  if (!data || !data.months_available?.length) return <EmptyState msg="אין נתונים היסטוריים" />;

  const concreteRoundingMode = resolveConcreteMode(roundingMode, extractNumericValues(data));
  activeRoundingMode = concreteRoundingMode;

  useEffect(() => {
    onModeResolved?.(concreteRoundingMode);
  }, [concreteRoundingMode, onModeResolved]);

  const { trends, total_budget_trend } = data;

  const totalChartData = total_budget_trend.map(m => ({
    name: m.month_display,
    'סה״כ': m.total,
  }));

  return (
    <div className="space-y-8">
      <Section title="סה״כ תקציב לאורך זמן">
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={totalChartData} margin={{ top: 10, right: 20, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis dataKey="name" tick={{ fontSize: 11, fontFamily: 'inherit' }} />
            <YAxis tickFormatter={v => `₪${(v/1000).toFixed(0)}K`} tick={{ fontSize: 11 }} />
            <Tooltip content={<HebTooltip />} />
            <Line type="monotone" dataKey="סה״כ" stroke={CODE_COLORS.total} strokeWidth={2.5} dot={{ r: 4 }} />
          </LineChart>
        </ResponsiveContainer>
      </Section>

      {Object.entries(trends).map(([code, t]) => {
        const chartData = t.data.map(d => ({
          name: d.month_display,
          total: d.total,
          regular: d.regular_total,
        }));
        return (
          <Section key={code} title={`${t.name} (קוד ${code})`}>
            <div className="grid grid-cols-3 gap-3 mb-4 text-center">
              <StatPill label="ממוצע" value={formatShekel(t.average)} color="blue" />
              <StatPill label="שינוי %" value={`${t.change_percent > 0 ? '+' : ''}${t.change_percent}%`} color={t.trend_direction === 'up' ? 'green' : t.trend_direction === 'down' ? 'red' : 'gray'} />
              <StatPill label="מגמה" value={`${trendArrow(t.trend_direction)} ${t.trend_direction === 'up' ? 'עלייה' : t.trend_direction === 'down' ? 'ירידה' : 'יציב'}`} color="gray" />
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={chartData} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis dataKey="name" tick={{ fontSize: 11, fontFamily: 'inherit' }} />
                <YAxis tickFormatter={v => `₪${(v/1000).toFixed(0)}K`} tick={{ fontSize: 11 }} />
                <Tooltip content={<HebTooltip />} />
                <Line type="monotone" dataKey="total" name="סה״כ" stroke={CODE_COLORS[code] || '#6B7280'} strokeWidth={2.5} dot={{ r: 4 }} />
                <Line type="monotone" dataKey="regular" name="רגיל" stroke={CODE_COLORS[code] || '#6B7280'} strokeWidth={1.5} strokeDasharray="5 3" dot={false} opacity={0.7} />
              </LineChart>
            </ResponsiveContainer>
          </Section>
        );
      })}
    </div>
  );
}

// ────────────────────────────────────────────────────────────
// Tab: Forecast (admin — requires municipality)
// ────────────────────────────────────────────────────────────
function AdminForecastTab({ municipalityId, roundingMode, onModeResolved }) {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);

  useEffect(() => {
    if (!municipalityId) return;
    setLoading(true);
    analyticsAPI.getForecast(municipalityId)
      .then(r => setData(r.data))
      .catch(e => setError(e.response?.data?.detail || 'שגיאה בטעינת תחזית'))
      .finally(() => setLoading(false));
  }, [municipalityId]);

  if (!municipalityId) return <EmptyState msg="בחר רשות מקומית להצגת תחזית" />;
  if (loading) return <Spinner />;
  if (error)   return <ErrorBox msg={error} />;
  if (!data?.predicted_total) return <EmptyState msg="אין מספיק נתונים לחישוב תחזית" />;

  const concreteRoundingMode = resolveConcreteMode(roundingMode, extractNumericValues(data));
  activeRoundingMode = concreteRoundingMode;

  useEffect(() => {
    onModeResolved?.(concreteRoundingMode);
  }, [concreteRoundingMode, onModeResolved]);

  const conf = CONFIDENCE_STYLES[data.confidence] || CONFIDENCE_STYLES.none;

  const historicalData = (data.based_on_months || []).map((m, i) => ({
    name: m,
    'בפועל': data.based_on_totals?.[i] ?? 0,
    תחזית: null,
  }));

  const chartData = [
    ...historicalData.slice(0, -1),
    { ...historicalData[historicalData.length - 1], תחזית: historicalData[historicalData.length - 1]?.['בפועל'] },
    { name: data.forecast_month, 'בפועל': null, תחזית: data.predicted_total },
  ];

  return (
    <div className="space-y-6">
      <div className={`rounded-xl border-2 ${conf.border} ${conf.bg} p-4 flex items-center gap-3`} dir="rtl">
        <span className="text-2xl">{conf.icon}</span>
        <div>
          <p className={`font-bold font-hebrew ${conf.text}`}>{conf.label}</p>
          <p className={`text-sm font-hebrew ${conf.text}`}>{data.confidence_reason}</p>
        </div>
      </div>

      <Section title={`תחזית לחודש ${data.forecast_month_display}`}>
        <div className="text-center py-4 space-y-2">
          <p className="text-5xl font-bold text-purple-700">{formatShekel(data.predicted_total)}</p>
          <p className={`text-lg font-hebrew font-semibold ${data.change_from_last >= 0 ? 'text-red-600' : 'text-green-600'}`}>
            {data.change_from_last >= 0 ? '↑' : '↓'} {formatShekel(Math.abs(data.change_from_last))}
            &nbsp;({data.change_percent > 0 ? '+' : ''}{data.change_percent}%)
          </p>
        </div>

        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={chartData} margin={{ top: 10, right: 20, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis dataKey="name" tick={{ fontSize: 11, fontFamily: 'inherit' }} />
            <YAxis tickFormatter={v => `₪${(v/1000).toFixed(0)}K`} tick={{ fontSize: 11 }} />
            <Tooltip content={<HebTooltip />} />
            <Line type="monotone" dataKey="בפועל" stroke={CODE_COLORS.total} strokeWidth={2.5} dot={{ r: 4 }} connectNulls={false} />
            <Line type="monotone" dataKey="תחזית" stroke={CODE_COLORS.forecast} strokeWidth={2.5} strokeDasharray="8 4" dot={{ r: 6, fill: '#8B5CF6' }} connectNulls />
          </LineChart>
        </ResponsiveContainer>
      </Section>

      <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 text-xs text-gray-500 font-hebrew" dir="rtl">
        {data.disclaimer}
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────
// Tab: Anomalies (admin — requires municipality)
// ────────────────────────────────────────────────────────────
function AdminAnomaliesTab({ municipalityId, selectedMonth, roundingMode, onModeResolved }) {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);

  useEffect(() => {
    if (!municipalityId || !selectedMonth) return;
    setLoading(true);
    analyticsAPI.getAnomalies(municipalityId, selectedMonth)
      .then(r => setData(r.data))
      .catch(e => setError(e.response?.data?.detail || 'שגיאה בטעינת חריגות'))
      .finally(() => setLoading(false));
  }, [municipalityId, selectedMonth]);

  if (!municipalityId) return <EmptyState msg="בחר רשות מקומית" />;
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

// ────────────────────────────────────────────────────────────
// Tab: Retro Aging (admin — requires municipality)
// ────────────────────────────────────────────────────────────
function AdminRetroTab({ municipalityId, selectedMonth, roundingMode, onModeResolved }) {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const [sortDir, setSortDir] = useState('desc');

  useEffect(() => {
    if (!municipalityId || !selectedMonth) return;
    setLoading(true);
    analyticsAPI.getRetroAging(municipalityId, selectedMonth)
      .then(r => setData(r.data))
      .catch(e => setError(e.response?.data?.detail || 'שגיאה בטעינת נתוני רטרו'))
      .finally(() => setLoading(false));
  }, [municipalityId, selectedMonth]);

  if (!municipalityId) return <EmptyState msg="בחר רשות מקומית" />;
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

  return (
    <div className="space-y-6" dir="rtl">
      {aging_summary.very_old_7_plus.count > 0 && (
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

      <div className="bg-white border border-gray-200 rounded-xl p-5 flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500 font-hebrew">סה״כ תשלומי רטרו</p>
          <p className="text-3xl font-bold text-gray-800">{formatShekel(total_retro_amount)}</p>
        </div>
        <p className="text-4xl">🔄</p>
      </div>

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
                const ageTxt = line.age_color === 'red' ? 'text-red-700' : line.age_color === 'amber' ? 'text-amber-700' : 'text-green-700';
                const ageBg  = line.age_color === 'red' ? 'bg-red-50' : line.age_color === 'amber' ? 'bg-amber-50' : '';
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
// Shared anomaly card (used by AnomaliesTab)
// ────────────────────────────────────────────────────────────
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

// ────────────────────────────────────────────────────────────
// Shared UI
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
// Main admin page
// ────────────────────────────────────────────────────────────
export default function AdminAnalyticsPage() {
  const months = getLast12Months();
  const [searchParams, setSearchParams] = useSearchParams();
  const defaultMonth = months[0]?.value || '';
  const [activeTab, setActiveTab]           = useState('overview');
  const [municipalities, setMunicipalities] = useState([]);
  const [selectedMuni, setSelectedMuni]     = useState(null);
  const [roundingMode, setRoundingMode] = useRoundingMode();
  const [resolvedModeForBanner, setResolvedModeForBanner] = useState(ROUNDING_MODES.EXACT);
  const selectedMonth = searchParams.get('month') || defaultMonth;
  const analyticsDisclosureText = getRoundingDisclosureText(resolvedModeForBanner);

  useEffect(() => {
    if (!searchParams.get('month') && defaultMonth) {
      const next = new URLSearchParams(searchParams);
      next.set('month', defaultMonth);
      setSearchParams(next, { replace: true });
    }
  }, [searchParams, setSearchParams, defaultMonth]);

  const handleMonthChange = useCallback((nextMonth) => {
    const next = new URLSearchParams(searchParams);
    if (nextMonth) {
      next.set('month', nextMonth);
    } else {
      next.delete('month');
    }
    setSearchParams(next);
  }, [searchParams, setSearchParams]);

  // Load municipalities on mount
  useEffect(() => {
    municipalityAPI.getAll()
      .then(r => {
        const list = r.data || [];
        setMunicipalities(list);
        if (list.length > 0) setSelectedMuni(list[0].id);
      })
      .catch(() => {});
  }, []);

  const needsMuniSelector = activeTab !== 'overview';
  const needsMonthSelector = activeTab === 'overview' || activeTab === 'anomalies' || activeTab === 'retro';

  return (
    <PageWrapper title="ניתוח ומגמות">
      <div dir="rtl" className="space-y-6">
        {/* Header */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
          <h1 className="text-2xl font-bold font-hebrew text-gray-800 mb-4 flex items-center gap-2">
            📊 ניתוח ומגמות — מנהל מערכת
          </h1>
          {needsMonthSelector && selectedMonth && (
            <p className="text-sm text-gray-600 font-hebrew mb-3">
              חודש מוצג: {formatMonthDisplay(selectedMonth)}
            </p>
          )}

          <div className="flex flex-wrap gap-4 items-center">
            <RoundingModeToggle mode={roundingMode} onChange={setRoundingMode} />

            {/* Month selector */}
            {needsMonthSelector && (
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-600 font-hebrew">חודש:</label>
                <select
                  value={selectedMonth}
                  onChange={e => handleMonthChange(e.target.value)}
                  className="border border-gray-300 rounded-lg px-3 py-2 text-sm font-hebrew bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                  dir="rtl"
                >
                  <option value="">בחר חודש</option>
                  {months.map(m => (
                    <option key={m.value} value={m.value}>{m.value}</option>
                  ))}
                </select>
              </div>
            )}

            {/* Municipality selector */}
            {needsMuniSelector && (
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-600 font-hebrew">רשות:</label>
                <select
                  value={selectedMuni || ''}
                  onChange={e => setSelectedMuni(Number(e.target.value))}
                  className="border border-gray-300 rounded-lg px-3 py-2 text-sm font-hebrew bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                  dir="rtl"
                >
                  <option value="">בחר רשות</option>
                  {municipalities.map(m => (
                    <option key={m.id} value={m.id}>{m.name}</option>
                  ))}
                </select>
              </div>
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
        {activeTab === 'overview'  && <OverviewTab selectedMonth={selectedMonth} roundingMode={roundingMode} onModeResolved={setResolvedModeForBanner} />}
        {activeTab === 'trends'    && <AdminTrendsTab municipalityId={selectedMuni} roundingMode={roundingMode} onModeResolved={setResolvedModeForBanner} />}
        {activeTab === 'forecast'  && <AdminForecastTab municipalityId={selectedMuni} roundingMode={roundingMode} onModeResolved={setResolvedModeForBanner} />}
        {activeTab === 'anomalies' && <AdminAnomaliesTab municipalityId={selectedMuni} selectedMonth={selectedMonth} roundingMode={roundingMode} onModeResolved={setResolvedModeForBanner} />}
        {activeTab === 'retro'     && <AdminRetroTab municipalityId={selectedMuni} selectedMonth={selectedMonth} roundingMode={roundingMode} onModeResolved={setResolvedModeForBanner} />}
      </div>
    </PageWrapper>
  );
}
