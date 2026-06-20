import React, { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import PageWrapper from '../components/layout/PageWrapper';
import { budgetAPI, reportsAPI } from '../services/api';
import { formatHebrewDate, formatShekel, getCurrentMonth } from '../utils/format';
import { getBudgetStatus, getBudgetStatusBadge } from '../utils/budgetStatus';

export default function MunicipalityPage() {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [budget, setBudget] = useState(null);
  const [historyMonths, setHistoryMonths] = useState({});
  const [loading, setLoading] = useState(true);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [error, setError] = useState(null);

  const selectedMonth = useMemo(() => {
    return searchParams.get('month') || getCurrentMonth();
  }, [location.search]);

  const hasMonthInQuery = useMemo(
    () => searchParams.has('month'),
    [location.search]
  );

  useEffect(() => {
    loadData();
  }, [selectedMonth, id]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      try {
        const [budgetRes, historyRes] = await Promise.all([
          budgetAPI.getBudgetMonth(id, selectedMonth),
          budgetAPI.getBudgetHistory(id, 6),
        ]);

        setBudget(budgetRes.data);
        setHistoryMonths(historyRes?.data?.months || {});
      } catch (err) {
        if (err?.response?.status === 404 && !hasMonthInQuery) {
          try {
            const historyRes = await budgetAPI.getBudgetHistory(id, 12);
            const availableMonths = Object.keys(historyRes?.data?.months || {}).sort().reverse();
            const fallbackMonth = availableMonths[0];

            if (fallbackMonth) {
              const nextParams = new URLSearchParams(searchParams);
              nextParams.set('month', fallbackMonth);
              setSearchParams(nextParams, { replace: true });
              return;
            }

            setError('אין נתוני תקציב זמינים כרגע');
          } catch {
            setError('אין נתוני תקציב זמינים כרגע');
          }
        } else if (err?.response?.status === 404) {
          setError('אין נתונים לחודש שנבחר');
        } else {
          setError('שגיאה בטעינת נתוני התקציב');
        }

        setBudget(null);
        setHistoryMonths({});
      }
    } finally {
      setLoading(false);
    }
  };

  const currentLines = budget?.budget_lines || [];

  // Prefer backend-computed retro splits (they're derived from the same filtered
  // line set the backend considers "real"). Fall back to a client-side sum
  // for older API responses without these fields.
  const retroPositive = budget?.retro_positive != null
    ? Number(budget.retro_positive)
    : currentLines
        .filter((line) => line.is_retro && Number(line.amount || 0) > 0)
        .reduce((sum, line) => sum + Number(line.amount || 0), 0);

  const retroNegative = budget?.retro_negative != null
    ? Number(budget.retro_negative)
    : currentLines
        .filter((line) => line.is_retro && Number(line.amount || 0) < 0)
        .reduce((sum, line) => sum + Number(line.amount || 0), 0);

  const linesSumRegular = budget?.lines_sum_regular != null
    ? Number(budget.lines_sum_regular)
    : currentLines
        .filter((line) => !line.is_retro)
        .reduce((sum, line) => sum + Number(line.amount || 0), 0);

  // breakdown_mismatch = the stored run.breakdown_total doesn't match the
  // actual sum of the ingested budget lines. When that happens we trust the
  // computed line sum (lines_sum) over the stored value.
  const breakdownMismatch = Boolean(budget?.breakdown_mismatch);
  const linesSum = budget?.lines_sum != null
    ? Number(budget.lines_sum)
    : Number(budget?.breakdown_total || 0);
  const storedBreakdown = Number(budget?.breakdown_total || 0);
  const dueAmount = breakdownMismatch ? linesSum : storedBreakdown;
  const paidAmount = Number(budget?.invoice_total || 0);
  const gapAmount = dueAmount - paidAmount;
  const status = getBudgetStatus({
    dueAmount,
    paidAmount,
    month: selectedMonth,
  });
  const statusBadge = getBudgetStatusBadge(status.key);

  const groupedRows = useMemo(() => {
    const formatPeriodMonth = (period) => {
      const value = String(period || '').trim();
      if (!value) return '';
      if (/^\d{4}-\d{2}$/.test(value)) {
        return `${value.slice(5, 7)}/${value.slice(0, 4)}`;
      }
      return value;
    };

    const map = new Map();
    for (const line of currentLines) {
      // Belt-and-suspenders: suppress phantom rows that are exactly code 0 with zero amount.
      if (String(line.topic_code || '') === '0' && Number(line.amount || 0) === 0) {
        continue;
      }
      const code = String(line.topic_code || '');
      if (!map.has(code)) {
        map.set(code, {
          code,
          topic: line.budget_topic || '',
          amount: 0,
          periods: new Set(),
          hasRetro: false,
        });
      }
      const row = map.get(code);
      row.amount += Number(line.amount || 0);
      row.periods.add(line.period_month || '');
      if (line.is_retro) row.hasRetro = true;
    }

    const parseCode = (code) => {
      const n = Number(code);
      return Number.isFinite(n) ? n : Number.MAX_SAFE_INTEGER;
    };

    return Array.from(map.values())
      .sort((a, b) => {
        const na = parseCode(a.code);
        const nb = parseCode(b.code);
        if (na !== nb) return na - nb;
        return a.code.localeCompare(b.code, 'he');
      })
      .map((row) => ({
        ...row,
        periodText: (() => {
          const periods = Array.from(row.periods).filter(Boolean).sort();
          const formatted = periods.map(formatPeriodMonth).filter(Boolean);
          if (formatted.length <= 1) return formatted[0] || '';
          return formatted.join(', ');
        })(),
      }));
  }, [currentLines]);

  const prevMonth = useMemo(() => {
    if (!selectedMonth || selectedMonth.length !== 7) return null;
    const year = Number(selectedMonth.slice(0, 4));
    const month = Number(selectedMonth.slice(5, 7));
    if (!Number.isFinite(year) || !Number.isFinite(month)) return null;
    if (month === 1) return `${year - 1}-12`;
    return `${year}-${String(month - 1).padStart(2, '0')}`;
  }, [selectedMonth]);

  const comparisonRows = useMemo(() => {
    if (!prevMonth || !historyMonths[prevMonth]) return [];

    const prevLines = historyMonths[prevMonth].budget_lines || [];
    const prevByCode = new Map();
    const currentByCode = new Map();

    for (const row of groupedRows) {
      currentByCode.set(row.code, row.amount);
    }

    for (const line of prevLines) {
      const code = String(line.topic_code || '');
      const prev = prevByCode.get(code) || 0;
      prevByCode.set(code, prev + Number(line.amount || 0));
    }

    const allCodes = Array.from(new Set([...currentByCode.keys(), ...prevByCode.keys()]));
    allCodes.sort((a, b) => {
      const na = Number(a);
      const nb = Number(b);
      if (Number.isFinite(na) && Number.isFinite(nb)) return na - nb;
      return a.localeCompare(b, 'he');
    });

    return allCodes.map((code) => {
      const prevValue = prevByCode.get(code) || 0;
      const currentValue = currentByCode.get(code) || 0;
      const change = currentValue - prevValue;
      return { code, prevValue, currentValue, change };
    });
  }, [groupedRows, historyMonths, prevMonth]);

  const currentByCode = useMemo(() => {
    const byCode = new Map();
    for (const line of currentLines) {
      const code = String(line.topic_code || '');
      const prev = byCode.get(code) || 0;
      byCode.set(code, prev + Number(line.amount || 0));
    }
    return byCode;
  }, [currentLines]);

  const prevByCode = useMemo(() => {
    if (!prevMonth || !historyMonths[prevMonth]) return new Map();
    const byCode = new Map();
    const prevLines = historyMonths[prevMonth].budget_lines || [];
    for (const line of prevLines) {
      const code = String(line.topic_code || '');
      const prev = byCode.get(code) || 0;
      byCode.set(code, prev + Number(line.amount || 0));
    }
    return byCode;
  }, [historyMonths, prevMonth]);

  const hasPrevData = prevMonth && historyMonths[prevMonth];

  const retroChecks = useMemo(() => {
    const rows = [];
    for (const line of currentLines.filter((r) => r.is_retro)) {
      const code = String(line.topic_code || '');
      const prevAmount = prevByCode.get(code) || 0;
      const currentAmount = currentByCode.get(code) || 0;
      const deltaFromPrev = currentAmount - prevAmount;
      const retroAmount = Number(line.amount || 0);

      let signal;
      if (!hasPrevData) {
        signal = 'אין נתוני חודש קודם';
      } else if (Math.abs(prevAmount) < 1) {
        signal = 'אין בסיס להשוואה';
      } else {
        const ratio = Math.abs(retroAmount) / Math.abs(prevAmount);
        if (ratio > 2) signal = 'חריגה משמעותית';
        else if (ratio < 0.5) signal = 'נמוך יחסית';
        else signal = 'רגיל';
      }

      rows.push({
        id: line.id,
        code,
        periodMonth: line.period_month || '—',
        prevAmount,
        retroAmount,
        deltaFromPrev,
        signal,
      });
    }

    rows.sort((a, b) => {
      const na = Number(a.code);
      const nb = Number(b.code);
      if (Number.isFinite(na) && Number.isFinite(nb)) return na - nb;
      return a.code.localeCompare(b.code, 'he');
    });

    return rows;
  }, [currentLines, currentByCode, prevByCode, hasPrevData]);

  const handleDownloadPdf = async () => {
    try {
      setPdfLoading(true);
      setError(null);

      const generateRes = await reportsAPI.generate(id, selectedMonth);
      const jobId = generateRes?.data?.job_id;
      if (!jobId) {
        throw new Error('failed to start report job');
      }

      let reportId = null;
      for (let i = 0; i < 40; i += 1) {
        const statusRes = await reportsAPI.getStatus(jobId);
        const job = statusRes?.data || {};
        if (job.status === 'done') {
          reportId = job.report_id;
          break;
        }
        if (job.status === 'error') {
          throw new Error(job.error || 'report generation failed');
        }
        await new Promise((resolve) => setTimeout(resolve, 1500));
      }

      if (!reportId) {
        throw new Error('timeout while generating report');
      }

      const downloadRes = await reportsAPI.download(reportId);
      const blob = new Blob([downloadRes.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${id}_${selectedMonth}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('שגיאה בהורדת דוח PDF');
    } finally {
      setPdfLoading(false);
    }
  };

  if (loading) {
    return (
      <PageWrapper title="נתוני רשות">
        <div className="flex items-center justify-center py-16">
          <div className="animate-spin w-8 h-8 border-4 border-slate-400 border-t-transparent rounded-full" />
        </div>
      </PageWrapper>
    );
  }

  return (
    <PageWrapper title={`${budget?.municipality?.name || 'רשות'} - ${formatHebrewDate(selectedMonth)}`}>
      <div className="space-y-6" dir="rtl">
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl">
            {error}
          </div>
        )}

        {/* SECTION 1 — Header bar */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h1 className="text-3xl font-hebrew font-bold text-slate-900">
                {budget?.municipality?.name || 'רשות'}
              </h1>
              <p className="text-slate-600 mt-1 font-hebrew">{formatHebrewDate(selectedMonth)}</p>
            </div>
            {budget && (
              <span className={`inline-flex items-center px-4 py-2 rounded-full border font-hebrew font-semibold ${statusBadge.className}`}>
                {statusBadge.icon} {statusBadge.text}
              </span>
            )}
          </div>
        </div>

        {/* SECTION 2 — Summary cards */}
        {budget && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <SummaryCard
              title="סך הכל מגיע"
              value={formatShekel(budget.breakdown_total || 0)}
              valueClass="text-slate-900"
            />
            <SummaryCard
              title="שולם בפועל"
              value={formatShekel(budget.invoice_total || 0)}
              valueClass="text-green-700"
            />
            <SummaryCard
              title="יתרה לביצוע"
              value={formatShekel(Math.max(0, gapAmount))}
              valueClass={gapAmount > 0 ? 'text-indigo-700' : 'text-slate-500'}
            />
            <SummaryCard
              title="תשלום יתר"
              value={formatShekel(Math.abs(Math.min(0, gapAmount)))}
              valueClass={gapAmount < 0 ? 'text-red-700' : 'text-slate-500'}
            />
          </div>
        )}

        {budget && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <SummaryCard
              title="סכום רגיל (החודש)"
              value={formatShekel(linesSumRegular)}
              valueClass="text-slate-900"
            />
            <SummaryCard
              title="רטרו חיובי"
              value={formatShekel(retroPositive)}
              valueClass={retroPositive > 0 ? 'text-amber-700' : 'text-slate-500'}
            />
            <SummaryCard
              title="רטרו שלילי (ניכוי)"
              value={formatShekel(retroNegative)}
              valueClass={retroNegative < 0 ? 'text-red-700' : 'text-slate-500'}
            />
          </div>
        )}

        {breakdownMismatch && (
          <div className="rounded-xl border p-4 bg-amber-50 border-amber-200 text-amber-800">
            <p className="font-hebrew font-semibold">
              ⚠️ חוסר עקביות בנתוני הריצה:
            </p>
            <p className="font-hebrew text-sm mt-1">
              הסכום המופיע ב"פירוט" של הריצה ({formatShekel(storedBreakdown)}) אינו תואם
              לסיכום שורות התקציב ({formatShekel(linesSum)}). הסכומים המוצגים כאן מחושבים
              מתוך שורות התקציב בפועל. סביר שהקובץ שהועלה שלח סיכום שונה מהתוכן. מומלץ
              לבדוק את המקור.
            </p>
          </div>
        )}

        {budget && (
          <div className={`rounded-xl border p-4 ${
            status.key === 'balanced'
              ? 'bg-green-50 border-green-200 text-green-800'
              : status.key === 'awaiting_data'
                ? 'bg-slate-50 border-slate-200 text-slate-700'
                : status.key === 'current_gap'
                  ? 'bg-indigo-50 border-indigo-200 text-indigo-800'
                  : 'bg-red-50 border-red-200 text-red-800'
          }`}>
            <p className="font-hebrew font-semibold">
              {status.key === 'balanced'
                ? 'בדיקת איזון: הסכום ששולם תואם לסכום המגיע (סטייה עד 1 ש"ח).'
                : status.key === 'awaiting_data'
                  ? 'ממתין לנתונים: טרם התקבלו סכומים לחודש זה.'
                  : status.key === 'current_gap'
                    ? `יתרה לביצוע: המשרד חייב ${formatShekel(Math.abs(gapAmount))} במסגרת מחזור הדיווח הנוכחי.`
                    : status.key === 'deviation_overdue'
                      ? `חריגה: יתרה פתוחה מעל 60 יום (${formatShekel(Math.abs(gapAmount))}) — נדרש בירור.`
                      : `חריגה: שולם ${formatShekel(Math.abs(gapAmount))} מעבר לסכום המגיע — נדרש בירור.`}
            </p>
          </div>
        )}

        {/* SECTION 3 — Budget breakdown */}
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
          <div className="px-6 py-4 border-b border-slate-200">
            <h2 className="font-hebrew font-bold text-xl text-slate-900">פירוט תקציב</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-100">
                <tr>
                  <th className="px-4 py-3 text-right font-hebrew">קוד</th>
                  <th className="px-4 py-3 text-right font-hebrew">נושא</th>
                  <th className="px-4 py-3 text-right font-hebrew">סכום</th>
                  <th className="px-4 py-3 text-right font-hebrew">חודש תחולה</th>
                  <th className="px-4 py-3 text-right font-hebrew">סוג</th>
                </tr>
              </thead>
              <tbody>
                {groupedRows.map((row) => {
                  const isOverpaid = Number(row.amount) < 0;
                  const bgClass = isOverpaid
                    ? 'bg-red-50'
                    : row.hasRetro
                      ? 'bg-amber-50'
                      : 'bg-white';
                  const typeLabel = isOverpaid
                    ? 'תשלום יתר'
                    : row.hasRetro
                      ? 'רטרו'
                      : 'רגיל';
                  const typeClass = isOverpaid
                    ? 'text-red-700 font-semibold'
                    : row.hasRetro
                      ? 'text-amber-700'
                      : 'text-slate-700';
                  return (
                    <tr key={row.code} className={`border-t border-slate-100 ${bgClass}`}>
                      <td className="px-4 py-3 font-medium text-slate-800">{row.code}</td>
                      <td className="px-4 py-3 text-slate-700">{row.topic}</td>
                      <td className={`px-4 py-3 font-semibold ${isOverpaid ? 'text-red-700' : 'text-slate-900'}`}>
                        {formatShekel(row.amount)}
                      </td>
                      <td className="px-4 py-3 text-slate-700">
                        {row.periodText ? (
                          <span className="inline-flex items-center gap-1">
                            {row.hasRetro && <span className="text-amber-700 text-xs font-hebrew font-semibold">🔁 רטרו:</span>}
                            <span>{row.periodText}</span>
                          </span>
                        ) : '—'}
                      </td>
                      <td className={`px-4 py-3 ${typeClass}`}>{typeLabel}</td>
                    </tr>
                  );
                })}
                {groupedRows.length === 0 && (
                  <tr>
                    <td className="px-4 py-6 text-center text-slate-500 font-hebrew" colSpan="5">
                      אין נתוני תקציב לחודש זה
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* SECTION 4 — Comparison vs last month */}
        {comparisonRows.length > 0 && (
          <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
            <div className="px-6 py-4 border-b border-slate-200">
              <h2 className="font-hebrew font-bold text-xl text-slate-900">
                השוואה לחודש קודם ({formatHebrewDate(prevMonth)})
              </h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-100">
                  <tr>
                    <th className="px-4 py-3 text-right font-hebrew">קוד</th>
                    <th className="px-4 py-3 text-right font-hebrew">חודש קודם</th>
                    <th className="px-4 py-3 text-right font-hebrew">חודש נוכחי</th>
                    <th className="px-4 py-3 text-right font-hebrew">שינוי</th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonRows.map((row) => (
                    <tr key={row.code} className="border-t border-slate-100">
                      <td className="px-4 py-3 font-medium text-slate-800">{row.code}</td>
                      <td className="px-4 py-3 text-slate-700">{formatShekel(row.prevValue)}</td>
                      <td className="px-4 py-3 text-slate-700">{formatShekel(row.currentValue)}</td>
                      <td className={`px-4 py-3 font-semibold ${row.change < 0 ? 'text-red-700' : 'text-green-700'}`}>
                        {row.change > 0 ? '+' : ''}{formatShekel(row.change)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {retroChecks.length > 0 && (
          <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
            <div className="px-6 py-4 border-b border-slate-200">
              <h2 className="font-hebrew font-bold text-xl text-slate-900">בדיקת תשלומי רטרו</h2>
              <p className="text-sm text-slate-500 mt-1">
                {hasPrevData
                  ? 'כל שורה מציגה עבור איזה חודש שולם רטרו, מול תשלום החודש הקודם לאותו קוד.'
                  : 'לא נטענו נתונים עבור החודש הקודם — ההשוואה לא זמינה. העלה את קובץ ינואר 2026 להפעלת ההשוואה.'}
              </p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-100">
                  <tr>
                    <th className="px-4 py-3 text-right font-hebrew">קוד</th>
                    <th className="px-4 py-3 text-right font-hebrew">רטרו עבור חודש</th>
                    <th className="px-4 py-3 text-right font-hebrew">תשלום חודש קודם</th>
                    <th className="px-4 py-3 text-right font-hebrew">סכום רטרו</th>
                    <th className="px-4 py-3 text-right font-hebrew">שינוי מול חודש קודם</th>
                    <th className="px-4 py-3 text-right font-hebrew">סימון</th>
                  </tr>
                </thead>
                <tbody>
                  {retroChecks.map((row) => (
                    <tr key={row.id} className="border-t border-slate-100">
                      <td className="px-4 py-3 font-medium text-slate-800">{row.code}</td>
                      <td className="px-4 py-3 text-slate-700">{formatHebrewDate(row.periodMonth)}</td>
                      <td className="px-4 py-3 text-slate-700">{formatShekel(row.prevAmount)}</td>
                      <td className="px-4 py-3 text-amber-700 font-semibold">{formatShekel(row.retroAmount)}</td>
                      <td className={`px-4 py-3 font-semibold ${row.deltaFromPrev < 0 ? 'text-red-700' : 'text-green-700'}`}>
                        {row.deltaFromPrev > 0 ? '+' : ''}{formatShekel(row.deltaFromPrev)}
                      </td>
                      <td className="px-4 py-3 text-slate-700">{row.signal}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* SECTION 5 — Action buttons */}
        <div className="flex flex-wrap justify-start gap-3">
          <button
            onClick={() => navigate(`/municipality/${id}/detail?month=${selectedMonth}`)}
            disabled={!budget}
            className="inline-flex items-center gap-2 px-5 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-400 text-white rounded-lg font-hebrew font-semibold transition shadow"
          >
            <span>📊</span>
            <span>פירוט מלא לפי קוד נושא</span>
          </button>
          <button
            onClick={handleDownloadPdf}
            disabled={pdfLoading || !budget}
            className="inline-flex items-center gap-2 px-5 py-3 bg-slate-900 hover:bg-slate-800 disabled:bg-slate-400 text-white rounded-lg font-hebrew font-semibold transition"
          >
            {pdfLoading && <span className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />}
            <span>הורד PDF</span>
          </button>
        </div>
      </div>
    </PageWrapper>
  );
}

function SummaryCard({ title, value, valueClass }) {
  return (
    <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
      <p className="text-sm text-slate-600 font-hebrew mb-2">{title}</p>
      <p className={`text-3xl font-bold font-hebrew ${valueClass}`}>{value}</p>
    </div>
  );
}
