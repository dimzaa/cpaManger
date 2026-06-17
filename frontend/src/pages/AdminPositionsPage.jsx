import React, { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { positionsAPI } from '../services/api';
import {
  Briefcase,
  AlertTriangle,
  CheckCircle,
  XCircle,
  TrendingUp,
  Building2,
  Mail,
  ChevronDown,
  ChevronUp,
  Search,
  RefreshCw,
  Info,
  Download,
} from 'lucide-react';

// ─── Helpers ────────────────────────────────────────────────────────────────

const POSITION_LABELS = {
  assistants: 'עוזרות גננות',
  kindergartens: 'גן נוסף',
  completion_children: 'ילדי השלמה',
  six_day: 'שעת שישי',
  attendance_officer: 'קב"ס',
};

const POSITION_IDS = ['assistants', 'kindergartens', 'completion_children', 'six_day', 'attendance_officer'];
const TABLE_COLUMN_COUNT = POSITION_IDS.length + 5;

function toFiniteNumber(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function sanitizePositionValue(pos) {
  if (!pos || typeof pos !== 'object' || Array.isArray(pos)) return null;

  const direction = ['missing', 'surplus', 'ok'].includes(pos.gap_direction)
    ? pos.gap_direction
    : 'ok';
  const severity = ['critical', 'attention', 'ok', 'surplus', 'none'].includes(pos.severity)
    ? pos.severity
    : 'none';

  return {
    current: toFiniteNumber(pos.current),
    entitled: toFiniteNumber(pos.entitled),
    gap: toFiniteNumber(pos.gap),
    gap_direction: direction,
    severity,
    annual_value: toFiniteNumber(pos.annual_value),
    monthly_value: toFiniteNumber(pos.monthly_value),
  };
}

function sanitizeMunicipalityRow(muni) {
  const sourcePositions = muni?.positions && typeof muni.positions === 'object' ? muni.positions : {};

  const normalizedPositions = POSITION_IDS.reduce((acc, id) => {
    const normalized = sanitizePositionValue(sourcePositions[id]);
    if (normalized) acc[id] = normalized;
    return acc;
  }, {});

  const divisor = toFiniteNumber(muni?.divisor, 0);

  return {
    ...muni,
    code: String(muni?.code ?? ''),
    name: String(muni?.name ?? ''),
    total_children: toFiniteNumber(muni?.total_children),
    total_potential_value: toFiniteNumber(muni?.total_potential_value),
    grant_status: String(muni?.grant_status ?? 'לא ידוע'),
    divisor,
    has_data: Boolean(muni?.has_data),
    positions: normalizedPositions,
  };
}

function formatCurrency(value) {
  if (!value && value !== 0) return '—';
  if (value >= 1_000_000) {
    return `₪${(value / 1_000_000).toFixed(1)}M`;
  }
  if (value >= 1_000) {
    return `₪${Math.round(value / 1_000).toLocaleString()}K`;
  }
  return `₪${Math.round(value).toLocaleString()}`;
}

function AlertBadge({ alertLevel }) {
  const cfg = {
    critical: { bg: 'bg-red-100', text: 'text-red-700', label: '🔴 דחוף' },
    attention: { bg: 'bg-amber-100', text: 'text-amber-700', label: '⚠️ לטיפול' },
    ok: { bg: 'bg-green-100', text: 'text-green-700', label: '✅ תקין' },
    no_data: { bg: 'bg-gray-100', text: 'text-gray-500', label: '— אין נתונים' },
  };
  const c = cfg[alertLevel] || cfg.no_data;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${c.bg} ${c.text}`}>
      {c.label}
    </span>
  );
}

function PositionCell({ pos }) {
  if (!pos) return <td className="px-3 py-2 text-center text-gray-300 text-sm">—</td>;

  const { gap, gap_direction, severity, annual_value } = pos;

  if (gap_direction === 'ok') {
    return (
      <td className="px-3 py-2 text-center">
        <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-green-100 text-green-600">
          <CheckCircle size={14} />
        </span>
      </td>
    );
  }

  if (gap_direction === 'missing') {
    const colorCls = severity === 'critical'
      ? 'bg-red-100 text-red-700'
      : 'bg-amber-100 text-amber-700';
    return (
      <td className="px-3 py-2 text-center">
        <div className="flex flex-col items-center gap-0.5">
          <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-bold ${colorCls}`}>
            {severity === 'critical' ? '🔴' : '⚠️'} -{gap}
          </span>
          <span className="text-xs text-gray-400">{formatCurrency(annual_value)}</span>
        </div>
      </td>
    );
  }

  if (gap_direction === 'surplus') {
    return (
      <td className="px-3 py-2 text-center">
        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-bold bg-orange-100 text-orange-600">
          🟠 +{gap}
        </span>
      </td>
    );
  }

  return <td className="px-3 py-2 text-center text-gray-300 text-sm">—</td>;
}

// ─── Email builder ───────────────────────────────────────────────────────────

function buildEmail(muni) {
  const lines = [
    `שלום רב,`,
    ``,
    `להלן תוצאות ניתוח משרות ותקנים עבור ${muni.name}:`,
    ``,
    `ילדים כולל: ${muni.total_children}  |  חלוקה: ${muni.grant_status} (${muni.divisor})`,
    ``,
    `פירוט לפי תחום:`,
  ];

  POSITION_IDS.forEach((id) => {
    const p = muni.positions[id];
    if (!p) return;
    const label = POSITION_LABELS[id];
    if (p.gap_direction === 'ok') {
      lines.push(`✅ ${label}: תקין`);
    } else if (p.gap_direction === 'missing') {
      lines.push(`⚠️ ${label}: חסר ${p.gap} תקנים | שווי שנתי: ₪${Math.round(p.annual_value).toLocaleString()}`);
    } else if (p.gap_direction === 'surplus') {
      lines.push(`🟠 ${label}: עודף ${p.gap} תקנים`);
    }
  });

  lines.push(``, `סה"כ פוטנציאל שנתי לא מנוצל: ₪${Math.round(muni.total_potential_value).toLocaleString()}`);
  lines.push(``, `בברכה,`, `מחלקת ייעוץ תקציבי`);

  return {
    subject: `ניתוח משרות ותקנים — ${muni.name}`,
    body: lines.join('\n'),
  };
}

// ─── Skeletons ───────────────────────────────────────────────────────────────

function SkeletonRow() {
  return (
    <tr className="animate-pulse border-b border-gray-100">
      {Array.from({ length: TABLE_COLUMN_COUNT }).map((_, i) => (
        <td key={i} className="px-3 py-3">
          <div className="h-4 bg-gray-200 rounded w-full" />
        </td>
      ))}
    </tr>
  );
}

// ─── Default month helper ─────────────────────────────────────────────────────

function getDefaultMonth() {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  return `${y}-${m}`;
}

// ─── Main component ──────────────────────────────────────────────────────────

export default function AdminPositionsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const month = searchParams.get('month') || getDefaultMonth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filterLevel, setFilterLevel] = useState('all');
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('potential');
  const [sortDir, setSortDir] = useState('desc');
  const [expandedRow, setExpandedRow] = useState(null);
  const [analysisCache, setAnalysisCache] = useState({});
  const [loadingEmailKey, setLoadingEmailKey] = useState(null);
  const [showAllMunicipalities, setShowAllMunicipalities] = useState(false);

  useEffect(() => {
    if (!searchParams.get('month')) {
      const next = new URLSearchParams(searchParams);
      next.set('month', getDefaultMonth());
      setSearchParams(next, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  function handleMonthChange(nextMonth) {
    const next = new URLSearchParams(searchParams);
    if (nextMonth) {
      next.set('month', nextMonth);
    } else {
      next.delete('month');
    }
    setSearchParams(next);
  }

  async function fetchData() {
    setLoading(true);
    setError(null);
    try {
      const res = await positionsAPI.getAdminSummary(month);
      const normalizedMunicipalities = (res?.data?.municipalities || []).map(sanitizeMunicipalityRow);
      setData({
        ...res.data,
        municipalities: normalizedMunicipalities,
      });
    } catch (err) {
      setError(err?.response?.data?.detail || 'שגיאה בטעינת נתונים');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchData();
  }, [month]);

  // ── Sorting & filtering ──────────────────────────────────────────────────

  const filtered = useMemo(() => {
    if (!data?.municipalities) return [];
    let rows = [...data.municipalities];

    if (!showAllMunicipalities) {
      rows = rows.filter((r) => r.has_data);
    }

    if (filterLevel !== 'all') {
      rows = rows.filter((r) => r.alert_level === filterLevel);
    }

    if (search.trim()) {
      const q = search.trim().toLowerCase();
      rows = rows.filter((r) => String(r.name || '').toLowerCase().includes(q) || String(r.code || '').toLowerCase().includes(q));
    }

    rows.sort((a, b) => {
      let valA, valB;
      if (sortBy === 'potential') { valA = a.total_potential_value; valB = b.total_potential_value; }
      else if (sortBy === 'children') { valA = a.total_children; valB = b.total_children; }
      else { valA = a.name; valB = b.name; }

      if (typeof valA === 'string') {
        return sortDir === 'asc' ? valA.localeCompare(valB, 'he') : valB.localeCompare(valA, 'he');
      }
      return sortDir === 'asc' ? valA - valB : valB - valA;
    });

    return rows;
  }, [data, filterLevel, search, sortBy, sortDir, showAllMunicipalities]);

  function toggleSort(field) {
    if (sortBy === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(field);
      setSortDir('desc');
    }
  }

  function SortIcon({ field }) {
    if (sortBy !== field) return null;
    return sortDir === 'asc' ? <ChevronUp size={12} /> : <ChevronDown size={12} />;
  }

  // ── Grand summary cards ──────────────────────────────────────────────────

  const gs = data?.grand_summary;
  const summaryCards = gs
    ? [
        {
          label: 'רשויות עם נתונים',
          value: data.municipalities_with_data,
          sub: `מתוך ${data.total_municipalities} רשויות`,
          icon: Building2,
          color: 'blue',
        },
        {
          label: 'דורש טיפול דחוף',
          value: gs.total_urgent,
          sub: 'רשויות עם חריגה קריטית',
          icon: XCircle,
          color: 'red',
        },
        {
          label: 'לטיפול',
          value: gs.total_attention,
          sub: 'פערים שניתן לתקן',
          icon: AlertTriangle,
          color: 'amber',
        },
        {
          label: 'פוטנציאל כולל',
          value: formatCurrency(gs.total_potential_value),
          sub: 'בשנה — כלל הרשויות',
          icon: TrendingUp,
          color: 'green',
        },
      ]
    : [];

  const colorMap = {
    blue: 'bg-blue-50 border-blue-200 text-blue-700',
    red: 'bg-red-50 border-red-200 text-red-700',
    amber: 'bg-amber-50 border-amber-200 text-amber-700',
    green: 'bg-green-50 border-green-200 text-green-700',
  };

  const urgentRows = filtered.filter((r) => r.alert_level === 'critical');

  const annualPotential = gs?.total_potential_value || 0;
  const monthlyPotential = annualPotential / 12;

  async function getPositionEmail(muniId, positionId) {
    if (analysisCache[muniId]) {
      const pos = analysisCache[muniId].find((p) => p.id === positionId);
      if (pos?.email_subject && pos?.email_body) {
        return { subject: pos.email_subject, body: pos.email_body };
      }
      return null;
    }

    const res = await positionsAPI.getAnalysis(muniId, month);
    const positions = res?.data?.positions || [];
    setAnalysisCache((prev) => ({ ...prev, [muniId]: positions }));
    const pos = positions.find((p) => p.id === positionId);
    if (pos?.email_subject && pos?.email_body) {
      return { subject: pos.email_subject, body: pos.email_body };
    }
    return null;
  }

  async function handleGapEmail(muni, positionId) {
    const key = `${muni.id}-${positionId}`;
    try {
      setLoadingEmailKey(key);
      const email = await getPositionEmail(muni.id, positionId);
      if (!email) return;
      const mailto = `mailto:?subject=${encodeURIComponent(email.subject)}&body=${encodeURIComponent(email.body)}`;
      window.open(mailto, '_blank');
    } finally {
      setLoadingEmailKey(null);
    }
  }

  function handleExportExcel() {
    const header = ['Position Type', 'Entitled', 'Actual', 'Gap', 'Monthly Value', 'Annual Value'];
    const rows = [header];

    filtered.forEach((muni) => {
      if (!muni.has_data) return;
      POSITION_IDS.forEach((id) => {
        const p = muni.positions[id];
        if (!p) return;
        rows.push([
          POSITION_LABELS[id],
          String(p.entitled ?? 0),
          String(p.current ?? 0),
          String(p.gap ?? 0),
          String(Math.round(p.monthly_value || 0)),
          String(Math.round(p.annual_value || 0)),
        ]);
      });
    });

    const csv = rows.map((r) => r.map((v) => `"${String(v).replaceAll('"', '""')}"`).join(',')).join('\n');
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `positions_gap_${month}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  }

  return (
    <div className="p-6 max-w-screen-2xl mx-auto" dir="rtl">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-100 rounded-xl">
            <Briefcase size={24} className="text-indigo-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">ניתוח משרות — כלל הרשויות</h1>
            <p className="text-sm text-gray-500">השוואת תקנים ופערים בין כלל הרשויות המקומיות</p>
            <p className="text-sm text-indigo-700 mt-1 font-hebrew">
              דף זה מציג את הפער בין מה שהרשות זכאית לקבל לבין מה שקיבלה בפועל, על פי חוברת התקצוב.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <label className="text-sm text-gray-600 font-medium">חודש:</label>
          <input
            type="month"
            value={month}
            onChange={(e) => handleMonthChange(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            רענן
          </button>
          <button
            onClick={handleExportExcel}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white text-sm rounded-lg hover:bg-emerald-700 transition-colors"
          >
            <Download size={14} />
            הורד Excel
          </button>
        </div>
      </div>

      {!loading && data && (
        <div className="mb-6 p-4 md:p-5 rounded-xl border border-emerald-300 bg-gradient-to-l from-emerald-100 to-emerald-50 text-emerald-900 font-hebrew">
          <div className="text-sm md:text-base font-semibold">פוטנציאל החזר</div>
          <div className="mt-1 text-2xl md:text-3xl font-extrabold tracking-tight">
            {formatCurrency(monthlyPotential)}
            <span className="text-base md:text-lg font-medium mr-2">לחודש</span>
            <span className="mx-2 text-emerald-500">/</span>
            {formatCurrency(annualPotential)}
            <span className="text-base md:text-lg font-medium mr-2">לשנה</span>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm flex items-center gap-2">
          <XCircle size={16} />
          {error}
        </div>
      )}

      {/* Grand summary cards */}
      {!loading && data && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {summaryCards.map((card) => {
            const Icon = card.icon;
            return (
              <div
                key={card.label}
                className={`p-4 rounded-xl border ${colorMap[card.color]} flex items-start gap-3`}
              >
                <Icon size={22} className="mt-0.5 shrink-0" />
                <div>
                  <div className="text-2xl font-bold">{card.value}</div>
                  <div className="text-sm font-medium">{card.label}</div>
                  <div className="text-xs opacity-70 mt-0.5">{card.sub}</div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Urgent alert */}
      {!loading && urgentRows.length > 0 && (
        <div className="mb-5 p-4 bg-red-50 border border-red-300 rounded-xl">
          <div className="flex items-center gap-2 text-red-700 font-bold mb-2">
            <AlertTriangle size={18} />
            {urgentRows.length} רשויות דורשות טיפול דחוף
          </div>
          <ul className="flex flex-wrap gap-2">
            {urgentRows.map((r) => (
              <li
                key={r.id}
                className="px-3 py-1 bg-red-100 text-red-800 text-xs rounded-full font-medium"
              >
                {r.name} — {formatCurrency(r.total_potential_value)}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Filter & Search bar */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="חיפוש רשות..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full border border-gray-200 rounded-lg pr-9 pl-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
        </div>

        {['all', 'critical', 'attention', 'ok', 'no_data'].map((level) => {
          const labels = {
            all: 'כולן',
            critical: '🔴 דחוף',
            attention: '⚠️ לטיפול',
            ok: '✅ תקין',
            no_data: '— אין נתונים',
          };
          return (
            <button
              key={level}
              onClick={() => setFilterLevel(level)}
              className={`px-3 py-1.5 text-xs rounded-full border transition-colors ${
                filterLevel === level
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-white text-gray-600 border-gray-200 hover:border-indigo-400'
              }`}
            >
              {labels[level]}
            </button>
          );
        })}

        <button
          onClick={() => setShowAllMunicipalities((v) => !v)}
          className={`px-3 py-1.5 text-xs rounded-full border transition-colors ${
            showAllMunicipalities
              ? 'bg-gray-700 text-white border-gray-700'
              : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400'
          }`}
          title="הצג/הסתר רשויות ללא העלאת נתונים"
        >
          {showAllMunicipalities ? 'הצג רק רשויות פעילות' : 'הצג את כל הרשויות'}
        </button>

        <div className="text-sm text-gray-400 mr-auto">
          {filtered.length} רשויות מוצגות
        </div>
      </div>

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1180px] text-sm border-separate border-spacing-0">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th
                  className="px-4 py-3 text-right font-semibold text-gray-700 cursor-pointer hover:bg-gray-100 select-none border-s border-gray-200 first:border-s-0"
                  onClick={() => toggleSort('name')}
                >
                  <span className="flex items-center gap-1">רשות <SortIcon field="name" /></span>
                </th>
                <th
                  className="px-3 py-3 text-center font-semibold text-gray-700 cursor-pointer hover:bg-gray-100 select-none border-s border-gray-200"
                  onClick={() => toggleSort('children')}
                >
                  <span className="flex items-center justify-center gap-1 whitespace-nowrap">ילדים <SortIcon field="children" /></span>
                </th>
                <th className="px-3 py-3 text-center font-semibold text-gray-700 whitespace-nowrap border-s border-gray-200">מענק</th>
                {POSITION_IDS.map((id) => (
                  <th key={id} className="px-3 py-3 text-center font-semibold text-gray-700 whitespace-nowrap text-xs border-s border-gray-200">
                    {POSITION_LABELS[id]}
                  </th>
                ))}
                <th
                  className="px-3 py-3 text-center font-semibold text-gray-700 cursor-pointer hover:bg-gray-100 select-none whitespace-nowrap border-s border-gray-200"
                  onClick={() => toggleSort('potential')}
                >
                  <span className="flex items-center justify-center gap-1">פוטנציאל <SortIcon field="potential" /></span>
                </th>
                <th className="px-4 py-3 text-center font-semibold text-gray-700 border-s border-gray-200">פעולות</th>
              </tr>
            </thead>
            <tbody>
              {loading && Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} />)}

              {!loading && filtered.length === 0 && (
                <tr>
                  <td colSpan={TABLE_COLUMN_COUNT} className="px-4 py-12 text-center text-gray-400">
                    <div className="flex flex-col items-center gap-2">
                      <Info size={32} className="text-gray-300" />
                      <span>לא נמצאו רשויות התואמות את הסינון</span>
                    </div>
                  </td>
                </tr>
              )}

              {!loading &&
                filtered.map((muni) => {
                  const isExpanded = expandedRow === muni.id;
                  const email = muni.has_data ? buildEmail(muni) : null;

                  return (
                    <React.Fragment key={muni.id}>
                      <tr
                        className={`border-b border-gray-100 hover:bg-gray-50 transition-colors ${
                          !muni.has_data ? 'opacity-50' : ''
                        } ${isExpanded ? 'bg-indigo-50' : ''}`}
                      >
                        {/* Name + status */}
                        <td className="px-4 py-3">
                          <div className="font-medium text-gray-900">{muni.name}</div>
                          <div className="mt-0.5">
                            <AlertBadge alertLevel={muni.alert_level} />
                          </div>
                          {!muni.has_data && (
                            <div className="text-xs text-gray-400 italic mt-1">אין נתונים לחודש זה</div>
                          )}
                        </td>

                        {/* Children */}
                        <td className="px-3 py-3 text-center font-medium text-gray-700">
                          {muni.has_data ? muni.total_children.toLocaleString() : '—'}
                        </td>

                        {/* Grant */}
                        <td className="px-3 py-3 text-center text-xs text-gray-600 whitespace-nowrap">
                          {muni.has_data ? (
                            <span className={`px-2 py-0.5 rounded-full text-xs ${muni.divisor === 31 ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'}`}>
                              {muni.divisor === 31 ? 'מענק' : 'ללא'}
                            </span>
                          ) : '—'}
                        </td>

                        {/* Position cells */}
                        {POSITION_IDS.map((id) => (
                          <PositionCell key={id} pos={muni.positions[id]} />
                        ))}

                        {/* Potential */}
                        <td className="px-3 py-3 text-center font-extrabold text-indigo-700 text-base whitespace-nowrap">
                          {muni.has_data ? formatCurrency(muni.total_potential_value) : '—'}
                        </td>

                        {/* Actions */}
                        <td className="px-4 py-3 text-center">
                          <div className="flex items-center justify-center gap-2">
                            {email && (
                              <a
                                href={`mailto:?subject=${encodeURIComponent(email.subject)}&body=${encodeURIComponent(email.body)}`}
                                className="inline-flex items-center gap-1 px-2 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs rounded-lg transition-colors"
                                title="שלח מייל לרשות"
                              >
                                <Mail size={13} />
                                שלח
                              </a>
                            )}
                            {muni.has_data && (
                              <button
                                onClick={() => setExpandedRow(isExpanded ? null : muni.id)}
                                className="inline-flex items-center gap-1 px-2 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-600 text-xs rounded-lg transition-colors"
                              >
                                {isExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                                פרטים
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>

                      {/* Expanded detail row */}
                      {isExpanded && muni.has_data && (
                        <tr className="bg-indigo-50 border-b border-indigo-100">
                          <td colSpan={TABLE_COLUMN_COUNT} className="px-6 py-4">
                            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
                              {POSITION_IDS.map((id) => {
                                const p = muni.positions[id];
                                if (!p) return null;
                                return (
                                  <div key={id} className="bg-white rounded-xl p-3 shadow-sm border border-indigo-100">
                                    <div className="text-xs font-semibold text-gray-700 mb-2">
                                      {POSITION_LABELS[id]}
                                    </div>
                                    <div className="space-y-1 text-xs text-gray-600">
                                      <div className="flex justify-between">
                                        <span>קיים:</span>
                                        <span className="font-medium">{p.current}</span>
                                      </div>
                                      <div className="flex justify-between">
                                        <span>זכאות:</span>
                                        <span className="font-medium">{p.entitled}</span>
                                      </div>
                                      <div className="flex justify-between">
                                        <span>פער:</span>
                                        <span className={`font-bold ${
                                          p.gap_direction === 'missing' && p.gap > 0 ? 'text-red-600' :
                                          p.gap_direction === 'surplus' ? 'text-orange-600' : 'text-green-600'
                                        }`}>
                                          {p.gap_direction === 'missing' && p.gap > 0 ? `-${p.gap}` :
                                           p.gap_direction === 'surplus' ? `+${p.gap}` : '0'}
                                        </span>
                                      </div>
                                      {p.annual_value > 0 && (
                                        <div className="flex justify-between border-t border-gray-100 pt-1 mt-1">
                                          <span>שווי שנתי:</span>
                                          <span className="font-bold text-indigo-700">
                                            {formatCurrency(p.annual_value)}
                                          </span>
                                        </div>
                                      )}
                                      {p.gap_direction === 'missing' && p.gap > 0 && (
                                        <button
                                          onClick={() => handleGapEmail(muni, id)}
                                          className="w-full mt-2 inline-flex items-center justify-center gap-1 px-2 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-hebrew"
                                        >
                                          <Mail size={12} />
                                          {loadingEmailKey === `${muni.id}-${id}` ? 'טוען...' : '📧 שלח מייל לרשות'}
                                        </button>
                                      )}
                                    </div>
                                  </div>
                                );
                              })}
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
      </div>

      {/* Footer note */}
      {data && (
        <div className="mt-4 text-xs text-gray-400 text-center flex items-center justify-center gap-1">
          <Info size={12} />
          נתונים מבוססים על חוברת התקצוב הסגולה של משרד החינוך | עודכן: {data.generated_at?.slice(0, 16).replace('T', ' ')}
        </div>
      )}
    </div>
  );
}
