import React, { useState, useEffect, useCallback, useRef } from 'react';
import PageWrapper from '../components/layout/PageWrapper';
import { reportsAPI, municipalityAPI } from '../services/api';
import { getLast12Months } from '../utils/format';

// ─── Helpers ──────────────────────────────────────────────────────────────────
function formatDateTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString('he-IL', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

const TYPE_LABELS = {
  monthly: 'חודשי', comparison: 'השוואה', custom: 'מותאם', positions: 'משרות',
};
const TYPE_ICONS = {
  monthly: '📄', comparison: '📊', custom: '📋', positions: '💼',
};

// ─── Toast ────────────────────────────────────────────────────────────────────
function Toast({ message, type = 'success', onDismiss }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 3800);
    return () => clearTimeout(t);
  }, [onDismiss]);
  return (
    <div
      className={`fixed bottom-6 left-1/2 -translate-x-1/2 z-50 ${type === 'error' ? 'bg-red-600' : 'bg-emerald-600'} text-white px-6 py-3 rounded-xl shadow-2xl font-hebrew text-sm cursor-pointer`}
      onClick={onDismiss}
    >
      {message}
    </div>
  );
}

// ─── TAB 1: Archive ────────────────────────────────────────────────────────────
function ArchiveTab({ showToast }) {
  const [byMuni, setByMuni] = useState({});
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [filterText, setFilterText] = useState('');
  const [filterType, setFilterType] = useState('');
  const months = getLast12Months();
  const [filterMonth, setFilterMonth] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await reportsAPI.adminAll();
      const payload = res?.data;
      let normalized = {};

      if (Array.isArray(payload)) {
        // Support legacy/list payload shape and bucket by municipality name.
        normalized = payload.reduce((acc, report) => {
          const muniName = report?.muni || report?.municipality_name || report?.municipality || 'לא ידוע';
          if (!acc[muniName]) acc[muniName] = [];
          acc[muniName].push(report);
          return acc;
        }, {});
      } else if (payload && typeof payload === 'object') {
        normalized = payload;
      }

      if (!payload || typeof payload !== 'object') {
        console.warn('[AdminReportsPage] Unexpected adminAll payload shape, using empty archive', payload);
      }

      setByMuni(normalized);
    } catch {
      showToast('❌ שגיאה בטעינת הדוחות', 'error');
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => { load(); }, [load]);

  const handleDownload = async (r) => {
    setDownloading(r.id);
    try {
      const res = await reportsAPI.download(r.id);
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = r.file_name || `report_${r.id}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      showToast('✅ הדוח הורד בהצלחה');
      load();
    } catch {
      showToast('❌ שגיאה בהורדת הדוח', 'error');
    } finally {
      setDownloading(null);
    }
  };

  const handleDelete = async (r) => {
    if (!window.confirm(`למחוק את הדוח "${r.file_name || r.id}"?`)) return;
    setDeleting(r.id);
    try {
      await reportsAPI.delete(r.id);
      showToast('✅ הדוח נמחק');
      load();
    } catch {
      showToast('❌ שגיאה במחיקה', 'error');
    } finally {
      setDeleting(null);
    }
  };

  const allReports = Object.entries(byMuni).flatMap(([muniName, reports]) => {
    if (!Array.isArray(reports)) return [];
    return reports.map(r => ({ ...r, muni: muniName }));
  });

  const shown = allReports.filter(r => {
    if (filterText && !r.muni.includes(filterText)) return false;
    if (filterType && r.report_type !== filterType) return false;
    if (filterMonth && r.month !== filterMonth) return false;
    return true;
  });

  return (
    <div dir="rtl">
      <div className="flex flex-wrap gap-3 mb-5 items-center">
        <input
          type="text"
          placeholder="🔍 חפש רשות..."
          value={filterText}
          onChange={e => setFilterText(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm font-hebrew focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <select
          value={filterMonth}
          onChange={e => setFilterMonth(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm font-hebrew focus:outline-none focus:ring-2 focus:ring-blue-400"
          dir="rtl"
        >
          <option value="">כל החודשים</option>
          {months.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
        </select>
        <select
          value={filterType}
          onChange={e => setFilterType(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm font-hebrew focus:outline-none focus:ring-2 focus:ring-blue-400"
        >
          <option value="">כל הסוגים</option>
          <option value="monthly">📄 חודשי</option>
          <option value="comparison">📊 השוואה</option>
          <option value="positions">💼 משרות</option>
        </select>
        <button onClick={load} className="text-sm text-blue-600 hover:text-blue-800 font-hebrew">🔄 רענן</button>
        <span className="text-sm text-gray-400 font-hebrew">{shown.length} דוחות</span>
      </div>

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : shown.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="text-4xl mb-3">📭</p>
          <p className="font-hebrew font-semibold text-gray-600">אין דוחות להצגה</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-200 shadow-sm">
          <table className="w-full min-w-[800px]" dir="rtl">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {['רשות', 'חודש', 'סוג', 'תאריך יצירה', 'גודל', 'הורדות', 'פעולות'].map(h => (
                  <th key={h} className="px-4 py-3 text-right text-xs font-bold text-gray-500 font-hebrew uppercase">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {shown.map(r => (
                <tr key={r.id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-hebrew font-semibold text-sm text-gray-800">{r.muni}</td>
                  <td className="px-4 py-3 font-hebrew text-sm text-gray-700">{r.month_display}</td>
                  <td className="px-4 py-3 text-sm font-hebrew text-gray-700">
                    {TYPE_ICONS[r.report_type]} {TYPE_LABELS[r.report_type] || r.report_type}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500 font-hebrew">{formatDateTime(r.generated_at)}</td>
                  <td className="px-4 py-3 text-sm text-gray-500 font-hebrew text-center">{r.file_size_display}</td>
                  <td className="px-4 py-3 text-sm text-center text-gray-500 font-hebrew">{r.download_count}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      {r.file_exists && (
                        <button
                          onClick={() => handleDownload(r)}
                          disabled={downloading === r.id}
                          className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-lg text-xs font-hebrew transition-colors"
                        >
                          {downloading === r.id ? '...' : '📥 הורד'}
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(r)}
                        disabled={deleting === r.id}
                        className="px-2 py-1.5 bg-red-50 hover:bg-red-100 text-red-600 rounded-lg text-xs font-hebrew transition-colors"
                      >
                        {deleting === r.id ? '...' : '🗑️'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── TAB 2: Generate ──────────────────────────────────────────────────────────
function GenerateTab({ showToast }) {
  const months = getLast12Months();
  const [municipalities, setMunicipalities] = useState([]);
  const [selectedMuni, setSelectedMuni] = useState('');
  const [selectedMonth, setSelectedMonth] = useState(months[0]?.value || '');
  const [reportType, setReportType] = useState('monthly');
  const [generating, setGenerating] = useState(false);
  const [doneReport, setDoneReport] = useState(null);
  const [statusMsg, setStatusMsg] = useState('');
  const pollRef = useRef(null);

  useEffect(() => {
    municipalityAPI.getAll().then(res => {
      const payload = res?.data;
      const normalizedMunicipalities = Array.isArray(payload)
        ? payload
        : Array.isArray(payload?.items)
          ? payload.items
          : Array.isArray(payload?.results)
            ? payload.results
            : [];

      setMunicipalities(normalizedMunicipalities);
    }).catch(() => {});
  }, []);

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  const poll = useCallback((jobId) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const res = await reportsAPI.getStatus(jobId);
        const job = res.data;
        if (job.status === 'done') {
          clearInterval(pollRef.current);
          setGenerating(false);
          setStatusMsg('');
          setDoneReport({ report_id: job.report_id });
          showToast('✅ הדוח נוצר בהצלחה');
        } else if (job.status === 'error') {
          clearInterval(pollRef.current);
          setGenerating(false);
          setStatusMsg('');
          showToast(`❌ שגיאה: ${job.error || 'ייצור נכשל'}`, 'error');
        } else {
          setStatusMsg(job.status === 'running' ? '⏳ מייצר דוח...' : '⏳ ממתין בתור...');
        }
      } catch {
        clearInterval(pollRef.current);
        setGenerating(false);
        setStatusMsg('');
        showToast('❌ שגיאת תקשורת', 'error');
      }
    }, 1500);
  }, [showToast]);

  const handleGenerate = async () => {
    if (!selectedMuni) return showToast('יש לבחור רשות', 'error');
    setGenerating(true);
    setDoneReport(null);
    setStatusMsg('⏳ שולח בקשה...');
    try {
      let res;
      if (reportType === 'comparison') {
        res = await reportsAPI.generateComparison(selectedMuni);
      } else {
        res = await reportsAPI.generate(selectedMuni, selectedMonth);
      }
      poll(res.data.job_id);
    } catch (err) {
      setGenerating(false);
      setStatusMsg('');
      showToast(err.response?.data?.detail || '❌ שגיאה ביצירת הדוח', 'error');
    }
  };

  const handleDownloadDone = async () => {
    if (!doneReport?.report_id) return;
    try {
      const res = await reportsAPI.download(doneReport.report_id);
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${doneReport.report_id}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      showToast('❌ שגיאה בהורדה', 'error');
    }
  };

  return (
    <div dir="rtl" className="max-w-xl mx-auto space-y-6">
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-5">
        <h3 className="font-bold font-hebrew text-xl text-gray-800">⚙️ יצירת דוח PDF</h3>

        <div>
          <label className="block text-sm font-bold font-hebrew text-gray-600 mb-1">רשות</label>
          {municipalities.length === 0 && (
            <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-2 py-1 mb-2 font-hebrew">
              לא נמצאו רשויות זמינות כרגע. ניתן לרענן מאוחר יותר.
            </p>
          )}
          <select
            value={selectedMuni}
            onChange={e => { setSelectedMuni(e.target.value); setDoneReport(null); }}
            className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm font-hebrew w-full focus:outline-none focus:ring-2 focus:ring-blue-400"
            dir="rtl"
          >
            <option value="">— בחר רשות —</option>
            {municipalities.map(m => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-bold font-hebrew text-gray-600 mb-2">סוג דוח</label>
          <div className="flex gap-3 flex-wrap">
            {[
              { id: 'monthly',    label: '📄 חודשי',   desc: 'דוח לחודש ספציפי' },
              { id: 'comparison', label: '📊 השוואה',   desc: 'כל החודשים' },
            ].map(opt => (
              <button
                key={opt.id}
                onClick={() => { setReportType(opt.id); setDoneReport(null); }}
                className={`flex-1 min-w-[130px] text-right rounded-xl border-2 px-4 py-3 transition-all ${
                  reportType === opt.id
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 hover:border-gray-300 text-gray-700'
                }`}
              >
                <p className="font-bold font-hebrew text-sm">{opt.label}</p>
                <p className="text-xs text-gray-500 font-hebrew mt-0.5">{opt.desc}</p>
              </button>
            ))}
          </div>
        </div>

        {reportType === 'monthly' && (
          <div>
            <label className="block text-sm font-bold font-hebrew text-gray-600 mb-1">חודש</label>
            <select
              value={selectedMonth}
              onChange={e => { setSelectedMonth(e.target.value); setDoneReport(null); }}
              className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm font-hebrew focus:outline-none focus:ring-2 focus:ring-blue-400"
              dir="rtl"
            >
              {months.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
            </select>
          </div>
        )}

        <button
          onClick={handleGenerate}
          disabled={generating || !selectedMuni}
          className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-xl font-bold font-hebrew text-base transition-colors flex items-center justify-center gap-2"
        >
          {generating ? (
            <>
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              מייצר...
            </>
          ) : '⚙️ צור דוח עכשיו'}
        </button>

        {statusMsg && (
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 font-hebrew text-sm text-blue-700">
            {statusMsg}
          </div>
        )}

        {doneReport && (
          <div className="bg-green-50 border border-green-300 rounded-xl p-4 flex items-center justify-between">
            <p className="font-bold font-hebrew text-green-800 text-sm">✅ הדוח מוכן להורדה!</p>
            <button
              onClick={handleDownloadDone}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-hebrew font-bold transition-colors"
            >
              📥 הורד PDF
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── TAB 3: Branding ─────────────────────────────────────────────────────────
function BrandingTab({ showToast }) {
  const [form, setForm] = useState({
    firm_name: '', firm_address: '', firm_phone: '', firm_email: '', primary_color: '#1E3A5F',
  });
  const [logoFile, setLogoFile] = useState(null);
  const [logoPreview, setLogoPreview] = useState(null);
  const [hasLogo, setHasLogo] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const fileRef = useRef();

  useEffect(() => {
    reportsAPI.getBranding().then(res => {
      if (res.data) {
        setForm(f => ({ ...f, ...res.data }));
        setHasLogo(!!res.data.logo_path);
      }
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const handleLogoChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLogoFile(file);
    setLogoPreview(URL.createObjectURL(file));
  };

  const handleDeleteLogo = async () => {
    if (!window.confirm('למחוק את הלוגו?')) return;
    try {
      await reportsAPI.deleteLogo();
      setHasLogo(false);
      setLogoFile(null);
      setLogoPreview(null);
      showToast('✅ הלוגו נמחק');
    } catch {
      showToast('❌ שגיאה במחיקה', 'error');
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const fd = new FormData();
      Object.entries(form).forEach(([k, v]) => fd.append(k, v || ''));
      if (logoFile) fd.append('logo', logoFile);
      await reportsAPI.saveBranding(fd);
      showToast('✅ הגדרות המיתוג נשמרו');
      if (logoFile) setHasLogo(true);
    } catch {
      showToast('❌ שגיאה בשמירה', 'error');
    } finally {
      setSaving(false);
    }
  };

  const logoSrc = logoPreview || (hasLogo ? '/api/reports/branding/logo' : null);

  const fields = [
    { key: 'firm_name',    label: 'שם המשרד',  placeholder: 'רו"ח ישראל ישראלי' },
    { key: 'firm_address', label: 'כתובת',      placeholder: 'רחוב הרצל 1, ת"א' },
    { key: 'firm_phone',   label: 'טלפון',      placeholder: '03-1234567' },
    { key: 'firm_email',   label: 'דוא"ל',     placeholder: 'office@cpa.co.il' },
  ];

  if (loading) return (
    <div className="flex justify-center py-16">
      <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div dir="rtl" className="max-w-xl mx-auto">
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-5">
        <h3 className="font-bold font-hebrew text-xl text-gray-800">🎨 הגדרות מיתוג לדוחות</h3>

        <div>
          <label className="block text-sm font-bold font-hebrew text-gray-600 mb-2">לוגו משרד</label>
          <div
            className="border-2 border-dashed border-gray-300 hover:border-blue-400 rounded-xl p-5 text-center cursor-pointer transition-colors"
            onClick={() => fileRef.current?.click()}
          >
            {logoSrc
              ? <img src={logoSrc} alt="לוגו" className="max-h-20 mx-auto object-contain" />
              : <p className="text-gray-400 font-hebrew text-sm">לחץ להעלאת לוגו (PNG / JPG)</p>
            }
          </div>
          <input type="file" accept="image/*" ref={fileRef} className="hidden" onChange={handleLogoChange} />
          {logoSrc && (
            <button onClick={handleDeleteLogo} className="mt-1 text-xs text-red-600 hover:text-red-800 font-hebrew">
              🗑️ מחק לוגו
            </button>
          )}
        </div>

        {fields.map(({ key, label, placeholder }) => (
          <div key={key}>
            <label className="block text-sm font-bold font-hebrew text-gray-600 mb-1">{label}</label>
            <input
              type="text"
              value={form[key] || ''}
              onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
              placeholder={placeholder}
              className="border border-gray-300 rounded-lg px-4 py-2.5 text-sm font-hebrew w-full focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </div>
        ))}

        <div>
          <label className="block text-sm font-bold font-hebrew text-gray-600 mb-1">צבע ראשי</label>
          <div className="flex items-center gap-3">
            <input
              type="color"
              value={form.primary_color || '#1E3A5F'}
              onChange={e => setForm(f => ({ ...f, primary_color: e.target.value }))}
              className="w-12 h-10 rounded border border-gray-300 cursor-pointer"
            />
            <span className="text-sm font-mono text-gray-500">{form.primary_color}</span>
          </div>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-xl font-bold font-hebrew transition-colors flex items-center justify-center gap-2"
        >
          {saving ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              שומר...
            </>
          ) : '💾 שמור הגדרות'}
        </button>
      </div>
    </div>
  );
}

// ─── Main Page ─────────────────────────────────────────────────────────────────
const TABS = [
  { id: 'archive',  label: '📁 ארכיון דוחות' },
  { id: 'generate', label: '⚙️ צור דוח' },
  { id: 'branding', label: '🎨 הגדרות מיתוג' },
];

export default function AdminReportsPage() {
  console.log('[AdminReportsPage] render', { path: window.location.pathname });

  const [activeTab, setActiveTab] = useState('archive');
  const [toast, setToast] = useState(null);

  useEffect(() => {
    console.log('Reports Page Mounted');
  }, []);

  const showToast = useCallback((message, type = 'success') => {
    setToast({ message, type, key: Date.now() });
  }, []);

  const isKnownTab = TABS.some((tab) => tab.id === activeTab);

  return (
    <PageWrapper title="דוחות ומסמכים" backPath="/dashboard">
      <div dir="rtl" className="space-y-6">

        <div className="bg-gradient-to-r from-slate-800 to-slate-700 rounded-2xl p-6 text-right">
          <p className="text-xs text-slate-300 font-hebrew mb-2">לוח בקרה / ניהול / דוחות ומסמכים</p>
          <h1 className="text-2xl font-bold font-hebrew text-white">📄 דוחות ומסמכים</h1>
          <p className="text-slate-300 font-hebrew text-sm mt-1">ארכיון, יצירת דוחות PDF והגדרות מיתוג</p>
        </div>

        <div className="border-b border-gray-200">
          <nav className="flex gap-1 overflow-x-auto" dir="rtl">
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-5 py-3 text-sm font-bold font-hebrew whitespace-nowrap border-b-2 -mb-px transition-colors ${
                  activeTab === tab.id
                    ? 'text-blue-700 border-blue-600'
                    : 'text-gray-500 border-transparent hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {activeTab === 'archive'  && <ArchiveTab  showToast={showToast} />}
        {activeTab === 'generate' && <GenerateTab showToast={showToast} />}
        {activeTab === 'branding' && <BrandingTab showToast={showToast} />}

        {!isKnownTab && (
          <div className="bg-white border border-gray-200 rounded-2xl p-8 text-center">
            <h2 className="text-xl font-hebrew font-bold text-gray-800 mb-2">דוחות ומסמכים</h2>
            <p className="text-gray-600 font-hebrew">אין נתונים זמינים כרגע</p>
          </div>
        )}

      </div>

      {toast && (
        <Toast key={toast.key} message={toast.message} type={toast.type} onDismiss={() => setToast(null)} />
      )}
    </PageWrapper>
  );
}