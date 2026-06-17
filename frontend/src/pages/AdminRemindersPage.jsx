import React, { useState, useEffect, useCallback } from 'react';
import PageWrapper from '../components/layout/PageWrapper';
import { remindersAPI, municipalityAPI } from '../services/api';
import { Bell, Calendar, Settings, Plus, Edit3, Trash2, Save, X, Check, ChevronDown, ChevronUp, Filter } from 'lucide-react';

// ─── HELPERS ──────────────────────────────────────────────────────────────────
const TABS = [
  { id: 'deadlines', label: 'מועדי הגשה', icon: Calendar },
  { id: 'status', label: 'סטטוס תזכורות', icon: Bell },
  { id: 'settings', label: 'הגדרות', icon: Settings },
];

const STATUS_LABELS = {
  pending: { label: 'ממתין', class: 'bg-blue-100 text-blue-700' },
  sent:    { label: 'נשלח', class: 'bg-green-100 text-green-700' },
  failed:  { label: 'נכשל', class: 'bg-red-100 text-red-700' },
  dismissed: { label: 'בוטל', class: 'bg-slate-100 text-slate-600' },
};

const REMINDER_DAY_OPTIONS = [1, 3, 7, 14, 30, 60];

const MONTH_OPTIONS = [
  { v: '1', l: 'ינואר' }, { v: '2', l: 'פברואר' }, { v: '3', l: 'מרץ' },
  { v: '4', l: 'אפריל' }, { v: '5', l: 'מאי' }, { v: '6', l: 'יוני' },
  { v: '7', l: 'יולי' }, { v: '8', l: 'אוגוסט' }, { v: '9', l: 'ספטמבר' },
  { v: '10', l: 'אוקטובר' }, { v: '11', l: 'נובמבר' }, { v: '12', l: 'דצמבר' },
];

function urgencyBadge(days) {
  if (days === null || days === undefined) return <span className="text-slate-400">—</span>;
  if (days <= 1) return <span className="bg-red-100 text-red-700 text-xs font-hebrew px-2 py-0.5 rounded-full">🚨 {days <= 0 ? 'עבר' : 'מחר'}</span>;
  if (days <= 7) return <span className="bg-amber-100 text-amber-700 text-xs font-hebrew px-2 py-0.5 rounded-full">⚠️ {days} ימים</span>;
  if (days <= 30) return <span className="bg-blue-100 text-blue-700 text-xs font-hebrew px-2 py-0.5 rounded-full">📋 {days} ימים</span>;
  return <span className="bg-slate-100 text-slate-600 text-xs font-hebrew px-2 py-0.5 rounded-full">{days} ימים</span>;
}

// ─── DEADLINE FORM ────────────────────────────────────────────────────────────
function DeadlineForm({ initial, onSave, onCancel }) {
  const [form, setForm] = useState(() => ({
    title: initial?.title ?? '',
    description: initial?.description ?? '',
    deadline_type: initial?.deadline_type ?? 'annual',
    deadline_month: initial?.deadline_month ?? '7',
    deadline_day: initial?.deadline_day ?? 31,
    reminder_days_before: initial?.reminder_days_before ?? [30, 14, 7, 1],
    topic_codes: (initial?.topic_codes ?? ['all']).join(', '),
    applies_to: initial?.applies_to ?? 'all',
    ministry_reference: initial?.ministry_reference ?? '',
    action_required: initial?.action_required ?? '',
    is_active: initial?.is_active ?? true,
  }));
  const [saving, setSaving] = useState(false);

  const toggleDay = (day) => {
    setForm(f => ({
      ...f,
      reminder_days_before: f.reminder_days_before.includes(day)
        ? f.reminder_days_before.filter(d => d !== day)
        : [...f.reminder_days_before, day].sort((a, b) => b - a),
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {
        ...form,
        deadline_day: Number(form.deadline_day),
        topic_codes: form.topic_codes.split(',').map(s => s.trim()).filter(Boolean),
      };
      await onSave(payload);
    } finally {
      setSaving(false);
    }
  };

  const f = (key) => (e) => setForm(prev => ({ ...prev, [key]: e.target.value }));

  return (
    <div className="space-y-4" dir="rtl">
      <div className="grid grid-cols-1 gap-4">
        <div>
          <label className="block text-xs font-hebrew font-semibold text-slate-600 mb-1">כותרת *</label>
          <input className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-hebrew focus:outline-none focus:ring-2 focus:ring-blue-400" value={form.title} onChange={f('title')} placeholder="הגשת בקשת תקן..." />
        </div>

        <div>
          <label className="block text-xs font-hebrew font-semibold text-slate-600 mb-1">תיאור</label>
          <textarea className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-hebrew focus:outline-none focus:ring-2 focus:ring-blue-400 h-20" value={form.description} onChange={f('description')} />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-hebrew font-semibold text-slate-600 mb-1">סוג מועד</label>
            <select className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-hebrew" value={form.deadline_type} onChange={f('deadline_type')}>
              <option value="annual">שנתי</option>
              <option value="quarterly">רבעוני</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-hebrew font-semibold text-slate-600 mb-1">חל על</label>
            <select className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-hebrew" value={form.applies_to} onChange={f('applies_to')}>
              <option value="all">כל הרשויות</option>
              <option value="grant_municipalities">רשויות עם מענק</option>
              <option value="no_grant">רשויות ללא מענק</option>
            </select>
          </div>
        </div>

        {form.deadline_type === 'annual' && (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-hebrew font-semibold text-slate-600 mb-1">חודש</label>
              <select className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-hebrew" value={form.deadline_month} onChange={f('deadline_month')}>
                {MONTH_OPTIONS.map(m => <option key={m.v} value={m.v}>{m.l}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-hebrew font-semibold text-slate-600 mb-1">יום</label>
              <input type="number" min={1} max={31} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-hebrew" value={form.deadline_day} onChange={f('deadline_day')} />
            </div>
          </div>
        )}

        <div>
          <label className="block text-xs font-hebrew font-semibold text-slate-600 mb-2">לוח תזכורות (ימים לפני)</label>
          <div className="flex flex-wrap gap-2">
            {REMINDER_DAY_OPTIONS.map(day => (
              <button
                key={day}
                type="button"
                onClick={() => toggleDay(day)}
                className={`px-3 py-1.5 rounded-lg text-sm font-hebrew font-medium transition ${
                  form.reminder_days_before.includes(day)
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {day} ימים
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-hebrew font-semibold text-slate-600 mb-1">קודי נושא (מופרדים בפסיק)</label>
            <input className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-mono" value={form.topic_codes} onChange={f('topic_codes')} placeholder="19, 3, 45" />
          </div>
          <div>
            <label className="block text-xs font-hebrew font-semibold text-slate-600 mb-1">מקור משרד החינוך</label>
            <input className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-hebrew" value={form.ministry_reference} onChange={f('ministry_reference')} placeholder="חוברת התקצוב עמ' 48" />
          </div>
        </div>

        <div>
          <label className="block text-xs font-hebrew font-semibold text-slate-600 mb-1">מה צריך לעשות</label>
          <textarea className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-hebrew h-20" value={form.action_required} onChange={f('action_required')} placeholder="הגש טופס בקשה ל..." />
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setForm(f => ({ ...f, is_active: !f.is_active }))}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${form.is_active ? 'bg-green-500' : 'bg-slate-300'}`}
          >
            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${form.is_active ? 'translate-x-1' : 'translate-x-6'}`} />
          </button>
          <span className="font-hebrew text-sm text-slate-600">{form.is_active ? 'פעיל' : 'לא פעיל'}</span>
        </div>
      </div>

      <div className="flex gap-3 pt-4 border-t border-slate-100">
        <button onClick={handleSave} disabled={saving || !form.title}
          className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-hebrew text-sm font-medium transition disabled:opacity-50">
          <Save size={16} />
          {saving ? 'שומר...' : 'שמור'}
        </button>
        <button onClick={onCancel}
          className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-hebrew text-sm font-medium transition">
          ביטול
        </button>
      </div>
    </div>
  );
}

// ─── TAB: DEADLINES ──────────────────────────────────────────────────────────
function DeadlinesTab() {
  const [deadlines, setDeadlines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editTarget, setEditTarget] = useState(null);
  const [expandedRows, setExpandedRows] = useState(new Set());

  const load = async () => {
    setLoading(true);
    try { setDeadlines((await remindersAPI.getDeadlines()).data || []); }
    catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async (data) => {
    await remindersAPI.createDeadline(data);
    setShowForm(false);
    await load();
  };

  const handleUpdate = async (data) => {
    await remindersAPI.updateDeadline(editTarget.id, data);
    setEditTarget(null);
    await load();
  };

  const handleDeactivate = async (id) => {
    if (!window.confirm('להשבית מועד זה?')) return;
    await remindersAPI.deleteDeadline(id);
    await load();
  };

  const toggleRow = id => setExpandedRows(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });

  if (loading) return <div className="py-12 text-center text-slate-400 font-hebrew">טוען...</div>;

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <p className="font-hebrew text-sm text-slate-500">{deadlines.length} מועדים רשומים</p>
        <button
          onClick={() => { setEditTarget(null); setShowForm(s => !s); }}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-hebrew text-sm font-medium transition"
        >
          <Plus size={16} />
          הוסף מועד חדש
        </button>
      </div>

      {showForm && !editTarget && (
        <div className="bg-blue-50 border border-blue-200 rounded-2xl p-6">
          <h3 className="font-hebrew font-semibold text-blue-800 mb-4">מועד חדש</h3>
          <DeadlineForm onSave={handleCreate} onCancel={() => setShowForm(false)} />
        </div>
      )}

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200 text-right">
              <th className="px-4 py-3 font-hebrew text-xs font-semibold text-slate-500">נושא</th>
              <th className="px-4 py-3 font-hebrew text-xs font-semibold text-slate-500">סוג</th>
              <th className="px-4 py-3 font-hebrew text-xs font-semibold text-slate-500">מועד הבא</th>
              <th className="px-4 py-3 font-hebrew text-xs font-semibold text-slate-500">ימים שנותרו</th>
              <th className="px-4 py-3 font-hebrew text-xs font-semibold text-slate-500">סטטוס</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {deadlines.map(dl => {
              const isExpanded = expandedRows.has(dl.id);
              const isEditThis = editTarget?.id === dl.id;
              const nd = dl.next_deadline_date ? new Date(dl.next_deadline_date).toLocaleDateString('he-IL') : '—';

              return (
                <React.Fragment key={dl.id}>
                  <tr className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <span className="font-hebrew text-sm text-slate-800 font-medium">{dl.title}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs font-hebrew text-slate-500">{dl.deadline_type === 'quarterly' ? 'רבעוני' : 'שנתי'}</span>
                    </td>
                    <td className="px-4 py-3 font-hebrew text-sm text-slate-600">{nd}</td>
                    <td className="px-4 py-3">{urgencyBadge(dl.days_until)}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-hebrew px-2 py-0.5 rounded-full ${dl.is_active ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'}`}>
                        {dl.is_active ? '✅ פעיל' : '⏸ לא פעיל'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <button onClick={() => { setEditTarget(dl); setShowForm(true); }} className="p-1.5 text-slate-400 hover:text-blue-600 rounded hover:bg-blue-50 transition" title="עריכה">
                          <Edit3 size={15} />
                        </button>
                        <button onClick={() => handleDeactivate(dl.id)} className="p-1.5 text-slate-400 hover:text-red-600 rounded hover:bg-red-50 transition" title="השבת">
                          <Trash2 size={15} />
                        </button>
                        <button onClick={() => toggleRow(dl.id)} className="p-1.5 text-slate-400 hover:text-slate-600 rounded hover:bg-slate-100 transition">
                          {isExpanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
                        </button>
                      </div>
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr className="bg-slate-50">
                      <td colSpan={6} className="px-6 py-4 border-b border-slate-100">
                        {isEditThis ? (
                          <DeadlineForm initial={editTarget} onSave={handleUpdate} onCancel={() => setEditTarget(null)} />
                        ) : (
                          <div className="space-y-2 text-right" dir="rtl">
                            {dl.description && <p className="font-hebrew text-sm text-slate-600">{dl.description}</p>}
                            {dl.action_required && (
                              <div className="bg-blue-50 rounded-lg p-3">
                                <p className="font-hebrew text-xs font-semibold text-blue-700 mb-1">📋 מה צריך לעשות:</p>
                                <p className="font-hebrew text-sm text-blue-800">{dl.action_required}</p>
                              </div>
                            )}
                            <div className="flex flex-wrap gap-4 text-xs text-slate-400 font-hebrew">
                              {dl.ministry_reference && <span>📖 {dl.ministry_reference}</span>}
                              <span>⏰ תזכורות: {dl.reminder_days_before?.join(', ')} ימים לפני</span>
                              {dl.topic_codes && !dl.topic_codes.includes('all') && (
                                <span>קודים: {dl.topic_codes.join(', ')}</span>
                              )}
                            </div>
                          </div>
                        )}
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
  );
}

// ─── TAB: STATUS ──────────────────────────────────────────────────────────────
function StatusTab({ municipalities }) {
  const [reminders, setReminders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({ status: '', municipality_id: '' });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (filter.status) params.status_filter = filter.status;
      if (filter.municipality_id) params.municipality_id = filter.municipality_id;
      setReminders((await remindersAPI.adminAll(params)).data || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <select
          className="border border-slate-300 rounded-lg px-3 py-2 text-sm font-hebrew"
          value={filter.status}
          onChange={e => setFilter(f => ({ ...f, status: e.target.value }))}
        >
          <option value="">כל הסטטוסים</option>
          <option value="pending">ממתין</option>
          <option value="sent">נשלח</option>
          <option value="failed">נכשל</option>
          <option value="dismissed">בוטל</option>
        </select>

        <select
          className="border border-slate-300 rounded-lg px-3 py-2 text-sm font-hebrew"
          value={filter.municipality_id}
          onChange={e => setFilter(f => ({ ...f, municipality_id: e.target.value }))}
        >
          <option value="">כל הרשויות</option>
          {municipalities.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
        </select>

        <button onClick={load} className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-sm font-hebrew transition flex items-center gap-1">
          <Filter size={14} />
          סנן
        </button>
      </div>

      {loading ? (
        <div className="py-12 text-center text-slate-400 font-hebrew">טוען...</div>
      ) : (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-right">
                  <th className="px-4 py-3 font-hebrew text-xs font-semibold text-slate-500">רשות</th>
                  <th className="px-4 py-3 font-hebrew text-xs font-semibold text-slate-500">מועד</th>
                  <th className="px-4 py-3 font-hebrew text-xs font-semibold text-slate-500">תזכורת</th>
                  <th className="px-4 py-3 font-hebrew text-xs font-semibold text-slate-500">ימים לפני</th>
                  <th className="px-4 py-3 font-hebrew text-xs font-semibold text-slate-500">תאריך שליחה</th>
                  <th className="px-4 py-3 font-hebrew text-xs font-semibold text-slate-500">סטטוס</th>
                </tr>
              </thead>
              <tbody>
                {reminders.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-slate-400 font-hebrew text-sm">אין תזכורות</td>
                  </tr>
                ) : reminders.map(r => {
                  const s = STATUS_LABELS[r.status] || { label: r.status, class: 'bg-slate-100 text-slate-600' };
                  return (
                    <tr key={r.id} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="px-4 py-3 font-hebrew text-sm text-slate-800">{r.municipality_name}</td>
                      <td className="px-4 py-3 font-hebrew text-sm text-slate-600 max-w-[200px] truncate">{r.deadline_title}</td>
                      <td className="px-4 py-3 font-hebrew text-sm text-slate-600">{r.reminder_date}</td>
                      <td className="px-4 py-3">
                        <span className="text-xs font-hebrew text-slate-500">{r.days_before} ימים</span>
                      </td>
                      <td className="px-4 py-3 font-hebrew text-sm text-slate-500">
                        {r.sent_at ? new Date(r.sent_at).toLocaleDateString('he-IL') : r.dismissed_at ? new Date(r.dismissed_at).toLocaleDateString('he-IL') : '—'}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs font-hebrew px-2 py-0.5 rounded-full ${s.class}`}>{s.label}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── TAB: SETTINGS ────────────────────────────────────────────────────────────
function SettingsTab({ municipalities }) {
  const [global, setGlobal] = useState({ email_enabled: true, in_app_enabled: true, whatsapp_enabled: false });
  const [perMuni, setPerMuni] = useState([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const loadSettings = useCallback(async () => {
    try {
      const [gRes, mRes] = await Promise.all([
        remindersAPI.getSettings(),
        remindersAPI.getAllMunicipalitySettings(),
      ]);
      const g = gRes.data || {};
      setGlobal({
        email_enabled: g.email_enabled ?? true,
        in_app_enabled: g.in_app_enabled ?? true,
        whatsapp_enabled: g.whatsapp_enabled ?? false,
      });
      setPerMuni(mRes.data || []);
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => { loadSettings(); }, [loadSettings]);

  const handleSaveGlobal = async () => {
    setSaving(true);
    try {
      await remindersAPI.saveSettings(global);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } finally {
      setSaving(false);
    }
  };

  const handleSaveMuni = async (muniId, data) => {
    await remindersAPI.saveSettings(data, muniId);
    await loadSettings();
  };

  const Toggle = ({ value, onChange }) => (
    <button
      type="button"
      onClick={() => onChange(!value)}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${value ? 'bg-green-500' : 'bg-slate-300'}`}
    >
      <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${value ? '-translate-x-1' : 'translate-x-6'}`} />
    </button>
  );

  return (
    <div className="space-y-6">
      {/* Global Settings */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6" dir="rtl">
        <h3 className="font-hebrew font-bold text-slate-800 text-lg mb-5">⚙️ הגדרות גלובליות</h3>
        <div className="space-y-4">
          {[
            { key: 'email_enabled', label: 'שליחת תזכורות באימייל', desc: 'שולח אימייל HTML לאנשי הקשר בכל רשות' },
            { key: 'in_app_enabled', label: 'התראות בתוך המערכת', desc: 'מציג התראות בעמוד הפורטל של הרשות' },
            { key: 'whatsapp_enabled', label: 'שליחה בוואטסאפ', desc: 'שליחת הודעות WhatsApp (דורש הגדרה נוספת)' },
          ].map(({ key, label, desc }) => (
            <div key={key} className="flex items-center justify-between py-3 border-b border-slate-100">
              <div>
                <p className="font-hebrew font-medium text-slate-800 text-sm">{label}</p>
                <p className="font-hebrew text-xs text-slate-400">{desc}</p>
              </div>
              <Toggle value={global[key]} onChange={v => setGlobal(g => ({ ...g, [key]: v }))} />
            </div>
          ))}
        </div>
        <button
          onClick={handleSaveGlobal}
          disabled={saving}
          className="mt-5 flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-hebrew text-sm font-medium transition disabled:opacity-50"
        >
          {saved ? <><Check size={16} /> נשמר!</> : <><Save size={16} />{saving ? 'שומר...' : 'שמור הגדרות'}</>}
        </button>
      </div>

      {/* Per-municipality */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100">
          <h3 className="font-hebrew font-bold text-slate-800 text-lg">🏛 הגדרות לכל רשות</h3>
          <p className="font-hebrew text-xs text-slate-400 mt-1">email ריק = שימוש באימייל המשתמש של הרשות</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-right">
                <th className="px-4 py-3 font-hebrew text-xs font-semibold text-slate-500">רשות</th>
                <th className="px-4 py-3 font-hebrew text-xs font-semibold text-slate-500">אימייל מותאם</th>
                <th className="px-4 py-3 font-hebrew text-xs font-semibold text-slate-500">אימייל</th>
                <th className="px-4 py-3 font-hebrew text-xs font-semibold text-slate-500">התראות</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {perMuni.map(m => (
                <PerMuniRow key={m.municipality_id} muni={m} onSave={handleSaveMuni} />
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function PerMuniRow({ muni, onSave }) {
  const [emailEnabled, setEmailEnabled] = useState(muni.email_enabled);
  const [inAppEnabled, setInAppEnabled] = useState(muni.in_app_enabled);
  const [contactEmail, setContactEmail] = useState(muni.contact_email || '');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(muni.municipality_id, {
        email_enabled: emailEnabled,
        in_app_enabled: inAppEnabled,
        contact_email: contactEmail || null,
      });
    } finally {
      setSaving(false);
    }
  };

  const Toggle = ({ value, onChange }) => (
    <button
      type="button"
      onClick={() => onChange(!value)}
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${value ? 'bg-green-500' : 'bg-slate-300'}`}
    >
      <span className={`inline-block h-3 w-3 transform rounded-full bg-white transition ${value ? '-translate-x-1' : 'translate-x-5'}`} />
    </button>
  );

  return (
    <tr className="border-b border-slate-100 hover:bg-slate-50">
      <td className="px-4 py-2.5 font-hebrew text-sm text-slate-800">{muni.municipality_name}</td>
      <td className="px-4 py-2.5">
        <input
          className="border border-slate-300 rounded px-2 py-1 text-xs w-48 font-hebrew"
          value={contactEmail}
          onChange={e => setContactEmail(e.target.value)}
          placeholder="default@email.com"
          dir="ltr"
        />
      </td>
      <td className="px-4 py-2.5"><Toggle value={emailEnabled} onChange={setEmailEnabled} /></td>
      <td className="px-4 py-2.5"><Toggle value={inAppEnabled} onChange={setInAppEnabled} /></td>
      <td className="px-4 py-2.5">
        <button onClick={handleSave} disabled={saving}
          className="text-xs font-hebrew text-blue-600 hover:text-blue-800 px-2 py-1 rounded hover:bg-blue-50 transition">
          {saving ? '...' : 'שמור'}
        </button>
      </td>
    </tr>
  );
}

// ─── MAIN PAGE ────────────────────────────────────────────────────────────────
export default function AdminRemindersPage() {
  const [activeTab, setActiveTab] = useState('deadlines');
  const [municipalities, setMunicipalities] = useState([]);

  useEffect(() => {
    municipalityAPI.getAll().then(r => setMunicipalities(r.data || [])).catch(() => {});
  }, []);

  return (
    <PageWrapper title="תזכורות ומועדים">
      <div dir="rtl" className="max-w-6xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-hebrew font-bold text-slate-800">🔔 תזכורות ומועדים</h1>
          <p className="font-hebrew text-sm text-slate-500 mt-1">ניהול מועדי הגשה ותזכורות אוטומטיות לרשויות</p>
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

        {/* Tab Content */}
        {activeTab === 'deadlines' && <DeadlinesTab />}
        {activeTab === 'status' && <StatusTab municipalities={municipalities} />}
        {activeTab === 'settings' && <SettingsTab municipalities={municipalities} />}
      </div>
    </PageWrapper>
  );
}
