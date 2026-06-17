import React, { useState, useEffect, useCallback, useRef } from 'react';
import PageWrapper from '../components/layout/PageWrapper';
import { ministryAPI } from '../services/api';
import {
  BookOpen, Bell, FileText, BarChart2, Plus, Edit3, Trash2,
  Save, X, Check, Search, ChevronDown, ChevronUp, Eye,
} from 'lucide-react';

// ─── TABS ───────────────────────────────────────────────────────────────────
const TABS = [
  { id: 'codes',     label: 'קודי תקצוב',    icon: BookOpen  },
  { id: 'policy',    label: 'שינויי מדיניות', icon: Bell      },
  { id: 'circulars', label: 'חוזרי מנכ"ל',   icon: FileText  },
  { id: 'stats',     label: 'סטטיסטיקות',    icon: BarChart2 },
];

// ─── SEVERITY / IMPORTANCE CONFIG ──────────────────────────────────────────
const SEVERITY = {
  high:   { icon: '🔴', label: 'חמור',   badge: 'bg-red-100 text-red-700'     },
  medium: { icon: '🟡', label: 'בינוני', badge: 'bg-amber-100 text-amber-700' },
  low:    { icon: '🔵', label: 'נמוך',   badge: 'bg-blue-100 text-blue-700'   },
  info:   { icon: 'ℹ️',  label: 'מידע',   badge: 'bg-slate-100 text-slate-600' },
};
const IMPORTANCE = {
  critical:  { icon: '🔴', label: 'דחוף',   badge: 'bg-red-100 text-red-700'    },
  important: { icon: '🟡', label: 'חשוב',   badge: 'bg-amber-100 text-amber-700' },
  routine:   { icon: '⚪', label: 'שגרתי',  badge: 'bg-slate-100 text-slate-500' },
};

const CHANGE_TYPES = [
  { v: 'formula',       l: 'שינוי נוסחה'       },
  { v: 'percentage',    l: 'שינוי אחוז'         },
  { v: 'threshold',     l: 'שינוי סף'           },
  { v: 'new_code',      l: 'קוד חדש'            },
  { v: 'removed_code',  l: 'ביטול קוד'          },
  { v: 'deadline',      l: 'שינוי מועד'         },
  { v: 'salary_table',  l: 'עדכון טבלת שכר'    },
  { v: 'eligibility',   l: 'שינוי זכאות'        },
];
const CIRCULAR_CATEGORIES = ['תקצוב', 'כוח אדם', 'פדגוגיה', 'ביטחון', 'הסעות', 'כללי'];

function fmt(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('he-IL');
}

// ─── INLINE FIELD ──────────────────────────────────────────────────────────
const F = ({ label, children }) => (
  <div>
    <label className="block text-xs font-hebrew font-semibold text-slate-500 mb-1">{label}</label>
    {children}
  </div>
);
const Inp = ({ ...props }) => (
  <input {...props} className={`w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-hebrew focus:outline-none focus:ring-2 focus:ring-blue-400 ${props.className || ''}`} />
);
const Sel = ({ children, ...props }) => (
  <select {...props} className={`w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-hebrew focus:outline-none focus:ring-2 focus:ring-blue-400 ${props.className || ''}`}>
    {children}
  </select>
);
const Txt = ({ rows = 3, ...props }) => (
  <textarea rows={rows} {...props} className={`w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-hebrew focus:outline-none focus:ring-2 focus:ring-blue-400 resize-y ${props.className || ''}`} />
);

// ─── CODE EDIT MODAL ────────────────────────────────────────────────────────
function CodeEditModal({ code, onSave, onClose }) {
  const [form, setForm] = useState({
    name_short: code.name_short || '',
    name_full: code.name_full || '',
    category: code.category || '',
    description: code.description || '',
    formula: code.formula || '',
    participation_percent: code.participation_percent ?? '',
    booklet_page: code.booklet_page ?? '',
    purple_book_column: code.purple_book_column || '',
    booklet_section: code.booklet_section || '',
    keywords: code.keywords || '',
    is_active: code.is_active ?? true,
  });
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      const payload = { ...form };
      if (payload.participation_percent !== '') payload.participation_percent = Number(payload.participation_percent);
      if (payload.booklet_page !== '') payload.booklet_page = Number(payload.booklet_page);
      await onSave(code.id, payload);
      onClose();
    } finally { setSaving(false); }
  };

  const f = k => e => setForm(p => ({ ...p, [k]: e.target.value }));

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[85vh] overflow-y-auto" dir="rtl">
        <div className="flex items-center justify-between p-5 border-b border-slate-100">
          <h2 className="font-hebrew font-bold text-slate-800">עריכת קוד {code.code}</h2>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-100 transition text-slate-400"><X size={18} /></button>
        </div>
        <div className="p-5 space-y-4">
          <F label="שם קצר"><Inp value={form.name_short} onChange={f('name_short')} /></F>
          <F label="שם מלא"><Inp value={form.name_full} onChange={f('name_full')} /></F>
          <F label="קטגוריה"><Inp value={form.category} onChange={f('category')} /></F>
          <F label="תיאור"><Txt rows={4} value={form.description} onChange={f('description')} /></F>
          <F label="נוסחה"><Txt rows={3} value={form.formula} onChange={f('formula')} /></F>
          <div className="grid grid-cols-2 gap-4">
            <F label="אחוז השתתפות (%)"><Inp type="number" value={form.participation_percent} onChange={f('participation_percent')} /></F>
            <F label="עמוד בחוברת"><Inp type="number" value={form.booklet_page} onChange={f('booklet_page')} /></F>
          </div>
          <F label="עמודה בחוברת"><Inp value={form.purple_book_column} onChange={f('purple_book_column')} placeholder="למשל: ב / ג / ד" /></F>
          <F label="סעיף בחוברת"><Inp value={form.booklet_section} onChange={f('booklet_section')} /></F>
          <F label="מילות מפתח"><Inp value={form.keywords} onChange={f('keywords')} /></F>
          <div className="flex items-center gap-3">
            <button type="button" onClick={() => setForm(p => ({ ...p, is_active: !p.is_active }))}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${form.is_active ? 'bg-green-500' : 'bg-slate-300'}`}>
              <span className={`inline-block h-4 w-4 rounded-full bg-white transition transform ${form.is_active ? 'translate-x-1' : 'translate-x-6'}`} />
            </button>
            <span className="font-hebrew text-sm text-slate-600">{form.is_active ? 'פעיל' : 'לא פעיל'}</span>
          </div>
        </div>
        <div className="flex gap-3 p-5 border-t border-slate-100">
          <button onClick={save} disabled={saving}
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-hebrew text-sm font-medium transition disabled:opacity-50">
            <Save size={16} />{saving ? 'שומר...' : 'שמור'}
          </button>
          <button onClick={onClose} className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-hebrew text-sm transition">ביטול</button>
        </div>
      </div>
    </div>
  );
}

// ─── TAB 1: CODES ──────────────────────────────────────────────────────────
function AdminCodesTab() {
  const [codes, setCodes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);
  const [editCode, setEditCode] = useState(null);
  const [expanded, setExpanded] = useState(new Set());
  const searchRef = useRef(null);

  const load = useCallback(async (q = search) => {
    setLoading(true);
    try {
      const params = {};
      if (q) params.search = q;
      params.include_unknown = true;
      const res = await ministryAPI.getCodes(params);
      setCodes(res.data || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [search]);

  useEffect(() => { load(); }, []);

  const handleSearch = val => {
    setSearch(val);
    setPage(1);
    if (searchRef.current) clearTimeout(searchRef.current);
    searchRef.current = setTimeout(() => load(val), 350);
  };

  const handleSave = async (id, data) => {
    await ministryAPI.updateCode(id, data);
    await load();
  };

  const toggleExpanded = id => setExpanded(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });

  const totalPages = Math.max(1, Math.ceil(codes.length / pageSize));
  const safePage = Math.min(page, totalPages);
  const startIdx = (safePage - 1) * pageSize;
  const endIdx = startIdx + pageSize;
  const pagedCodes = codes.slice(startIdx, endIdx);
  const missingMetadataCount = codes.filter((c) => {
    const nameValue = String(c.name_short ?? c.name ?? '').trim();
    const categoryValue = String(c.category ?? '').trim();
    const nameMissing = !nameValue || nameValue === 'Unknown Code';
    const categoryMissing = !categoryValue || categoryValue === 'Missing Metadata';
    return nameMissing && categoryMissing;
  }).length;

  return (
    <div className="space-y-4">
      <div className="relative">
        <Search size={16} className="absolute right-3 top-3 text-slate-400" />
        <Inp value={search} onChange={e => handleSearch(e.target.value)} placeholder="חיפוש קודים..." className="pr-9" />
      </div>

      <div className="flex items-center justify-between" dir="rtl">
        <p className="font-hebrew text-sm text-slate-500">
          {codes.length} קודים סה"כ | {missingMetadataCount} עם מטאדטה חסרה
        </p>
        <div className="flex items-center gap-2">
          <span className="font-hebrew text-xs text-slate-500">שורות בעמוד</span>
          <Sel value={pageSize} onChange={e => { setPageSize(Number(e.target.value)); setPage(1); }} className="w-24">
            {[10, 15, 25, 50].map(size => <option key={size} value={size}>{size}</option>)}
          </Sel>
        </div>
      </div>

      {loading ? <div className="py-12 text-center text-slate-400 font-hebrew">טוען...</div> : (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50 border-b text-right">
                {['קוד', 'שם', 'קטגוריה', 'השתתפות', 'עמוד', 'עמודה', 'סטטוס מטאדטה', 'ניכוי', 'פעיל', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-xs font-hebrew font-semibold text-slate-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pagedCodes.map(code => {
                const rowKey = code.id ?? `unknown-${code.code}`;
                const isExp = expanded.has(rowKey);
                return (
                  <React.Fragment key={rowKey}>
                    <tr className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="px-4 py-3 font-bold text-slate-700 font-hebrew">{code.code}</td>
                      <td className="px-4 py-3 font-hebrew text-sm text-slate-700 max-w-[200px] truncate">{code.name_short}</td>
                      <td className="px-4 py-3 text-xs font-hebrew text-slate-500">{code.category}</td>
                      <td className="px-4 py-3 text-sm text-slate-600 font-hebrew">{code.participation_percent != null ? `${code.participation_percent}%` : '—'}</td>
                      <td className="px-4 py-3 text-sm text-slate-500">{code.booklet_page || '—'}</td>
                      <td className="px-4 py-3 text-sm text-slate-500">{code.purple_book_column || '—'}</td>
                      <td className="px-4 py-3">
                        {code.metadata_status === 'missing_metadata' ? (
                          <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-hebrew">Missing Metadata</span>
                        ) : (
                          <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-hebrew">תקין</span>
                        )}
                      </td>
                      <td className="px-4 py-3">{code.is_deduction ? <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-hebrew">ניכוי</span> : '—'}</td>
                      <td className="px-4 py-3">{code.is_active ? '✅' : '⏸'}</td>
                      <td className="px-4 py-3">
                        <div className="flex gap-1">
                          {code.id ? (
                            <button onClick={() => setEditCode(code)} className="p-1.5 text-slate-400 hover:text-blue-600 rounded hover:bg-blue-50 transition"><Edit3 size={14} /></button>
                          ) : (
                            <span className="px-2 py-1 text-[10px] font-hebrew text-amber-700 bg-amber-100 rounded">מזוהה בלבד</span>
                          )}
                          <button onClick={() => toggleExpanded(rowKey)} className="p-1.5 text-slate-400 hover:text-slate-600 rounded hover:bg-slate-100 transition">
                            {isExp ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                          </button>
                        </div>
                      </td>
                    </tr>
                    {isExp && (
                      <tr className="bg-slate-50">
                        <td colSpan={10} className="px-6 py-4 border-b border-slate-100">
                          <div className="text-right space-y-1 text-sm font-hebrew text-slate-600" dir="rtl">
                            {code.description && <p>{code.description}</p>}
                            {code.observed_topic && <p>נושא מזוהה בקובץ CHESHBONIT: {code.observed_topic}</p>}
                            {Array.isArray(code.missing_fields) && code.missing_fields.length > 0 && (
                              <p className="text-amber-700">שדות חסרים: {code.missing_fields.join(', ')}</p>
                            )}
                            {code.formula && <pre className="text-xs mt-2 bg-white rounded-lg p-3 border border-slate-200 whitespace-pre-wrap">{code.formula}</pre>}
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
      )}

      {!loading && (
        <div className="flex items-center justify-between" dir="rtl">
          <p className="font-hebrew text-xs text-slate-500">
            מציג {codes.length === 0 ? 0 : startIdx + 1}-{Math.min(endIdx, codes.length)} מתוך {codes.length}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={safePage <= 1}
              className="px-3 py-1.5 rounded-lg border border-slate-200 text-sm font-hebrew text-slate-600 disabled:opacity-50"
            >
              הקודם
            </button>
            <span className="text-sm font-hebrew text-slate-600">עמוד {safePage} / {totalPages}</span>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={safePage >= totalPages}
              className="px-3 py-1.5 rounded-lg border border-slate-200 text-sm font-hebrew text-slate-600 disabled:opacity-50"
            >
              הבא
            </button>
          </div>
        </div>
      )}

      {editCode && (
        <CodeEditModal code={editCode} onSave={handleSave} onClose={() => setEditCode(null)} />
      )}
    </div>
  );
}

// ─── POLICY CHANGE FORM MODAL ───────────────────────────────────────────────
function PolicyChangeModal({ allCodes, onSave, onClose }) {
  const [form, setForm] = useState({
    title: '', description: '', change_type: 'formula',
    affected_codes: [], effective_date: '', announced_date: '',
    source: '', impact_description: '', action_required: '',
    action_deadline: '', severity: 'medium',
  });
  const [saving, setSaving] = useState(false);

  const toggleCode = c => setForm(p => ({
    ...p,
    affected_codes: p.affected_codes.includes(c)
      ? p.affected_codes.filter(x => x !== c)
      : [...p.affected_codes, c],
  }));

  const save = async () => {
    setSaving(true);
    try {
      const payload = {
        ...form,
        effective_date: form.effective_date || null,
        announced_date: form.announced_date || null,
        action_deadline: form.action_deadline || null,
      };
      await onSave(payload);
      onClose();
    } finally { setSaving(false); }
  };

  const f = k => e => setForm(p => ({ ...p, [k]: e.target.value }));

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-xl max-h-[90vh] overflow-y-auto" dir="rtl">
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="font-hebrew font-bold text-slate-800">הוסף שינוי מדיניות</h2>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-100"><X size={18} /></button>
        </div>
        <div className="p-5 space-y-4">
          <F label="כותרת *"><Inp value={form.title} onChange={f('title')} placeholder="עדכון טבלת שכר גננות..." /></F>
          <F label="תיאור"><Txt value={form.description} onChange={f('description')} /></F>
          <div className="grid grid-cols-2 gap-4">
            <F label="סוג שינוי">
              <Sel value={form.change_type} onChange={f('change_type')}>
                {CHANGE_TYPES.map(ct => <option key={ct.v} value={ct.v}>{ct.l}</option>)}
              </Sel>
            </F>
            <F label="חומרה">
              <Sel value={form.severity} onChange={f('severity')}>
                {Object.entries(SEVERITY).map(([k, v]) => <option key={k} value={k}>{v.icon} {v.label}</option>)}
              </Sel>
            </F>
          </div>

          <F label="קודים מושפעים">
            <div className="flex flex-wrap gap-2 p-2 border border-slate-300 rounded-lg min-h-[40px]">
              {allCodes.map(c => (
                <button key={c.code} type="button" onClick={() => toggleCode(c.code)}
                  className={`text-xs font-hebrew px-2 py-1 rounded-full transition ${
                    form.affected_codes.includes(c.code)
                      ? 'bg-blue-600 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}>
                  {c.code} – {c.name_short}
                </button>
              ))}
            </div>
          </F>

          <div className="grid grid-cols-2 gap-4">
            <F label="תאריך הכרזה"><Inp type="date" value={form.announced_date} onChange={f('announced_date')} /></F>
            <F label="תאריך כניסה לתוקף"><Inp type="date" value={form.effective_date} onChange={f('effective_date')} /></F>
          </div>

          <F label="מקור (מספר חוזר / הכרזה)"><Inp value={form.source} onChange={f('source')} /></F>
          <F label="השפעה על התקציב"><Txt value={form.impact_description} onChange={f('impact_description')} /></F>
          <F label="פעולה נדרשת"><Txt value={form.action_required} onChange={f('action_required')} /></F>
          <F label="דדליין לפעולה (אופציונלי)"><Inp type="date" value={form.action_deadline} onChange={f('action_deadline')} /></F>
        </div>
        <div className="flex gap-3 p-5 border-t">
          <button onClick={save} disabled={saving || !form.title}
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-hebrew text-sm font-medium disabled:opacity-50 transition">
            <Save size={15} />{saving ? 'שומר...' : 'שמור ושלח התראות'}
          </button>
          <button onClick={onClose} className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-hebrew text-sm transition">ביטול</button>
        </div>
      </div>
    </div>
  );
}

// ─── TAB 2: POLICY CHANGES ─────────────────────────────────────────────────
function AdminPolicyTab() {
  const [changes, setChanges] = useState([]);
  const [allCodes, setAllCodes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [pcRes, codesRes] = await Promise.all([
        ministryAPI.getPolicyChanges(),
        ministryAPI.getCodes(),
      ]);
      setChanges(pcRes.data || []);
      setAllCodes(codesRes.data || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async (data) => {
    await ministryAPI.createPolicyChange(data);
    await load();
  };

  const handleDelete = async (id) => {
    if (!window.confirm('למחוק שינוי מדיניות זה?')) return;
    await ministryAPI.deletePolicyChange(id);
    await load();
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <p className="font-hebrew text-sm text-slate-500">{changes.length} שינויי מדיניות</p>
        <button onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-hebrew text-sm font-medium transition">
          <Plus size={16} />
          הוסף שינוי מדיניות
        </button>
      </div>

      {loading ? <div className="py-12 text-center text-slate-400 font-hebrew">טוען...</div> : (
        <div className="space-y-4">
          {changes.map(pc => {
            const sv = SEVERITY[pc.severity] || SEVERITY.info;
            return (
              <div key={pc.id} className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5" dir="rtl">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span>{sv.icon}</span>
                    <span className={`text-xs font-hebrew font-semibold px-2 py-0.5 rounded-full ${sv.badge}`}>{sv.label}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-hebrew text-slate-400">{fmt(pc.announced_date)}</span>
                    <span className="text-xs font-hebrew text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
                      {pc.acknowledged_count} אישרו קריאה
                    </span>
                    <button onClick={() => handleDelete(pc.id)}
                      className="p-1.5 text-slate-400 hover:text-red-600 rounded hover:bg-red-50 transition">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
                <h3 className="font-hebrew font-bold text-slate-800">{pc.title}</h3>
                {pc.affected_codes?.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {pc.affected_codes.map(c => (
                      <span key={c} className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-hebrew">[{c}]</span>
                    ))}
                  </div>
                )}
                {pc.impact_description && (
                  <p className="text-sm font-hebrew text-slate-500 mt-2 line-clamp-2">{pc.impact_description}</p>
                )}
              </div>
            );
          })}
        </div>
      )}

      {showModal && (
        <PolicyChangeModal allCodes={allCodes} onSave={handleCreate} onClose={() => setShowModal(false)} />
      )}
    </div>
  );
}

// ─── CIRCULAR FORM MODAL ────────────────────────────────────────────────────
function CircularModal({ allCodes, initial = null, onSave, onClose }) {
  const [form, setForm] = useState({
    circular_number: initial?.circular_number || '',
    title: initial?.title || '',
    subject: initial?.subject || '',
    full_content: initial?.full_content || '',
    published_date: initial?.published_date || '',
    effective_date: initial?.effective_date || '',
    expiry_date: initial?.expiry_date || '',
    category: initial?.category || 'כללי',
    affected_codes: initial?.affected_codes || [],
    importance: initial?.importance || 'routine',
    action_required: initial?.action_required || '',
    action_deadline: initial?.action_deadline || '',
    tags: (initial?.tags || []).join(', '),
  });
  const [saving, setSaving] = useState(false);

  const toggleCode = c => setForm(p => ({
    ...p,
    affected_codes: p.affected_codes.includes(c)
      ? p.affected_codes.filter(x => x !== c)
      : [...p.affected_codes, c],
  }));

  const save = async () => {
    setSaving(true);
    try {
      const payload = {
        ...form,
        effective_date: form.effective_date || null,
        expiry_date: form.expiry_date || null,
        action_deadline: form.action_deadline || null,
        tags: form.tags.split(',').map(t => t.trim()).filter(Boolean),
      };
      await onSave(payload);
      onClose();
    } finally { setSaving(false); }
  };

  const f = k => e => setForm(p => ({ ...p, [k]: e.target.value }));

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto" dir="rtl">
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="font-hebrew font-bold text-slate-800">{initial ? 'עריכת חוזר' : 'חוזר חדש'}</h2>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-100"><X size={18} /></button>
        </div>
        <div className="p-5 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <F label={'מספר חוזר (למשל תשפ"ו/3)'}><Inp value={form.circular_number} onChange={f('circular_number')} placeholder='תשפ"ו/4' /></F>
            <F label="קטגוריה">
              <Sel value={form.category} onChange={f('category')}>
                {CIRCULAR_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
              </Sel>
            </F>
          </div>
          <F label="כותרת *"><Inp value={form.title} onChange={f('title')} /></F>
          <F label="תיאור קצר"><Inp value={form.subject} onChange={f('subject')} /></F>
          <F label="תוכן מלא"><Txt rows={8} value={form.full_content} onChange={f('full_content')} /></F>

          <div className="grid grid-cols-2 gap-4">
            <F label="תאריך פרסום"><Inp type="date" value={form.published_date} onChange={f('published_date')} /></F>
            <F label="תאריך כניסה לתוקף"><Inp type="date" value={form.effective_date} onChange={f('effective_date')} /></F>
            <F label="תאריך פקיעה (אופציונלי)"><Inp type="date" value={form.expiry_date} onChange={f('expiry_date')} /></F>
            <F label="חשיבות">
              <Sel value={form.importance} onChange={f('importance')}>
                {Object.entries(IMPORTANCE).map(([k, v]) => <option key={k} value={k}>{v.icon} {v.label}</option>)}
              </Sel>
            </F>
          </div>

          <F label="קודים מושפעים">
            <div className="flex flex-wrap gap-2 p-2 border border-slate-300 rounded-lg min-h-[40px]">
              {allCodes.map(c => (
                <button key={c.code} type="button" onClick={() => toggleCode(c.code)}
                  className={`text-xs font-hebrew px-2 py-1 rounded-full transition ${
                    form.affected_codes.includes(c.code)
                      ? 'bg-blue-600 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}>
                  {c.code} – {c.name_short}
                </button>
              ))}
            </div>
          </F>

          <F label="פעולה נדרשת"><Txt value={form.action_required} onChange={f('action_required')} /></F>
          <F label="דדליין לפעולה"><Inp type="date" value={form.action_deadline} onChange={f('action_deadline')} /></F>
          <F label="תגיות (מופרדות בפסיק)"><Inp value={form.tags} onChange={f('tags')} placeholder="רישום, גני ילדים, תקצוב" /></F>
        </div>
        <div className="flex gap-3 p-5 border-t">
          <button onClick={save} disabled={saving || !form.title}
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-hebrew text-sm font-medium disabled:opacity-50 transition">
            <Save size={15} />{saving ? 'שומר...' : (initial ? 'עדכן' : 'שמור ופרסם')}
          </button>
          <button onClick={onClose} className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-hebrew text-sm transition">ביטול</button>
        </div>
      </div>
    </div>
  );
}

// ─── TAB 3: CIRCULARS ──────────────────────────────────────────────────────
function AdminCircularsTab() {
  const [circulars, setCirculars] = useState([]);
  const [allCodes, setAllCodes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editItem, setEditItem] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const [clRes, codesRes] = await Promise.all([
        ministryAPI.getCirculars(),
        ministryAPI.getCodes(),
      ]);
      setCirculars(clRes.data || []);
      setAllCodes(codesRes.data || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async (data) => {
    await ministryAPI.createCircular(data);
    await load();
  };

  const handleUpdate = async (data) => {
    await ministryAPI.updateCircular(editItem.id, data);
    await load();
  };

  const handleDelete = async (id) => {
    if (!window.confirm('למחוק חוזר זה?')) return;
    await ministryAPI.deleteCircular(id);
    await load();
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <p className="font-hebrew text-sm text-slate-500">{circulars.length} חוזרים</p>
        <button onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-hebrew text-sm font-medium transition">
          <Plus size={16} />
          הוסף חוזר חדש
        </button>
      </div>

      {loading ? <div className="py-12 text-center text-slate-400 font-hebrew">טוען...</div> : (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50 border-b text-right">
                {['מספר', 'כותרת', 'קטגוריה', 'חשיבות', 'פרסום', 'קריאות', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-xs font-hebrew font-semibold text-slate-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {circulars.map(cl => {
                const imp = IMPORTANCE[cl.importance] || IMPORTANCE.routine;
                return (
                  <tr key={cl.id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="px-4 py-3 font-mono text-sm text-blue-700">{cl.circular_number || '—'}</td>
                    <td className="px-4 py-3 font-hebrew text-sm text-slate-700 max-w-[220px] truncate">{cl.title}</td>
                    <td className="px-4 py-3 text-xs font-hebrew text-slate-500">{cl.category}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-hebrew font-semibold px-2 py-0.5 rounded-full ${imp.badge}`}>
                        {imp.icon} {imp.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs font-hebrew text-slate-500">{fmt(cl.published_date)}</td>
                    <td className="px-4 py-3">
                      <span className="flex items-center gap-1 text-xs text-slate-500 font-hebrew">
                        <Eye size={12} />{cl.read_count}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <button onClick={() => setEditItem(cl)}
                          className="p-1.5 text-slate-400 hover:text-blue-600 rounded hover:bg-blue-50 transition"><Edit3 size={14} /></button>
                        <button onClick={() => handleDelete(cl.id)}
                          className="p-1.5 text-slate-400 hover:text-red-600 rounded hover:bg-red-50 transition"><Trash2 size={14} /></button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {(showModal || editItem) && (
        <CircularModal
          allCodes={allCodes}
          initial={editItem}
          onSave={editItem ? handleUpdate : handleCreate}
          onClose={() => { setShowModal(false); setEditItem(null); }}
        />
      )}
    </div>
  );
}

// ─── TAB 4: STATS ──────────────────────────────────────────────────────────
function StatsTab() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    ministryAPI.getStats()
      .then(r => setStats(r.data))
      .catch(() => setStats(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="py-12 text-center text-slate-400 font-hebrew">טוען...</div>;
  if (!stats) return <div className="py-12 text-center text-slate-400 font-hebrew">שגיאה בטעינה</div>;

  return (
    <div className="space-y-6" dir="rtl">
      {/* Top codes */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100">
          <h3 className="font-hebrew font-bold text-slate-800">📊 קודים הנצפים ביותר</h3>
        </div>
        {stats.top_codes.length === 0 ? (
          <p className="p-5 text-center text-slate-400 font-hebrew text-sm">אף קוד עדיין לא נצפה</p>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50 border-b text-right">
                <th className="px-5 py-3 text-xs font-hebrew font-semibold text-slate-500">קוד</th>
                <th className="px-5 py-3 text-xs font-hebrew font-semibold text-slate-500">שם</th>
                <th className="px-5 py-3 text-xs font-hebrew font-semibold text-slate-500">צפיות</th>
              </tr>
            </thead>
            <tbody>
              {stats.top_codes.map((r, i) => (
                <tr key={i} className="border-b border-slate-100">
                  <td className="px-5 py-3 font-bold text-slate-700 font-hebrew">{r.code}</td>
                  <td className="px-5 py-3 font-hebrew text-sm text-slate-600">{r.name}</td>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-slate-100 rounded-full h-1.5 max-w-[80px]">
                        <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${Math.min(100, (r.views / (stats.top_codes[0]?.views || 1)) * 100)}%` }} />
                      </div>
                      <span className="text-sm text-slate-600 font-hebrew">{r.views}</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Circular read rates */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="font-hebrew font-bold text-slate-800">📋 קריאת חוזרים ({stats.total_municipalities} רשויות)</h3>
        </div>
        {stats.circular_stats.length === 0 ? (
          <p className="p-5 text-center text-slate-400 font-hebrew text-sm">אין חוזרים</p>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50 border-b text-right">
                {['חוזר', 'פרסום', 'חשיבות', 'קראו', 'לא קראו'].map(h => (
                  <th key={h} className="px-4 py-3 text-xs font-hebrew font-semibold text-slate-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {stats.circular_stats.map(cl => {
                const imp = IMPORTANCE[cl.importance] || IMPORTANCE.routine;
                return (
                  <tr key={cl.id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="px-4 py-3 font-hebrew text-sm text-slate-700 max-w-[200px] truncate">
                      {cl.circular_number && <span className="font-mono text-blue-600 mr-1">{cl.circular_number}</span>}
                      {cl.title}
                    </td>
                    <td className="px-4 py-3 text-xs font-hebrew text-slate-500">{fmt(cl.published_date)}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-hebrew font-semibold px-2 py-0.5 rounded-full ${imp.badge}`}>{imp.icon} {imp.label}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm font-hebrew text-green-700 font-bold">{cl.read_count}</span>
                    </td>
                    <td className="px-4 py-3">
                      {cl.unread_count > 0 ? (
                        <span className="text-sm font-hebrew text-red-600 font-bold">{cl.unread_count}</span>
                      ) : (
                        <span className="text-xs font-hebrew text-green-600">✅ הכל</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ─── MAIN PAGE ──────────────────────────────────────────────────────────────
export default function AdminMinistryPage() {
  const [activeTab, setActiveTab] = useState('codes');

  return (
    <PageWrapper title="משרד החינוך">
      <div dir="rtl" className="max-w-6xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-hebrew font-bold text-slate-800">🏛️ משרד החינוך</h1>
          <p className="font-hebrew text-sm text-slate-500 mt-1">ניהול קודי תקצוב, שינויי מדיניות וחוזרי מנכ"ל</p>
        </div>

        {/* Tabs */}
        <div className="border-b border-slate-200 flex gap-1">
          {TABS.map(tab => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-5 py-3 font-hebrew text-sm font-medium border-b-2 transition -mb-px ${
                  activeTab === tab.id
                    ? 'border-blue-600 text-blue-700'
                    : 'border-transparent text-slate-500 hover:text-slate-700'
                }`}
              >
                <Icon size={16} />
                {tab.label}
              </button>
            );
          })}
        </div>

        {activeTab === 'codes'     && <AdminCodesTab />}
        {activeTab === 'policy'    && <AdminPolicyTab />}
        {activeTab === 'circulars' && <AdminCircularsTab />}
        {activeTab === 'stats'     && <StatsTab />}
      </div>
    </PageWrapper>
  );
}
