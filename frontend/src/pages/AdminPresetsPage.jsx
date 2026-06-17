import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { reasonsAPI } from '../services/api';

export default function AdminPresetsPage() {
  console.log('[AdminPresetsPage] render', { path: window.location.pathname });

  const navigate = useNavigate();
  const [reasons, setReasons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [filterCategory, setFilterCategory] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [formData, setFormData] = useState({
    code: '',
    title_hebrew: '',
    category: 'ילדים',
    explanation_template: '',
    topic_codes: ['3'],
    direction: 'neutral',
    severity: 'routine',
    requires_detail: false,
    detail_prompt: '',
    sort_order: 999
  });
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState('');

  const CATEGORIES = ['ילדים', 'משרות', 'שכר', 'גן', 'רטרו', 'תיקון', 'מדיניות', 'משפטי', 'אחר'];
  const TOPIC_CODES = ['3', '19', '33', 'all'];
  const DIRECTIONS = ['increase', 'decrease', 'neutral'];
  const SEVERITIES = ['routine', 'attention', 'urgent'];

  const categoryIcons = {
    'ילדים': '👶', 'משרות': '💼', 'שכר': '💰', 'גן': '🏫',
    'רטרו': '↩️', 'תיקון': '🔧', 'מדיניות': '📋', 'משפטי': '⚖️', 'אחר': '❓'
  };

  useEffect(() => {
    console.log('Presets Page Mounted');
    loadReasons();
  }, []);

  const loadReasons = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await reasonsAPI.getAll({ active_only: false });
      const payload = res?.data;
      const normalizedReasons = Array.isArray(payload)
        ? payload
        : Array.isArray(payload?.items)
          ? payload.items
          : Array.isArray(payload?.data)
            ? payload.data
          : Array.isArray(payload?.results)
            ? payload.results
            : [];

      if (!Array.isArray(payload)) {
        console.warn('[AdminPresetsPage] Unexpected reasons payload shape, normalized to array', payload);
      }

      setReasons(normalizedReasons);
    } catch (err) {
      setError('שגיאה בטעינת נתונים');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddReason = async () => {
    try {
      if (!formData.code.trim()) {
        setError('חובה להזין קוד');
        return;
      }
      if (!formData.title_hebrew.trim()) {
        setError('חובה להזין כותרת בעברית');
        return;
      }
      if (!formData.explanation_template.trim()) {
        setError('חובה להזין תבנית הסבר');
        return;
      }
      if (formData.requires_detail && !formData.detail_prompt.trim()) {
        setError('חובה להזין את טקסט השאלה לפרטים');
        return;
      }

      setSubmitting(true);
      if (editingId) {
        await reasonsAPI.update(editingId, formData);
        setSuccess('✅ סיבה עודכנה בהצלחה');
      } else {
        await reasonsAPI.create(formData);
        setSuccess('✅ סיבה חדשה נוספה בהצלחה');
      }

      setTimeout(() => {
        setSuccess('');
        resetForm();
        loadReasons();
      }, 2000);
    } catch (err) {
      setError(err.response?.data?.detail || 'שגיאה בשמירה');
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteReason = async (reasonId) => {
    if (!window.confirm('בטוח שברצונך למחוק סיבה זו?')) return;

    try {
      setSubmitting(true);
      await reasonsAPI.delete(reasonId);
      setSuccess('✅ סיבה מחוקה בהצלחה');
      setTimeout(() => {
        setSuccess('');
        loadReasons();
      }, 2000);
    } catch (err) {
      setError('שגיאה במחיקה');
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleEditReason = (reason) => {
    setFormData(reason);
    setEditingId(reason.id);
    setShowAddForm(true);
  };

  const resetForm = () => {
    setFormData({
      code: '',
      title_hebrew: '',
      category: 'ילדים',
      explanation_template: '',
      topic_codes: ['3'],
      direction: 'neutral',
      severity: 'routine',
      requires_detail: false,
      detail_prompt: '',
      sort_order: 999
    });
    setEditingId(null);
    setShowAddForm(false);
    setError(null);
  };

  const groupedReasons = (Array.isArray(reasons) ? reasons : []).reduce((acc, reason) => {
    const cat = reason.category;
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(reason);
    return acc;
  }, {});

  const filteredGroups = filterCategory 
    ? { [filterCategory]: groupedReasons[filterCategory] || [] }
    : groupedReasons;

  const hasReasons = Object.values(filteredGroups).some((group) => Array.isArray(group) && group.length > 0);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-gray-50">
      {/* Header */}
      <div className="sticky top-0 z-40 bg-gradient-to-r from-slate-900 to-slate-800 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8 flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-300 font-hebrew mb-2">לוח בקרה / ניהול / ספריית סיבות</p>
            <h1 className="text-3xl font-bold text-white font-hebrew">📚 ספריית סיבות</h1>
            <p className="text-slate-300 font-hebrew text-sm mt-1">דירוג וניהול של סיבות לשינויים בתקציב</p>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={() => resetForm()}
              className="px-4 py-2 bg-white text-slate-900 font-hebrew font-semibold rounded-lg hover:bg-slate-100 transition"
            >
              ➕ הוסף סיבה חדשה
            </button>
            <button
              onClick={() => navigate('/dashboard')}
              className="px-4 py-2 bg-slate-700 text-white font-hebrew font-semibold rounded-lg hover:bg-slate-600 transition"
            >
              ← חזור
            </button>
          </div>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Messages */}
        {success && (
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg mb-6 text-green-700 font-hebrew font-semibold">
            {success}
          </div>
        )}
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg mb-6 text-red-700 font-hebrew font-semibold">
            ❌ {error}
          </div>
        )}

        {/* Add/Edit Form */}
        {showAddForm && (
          <div className="bg-white rounded-xl shadow-lg p-8 mb-8 border border-slate-200">
            <h2 className="text-2xl font-hebrew font-bold text-slate-900 mb-6">
              {editingId ? '✏️ עדכון סיבה' : '➕ סיבה חדשה'}
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-hebrew font-semibold text-slate-900 mb-2">
                  קוד (יחיד)
                </label>
                <input
                  type="text"
                  value={formData.code}
                  onChange={(e) => setFormData({...formData, code: e.target.value})}
                  disabled={editingId}
                  placeholder="KID_REG_NEW"
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg font-hebrew resize-none disabled:bg-slate-100"
                />
              </div>
              <div>
                <label className="block text-sm font-hebrew font-semibold text-slate-900 mb-2">
                  כותרת בעברית
                </label>
                <input
                  type="text"
                  value={formData.title_hebrew}
                  onChange={(e) => setFormData({...formData, title_hebrew: e.target.value})}
                  placeholder="ילד/ה חדש/ה נרשמ/ה"
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg font-hebrew"
                />
              </div>
              <div>
                <label className="block text-sm font-hebrew font-semibold text-slate-900 mb-2">
                  קטגוריה
                </label>
                <select
                  value={formData.category}
                  onChange={(e) => setFormData({...formData, category: e.target.value})}
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg font-hebrew"
                >
                  {CATEGORIES.map(cat => (
                    <option key={cat} value={cat}>{categoryIcons[cat]} {cat}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-hebrew font-semibold text-slate-900 mb-2">
                  כיוון
                </label>
                <select
                  value={formData.direction}
                  onChange={(e) => setFormData({...formData, direction: e.target.value})}
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg font-hebrew"
                >
                  {DIRECTIONS.map(dir => (
                    <option key={dir} value={dir}>
                      {dir === 'increase' ? '📈 עלייה' : dir === 'decrease' ? '📉 ירידה' : '⚪ ניטרלי'}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-hebrew font-semibold text-slate-900 mb-2">
                  חומרה
                </label>
                <select
                  value={formData.severity}
                  onChange={(e) => setFormData({...formData, severity: e.target.value})}
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg font-hebrew"
                >
                  {SEVERITIES.map(sev => (
                    <option key={sev} value={sev}>
                      {sev === 'routine' ? '🟢 שגרה' : sev === 'attention' ? '🟡 לתשומת לב' : '🔴 דחוף'}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-hebrew font-semibold text-slate-900 mb-2">
                  קודי תקציב
                </label>
                <div className="flex flex-wrap gap-2">
                  {TOPIC_CODES.map(code => (
                    <label key={code} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.topic_codes.includes(code)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setFormData({...formData, topic_codes: [...formData.topic_codes, code]});
                          } else {
                            setFormData({...formData, topic_codes: formData.topic_codes.filter(c => c !== code)});
                          }
                        }}
                        className="w-4 h-4"
                      />
                      <span className="font-hebrew text-sm">{code}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-hebrew font-semibold text-slate-900 mb-2">
                  תבנית הסבר
                </label>
                <textarea
                  value={formData.explanation_template}
                  onChange={(e) => setFormData({...formData, explanation_template: e.target.value})}
                  placeholder="כתוב תבנית הסבר..."
                  rows={4}
                  maxLength={500}
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg font-hebrew text-right resize-none"
                />
                <p className="text-xs text-slate-500 mt-1 font-hebrew">
                  {formData.explanation_template.length} / 500
                </p>
              </div>
              <div className="md:col-span-2">
                <label className="flex items-center gap-2 cursor-pointer mb-2">
                  <input
                    type="checkbox"
                    checked={formData.requires_detail}
                    onChange={(e) => setFormData({...formData, requires_detail: e.target.checked})}
                    className="w-4 h-4"
                  />
                  <span className="font-hebrew font-semibold text-slate-900">דרוש פרט נוסף</span>
                </label>
                {formData.requires_detail && (
                  <input
                    type="text"
                    value={formData.detail_prompt}
                    onChange={(e) => setFormData({...formData, detail_prompt: e.target.value})}
                    placeholder="למשל: כמה ילדים נוספו?"
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg font-hebrew mt-2"
                  />
                )}
              </div>
            </div>
            <div className="flex gap-4 mt-6">
              <button
                onClick={handleAddReason}
                disabled={submitting}
                className="flex-1 px-6 py-3 bg-blue-600 text-white font-hebrew font-bold rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
              >
                {submitting ? 'שומר...' : editingId ? 'עדכן' : 'הוסף'}
              </button>
              <button
                onClick={resetForm}
                disabled={submitting}
                className="flex-1 px-6 py-3 bg-slate-300 text-slate-900 font-hebrew font-bold rounded-lg hover:bg-slate-400 transition disabled:opacity-50"
              >
                ביטול
              </button>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="mb-6 flex items-center gap-4">
          <label className="text-sm font-hebrew font-semibold text-slate-900">סנן לפי קטגוריה:</label>
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="px-4 py-2 border border-slate-300 rounded-lg font-hebrew"
          >
            <option value="">הכל</option>
            {CATEGORIES.map(cat => (
              <option key={cat} value={cat}>{categoryIcons[cat]} {cat}</option>
            ))}
          </select>
        </div>

        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center py-16">
            <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        )}

        {/* Reasons by Category */}
        {!loading && (
          <div className="space-y-8">
            {!hasReasons && (
              <div className="bg-white border border-slate-200 rounded-xl p-10 text-center">
                <h2 className="text-2xl font-hebrew font-bold text-slate-800 mb-2">אין נתונים להצגה</h2>
                <p className="text-slate-600 font-hebrew">לא נמצאו סיבות תואמות למסנן. אפשר להתחיל על ידי הוספת סיבה חדשה.</p>
              </div>
            )}
            {Object.entries(filteredGroups).map(([category, categoryReasons]) => (
              <div key={category}>
                <h2 className="text-2xl font-hebrew font-bold text-slate-900 mb-4">
                  {categoryIcons[category]} {category}
                  <span className="text-sm font-normal text-slate-600 ml-2">
                    ({categoryReasons.length})
                  </span>
                </h2>
                <div className="grid gap-4">
                  {categoryReasons.map(reason => {
                    const severityColors = {
                      routine: 'bg-green-50 border-green-200',
                      attention: 'bg-amber-50 border-amber-200',
                      urgent: 'bg-red-50 border-red-200'
                    };

                    return (
                      <div key={reason.id} className={`p-6 border-2 rounded-lg ${severityColors[reason.severity]}`}>
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex-1">
                            <h3 className="text-lg font-hebrew font-bold text-slate-900">
                              {reason.title_hebrew}
                            </h3>
                            <p className="text-sm text-slate-600 font-hebrew mt-1">
                              קוד: {reason.code}
                            </p>
                          </div>
                          <div className="flex gap-2">
                            <button
                              onClick={() => handleEditReason(reason)}
                              className="px-4 py-2 bg-blue-100 text-blue-600 font-hebrew font-semibold rounded-lg hover:bg-blue-200 transition"
                            >
                              ✏️ ערוך
                            </button>
                            <button
                              onClick={() => handleDeleteReason(reason.id)}
                              className="px-4 py-2 bg-red-100 text-red-600 font-hebrew font-semibold rounded-lg hover:bg-red-200 transition"
                            >
                              🗑️ מחק
                            </button>
                          </div>
                        </div>
                        <p className="text-slate-900 font-hebrew mb-3">
                          {reason.explanation_template}
                        </p>
                        <div className="flex flex-wrap gap-2 text-xs">
                          <span className="px-2 py-1 bg-white bg-opacity-50 rounded font-hebrew">
                            {reason.direction === 'increase' ? '📈 עלייה' : reason.direction === 'decrease' ? '📉 ירידה' : '⚪ ניטרלי'}
                          </span>
                          {reason.requires_detail && (
                            <span className="px-2 py-1 bg-white bg-opacity-50 rounded font-hebrew">
                              💬 דרוש פרט
                            </span>
                          )}
                          {reason.topic_codes.includes('all') ? (
                            <span className="px-2 py-1 bg-white bg-opacity-50 rounded font-hebrew">
                              🌍 כל הקודים
                            </span>
                          ) : (
                            <span className="px-2 py-1 bg-white bg-opacity-50 rounded font-hebrew">
                              קודים: {reason.topic_codes.join(', ')}
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
