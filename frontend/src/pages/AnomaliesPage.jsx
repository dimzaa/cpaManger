import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { AlertTriangle, Check, X, Sparkles, TrendingDown, TrendingUp } from 'lucide-react';
import PageWrapper from '../components/layout/PageWrapper';
import { budgetAPI, runsAPI } from '../services/api';
import { getCurrentMonth } from '../utils/format';

/**
 * Priority-4 anomalies view.
 *
 * For the currently-selected month, fetches every run's anomalies and lists them
 * with the auto-generated Hebrew narrative + filter chips + acknowledge button.
 */
const FLAG_META = {
  new:           { label: 'חדש',              color: 'bg-blue-100 text-blue-800',    icon: Sparkles },
  outlier:       { label: 'חריגה',            color: 'bg-amber-100 text-amber-800',  icon: AlertTriangle },
  disappeared:   { label: 'נעלם',             color: 'bg-rose-100 text-rose-800',    icon: TrendingDown },
  tie_out_gap:   { label: 'פער בהצלבה',       color: 'bg-purple-100 text-purple-800', icon: AlertTriangle },
};

export default function AnomaliesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const monthFromQuery = searchParams.get('month');
  const [month, setMonth] = useState(monthFromQuery || getCurrentMonth());
  const [activeFilter, setActiveFilter] = useState('all');
  const [showAcked, setShowAcked] = useState(false);
  const [anomalies, setAnomalies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        // Get all runs for this month, then fetch their anomalies
        const runsRes = await runsAPI.getAll({ month });
        const runs = runsRes.data || [];
        if (runs.length === 0) {
          if (!cancelled) setAnomalies([]);
          return;
        }
        const lists = await Promise.all(
          runs.map((r) =>
            budgetAPI
              .getCodeAnomalies(r.id)
              .then((res) => (res.data || []).map((a) => ({ ...a, _muni: r.municipality_id })))
              .catch(() => [])
          )
        );
        const merged = lists.flat();
        if (!cancelled) setAnomalies(merged);
      } catch (e) {
        if (!cancelled) setError(String(e?.message || e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [month]);

  const visible = useMemo(() => {
    return anomalies.filter((a) => {
      if (!showAcked && a.acknowledged_by_cpa) return false;
      if (activeFilter !== 'all' && a.flag_type !== activeFilter) return false;
      return true;
    });
  }, [anomalies, activeFilter, showAcked]);

  const counts = useMemo(() => {
    const c = { all: 0, new: 0, outlier: 0, disappeared: 0, tie_out_gap: 0 };
    anomalies.forEach((a) => {
      if (showAcked || !a.acknowledged_by_cpa) {
        c.all += 1;
        c[a.flag_type] = (c[a.flag_type] || 0) + 1;
      }
    });
    return c;
  }, [anomalies, showAcked]);

  const acknowledge = async (anomalyId) => {
    try {
      await budgetAPI.acknowledgeAnomaly(anomalyId);
      setAnomalies((prev) =>
        prev.map((a) =>
          a.id === anomalyId
            ? { ...a, acknowledged_by_cpa: true, acknowledged_at: new Date().toISOString() }
            : a
        )
      );
    } catch (e) {
      alert(`שגיאה באישור: ${e?.message || e}`);
    }
  };

  return (
    <PageWrapper title="חריגות ובקרה">
      <div className="max-w-6xl mx-auto space-y-6" dir="rtl">
        {/* Header */}
        <div className="bg-white rounded-lg shadow p-6">
          <h1 className="text-2xl font-bold text-slate-900 mb-2">חריגות ובקרה</h1>
          <p className="text-slate-600 mb-4">
            רשימת כל החריגות עבור החודש שנבחר — קודים חדשים, נעלמים, חריגות סכום, ופערי הצלבה.
            ניתן לסמן חריגה כ"טופלה" כדי להסתיר אותה מהרשימה הפעילה.
          </p>

          <div className="flex flex-wrap gap-3 items-center">
            <label className="text-sm text-slate-700">חודש:</label>
            <input
              type="month"
              value={month}
              onChange={(e) => { setMonth(e.target.value); setSearchParams({ month: e.target.value }); }}
              className="px-3 py-1 border border-slate-300 rounded text-sm"
            />
            <label className="text-sm text-slate-700 mr-4 flex items-center gap-2">
              <input
                type="checkbox"
                checked={showAcked}
                onChange={(e) => setShowAcked(e.target.checked)}
              />
              הצג גם חריגות שטופלו
            </label>
          </div>
        </div>

        {/* Filter chips */}
        <div className="flex flex-wrap gap-2">
          {[
            ['all',         `הכל (${counts.all})`,         'bg-slate-200 text-slate-800'],
            ['new',         `${FLAG_META.new.label} (${counts.new})`,                 FLAG_META.new.color],
            ['outlier',     `${FLAG_META.outlier.label} (${counts.outlier})`,         FLAG_META.outlier.color],
            ['disappeared', `${FLAG_META.disappeared.label} (${counts.disappeared})`, FLAG_META.disappeared.color],
            ['tie_out_gap', `${FLAG_META.tie_out_gap.label} (${counts.tie_out_gap})`, FLAG_META.tie_out_gap.color],
          ].map(([key, label, color]) => (
            <button
              key={key}
              onClick={() => setActiveFilter(key)}
              className={`px-3 py-1 rounded-full text-sm font-medium border ${
                activeFilter === key
                  ? 'ring-2 ring-offset-1 ring-slate-700 ' + color
                  : color + ' opacity-70 hover:opacity-100'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* List */}
        {loading && <div className="text-center py-12 text-slate-500">טוען...</div>}
        {error && <div className="bg-rose-100 text-rose-800 p-4 rounded">{error}</div>}
        {!loading && !error && visible.length === 0 && (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <Check className="w-12 h-12 text-emerald-500 mx-auto mb-4" />
            <p className="text-slate-700 text-lg">אין חריגות לחודש זה.</p>
            <p className="text-slate-500 text-sm mt-2">
              {anomalies.length > 0
                ? 'כל החריגות כבר טופלו. סמן "הצג גם חריגות שטופלו" לראות אותן.'
                : 'לא נמצאו חריגות עבור הריצות בחודש הנבחר.'}
            </p>
          </div>
        )}
        {!loading && !error && visible.length > 0 && (
          <div className="space-y-3">
            {visible.map((a) => {
              const meta = FLAG_META[a.flag_type] || { label: a.flag_type, color: 'bg-slate-100 text-slate-800', icon: AlertTriangle };
              const Icon = meta.icon;
              return (
                <div
                  key={a.id}
                  className={`bg-white rounded-lg shadow p-4 flex items-start gap-4 border-r-4 ${
                    a.acknowledged_by_cpa
                      ? 'border-emerald-400 opacity-60'
                      : a.flag_type === 'outlier' || a.flag_type === 'tie_out_gap'
                      ? 'border-amber-400'
                      : 'border-blue-400'
                  }`}
                >
                  <div className="flex-shrink-0">
                    <Icon className="w-6 h-6 text-slate-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${meta.color}`}>
                        {meta.label}
                      </span>
                      <span className="text-xs text-slate-500">קוד {a.topic_code}</span>
                      {a.acknowledged_by_cpa && (
                        <span className="text-xs text-emerald-600 font-medium">✓ טופל</span>
                      )}
                    </div>
                    <p className="text-slate-900 text-sm">{a.narrative || `${a.flag_type} on code ${a.topic_code}`}</p>
                    {(a.previous_value !== null || a.current_value !== null) && (
                      <div className="text-xs text-slate-500 mt-1 flex gap-4">
                        {a.previous_value !== null && (
                          <span>חודש קודם: ₪{Number(a.previous_value).toLocaleString('he-IL', { maximumFractionDigits: 0 })}</span>
                        )}
                        {a.current_value !== null && (
                          <span>חודש נוכחי: ₪{Number(a.current_value).toLocaleString('he-IL', { maximumFractionDigits: 0 })}</span>
                        )}
                        {a.delta_pct !== null && a.delta_pct !== undefined && (
                          <span className={a.delta_pct < 0 ? 'text-rose-600' : 'text-emerald-600'}>
                            {a.delta_pct > 0 ? '+' : ''}{a.delta_pct.toFixed(1)}%
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                  {!a.acknowledged_by_cpa && (
                    <button
                      onClick={() => acknowledge(a.id)}
                      className="flex-shrink-0 px-3 py-1 bg-emerald-600 hover:bg-emerald-700 text-white text-sm rounded font-medium flex items-center gap-1"
                    >
                      <Check className="w-4 h-4" /> טופל
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </PageWrapper>
  );
}
