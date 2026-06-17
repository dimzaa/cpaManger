import React, { useEffect, useState } from 'react';
import { analyticsAPI } from '../../services/api';
import ShekelAmount from './ShekelAmount';
import { ROUNDING_MODES } from '../../utils/formatShekel';

/**
 * CpaInsightsPanel — Bundles the four computed CPA review blocks that the
 * accountant previously calculated by hand:
 *   1. Reconciliation tie-out (Σ lines vs invoice vs breakdown)
 *   2. Top variance drivers waterfall (month vs prev month)
 *   3. Explained-vs-unexplained ₪ delta coverage
 *   4. YTD cumulative per topic
 *
 * Renders as a single stacked block so it fits naturally at the top of the
 * budget detail pages (admin + portal). All currency is rendered through
 * ShekelAmount so the app-wide rounding toggle still applies.
 *
 * Props:
 *   municipalityId : number
 *   month          : 'YYYY-MM'
 *   roundingMode   : ROUNDING_MODES.*
 *   fiscalStartMonth : 1 (Jan) or 9 (Sept, Israeli school year) — default 1
 */
export default function CpaInsightsPanel({
  municipalityId,
  month,
  roundingMode = ROUNDING_MODES.EXACT,
  fiscalStartMonth = 1,
}) {
  const [tieOut, setTieOut] = useState(null);
  const [drivers, setDrivers] = useState(null);
  const [coverage, setCoverage] = useState(null);
  const [ytd, setYtd] = useState(null);
  const [peer, setPeer] = useState(null);
  const [formula, setFormula] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!municipalityId || !month) return;
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [tieRes, drvRes, covRes, ytdRes, peerRes, fmlRes] = await Promise.allSettled([
          analyticsAPI.getTieOut(municipalityId, month),
          analyticsAPI.getVarianceDrivers(municipalityId, month, 5),
          analyticsAPI.getExplainedCoverage(municipalityId, month),
          analyticsAPI.getYtd(municipalityId, month, fiscalStartMonth),
          analyticsAPI.getPeerBenchmark(municipalityId, month),
          analyticsAPI.getFormulaVariance(municipalityId, month),
        ]);
        if (cancelled) return;
        setTieOut(tieRes.status === 'fulfilled' ? tieRes.value.data : null);
        setDrivers(drvRes.status === 'fulfilled' ? drvRes.value.data : null);
        setCoverage(covRes.status === 'fulfilled' ? covRes.value.data : null);
        setYtd(ytdRes.status === 'fulfilled' ? ytdRes.value.data : null);
        setPeer(peerRes.status === 'fulfilled' ? peerRes.value.data : null);
        setFormula(fmlRes.status === 'fulfilled' ? fmlRes.value.data : null);
      } catch (err) {
        if (!cancelled) setError(err?.message || 'שגיאה בטעינת נתוני הבקרה');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [municipalityId, month, fiscalStartMonth]);

  if (!municipalityId || !month) return null;

  if (loading) {
    return (
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-5 bg-slate-200 rounded w-48" />
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-24 bg-slate-100 rounded-xl" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 text-amber-800 font-hebrew text-sm">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-hebrew font-bold text-slate-900">
          בקרת חשבון — חישובים אוטומטיים
        </h2>
        <span className="text-xs text-slate-500 font-hebrew">
          כל הסכומים מחושבים אוטומטית מתוך הקובץ
        </span>
      </div>

      {/* Row of 4 top-level metric cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <TieOutCard tieOut={tieOut} roundingMode={roundingMode} />
        <DeltaCard drivers={drivers} roundingMode={roundingMode} />
        <CoverageCard coverage={coverage} roundingMode={roundingMode} />
        <YtdCard ytd={ytd} roundingMode={roundingMode} />
      </div>

      {/* Second row: projection + FY gap + peer outliers + formula variance */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <ProjectionCard ytd={ytd} roundingMode={roundingMode} />
        <FyGapCard ytd={ytd} roundingMode={roundingMode} />
        <PeerOutlierCard peer={peer} />
        <FormulaCard formula={formula} roundingMode={roundingMode} />
      </div>

      {/* Auto-computed bullets (not prose rewrites — actual numbers) */}
      {ytd?.smart_bullets?.length > 0 && (
        <SmartBullets bullets={ytd.smart_bullets} />
      )}

      {/* Detailed waterfall */}
      {drivers?.drivers?.length > 0 && (
        <VarianceWaterfall drivers={drivers} roundingMode={roundingMode} />
      )}

      {/* Coverage breakdown (naked deltas first) */}
      {coverage?.by_code?.length > 0 && coverage.has_prev_month && (
        <CoverageBreakdown coverage={coverage} roundingMode={roundingMode} />
      )}

      {/* Peer benchmark table */}
      {peer?.has_peer_data && peer.by_code?.length > 0 && (
        <PeerBenchmarkTable peer={peer} roundingMode={roundingMode} />
      )}

      {/* Formula variance table (purple booklet) — hide if every row is "no_formula" */}
      {formula?.by_code?.some((r) => r.flag !== 'no_formula') && (
        <FormulaVarianceTable formula={formula} roundingMode={roundingMode} />
      )}

      {/* YTD table */}
      {ytd?.by_code?.length > 0 && (
        <YtdTable ytd={ytd} roundingMode={roundingMode} />
      )}
    </div>
  );
}

// ───────── small card components ─────────

function TieOutCard({ tieOut, roundingMode }) {
  if (!tieOut) {
    return (
      <StatCard title="בקרת סגירה" variant="neutral" subtitle="אין נתונים" />
    );
  }
  const { is_balanced, severity, breaks } = tieOut;
  const variant = is_balanced
    ? 'success'
    : severity === 'minor'
      ? 'warning'
      : 'danger';
  const label = is_balanced
    ? 'מאוזן ✓'
    : severity === 'minor'
      ? 'פער עיגול'
      : severity === 'material'
        ? 'פער מהותי'
        : 'פער קריטי';
  return (
    <StatCard
      title="בקרת סגירה"
      variant={variant}
      value={label}
      subtitle={
        <span>
          פער מקסימלי:{' '}
          <ShekelAmount amount={breaks.max_abs_break} mode={roundingMode} />
        </span>
      }
    />
  );
}

function DeltaCard({ drivers, roundingMode }) {
  if (!drivers || !drivers.has_prev_month) {
    return <StatCard title="שינוי מול חודש קודם" subtitle="אין חודש קודם" variant="neutral" />;
  }
  const delta = drivers.total_delta;
  const pct = drivers.total_delta_pct;
  const variant = Math.abs(pct || 0) >= 20 ? 'warning' : delta === 0 ? 'neutral' : 'info';
  const sign = delta > 0 ? '+' : delta < 0 ? '−' : '';
  return (
    <StatCard
      title="שינוי מול חודש קודם"
      variant={variant}
      value={
        <>
          {sign}<ShekelAmount amount={Math.abs(delta)} mode={roundingMode} />
        </>
      }
      subtitle={pct !== null ? `${pct > 0 ? '+' : ''}${pct}%` : null}
    />
  );
}

function CoverageCard({ coverage, roundingMode }) {
  if (!coverage || !coverage.has_prev_month) {
    return <StatCard title="כיסוי הסברים" subtitle="לא ניתן לחשב" variant="neutral" />;
  }
  const ratio = coverage.coverage_ratio_pct;
  const variant = ratio >= 80 ? 'success' : ratio >= 50 ? 'warning' : 'danger';
  const staleCount = coverage.stale_count || 0;
  return (
    <StatCard
      title="כיסוי הסברים"
      variant={variant}
      value={`${ratio}%`}
      subtitle={
        <span>
          ללא הסבר: <ShekelAmount amount={coverage.unexplained_delta_abs} mode={roundingMode} />
          {coverage.naked_codes_count > 0 && ` · ${coverage.naked_codes_count} קודים`}
          {staleCount > 0 && ` · ${staleCount} הסבר ישן`}
        </span>
      }
    />
  );
}

function YtdCard({ ytd, roundingMode }) {
  if (!ytd || !ytd.months_covered_count) {
    return <StatCard title="סך מצטבר (YTD)" subtitle="אין נתונים" variant="neutral" />;
  }
  return (
    <StatCard
      title={`סך מצטבר מ-${ytd.start_month_display}`}
      variant="info"
      value={<ShekelAmount amount={ytd.ytd_total} mode={roundingMode} />}
      subtitle={
        <span>
          {ytd.months_covered_count} חודשים · ממוצע{' '}
          <ShekelAmount amount={ytd.avg_per_month} mode={roundingMode} /> לחודש
          {ytd.ytd_retro_share_pct > 0 && ` · רטרו ${ytd.ytd_retro_share_pct}%`}
        </span>
      }
    />
  );
}

function ProjectionCard({ ytd, roundingMode }) {
  if (!ytd || !ytd.projected_annual) {
    return <StatCard title="תחזית שנתית" subtitle="אין נתונים" variant="neutral" />;
  }
  return (
    <StatCard
      title="תחזית שנתית"
      variant="info"
      value={<ShekelAmount amount={ytd.projected_annual} mode={roundingMode} />}
      subtitle={
        <span>
          על בסיס {ytd.months_covered_count} חודשים · נצברו עד כה {ytd.pct_of_projected_annual}%
        </span>
      }
    />
  );
}

function FyGapCard({ ytd, roundingMode }) {
  if (!ytd || ytd.fiscal_year_cumulative_gap === undefined || ytd.fiscal_year_cumulative_gap === null) {
    return <StatCard title="פער מצטבר (מגיע/שולם)" subtitle="אין נתונים" variant="neutral" />;
  }
  const gap = ytd.fiscal_year_cumulative_gap;
  const variant = Math.abs(gap) < 1 ? 'success' : gap > 0 ? 'danger' : 'warning';
  const label = Math.abs(gap) < 1
    ? 'מאוזן ✓'
    : gap > 0
      ? 'חסר בתשלום'
      : 'עודף תשלום';
  return (
    <StatCard
      title="פער מצטבר (מגיע/שולם)"
      variant={variant}
      value={
        <>
          {gap > 0 ? '+' : gap < 0 ? '−' : ''}
          <ShekelAmount amount={Math.abs(gap)} mode={roundingMode} />
        </>
      }
      subtitle={
        <span>
          {label} · מגיע:{' '}
          <ShekelAmount amount={ytd.fiscal_year_due_total} mode={roundingMode} /> / שולם:{' '}
          <ShekelAmount amount={ytd.fiscal_year_paid_total} mode={roundingMode} />
        </span>
      }
    />
  );
}

function PeerOutlierCard({ peer }) {
  if (!peer || !peer.has_peer_data) {
    return <StatCard title="השוואה לעמיתים" subtitle="אין נתוני עמיתים" variant="neutral" />;
  }
  const outliers = peer.outlier_count || 0;
  const variant = outliers === 0 ? 'success' : outliers <= 1 ? 'warning' : 'danger';
  return (
    <StatCard
      title="השוואה לעמיתים"
      variant={variant}
      value={outliers === 0 ? 'בקו הממוצע' : `${outliers} חריגים`}
      subtitle={
        <span>
          מתוך {peer.peer_count} רשויות · סף חריגה ±30% מהחציון
        </span>
      }
    />
  );
}

function FormulaCard({ formula, roundingMode }) {
  if (!formula || formula.expected_total == null || formula.expected_total === 0) {
    return <StatCard title="סטייה מנוסחה (הספר הסגול)" subtitle="אין נתוני ילדים" variant="neutral" />;
  }
  const pct = formula.variance_pct;
  const variant = pct == null
    ? 'neutral'
    : Math.abs(pct) <= 5
      ? 'success'
      : Math.abs(pct) <= 15
        ? 'warning'
        : 'danger';
  return (
    <StatCard
      title="סטייה מנוסחה (הספר הסגול)"
      variant={variant}
      value={pct != null ? `${pct > 0 ? '+' : ''}${pct}%` : '—'}
      subtitle={
        <span>
          בפועל:{' '}
          <ShekelAmount amount={formula.actual_regular_total} mode={roundingMode} /> / נוסחה:{' '}
          <ShekelAmount amount={formula.expected_total} mode={roundingMode} />
          {formula.material_count > 0 && ` · ${formula.material_count} נושאים חריגים`}
        </span>
      }
    />
  );
}

function SmartBullets({ bullets }) {
  return (
    <div className="bg-indigo-50 border border-indigo-200 rounded-2xl p-5">
      <h3 className="font-hebrew font-bold text-indigo-900 mb-2">
        עובדות מחושבות (לא מנוסח — מספרים)
      </h3>
      <ul className="space-y-1.5 list-disc pr-6 rtl:mr-0 rtl:pl-0">
        {bullets.map((b, i) => (
          <li key={i} className="font-hebrew text-sm text-indigo-900">
            {b}
          </li>
        ))}
      </ul>
    </div>
  );
}

function StatCard({ title, value, subtitle, variant = 'neutral' }) {
  const variants = {
    success: 'bg-emerald-50 border-emerald-200 text-emerald-900',
    warning: 'bg-amber-50 border-amber-200 text-amber-900',
    danger: 'bg-red-50 border-red-200 text-red-900',
    info: 'bg-indigo-50 border-indigo-200 text-indigo-900',
    neutral: 'bg-slate-50 border-slate-200 text-slate-700',
  };
  return (
    <div className={`rounded-xl border p-4 ${variants[variant] || variants.neutral}`}>
      <p className="text-xs font-hebrew opacity-80 mb-1">{title}</p>
      <p className="font-hebrew font-bold text-xl leading-tight">
        {value ?? '—'}
      </p>
      {subtitle && (
        <p className="text-xs font-hebrew opacity-75 mt-1">{subtitle}</p>
      )}
    </div>
  );
}

// ───────── detail panels ─────────

function VarianceWaterfall({ drivers, roundingMode }) {
  const maxAbs = Math.max(
    ...drivers.drivers.map((d) => Math.abs(d.delta_abs)),
    1,
  );
  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
      <h3 className="font-hebrew font-bold text-slate-900 mb-1">
        רכיבי השינוי המובילים
      </h3>
      <p className="text-xs text-slate-500 font-hebrew mb-4">
        ממוינים לפי השפעה ב-₪ מול {drivers.previous_month_display}
      </p>
      <div className="space-y-2">
        {drivers.drivers.map((d) => {
          const pctWidth = Math.round((Math.abs(d.delta_abs) / maxAbs) * 100);
          const barColor = d.direction === 'up' ? 'bg-emerald-500' : 'bg-red-500';
          const signLabel = d.direction === 'up' ? '+' : '−';
          return (
            <div key={d.topic_code} className="flex items-center gap-3">
              <div className="w-40 shrink-0 font-hebrew text-sm text-slate-700 truncate">
                {d.topic_name}{' '}
                <span className="text-slate-400 text-xs">({d.topic_code})</span>
              </div>
              <div className="flex-1 h-6 bg-slate-100 rounded-md overflow-hidden">
                <div
                  className={`h-full ${barColor} transition-all`}
                  style={{ width: `${pctWidth}%` }}
                />
              </div>
              <div className="w-32 shrink-0 text-left font-mono text-sm tabular-nums">
                <span className={d.direction === 'up' ? 'text-emerald-700' : 'text-red-700'}>
                  {signLabel}<ShekelAmount amount={Math.abs(d.delta_abs)} mode={roundingMode} />
                </span>
              </div>
              <div className="w-16 shrink-0 text-left text-xs text-slate-500">
                {d.share_of_total_change_pct !== null
                  ? `${d.share_of_total_change_pct}%`
                  : '—'}
              </div>
            </div>
          );
        })}
      </div>
      {drivers.other_drivers_delta !== 0 && (
        <p className="text-xs text-slate-500 font-hebrew mt-3">
          רכיבים נוספים יחד:{' '}
          <ShekelAmount amount={drivers.other_drivers_delta} mode={roundingMode} />
        </p>
      )}
    </div>
  );
}

function CoverageBreakdown({ coverage, roundingMode }) {
  const naked = coverage.by_code.filter((r) => r.is_naked);
  const stale = coverage.by_code.filter((r) => r.is_potentially_stale);
  if (naked.length === 0 && stale.length === 0) {
    return null;
  }
  return (
    <div className="space-y-3">
      {naked.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-5">
          <h3 className="font-hebrew font-bold text-red-900 mb-1">
            שינויים ללא הסבר מאושר ({naked.length})
          </h3>
          <p className="text-xs text-red-800 font-hebrew mb-3">
            מחייב בדיקה — לסכומים אלו אין הסבר מאושר לעומת {coverage.previous_month_display}
          </p>
          <div className="space-y-1.5">
            {naked.slice(0, 8).map((r) => (
              <div
                key={r.topic_code}
                className="flex items-center justify-between bg-white rounded-md px-3 py-2 text-sm"
              >
                <span className="font-hebrew text-slate-800">
                  {r.topic_name}{' '}
                  <span className="text-slate-400 text-xs">({r.topic_code})</span>
                </span>
                <span className="font-mono tabular-nums text-red-700">
                  {r.delta_abs > 0 ? '+' : '−'}
                  <ShekelAmount amount={Math.abs(r.delta_abs)} mode={roundingMode} />
                  {r.delta_pct !== null && (
                    <span className="ml-2 text-xs text-red-500">
                      ({r.delta_pct > 0 ? '+' : ''}{r.delta_pct}%)
                    </span>
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
      {stale.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5">
          <h3 className="font-hebrew font-bold text-amber-900 mb-1">
            הסברים שעלולים להיות ישנים ({stale.length})
          </h3>
          <p className="text-xs text-amber-800 font-hebrew mb-3">
            ההסבר נחתם לפני יותר מ-14 יום והסכום זז ב-10% ומעלה — כדאי לעדכן
          </p>
          <div className="space-y-1.5">
            {stale.slice(0, 8).map((r) => (
              <div
                key={r.topic_code}
                className="flex items-center justify-between bg-white rounded-md px-3 py-2 text-sm"
              >
                <span className="font-hebrew text-amber-900 flex items-center gap-2">
                  <span className="inline-block px-2 py-0.5 bg-amber-200 text-amber-900 text-xs rounded-full font-bold">
                    ישן
                  </span>
                  {r.topic_name}{' '}
                  <span className="text-amber-600 text-xs">({r.topic_code})</span>
                </span>
                <span className="font-mono tabular-nums text-amber-800">
                  {r.delta_abs > 0 ? '+' : '−'}
                  <ShekelAmount amount={Math.abs(r.delta_abs)} mode={roundingMode} />
                  {r.delta_pct !== null && (
                    <span className="ml-2 text-xs">
                      ({r.delta_pct > 0 ? '+' : ''}{r.delta_pct}%)
                    </span>
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function PeerBenchmarkTable({ peer, roundingMode }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
      <h3 className="font-hebrew font-bold text-slate-900 mb-1">
        השוואה לעמיתים (חציון {peer.peer_count} רשויות)
      </h3>
      <p className="text-xs text-slate-500 font-hebrew mb-3">
        סטייה מחציון העמיתים לאותו חודש — חריגה של מעל ±30% מסומנת
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-slate-500 font-hebrew border-b border-slate-200">
              <th className="text-right py-2 font-medium">נושא</th>
              <th className="text-left py-2 font-medium">הרשות</th>
              <th className="text-left py-2 font-medium">חציון</th>
              <th className="text-left py-2 font-medium">ממוצע</th>
              <th className="text-left py-2 font-medium">טווח</th>
              <th className="text-left py-2 font-medium">סטייה</th>
            </tr>
          </thead>
          <tbody>
            {peer.by_code.map((r) => {
              const flagColor = r.flag === 'above_peers'
                ? 'text-red-700'
                : r.flag === 'below_peers'
                  ? 'text-amber-700'
                  : 'text-slate-600';
              return (
                <tr key={r.topic_code} className="border-b border-slate-100 last:border-0">
                  <td className="py-2 font-hebrew text-slate-800">
                    {r.topic_name}{' '}
                    <span className="text-slate-400 text-xs">({r.topic_code})</span>
                  </td>
                  <td className="py-2 text-left font-mono tabular-nums font-semibold">
                    <ShekelAmount amount={r.my_amount} mode={roundingMode} />
                  </td>
                  <td className="py-2 text-left font-mono tabular-nums text-slate-600">
                    <ShekelAmount amount={r.peer_median} mode={roundingMode} />
                  </td>
                  <td className="py-2 text-left font-mono tabular-nums text-slate-600">
                    <ShekelAmount amount={r.peer_avg} mode={roundingMode} />
                  </td>
                  <td className="py-2 text-left font-mono tabular-nums text-xs text-slate-500">
                    <ShekelAmount amount={r.peer_min} mode={roundingMode} />
                    {' – '}
                    <ShekelAmount amount={r.peer_max} mode={roundingMode} />
                  </td>
                  <td className={`py-2 text-left font-mono tabular-nums ${flagColor}`}>
                    {r.deviation_pct !== null
                      ? `${r.deviation_pct > 0 ? '+' : ''}${r.deviation_pct}%`
                      : '—'}
                    {r.flag === 'above_peers' && (
                      <span className="mr-1 text-xs px-1.5 py-0.5 bg-red-100 text-red-700 rounded">גבוה</span>
                    )}
                    {r.flag === 'below_peers' && (
                      <span className="mr-1 text-xs px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded">נמוך</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function FormulaVarianceTable({ formula, roundingMode }) {
  const overallPct = formula.variance_pct;
  const overallColor = overallPct == null
    ? 'text-slate-700'
    : Math.abs(overallPct) <= 5
      ? 'text-emerald-700'
      : Math.abs(overallPct) <= 15
        ? 'text-amber-700'
        : 'text-red-700';
  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
      <h3 className="font-hebrew font-bold text-slate-900 mb-1">
        סטייה מנוסחת הספר הסגול
      </h3>
      <p className="text-xs text-slate-500 font-hebrew mb-3">
        בפועל מול מה שהנוסחה {`(מספר ילדים × תעריף לדלי)`} אומרת שצריך להיות.
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-slate-500 font-hebrew border-b border-slate-200">
              <th className="text-right py-2 font-medium">נושא</th>
              <th className="text-right py-2 font-medium">חישוב</th>
              <th className="text-left py-2 font-medium">צפוי</th>
              <th className="text-left py-2 font-medium">בפועל (רגיל)</th>
              <th className="text-left py-2 font-medium">פער</th>
              <th className="text-left py-2 font-medium">% סטייה</th>
            </tr>
          </thead>
          <tbody>
            {formula.by_code
              .filter((r) => r.flag !== 'no_formula')
              .map((r) => {
              const flagColor = r.flag === 'critical'
                ? 'text-red-700'
                : r.flag === 'material'
                  ? 'text-amber-700'
                  : r.flag === 'in_line'
                    ? 'text-emerald-700'
                    : 'text-slate-500';
              return (
                <tr key={r.topic_code} className="border-b border-slate-100 last:border-0">
                  <td className="py-2 font-hebrew text-slate-800">
                    {r.topic_name}{' '}
                    <span className="text-slate-400 text-xs">({r.topic_code})</span>
                    {r.flag === 'no_children_data' && (
                      <span className="mr-2 text-xs px-1.5 py-0.5 bg-amber-50 text-amber-700 rounded font-hebrew">
                        חסר מספר ילדים
                      </span>
                    )}
                  </td>
                  <td className="py-2 text-right font-mono text-xs text-slate-500">
                    {r.formula || '—'}
                  </td>
                  <td className="py-2 text-left font-mono tabular-nums text-slate-600">
                    {r.expected_amount != null
                      ? <ShekelAmount amount={r.expected_amount} mode={roundingMode} />
                      : '—'}
                  </td>
                  <td className="py-2 text-left font-mono tabular-nums font-semibold">
                    <ShekelAmount amount={r.actual_regular} mode={roundingMode} />
                  </td>
                  <td className={`py-2 text-left font-mono tabular-nums ${flagColor}`}>
                    {r.variance_abs != null
                      ? (
                        <>
                          {r.variance_abs > 0 ? '+' : r.variance_abs < 0 ? '−' : ''}
                          <ShekelAmount amount={Math.abs(r.variance_abs)} mode={roundingMode} />
                        </>
                      )
                      : '—'}
                  </td>
                  <td className={`py-2 text-left font-mono tabular-nums ${flagColor}`}>
                    {r.variance_pct != null
                      ? `${r.variance_pct > 0 ? '+' : ''}${r.variance_pct}%`
                      : '—'}
                  </td>
                </tr>
              );
            })}
            <tr className="font-bold bg-slate-50">
              <td colSpan={2} className="py-2 font-hebrew text-slate-900">
                סך הכל (נושאים עם נוסחה)
              </td>
              <td className="py-2 text-left font-mono tabular-nums">
                <ShekelAmount amount={formula.expected_total} mode={roundingMode} />
              </td>
              <td className="py-2 text-left font-mono tabular-nums">
                <ShekelAmount amount={formula.actual_regular_total} mode={roundingMode} />
              </td>
              <td className={`py-2 text-left font-mono tabular-nums ${overallColor}`}>
                {formula.variance_abs > 0 ? '+' : formula.variance_abs < 0 ? '−' : ''}
                <ShekelAmount amount={Math.abs(formula.variance_abs)} mode={roundingMode} />
              </td>
              <td className={`py-2 text-left font-mono tabular-nums ${overallColor}`}>
                {overallPct != null
                  ? `${overallPct > 0 ? '+' : ''}${overallPct}%`
                  : '—'}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

function YtdTable({ ytd, roundingMode }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
      <h3 className="font-hebrew font-bold text-slate-900 mb-1">
        פירוט מצטבר לפי קוד
      </h3>
      <p className="text-xs text-slate-500 font-hebrew mb-3">
        מ-{ytd.start_month_display} עד {ytd.end_month_display} ·{' '}
        {ytd.months_covered_count} חודשים עם נתונים
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-slate-500 font-hebrew border-b border-slate-200">
              <th className="text-right py-2 font-medium">קוד</th>
              <th className="text-right py-2 font-medium">נושא</th>
              <th className="text-left py-2 font-medium">סך מצטבר</th>
              <th className="text-left py-2 font-medium">רגיל</th>
              <th className="text-left py-2 font-medium">רטרו</th>
              <th className="text-left py-2 font-medium">ממוצע/חודש</th>
              <th className="text-left py-2 font-medium">% רטרו</th>
            </tr>
          </thead>
          <tbody>
            {ytd.by_code.map((r) => (
              <tr key={r.topic_code} className="border-b border-slate-100 last:border-0">
                <td className="py-2 text-slate-500 font-mono text-xs">{r.topic_code}</td>
                <td className="py-2 font-hebrew text-slate-800">{r.topic_name}</td>
                <td className="py-2 text-left font-mono tabular-nums font-semibold">
                  <ShekelAmount amount={r.ytd_total} mode={roundingMode} />
                </td>
                <td className="py-2 text-left font-mono tabular-nums text-slate-600">
                  <ShekelAmount amount={r.ytd_regular} mode={roundingMode} />
                </td>
                <td className="py-2 text-left font-mono tabular-nums text-amber-700">
                  <ShekelAmount amount={r.ytd_retro} mode={roundingMode} />
                </td>
                <td className="py-2 text-left font-mono tabular-nums text-slate-600">
                  <ShekelAmount amount={r.avg_per_month} mode={roundingMode} />
                </td>
                <td className="py-2 text-left text-xs text-slate-500">
                  {r.retro_share_pct}%
                </td>
              </tr>
            ))}
            <tr className="font-bold bg-slate-50">
              <td colSpan={2} className="py-2 font-hebrew text-slate-900">
                סך הכל
              </td>
              <td className="py-2 text-left font-mono tabular-nums">
                <ShekelAmount amount={ytd.ytd_total} mode={roundingMode} />
              </td>
              <td className="py-2 text-left font-mono tabular-nums">
                <ShekelAmount amount={ytd.ytd_regular} mode={roundingMode} />
              </td>
              <td className="py-2 text-left font-mono tabular-nums">
                <ShekelAmount amount={ytd.ytd_retro} mode={roundingMode} />
              </td>
              <td className="py-2 text-left font-mono tabular-nums">
                <ShekelAmount amount={ytd.avg_per_month} mode={roundingMode} />
              </td>
              <td className="py-2 text-left text-xs">
                {ytd.ytd_retro_share_pct}%
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
