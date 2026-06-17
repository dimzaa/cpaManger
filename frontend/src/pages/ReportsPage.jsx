import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import PortalWrapper from '../components/portal/PortalWrapper';
import { useAuth } from '../context/AuthContext';
import { reportsAPI } from '../services/api';
import { getLast12Months, formatHebrewDate } from '../utils/format';

// ─── Helpers ──────────────────────────────────────────────────────────────────
function formatDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString('he-IL', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

// ─── Toast ────────────────────────────────────────────────────────────────────
function Toast({ message, type = 'success', onDismiss }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 3500);
    return () => clearTimeout(t);
  }, [onDismiss]);
  const bg = type === 'error' ? 'bg-red-600' : 'bg-green-600';
  return (
    <div
      className={`fixed bottom-6 left-1/2 -translate-x-1/2 z-50 ${bg} text-white px-6 py-3 rounded-xl shadow-2xl font-hebrew text-sm flex items-center gap-2 cursor-pointer`}
      onClick={onDismiss}
    >
      <span>{message}</span>
    </div>
  );
}

// ─── Quick action card ────────────────────────────────────────────────────────
function ActionCard({ icon, title, subtitle, onClick, loading, disabled }) {
  return (
    <button
      onClick={onClick}
      disabled={loading || disabled}
      className="bg-white rounded-2xl border-2 border-gray-200 hover:border-blue-400 shadow-sm p-6 text-right transition-all duration-200 hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed flex flex-col gap-3 w-full"
      dir="rtl"
    >
      <span className="text-3xl">{icon}</span>
      <div>
        <p className="font-bold font-hebrew text-gray-800 text-base">{title}</p>
        <p className="text-sm text-gray-500 font-hebrew mt-1">{subtitle}</p>
      </div>
      {loading ? (
        <div className="flex items-center gap-2 text-blue-600 text-sm font-hebrew">
          <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <span>מייצר...</span>
        </div>
      ) : (
        <span className="text-blue-600 text-sm font-hebrew font-medium">הורד ←</span>
      )}
    </button>
  );
}

// ─── Report row ───────────────────────────────────────────────────────────────
function ReportRow({ report, onDownload, downloading }) {
  const TYPE_ICONS = {
    monthly: '📄', comparison: '📊', custom: '📋', positions: '💼',
  };

  return (
    <tr className="border-b border-gray-100 hover:bg-gray-50 transition-colors" dir="rtl">
      <td className="px-4 py-3 font-hebrew text-gray-800 font-medium">
        {report.month_display}
      </td>
      <td className="px-4 py-3">
        <span className="flex items-center gap-1.5 font-hebrew text-sm text-gray-700">
          {TYPE_ICONS[report.report_type] || '📄'} {report.report_type_display}
        </span>
      </td>
      <td className="px-4 py-3 text-sm text-gray-500 font-hebrew">
        {formatDate(report.generated_at)}
      </td>
      <td className="px-4 py-3">
        {report.is_auto_generated ? (
          <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full font-hebrew border border-gray-200">
            🤖 אוטומטי
          </span>
        ) : (
          <span className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full font-hebrew border border-blue-200">
            👤 ידני
          </span>
        )}
      </td>
      <td className="px-4 py-3 text-sm text-gray-500 font-hebrew text-center">
        {report.file_size_display}
      </td>
      <td className="px-4 py-3 text-sm text-gray-500 text-center font-hebrew">
        {report.download_count}
      </td>
      <td className="px-4 py-3">
        {report.file_exists ? (
          <button
            onClick={() => onDownload(report)}
            disabled={downloading === report.id}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-lg text-xs font-hebrew transition-colors"
          >
            {downloading === report.id ? (
              <>
                <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                מוריד...
              </>
            ) : (
              '📥 הורד'
            )}
          </button>
        ) : (
          <span className="text-xs text-gray-400 font-hebrew">❌ קובץ חסר</span>
        )}
      </td>
    </tr>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function ReportsPage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const municipalityId = user?.municipality_id;
  const municipalityName = user?.municipality_name || '';

  const months = getLast12Months();
  const defaultMonth = months[0]?.value || '';

  const [reports, setReports]           = useState([]);
  const [loading, setLoading]           = useState(true);
  const [downloading, setDownloading]   = useState(null); // report.id being downloaded
  const [generatingMonthly, setGeneratingMonthly] = useState(false);
  const [generatingCompar, setGeneratingCompar]   = useState(false);
  const [selectedMonth, setSelectedMonth]         = useState(defaultMonth);
  const [toast, setToast]               = useState(null);
  const pollRef = useRef(null);

  const showToast = useCallback((message, type = 'success') => {
    setToast({ message, type, key: Date.now() });
  }, []);

  const loadReports = useCallback(async () => {
    if (!municipalityId) return;
    try {
      const res = await reportsAPI.list(municipalityId);
      setReports(res.data || []);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [municipalityId]);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  // Poll job until done
  const pollJob = useCallback((jobId, onDone) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const res = await reportsAPI.getStatus(jobId);
        const job = res.data;
        if (job.status === 'done') {
          clearInterval(pollRef.current);
          onDone(job);
          loadReports();
        } else if (job.status === 'error') {
          clearInterval(pollRef.current);
          showToast(`❌ שגיאה: ${job.error || 'לא ניתן לייצר דוח'}`, 'error');
          onDone(null);
        }
      } catch {
        clearInterval(pollRef.current);
        onDone(null);
      }
    }, 1500);
  }, [loadReports, showToast]);

  // Download helper — triggers browser file download
  const triggerDownload = useCallback(async (report) => {
    setDownloading(report.id);
    try {
      const res = await reportsAPI.download(report.id);
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = report.file_name || `report_${report.id}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      showToast('✅ הדוח הורד בהצלחה');
      // Refresh to update download count
      loadReports();
    } catch (err) {
      if (err.response?.status === 410) {
        showToast('❌ קובץ לא נמצא — ניתן לצור מחדש', 'error');
      } else {
        showToast('❌ שגיאה בהורדת הדוח', 'error');
      }
    } finally {
      setDownloading(null);
    }
  }, [loadReports, showToast]);

  const handleGenerateMonthly = useCallback(async () => {
    if (!municipalityId || !selectedMonth) return;
    setGeneratingMonthly(true);
    try {
      const res = await reportsAPI.generate(municipalityId, selectedMonth);
      const { job_id } = res.data;
      pollJob(job_id, (job) => {
        setGeneratingMonthly(false);
        if (job) showToast('✅ הדוח נוצר בהצלחה — ניתן להוריד');
      });
    } catch (err) {
      setGeneratingMonthly(false);
      showToast(err.response?.data?.detail || '❌ שגיאה ביצירת הדוח', 'error');
    }
  }, [municipalityId, selectedMonth, pollJob, showToast]);

  const handleGenerateComparison = useCallback(async () => {
    if (!municipalityId) return;
    setGeneratingCompar(true);
    try {
      const res = await reportsAPI.generateComparison(municipalityId);
      const { job_id } = res.data;
      pollJob(job_id, (job) => {
        setGeneratingCompar(false);
        if (job) showToast('✅ דוח ההשוואה נוצר בהצלחה');
      });
    } catch (err) {
      setGeneratingCompar(false);
      showToast(err.response?.data?.detail || '❌ שגיאה ביצירת דוח ההשוואה', 'error');
    }
  }, [municipalityId, pollJob, showToast]);

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  const monthlyReports = reports.filter(r => r.report_type === 'monthly');
  const comparisonReports = reports.filter(r => r.report_type === 'comparison');
  const otherReports = reports.filter(r => !['monthly', 'comparison'].includes(r.report_type));
  const allSorted = reports;

  return (
    <PortalWrapper title="דוחות ומסמכים" onBack={() => navigate('/portal')}>
      <div dir="rtl" className="space-y-6">

        {/* ── Header ─────────────────────────────────────────────────── */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
          <h1 className="text-2xl font-bold font-hebrew text-gray-800 flex items-center gap-2">
            📄 דוחות ומסמכים
          </h1>
          {municipalityName && (
            <p className="text-sm text-blue-700 font-hebrew font-semibold mt-1">
              {municipalityName}
            </p>
          )}
          <p className="text-sm text-gray-500 font-hebrew mt-1">
            יצירת, הורדת וניהול דוחות תקציב
          </p>
        </div>

        {/* ── Quick actions ────────────────────────────────────────── */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
          <h2 className="font-bold font-hebrew text-gray-700 mb-4 text-lg">⚡ פעולות מהירות</h2>

          {/* Month selector */}
          <div className="mb-4">
            <label className="block text-xs font-bold text-gray-600 font-hebrew mb-1">
              בחר חודש לדוח חודשי:
            </label>
            <select
              value={selectedMonth}
              onChange={e => setSelectedMonth(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm font-hebrew bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              dir="rtl"
            >
              {months.map(m => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <ActionCard
              icon="📥"
              title="דוח חודשי"
              subtitle={`הורד דוח תקציב עבור ${months.find(m => m.value === selectedMonth)?.label || selectedMonth}`}
              onClick={handleGenerateMonthly}
              loading={generatingMonthly}
              disabled={!selectedMonth}
            />
            <ActionCard
              icon="📊"
              title="דוח השוואה"
              subtitle="דוח מקיף המשווה את כל החודשים"
              onClick={handleGenerateComparison}
              loading={generatingCompar}
            />
            <div
              className="bg-white rounded-2xl border-2 border-gray-200 shadow-sm p-6 text-right cursor-pointer hover:border-blue-400 transition-all"
              onClick={() => document.getElementById('archive-section')?.scrollIntoView({ behavior: 'smooth' })}
              dir="rtl"
            >
              <span className="text-3xl">📋</span>
              <div className="mt-3">
                <p className="font-bold font-hebrew text-gray-800 text-base">ארכיון</p>
                <p className="text-sm text-gray-500 font-hebrew mt-1">כל הדוחות הקודמים</p>
              </div>
              <span className="text-blue-600 text-sm font-hebrew font-medium mt-3 block">
                {reports.length} דוחות ←
              </span>
            </div>
          </div>

          {(generatingMonthly || generatingCompar) && (
            <div className="mt-4 bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-center gap-3">
              <div className="w-6 h-6 border-3 border-blue-500 border-t-transparent rounded-full animate-spin flex-shrink-0" />
              <div>
                <p className="font-bold font-hebrew text-blue-800 text-sm">מייצר דוח...</p>
                <p className="text-xs text-blue-600 font-hebrew">אנא המתן — הייצור נמשך עד 30 שניות</p>
              </div>
            </div>
          )}
        </div>

        {/* ── Archive ──────────────────────────────────────────────── */}
        <div id="archive-section" className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="font-bold font-hebrew text-gray-700 text-lg">📁 ארכיון דוחות</h2>
              <p className="text-sm text-gray-500 font-hebrew mt-0.5">כל הדוחות שנוצרו עבור הרשות</p>
            </div>
            <button
              onClick={loadReports}
              className="text-sm text-blue-600 hover:text-blue-800 font-hebrew flex items-center gap-1"
            >
              🔄 רענן
            </button>
          </div>

          {loading ? (
            <div className="flex justify-center py-12">
              <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : allSorted.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p className="text-4xl mb-3">📭</p>
              <p className="font-hebrew font-semibold text-gray-700">אין דוחות עדיין</p>
              <p className="text-sm font-hebrew mt-1">השתמש בפעולות מהירות למעלה ליצירת הדוח הראשון</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[700px]" dir="rtl">
                <thead>
                  <tr className="border-b-2 border-gray-200">
                    {['חודש', 'סוג דוח', 'תאריך יצירה', 'מקור', 'גודל', 'הורדות', 'פעולות'].map(h => (
                      <th key={h} className="px-4 py-3 text-right text-xs font-bold text-gray-500 font-hebrew uppercase">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {allSorted.map(report => (
                    <ReportRow
                      key={report.id}
                      report={report}
                      onDownload={triggerDownload}
                      downloading={downloading}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* ── Info box ─────────────────────────────────────────────── */}
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-5" dir="rtl">
          <div className="flex items-start gap-3">
            <span className="text-lg flex-shrink-0">ℹ️</span>
            <div>
              <p className="font-semibold font-hebrew text-gray-700 text-sm">על הדוחות האוטומטיים</p>
              <p className="text-gray-500 font-hebrew text-sm mt-1 leading-relaxed">
                בכל ראשון לחודש בשעה 06:00, המערכת מייצרת אוטומטית דוח חודשי עבור החודש שחלף.
                ניתן גם לצור דוח ידני בכל עת.
              </p>
            </div>
          </div>
        </div>

      </div>

      {/* Toast */}
      {toast && (
        <Toast
          key={toast.key}
          message={toast.message}
          type={toast.type}
          onDismiss={() => setToast(null)}
        />
      )}
    </PortalWrapper>
  );
}
