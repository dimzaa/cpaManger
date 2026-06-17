import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import PageWrapper from '../components/layout/PageWrapper';
import { exportAPI, municipalityAPI, runsAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { getCurrentMonth, getLast12Months } from '../utils/format';
import { formatShekel as formatShekelByMode, getRoundingDisclosureText, resolveConcreteMode } from '../utils/formatShekel';
import { getBudgetStatus, getBudgetStatusBadge } from '../utils/budgetStatus';
import { useRoundingMode } from '../utils/roundingMode';
import RoundingModeToggle from '../components/common/RoundingModeToggle';
import RoundingDisclosureBanner from '../components/common/RoundingDisclosureBanner';
import ShekelAmount from '../components/common/ShekelAmount';

export default function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [municipalities, setMunicipalities] = useState([]);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [exportLoading, setExportLoading] = useState(false);
  const [error, setError] = useState(null);
  const [defaultMonth, setDefaultMonth] = useState('');
  const [roundingMode, setRoundingMode] = useRoundingMode();
  const months = getLast12Months();
  const monthFromQuery = searchParams.get('month');
  const reviewStatusFromQuery = searchParams.get('review_status') || 'all';
  const selectedMonth = monthFromQuery || defaultMonth;

  // Keep URL month as the single source of truth.
  useEffect(() => {
    if (monthFromQuery) {
      return;
    }

    let cancelled = false;

    const resolveDefaultMonth = async () => {
      try {
        const monthsRes = await runsAPI.getAvailableMonths();
        const latestMonth = Array.isArray(monthsRes.data) ? monthsRes.data[0] : null;
        const fallbackMonth = latestMonth || getCurrentMonth();
        if (!cancelled) {
          setDefaultMonth(fallbackMonth);
          setSearchParams({ month: fallbackMonth }, { replace: true });
        }
      } catch {
        const fallbackMonth = getCurrentMonth();
        if (!cancelled) {
          setDefaultMonth(fallbackMonth);
          setSearchParams({ month: fallbackMonth }, { replace: true });
        }
      }
    };

    resolveDefaultMonth();

    return () => {
      cancelled = true;
    };
  }, [monthFromQuery, setSearchParams]);

  useEffect(() => {
    if (!selectedMonth) {
      return;
    }

    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);
        const [mRes, rRes] = await Promise.all([
          municipalityAPI.getAll(),
          runsAPI.getAll({
            month: selectedMonth,
            ...(reviewStatusFromQuery !== 'all' ? { review_status: reviewStatusFromQuery } : {}),
          }),
        ]);
        setMunicipalities(mRes.data || []);
        setRuns(rRes.data || []);
      } catch (err) {
        setError('שגיאה בטעינת הנתונים');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [selectedMonth, reviewStatusFromQuery]);

  // Defensive client-side filter in case backend returns extra months.
  const runsForSelectedMonth = useMemo(() => {
    return (runs || []).filter((run) => run?.month === selectedMonth);
  }, [runs, selectedMonth]);

  const runsByMunicipality = useMemo(() => {
    return new Map(runsForSelectedMonth.map((run) => [run.municipality_id, run]));
  }, [runsForSelectedMonth]);

  // Calculate summary stats for selected month only.
  const stats = {
    total_municipalities: municipalities.length,
    total_paid: runsForSelectedMonth.reduce((sum, r) => sum + Number(r.invoice_total || 0), 0),
    open_balances: runsForSelectedMonth.filter((r) => (Number(r.breakdown_total || 0) - Number(r.invoice_total || 0)) > 1).length,
    retro_payments: runsForSelectedMonth
      .filter((r) => r.has_retro)
      .reduce((sum, r) => sum + Number(r.retro_total || 0), 0),
  };

  const pageAmounts = [
    stats.total_paid,
    stats.retro_payments,
    ...runsForSelectedMonth.flatMap((r) => [r.breakdown_total, r.invoice_total, r.difference, r.retro_total]),
  ];
  const concreteRoundingMode = resolveConcreteMode(roundingMode, pageAmounts);
  const disclosureText = getRoundingDisclosureText(concreteRoundingMode);

  const handleMonthChange = (newMonth) => {
    const next = { month: newMonth };
    if (reviewStatusFromQuery !== 'all') {
      next.review_status = reviewStatusFromQuery;
    }
    setSearchParams(next);
  };

  const handleReviewStatusChange = (newReviewStatus) => {
    const next = { month: selectedMonth };
    if (newReviewStatus !== 'all') {
      next.review_status = newReviewStatus;
    }
    setSearchParams(next);
  };

  const handleExportExcel = async () => {
    try {
      setExportLoading(true);
      const response = await exportAPI.exportMonthlySummaryExcel(selectedMonth);
      const blob = new Blob([
        response.data,
      ], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `summary_${selectedMonth}.xlsx`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('שגיאה בהורדת קובץ האקסל');
    } finally {
      setExportLoading(false);
    }
  };

  return (
    <PageWrapper title="לוח בקרה">
      <div className="space-y-8">
        {/* Page Title */}
        <div className="mb-8">
          <h1 className="text-4xl font-hebrew font-bold text-slate-900 mb-2">לוח בקרה</h1>
          <p className="text-slate-600">סיכום תקציבי העיריות וניהול זרימת התקבול</p>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-100 shadow-sm flex items-center justify-end">
          <RoundingModeToggle mode={roundingMode} onChange={setRoundingMode} />
        </div>

        <RoundingDisclosureBanner text={disclosureText} />

        {/* Month Selector */}
        <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-lg">
          <h2 className="text-lg font-hebrew font-semibold text-slate-900 mb-4">בחר חודש</h2>
          <div className="flex flex-col md:flex-row md:items-center gap-3">
            <select
              value={selectedMonth}
              onChange={(e) => handleMonthChange(e.target.value)}
              className="w-full md:w-64 border border-slate-300 rounded-lg px-4 py-3 bg-white text-slate-900 font-medium focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition"
            >
              {months.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>

            <select
              value={reviewStatusFromQuery}
              onChange={(e) => handleReviewStatusChange(e.target.value)}
              className="w-full md:w-56 border border-slate-300 rounded-lg px-4 py-3 bg-white text-slate-900 font-hebrew"
            >
              <option value="all">כל הסטטוסים</option>
              <option value="pending">ממתין לבדיקה</option>
              <option value="in_review">בבדיקה</option>
              <option value="reviewed">נבדק</option>
              <option value="flagged">דורש תשומת לב</option>
            </select>

            {user?.is_admin && (
              <button
                onClick={handleExportExcel}
                disabled={exportLoading}
                className="inline-flex items-center justify-center gap-2 bg-slate-900 hover:bg-slate-800 disabled:bg-slate-500 text-white font-hebrew font-semibold px-5 py-3 rounded-lg transition"
              >
                {exportLoading && (
                  <span className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                )}
                <span>הורד Excel</span>
              </button>
            )}
          </div>
        </div>

        {/* Summary Stats - Filtered by Selected Month */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <SummaryStat label="עיריות" value={stats.total_municipalities} />
          <SummaryStat label="סכום ששולם" value={<ShekelAmount amount={stats.total_paid} mode={concreteRoundingMode} />} color="success" />
          <SummaryStat label="יתרות פתוחות" value={stats.open_balances} color="info" />
          <SummaryStat label="תשלומי רטרו" value={<ShekelAmount amount={stats.retro_payments} mode={concreteRoundingMode} />} color="warning" />
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-2xl shadow-md">
            {error}
          </div>
        )}

        {/* Admin Tools Section */}
        {user?.is_admin && (
          <div className="bg-gradient-to-r from-purple-50 to-indigo-50 rounded-2xl p-8 shadow-lg border border-purple-200">
            <h2 className="text-2xl font-hebrew font-bold text-purple-900 mb-6">🛠️ כלים לניהול</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Employees */}
              <button
                onClick={() => navigate('/admin/employees')}
                className="bg-white rounded-xl p-6 border border-purple-200 hover:shadow-lg hover:border-purple-400 transition text-right"
              >
                <p className="text-3xl mb-2">👥</p>
                <h3 className="font-hebrew font-bold text-lg text-slate-900 mb-1">ניהול עובדים</h3>
                <p className="text-sm text-slate-600 font-hebrew">יצירה וניהול של משתמשי עובדים השולחים הצעות</p>
              </button>

              {/* Presets */}
              <button
                onClick={() => navigate('/admin/presets')}
                className="bg-white rounded-xl p-6 border border-indigo-200 hover:shadow-lg hover:border-indigo-400 transition text-right"
              >
                <p className="text-3xl mb-2">📋</p>
                <h3 className="font-hebrew font-bold text-lg text-slate-900 mb-1">הסברים מוכנים</h3>
                <p className="text-sm text-slate-600 font-hebrew">διαχείριση של תבניות הסברים לשימוש עובדים</p>
              </button>

              {/* Approvals */}
              <button
                onClick={() => navigate('/admin/approvals')}
                className="bg-white rounded-xl p-6 border border-pink-200 hover:shadow-lg hover:border-pink-400 transition text-right"
              >
                <p className="text-3xl mb-2">🔍</p>
                <h3 className="font-hebrew font-bold text-lg text-slate-900 mb-1">בדיקה ואישור</h3>
                <p className="text-sm text-slate-600 font-hebrew">סקירה והאישור של הסברים שהוצעו על ידי עובדים</p>
              </button>

              {/* Reports */}
              <button
                onClick={() => navigate('/admin/reports')}
                className="bg-white rounded-xl p-6 border border-cyan-200 hover:shadow-lg hover:border-cyan-400 transition text-right"
              >
                <p className="text-3xl mb-2">📄</p>
                <h3 className="font-hebrew font-bold text-lg text-slate-900 mb-1">דוחות ומסמכים</h3>
                <p className="text-sm text-slate-600 font-hebrew">ארכיון דוחות PDF, יצירה, מיתוג ותבניות</p>
              </button>
            </div>
          </div>
        )}

        {/* Municipality Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {loading
            ? (municipalities.length > 0 ? municipalities : Array.from({ length: 6 })).map((mun, index) => (
              <MunicipalityCardSkeleton key={mun?.id || `skeleton-${index}`} />
            ))
            : municipalities.map((mun) => {
            const runForMonth = runsByMunicipality.get(mun.id);
            const runStatus = runForMonth
              ? getBudgetStatus({
                  dueAmount: runForMonth.breakdown_total,
                  paidAmount: runForMonth.invoice_total,
                  month: selectedMonth,
                })
              : null;
            const statusBadge = runStatus ? getBudgetStatusBadge(runStatus.key) : null;

            return (
              <div
                key={mun.id}
                onClick={() => navigate(`/municipality/${mun.id}?month=${selectedMonth}`)}
                className="bg-white p-6 rounded-2xl border border-slate-100 cursor-pointer hover:shadow-2xl transition-shadow duration-200"
              >
                <div className="mb-4">
                  <h3 className="font-hebrew font-bold text-lg text-slate-900">{mun.name}</h3>
                  <p className="text-sm text-slate-500 font-medium">קוד: {mun.code}</p>
                </div>

                {runForMonth ? (
                  <div className="space-y-3 text-sm">
                    <div className="flex justify-between pb-3 border-b border-slate-100">
                      <span className="text-slate-600">מגיע:</span>
                      <span className="font-semibold text-slate-900"><ShekelAmount amount={runForMonth.breakdown_total} mode={concreteRoundingMode} /></span>
                    </div>
                    <div className="flex justify-between pb-3 border-b border-slate-100">
                      <span className="text-slate-600">שולם:</span>
                      <span className="font-semibold text-slate-900"><ShekelAmount amount={runForMonth.invoice_total} mode={concreteRoundingMode} /></span>
                    </div>
                    <div className="flex justify-between pb-3 border-b border-slate-100">
                      <span className="text-slate-600">הפרש:</span>
                      <span className={`font-semibold ${
                        runStatus?.key === 'balanced'
                          ? 'text-green-600'
                          : runStatus?.key === 'current_gap'
                            ? 'text-indigo-700'
                            : runStatus?.key === 'awaiting_data'
                              ? 'text-slate-500'
                              : 'text-red-600'
                      }`}>
                        <ShekelAmount amount={runForMonth.difference} mode={concreteRoundingMode} />
                      </span>
                    </div>
                    <div className="flex gap-2 mt-4 pt-3">
                      {statusBadge && (
                        <span className={`inline-block px-3 py-1 text-xs font-medium rounded-lg border ${statusBadge.className}`}>
                          {statusBadge.icon} {statusBadge.text}
                        </span>
                      )}
                      {runForMonth.has_retro && (
                        <span className="inline-block px-3 py-1 bg-amber-50 text-amber-700 text-xs font-medium rounded-lg border border-amber-200">
                          💰 רטרו
                        </span>
                      )}
                    </div>
                  </div>
                ) : (
                  <p className="text-slate-500 text-sm font-medium">לא הועלה קובץ לחודש זה</p>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </PageWrapper>
  );
}

function MunicipalityCardSkeleton() {
  return (
    <div className="bg-white p-6 rounded-2xl border border-slate-100 animate-pulse">
      <div className="mb-4 space-y-2">
        <div className="h-6 bg-slate-200 rounded w-2/3"></div>
        <div className="h-4 bg-slate-200 rounded w-1/3"></div>
      </div>

      <div className="space-y-3 text-sm">
        <div className="flex justify-between pb-3 border-b border-slate-100">
          <div className="h-4 bg-slate-200 rounded w-16"></div>
          <div className="h-4 bg-slate-200 rounded w-20"></div>
        </div>
        <div className="flex justify-between pb-3 border-b border-slate-100">
          <div className="h-4 bg-slate-200 rounded w-16"></div>
          <div className="h-4 bg-slate-200 rounded w-20"></div>
        </div>
        <div className="flex justify-between pb-3 border-b border-slate-100">
          <div className="h-4 bg-slate-200 rounded w-16"></div>
          <div className="h-4 bg-slate-200 rounded w-20"></div>
        </div>
        <div className="flex gap-2 mt-4 pt-3">
          <div className="h-6 bg-slate-200 rounded-lg w-20"></div>
          <div className="h-6 bg-slate-200 rounded-lg w-16"></div>
        </div>
      </div>
    </div>
  );
}

function SummaryStat({ label, value, color }) {
  let bgClass = 'bg-blue-50';
  let textClass = 'text-blue-700';
  let borderClass = 'border-blue-200';

  if (color === 'danger') {
    bgClass = 'bg-red-50';
    textClass = 'text-red-700';
    borderClass = 'border-red-200';
  } else if (color === 'warning') {
    bgClass = 'bg-amber-50';
    textClass = 'text-amber-700';
    borderClass = 'border-amber-200';
  } else if (color === 'success') {
    bgClass = 'bg-green-50';
    textClass = 'text-green-700';
    borderClass = 'border-green-200';
  } else if (color === 'info') {
    bgClass = 'bg-indigo-50';
    textClass = 'text-indigo-700';
    borderClass = 'border-indigo-200';
  }

  return (
    <div className={`${bgClass} ${borderClass} border p-6 rounded-2xl shadow-lg`}>
      <p className="text-sm text-slate-600 mb-3 font-medium">{label}</p>
      <p className={`font-hebrew font-bold text-3xl ${textClass} tracking-tight`}>{value}</p>
    </div>
  );
}
