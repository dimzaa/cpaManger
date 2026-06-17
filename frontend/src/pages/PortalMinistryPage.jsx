import React, { useState, useEffect, useCallback, useRef } from 'react';
import PortalWrapper from '../components/portal/PortalWrapper';
import { useAuth } from '../context/AuthContext';
import { ministryAPI } from '../services/api';
import {
  Search, BookOpen, Bell, FileText, ChevronDown, ChevronUp,
  X, Check, AlertCircle, Info, ExternalLink, Tag,
} from 'lucide-react';

// ─── CATEGORY CONFIG ───────────────────────────────────────────────────────
const CATEGORY_CONFIG = {
  'גני ילדים':           { border: 'border-blue-400',   bg: 'bg-blue-50',   badge: 'bg-blue-100 text-blue-700',   dot: 'bg-blue-400'   },
  'נושאים רשותיים':     { border: 'border-purple-400', bg: 'bg-purple-50', badge: 'bg-purple-100 text-purple-700', dot: 'bg-purple-400' },
  'הסעות':               { border: 'border-green-400',  bg: 'bg-green-50',  badge: 'bg-green-100 text-green-700',  dot: 'bg-green-400'  },
  'שירותים פסיכולוגיים': { border: 'border-teal-400',   bg: 'bg-teal-50',   badge: 'bg-teal-100 text-teal-700',   dot: 'bg-teal-400'   },
  'חינוך יסודי':         { border: 'border-amber-400',  bg: 'bg-amber-50',  badge: 'bg-amber-100 text-amber-700',  dot: 'bg-amber-400'  },
  'חינוך מיוחד':         { border: 'border-orange-400', bg: 'bg-orange-50', badge: 'bg-orange-100 text-orange-700', dot: 'bg-orange-400' },
};
const DEDUCTION_CONFIG = { border: 'border-red-400', bg: 'bg-red-50', badge: 'bg-red-100 text-red-700', dot: 'bg-red-400' };
const DEFAULT_CONFIG = { border: 'border-slate-300', bg: 'bg-slate-50', badge: 'bg-slate-100 text-slate-600', dot: 'bg-slate-400' };

function categoryConfig(code) {
  if (code.is_deduction) return DEDUCTION_CONFIG;
  return CATEGORY_CONFIG[code.category] || DEFAULT_CONFIG;
}

// ─── SEVERITY CONFIG ───────────────────────────────────────────────────────
const SEVERITY = {
  high:   { icon: '🔴', label: 'חמור',   badge: 'bg-red-100 text-red-700',     border: 'border-red-300',   bg: 'bg-red-50'   },
  medium: { icon: '🟡', label: 'בינוני', badge: 'bg-amber-100 text-amber-700', border: 'border-amber-300', bg: 'bg-amber-50' },
  low:    { icon: '🔵', label: 'נמוך',   badge: 'bg-blue-100 text-blue-700',   border: 'border-blue-200',  bg: 'bg-blue-50'  },
  info:   { icon: 'ℹ️',  label: 'מידע',   badge: 'bg-slate-100 text-slate-600', border: 'border-slate-200', bg: 'bg-slate-50' },
};

// ─── IMPORTANCE CONFIG ─────────────────────────────────────────────────────
const IMPORTANCE = {
  critical:  { icon: '🔴', label: 'דחוף',  border: 'border-l-4 border-red-500',    badge: 'bg-red-100 text-red-700'    },
  important: { icon: '🟡', label: 'חשוב',  border: 'border-l-4 border-amber-500',  badge: 'bg-amber-100 text-amber-700' },
  routine:   { icon: '⚪', label: 'שגרתי', border: 'border-l-4 border-slate-300',  badge: 'bg-slate-100 text-slate-500' },
};

function fmt(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  return d.toLocaleDateString('he-IL');
}

// ─── CODE CARD ─────────────────────────────────────────────────────────────
function CodeCard({ code, onDetail, onRelatedClick }) {
  const cfg = categoryConfig(code);
  return (
    <div className={`bg-white rounded-2xl border-2 ${cfg.border} shadow-sm hover:shadow-md transition p-5`} dir="rtl">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-lg font-bold text-slate-800 font-hebrew">קוד {code.code}</span>
            {code.is_deduction && (
              <span className="text-xs font-hebrew font-semibold bg-red-100 text-red-700 px-2 py-0.5 rounded-full">ניכוי</span>
            )}
            <span className={`text-xs font-hebrew px-2 py-0.5 rounded-full ${cfg.badge}`}>{code.category}</span>
          </div>
          <p className="font-hebrew text-slate-700 font-medium">{code.name_full}</p>
        </div>
        {code.booklet_page && (
          <span className="flex items-center gap-1 text-xs text-slate-400 font-hebrew whitespace-nowrap bg-slate-50 px-2 py-1 rounded-lg">
            <BookOpen size={12} />
            עמ' {code.booklet_page}
          </span>
        )}
      </div>

      {code.description && (
        <p className="text-sm font-hebrew text-slate-500 mb-3 line-clamp-2">{code.description}</p>
      )}

      {code.formula && (
        <div className={`${cfg.bg} rounded-xl p-3 mb-3`}>
          <p className="text-xs font-hebrew font-semibold text-slate-500 mb-1">נוסחה:</p>
          <pre className="text-xs font-hebrew text-slate-700 whitespace-pre-wrap leading-relaxed">{code.formula}</pre>
        </div>
      )}

      {code.participation_percent != null && (
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs font-hebrew text-slate-400">השתתפות משרד:</span>
          <span className="text-sm font-bold text-slate-700 font-hebrew">{code.participation_percent}%</span>
        </div>
      )}

      {code.related_codes?.length > 0 && (
        <div className="flex items-center gap-2 mb-4 flex-wrap">
          <span className="text-xs font-hebrew text-slate-400">קודים קשורים:</span>
          {code.related_codes.map(rc => (
            <button key={rc}
              onClick={() => onRelatedClick(rc)}
              className="text-xs font-hebrew px-2 py-0.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-full transition">
              [{rc}]
            </button>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <button onClick={() => onDetail(code.code)}
          className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-hebrew font-medium transition">
          <BookOpen size={13} />
          פרטים מלאים
        </button>
        {code.booklet_page && (
          <span className="flex items-center gap-1.5 px-3 py-2 bg-slate-100 text-slate-500 rounded-xl text-xs font-hebrew">
            📋 עמוד {code.booklet_page} בחוברת
          </span>
        )}
      </div>
    </div>
  );
}

// ─── CODE DETAIL MODAL ─────────────────────────────────────────────────────
function CodeDetailModal({ codeStr, userId, onClose, onRelatedClick }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!codeStr) return;
    setLoading(true);
    ministryAPI.getCode(codeStr, userId)
      .then(r => setDetail(r.data))
      .catch(() => setDetail(null))
      .finally(() => setLoading(false));
  }, [codeStr, userId]);

  if (!codeStr) return null;
  const cfg = detail ? categoryConfig(detail) : DEFAULT_CONFIG;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-start justify-center overflow-y-auto py-8 px-4">
      <div className="bg-white rounded-3xl shadow-2xl w-full max-w-2xl relative" dir="rtl">
        <button onClick={onClose}
          className="absolute top-4 left-4 p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100 transition">
          <X size={20} />
        </button>

        {loading ? (
          <div className="p-12 text-center text-slate-400 font-hebrew">טוען...</div>
        ) : !detail ? (
          <div className="p-12 text-center text-slate-400 font-hebrew">שגיאה בטעינת הקוד</div>
        ) : (
          <>
            {/* Header */}
            <div className={`${cfg.bg} rounded-t-3xl p-6 border-b-2 ${cfg.border}`}>
              <div className="flex items-center gap-3 mb-2">
                <span className="text-2xl font-bold text-slate-800 font-hebrew">קוד {detail.code}</span>
                {detail.is_deduction && (
                  <span className="text-sm font-hebrew font-semibold bg-red-100 text-red-700 px-3 py-0.5 rounded-full">ניכוי</span>
                )}
                <span className={`text-sm font-hebrew px-3 py-0.5 rounded-full ${cfg.badge}`}>{detail.category}</span>
              </div>
              <h2 className="text-lg font-hebrew font-semibold text-slate-700">{detail.name_full}</h2>
              {detail.booklet_page && (
                <div className="flex items-center gap-2 mt-2">
                  <BookOpen size={14} className="text-slate-400" />
                  <span className="text-xs font-hebrew text-slate-500">
                    {detail.booklet_section} — עמוד {detail.booklet_page} בחוברת התקצוב
                  </span>
                </div>
              )}
            </div>

            <div className="p-6 space-y-6">
              {/* Description */}
              {detail.description && (
                <section>
                  <h3 className="font-hebrew font-bold text-slate-700 text-sm mb-2">📝 תיאור</h3>
                  <p className="font-hebrew text-slate-600 text-sm leading-relaxed">{detail.description}</p>
                </section>
              )}

              {/* Formula */}
              {detail.formula && (
                <section>
                  <h3 className="font-hebrew font-bold text-slate-700 text-sm mb-2">🧮 נוסחת החישוב</h3>
                  <div className={`${cfg.bg} rounded-xl p-4 border ${cfg.border}`}>
                    <pre className="font-hebrew text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">{detail.formula}</pre>
                    {detail.participation_percent != null && (
                      <div className="mt-3 pt-3 border-t border-slate-200 flex items-center gap-3">
                        <span className="font-hebrew text-xs text-slate-400">אחוז השתתפות:</span>
                        <span className="font-hebrew font-bold text-green-700 text-sm">{detail.participation_percent}%</span>
                        {detail.constant_divisor && (
                          <>
                            <span className="font-hebrew text-xs text-slate-400">מחלק קבוע:</span>
                            <span className="font-hebrew font-bold text-red-700 text-sm">[{detail.constant_divisor}]</span>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                </section>
              )}

              {/* Sub Topics */}
              {detail.sub_topics?.length > 0 && (
                <section>
                  <h3 className="font-hebrew font-bold text-slate-700 text-sm mb-2">📂 תת-נושאים</h3>
                  <ul className="space-y-1.5">
                    {detail.sub_topics.map((st, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm font-hebrew text-slate-600">
                        <span className="text-blue-400 mt-0.5">•</span>
                        <span>{st}</span>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {/* Change Triggers */}
              {detail.change_triggers?.length > 0 && (
                <section>
                  <h3 className="font-hebrew font-bold text-slate-700 text-sm mb-2">⚡ גורמים לשינוי בסכום</h3>
                  <p className="text-xs font-hebrew text-slate-400 mb-2">למה הסכום משתנה מחודש לחודש?</p>
                  <ul className="space-y-1.5">
                    {detail.change_triggers.map((ct, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm font-hebrew text-slate-600">
                        <span className="text-amber-500 mt-0.5">›</span>
                        <span>{ct}</span>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {/* Related Codes */}
              {detail.related_codes_details?.length > 0 && (
                <section>
                  <h3 className="font-hebrew font-bold text-slate-700 text-sm mb-2">🔗 קודים קשורים</h3>
                  <div className="flex flex-wrap gap-2">
                    {detail.related_codes_details.map(rc => (
                      <button key={rc.code}
                        onClick={() => { onClose(); onRelatedClick(rc.code); }}
                        className="flex items-center gap-2 px-3 py-2 bg-slate-100 hover:bg-blue-50 hover:text-blue-700 text-slate-600 rounded-xl text-sm font-hebrew transition">
                        קוד {rc.code} — {rc.name}
                        <ExternalLink size={12} />
                      </button>
                    ))}
                  </div>
                </section>
              )}

              {/* Recent Policy Changes */}
              {detail.recent_policy_changes?.length > 0 && (
                <section>
                  <h3 className="font-hebrew font-bold text-slate-700 text-sm mb-2">🔔 שינויי מדיניות אחרונים</h3>
                  <div className="space-y-2">
                    {detail.recent_policy_changes.map(pc => (
                      <div key={pc.id} className="bg-amber-50 border border-amber-200 rounded-xl p-3">
                        <p className="font-hebrew font-semibold text-amber-800 text-sm">{pc.title}</p>
                        {pc.effective_date && (
                          <p className="font-hebrew text-xs text-amber-600 mt-1">תאריך כניסה לתוקף: {fmt(pc.effective_date)}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* Recent Circulars */}
              {detail.recent_circulars?.length > 0 && (
                <section>
                  <h3 className="font-hebrew font-bold text-slate-700 text-sm mb-2">📄 חוזרים רלוונטיים</h3>
                  <div className="space-y-2">
                    {detail.recent_circulars.map(cl => (
                      <div key={cl.id} className="bg-blue-50 border border-blue-200 rounded-xl p-3">
                        <p className="font-hebrew font-semibold text-blue-800 text-sm">
                          {cl.circular_number && <span className="font-mono mr-1">{cl.circular_number}</span>}
                          {cl.title}
                        </p>
                        {cl.published_date && (
                          <p className="font-hebrew text-xs text-blue-600 mt-1">{fmt(cl.published_date)}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* Footer */}
              <footer className="border-t border-slate-100 pt-4 text-xs font-hebrew text-slate-400">
                <p>מקור: חוברת התקצוב — השתתפות משרד החינוך בתקציב הרשויות המקומיות</p>
                {detail.booklet_page && (
                  <p className="mt-1">עמוד {detail.booklet_page} | מנהל כלכלה ותקציבים</p>
                )}
              </footer>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ─── TAB 1: CODES ──────────────────────────────────────────────────────────
function CodesTab({ userId }) {
  const [codes, setCodes] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState('');
  const [detailCode, setDetailCode] = useState(null);
  const searchTimeout = useRef(null);

  const load = useCallback(async (q = search, cat = activeCategory) => {
    setLoading(true);
    try {
      const params = {};
      if (q) params.search = q;
      if (cat) params.category = cat;
      const [codesRes, catRes] = await Promise.all([
        ministryAPI.getCodes(params),
        categories.length === 0 ? ministryAPI.getCategories() : Promise.resolve({ data: categories }),
      ]);
      setCodes(codesRes.data || []);
      if (categories.length === 0) setCategories(catRes.data || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [search, activeCategory, categories]);

  useEffect(() => { load(); }, [activeCategory]);

  const handleSearch = (val) => {
    setSearch(val);
    if (searchTimeout.current) clearTimeout(searchTimeout.current);
    searchTimeout.current = setTimeout(() => load(val, activeCategory), 350);
  };

  const handleRelatedClick = (code) => setDetailCode(code);

  return (
    <div className="space-y-5">
      {/* Search */}
      <div className="relative">
        <Search size={18} className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          value={search}
          onChange={e => handleSearch(e.target.value)}
          placeholder="חפש קוד תקצוב, שם נושא, מילת מפתח..."
          className="w-full border-2 border-slate-200 rounded-2xl py-3.5 pr-12 pl-4 font-hebrew text-sm focus:outline-none focus:border-blue-400 transition"
          dir="rtl"
        />
      </div>

      {/* Category pills */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => { setActiveCategory(''); }}
          className={`px-4 py-2 rounded-full text-sm font-hebrew font-medium transition ${
            !activeCategory ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          הכל ({codes.length || '—'})
        </button>
        {categories.map(cat => (
          <button key={cat.category}
            onClick={() => setActiveCategory(activeCategory === cat.category ? '' : cat.category)}
            className={`px-4 py-2 rounded-full text-sm font-hebrew font-medium transition ${
              activeCategory === cat.category
                ? 'bg-blue-600 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {cat.category} ({cat.count})
          </button>
        ))}
      </div>

      {loading ? (
        <div className="py-12 text-center text-slate-400 font-hebrew">טוען קודי תקצוב...</div>
      ) : codes.length === 0 ? (
        <div className="py-12 text-center text-slate-400 font-hebrew">לא נמצאו קודים</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {codes.map(code => (
            <CodeCard
              key={code.id}
              code={code}
              onDetail={setDetailCode}
              onRelatedClick={handleRelatedClick}
            />
          ))}
        </div>
      )}

      {detailCode && (
        <CodeDetailModal
          codeStr={detailCode}
          userId={userId}
          onClose={() => setDetailCode(null)}
          onRelatedClick={handleRelatedClick}
        />
      )}
    </div>
  );
}

// ─── TAB 2: POLICY CHANGES ─────────────────────────────────────────────────
function PolicyChangesTab({ municipalityId }) {
  const [changes, setChanges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState('');
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = { municipality_id: municipalityId };
      if (severityFilter) params.severity = severityFilter;
      if (unreadOnly) params.unacknowledged_only = true;
      const [chRes, cntRes] = await Promise.all([
        ministryAPI.getPolicyChanges(params),
        municipalityId ? ministryAPI.getPolicyUnreadCount(municipalityId) : Promise.resolve({ data: { count: 0 } }),
      ]);
      setChanges(chRes.data || []);
      setUnreadCount(cntRes.data?.count || 0);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [municipalityId, severityFilter, unreadOnly]);

  useEffect(() => { load(); }, [load]);

  const handleAcknowledge = async (id) => {
    if (!municipalityId) return;
    try {
      await ministryAPI.acknowledgeChange(id, municipalityId);
      await load();
    } catch (e) { console.error(e); }
  };

  const handleMarkAll = async () => {
    if (!municipalityId) return;
    const unread = changes.filter(c => !c.is_acknowledged);
    await Promise.all(unread.map(c => ministryAPI.acknowledgeChange(c.id, municipalityId)));
    await load();
  };

  return (
    <div className="space-y-5">
      {/* Unread banner */}
      {unreadCount > 0 && (
        <div className="bg-amber-50 border border-amber-300 rounded-2xl p-4 flex items-center justify-between" dir="rtl">
          <div className="flex items-center gap-3">
            <Bell size={18} className="text-amber-600" />
            <span className="font-hebrew text-amber-800 font-medium">
              יש {unreadCount} שינויי מדיניות חדשים שלא קראת
            </span>
          </div>
          <button onClick={handleMarkAll}
            className="text-sm font-hebrew text-amber-700 hover:text-amber-900 underline transition">
            סמן הכל כנקרא
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-2" dir="rtl">
        {[['', 'הכל'], ['high', '🔴 חמור'], ['medium', '🟡 בינוני'], ['low', '🔵 נמוך'], ['info', 'ℹ️ מידע']].map(([val, label]) => (
          <button key={val}
            onClick={() => setSeverityFilter(val)}
            className={`px-4 py-2 rounded-full text-sm font-hebrew font-medium transition ${
              severityFilter === val ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {label}
          </button>
        ))}
        <button
          onClick={() => setUnreadOnly(v => !v)}
          className={`px-4 py-2 rounded-full text-sm font-hebrew font-medium transition ${
            unreadOnly ? 'bg-amber-500 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          {unreadOnly ? '✅ לא-נקראו בלבד' : 'לא-נקראו בלבד'}
        </button>
      </div>

      {loading ? (
        <div className="py-12 text-center text-slate-400 font-hebrew">טוען...</div>
      ) : changes.length === 0 ? (
        <div className="py-12 text-center text-slate-400 font-hebrew">אין שינויי מדיניות</div>
      ) : (
        <div className="space-y-4">
          {changes.map(pc => {
            const sv = SEVERITY[pc.severity] || SEVERITY.info;
            const isAcked = pc.is_acknowledged;
            return (
              <div key={pc.id}
                className={`rounded-2xl border ${sv.border} ${isAcked ? 'opacity-60' : ''} p-5`}
                style={{ background: isAcked ? '#f8fafc' : undefined }}
                dir="rtl"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span>{sv.icon}</span>
                    <span className={`text-xs font-hebrew font-semibold px-2 py-0.5 rounded-full ${sv.badge}`}>{sv.label}</span>
                    {isAcked && <span className="text-xs font-hebrew text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">✅ נקרא</span>}
                  </div>
                  {pc.announced_date && (
                    <span className="text-xs font-hebrew text-slate-400">{fmt(pc.announced_date)}</span>
                  )}
                </div>

                <h3 className="font-hebrew font-bold text-slate-800 text-base mb-2">{pc.title}</h3>

                {pc.affected_codes?.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mb-3">
                    <span className="text-xs text-slate-400 font-hebrew">קודים מושפעים:</span>
                    {pc.affected_codes.map(c => (
                      <span key={c} className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-hebrew">[{c}]</span>
                    ))}
                  </div>
                )}

                {pc.effective_date && (
                  <p className="text-xs font-hebrew text-slate-500 mb-3">
                    תאריך כניסה לתוקף: <strong>{fmt(pc.effective_date)}</strong>
                  </p>
                )}

                {pc.impact_description && (
                  <div className={`${sv.bg} rounded-xl p-3 mb-3`}>
                    <p className="text-xs font-hebrew font-semibold text-slate-600 mb-1">השפעה:</p>
                    <p className="text-sm font-hebrew text-slate-700">{pc.impact_description}</p>
                  </div>
                )}

                {pc.action_required && (
                  <div className="bg-slate-50 rounded-xl p-3 mb-4">
                    <p className="text-xs font-hebrew font-semibold text-slate-500 mb-1">נדרשת פעולה:</p>
                    <p className="text-sm font-hebrew text-slate-700">{pc.action_required}</p>
                  </div>
                )}

                {!isAcked && municipalityId && (
                  <button onClick={() => handleAcknowledge(pc.id)}
                    className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-xl text-sm font-hebrew font-medium transition">
                    <Check size={15} />
                    אישרתי קריאה
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── CIRCULAR FULL VIEW MODAL ──────────────────────────────────────────────
function CircularModal({ circularId, userId, onClose }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const imp = detail ? (IMPORTANCE[detail.importance] || IMPORTANCE.routine) : null;

  useEffect(() => {
    if (!circularId) return;
    setLoading(true);
    ministryAPI.getCircular(circularId, userId)
      .then(r => setDetail(r.data))
      .catch(() => setDetail(null))
      .finally(() => setLoading(false));
  }, [circularId, userId]);

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-start justify-center overflow-y-auto py-8 px-4">
      <div className="bg-white rounded-3xl shadow-2xl w-full max-w-2xl relative" dir="rtl">
        <button onClick={onClose}
          className="absolute top-4 left-4 p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100 transition">
          <X size={20} />
        </button>

        {loading ? (
          <div className="p-12 text-center text-slate-400 font-hebrew">טוען...</div>
        ) : !detail ? (
          <div className="p-12 text-center text-slate-400 font-hebrew">שגיאה בטעינה</div>
        ) : (
          <>
            <div className={`rounded-t-3xl p-6 border-b-4 ${imp?.border || ''}`}>
              <div className="flex items-center gap-3 mb-2">
                <span>{imp?.icon}</span>
                <span className={`text-xs font-hebrew font-semibold px-2 py-0.5 rounded-full ${imp?.badge}`}>{imp?.label}</span>
                <span className="text-xs font-hebrew text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">{detail.category}</span>
              </div>
              {detail.circular_number && (
                <p className="font-mono text-blue-700 text-sm mb-1">חוזר מנכ"ל {detail.circular_number}</p>
              )}
              <h2 className="font-hebrew font-bold text-xl text-slate-800 mb-2">{detail.title}</h2>
              <div className="flex gap-4 text-xs font-hebrew text-slate-500">
                {detail.published_date && <span>פורסם: {fmt(detail.published_date)}</span>}
                {detail.effective_date && <span>כניסה לתוקף: {fmt(detail.effective_date)}</span>}
              </div>
            </div>

            <div className="p-6 space-y-5">
              {detail.subject && (
                <div className="bg-blue-50 rounded-xl p-4">
                  <p className="font-hebrew text-blue-800 font-medium text-sm">{detail.subject}</p>
                </div>
              )}

              {detail.affected_codes?.length > 0 && (
                <div className="flex flex-wrap gap-2 items-center">
                  <span className="text-xs font-hebrew text-slate-400">קודים:</span>
                  {detail.affected_codes.map(c => (
                    <span key={c} className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-hebrew">[{c}]</span>
                  ))}
                </div>
              )}

              {detail.action_required && (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                  <p className="font-hebrew text-xs font-semibold text-amber-700 mb-1">📋 נדרשת פעולה:</p>
                  <p className="font-hebrew text-sm text-amber-800">{detail.action_required}</p>
                  {detail.action_deadline && (
                    <p className="font-hebrew text-xs text-amber-600 mt-2 font-semibold">
                      דדליין: {fmt(detail.action_deadline)}
                    </p>
                  )}
                </div>
              )}

              {detail.full_content && (
                <div>
                  <h3 className="font-hebrew font-bold text-slate-700 text-sm mb-3">📄 תוכן החוזר</h3>
                  <div className="bg-slate-50 rounded-xl p-5 font-hebrew text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
                    {detail.full_content}
                  </div>
                </div>
              )}

              {detail.tags?.length > 0 && (
                <div className="flex flex-wrap gap-2 items-center">
                  <Tag size={14} className="text-slate-400" />
                  {detail.tags.map((t, i) => (
                    <span key={i} className="text-xs font-hebrew bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full">{t}</span>
                  ))}
                </div>
              )}

              {detail.is_read === false && userId && (
                <button
                  onClick={() => ministryAPI.markCircularRead(circularId, userId).then(onClose)}
                  className="w-full flex items-center justify-center gap-2 py-3 bg-green-600 hover:bg-green-700 text-white rounded-xl font-hebrew font-medium transition"
                >
                  <Check size={16} />
                  סמן כנקרא וסגור
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ─── TAB 3: CIRCULARS ──────────────────────────────────────────────────────
function CircularsTab({ userId }) {
  const [circulars, setCirculars] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [importanceFilter, setImportanceFilter] = useState('');
  const [selectedId, setSelectedId] = useState(null);
  const [unreadCount, setUnreadCount] = useState(0);
  const searchRef = useRef(null);

  const load = useCallback(async (q = search) => {
    setLoading(true);
    try {
      const params = { user_id: userId };
      if (q) params.search = q;
      if (categoryFilter) params.category = categoryFilter;
      if (importanceFilter) params.importance = importanceFilter;
      const [clRes, cntRes] = await Promise.all([
        ministryAPI.getCirculars(params),
        userId ? ministryAPI.getCircularUnreadCount(userId) : Promise.resolve({ data: { count: 0 } }),
      ]);
      setCirculars(clRes.data || []);
      setUnreadCount(cntRes.data?.count || 0);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [userId, categoryFilter, importanceFilter, search]);

  useEffect(() => { load(); }, [categoryFilter, importanceFilter]);

  const handleSearch = (val) => {
    setSearch(val);
    if (searchRef.current) clearTimeout(searchRef.current);
    searchRef.current = setTimeout(() => load(val), 350);
  };

  const CATEGORIES = ['תקצוב', 'כוח אדם', 'פדגוגיה', 'ביטחון', 'הסעות', 'כללי'];

  return (
    <div className="space-y-5">
      {unreadCount > 0 && (
        <div className="bg-amber-50 border border-amber-300 rounded-2xl p-3 flex items-center gap-2" dir="rtl">
          <Bell size={16} className="text-amber-600" />
          <span className="font-hebrew text-amber-800 text-sm font-medium">
            {unreadCount} חוזרים שלא נקראו
          </span>
        </div>
      )}

      {/* Search + Filters */}
      <div className="flex gap-3 flex-wrap" dir="rtl">
        <div className="relative flex-1 min-w-48">
          <Search size={15} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={e => handleSearch(e.target.value)}
            placeholder="חיפוש חוזרים..."
            className="w-full border border-slate-300 rounded-xl py-2.5 pr-9 pl-3 font-hebrew text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 transition"
          />
        </div>
        <select
          value={categoryFilter}
          onChange={e => setCategoryFilter(e.target.value)}
          className="border border-slate-300 rounded-xl px-3 py-2.5 text-sm font-hebrew"
        >
          <option value="">כל הקטגוריות</option>
          {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <select
          value={importanceFilter}
          onChange={e => setImportanceFilter(e.target.value)}
          className="border border-slate-300 rounded-xl px-3 py-2.5 text-sm font-hebrew"
        >
          <option value="">כל החשיבות</option>
          <option value="critical">🔴 דחוף</option>
          <option value="important">🟡 חשוב</option>
          <option value="routine">⚪ שגרתי</option>
        </select>
      </div>

      {loading ? (
        <div className="py-12 text-center text-slate-400 font-hebrew">טוען...</div>
      ) : circulars.length === 0 ? (
        <div className="py-12 text-center text-slate-400 font-hebrew">אין חוזרים</div>
      ) : (
        <div className="space-y-4">
          {circulars.map(cl => {
            const imp = IMPORTANCE[cl.importance] || IMPORTANCE.routine;
            const isRead = cl.is_read;
            return (
              <div key={cl.id}
                className={`bg-white rounded-2xl shadow-sm ${imp.border} ${isRead ? 'opacity-70' : ''} p-5`}
                dir="rtl"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span>{imp.icon}</span>
                    <span className={`text-xs font-hebrew font-semibold px-2 py-0.5 rounded-full ${imp.badge}`}>{imp.label}</span>
                    <span className="text-xs font-hebrew text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">{cl.category}</span>
                    {cl.circular_number && (
                      <span className="text-xs font-mono text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">{cl.circular_number}</span>
                    )}
                    {isRead && <span className="text-xs font-hebrew text-slate-400">✅ נקרא</span>}
                  </div>
                  {cl.published_date && (
                    <span className="text-xs font-hebrew text-slate-400 whitespace-nowrap">{fmt(cl.published_date)}</span>
                  )}
                </div>

                <h3 className="font-hebrew font-bold text-slate-800 mb-2">{cl.title}</h3>

                {cl.subject && (
                  <p className="font-hebrew text-sm text-slate-500 mb-3 line-clamp-2">{cl.subject}</p>
                )}

                {cl.affected_codes?.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mb-3">
                    <span className="text-xs text-slate-400 font-hebrew">קודים:</span>
                    {cl.affected_codes.map(c => (
                      <span key={c} className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-hebrew">[{c}]</span>
                    ))}
                  </div>
                )}

                {cl.action_deadline && (
                  <p className="text-xs font-hebrew text-red-600 font-semibold mb-3">⏰ דדליין: {fmt(cl.action_deadline)}</p>
                )}

                <div className="flex gap-2">
                  <button onClick={() => setSelectedId(cl.id)}
                    className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-hebrew font-medium transition">
                    <FileText size={13} />
                    קרא חוזר מלא
                  </button>
                  {!isRead && userId && (
                    <button
                      onClick={() => ministryAPI.markCircularRead(cl.id, userId).then(() => load())}
                      className="flex items-center gap-1.5 px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-xl text-xs font-hebrew transition"
                    >
                      <Check size={13} />
                      סמן כנקרא
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {selectedId && (
        <CircularModal
          circularId={selectedId}
          userId={userId}
          onClose={() => { setSelectedId(null); load(); }}
        />
      )}
    </div>
  );
}

// ─── MAIN PAGE ─────────────────────────────────────────────────────────────
const TABS = [
  { id: 'codes',   label: 'קודי תקצוב',    icon: BookOpen },
  { id: 'policy',  label: 'שינויי מדיניות', icon: Bell     },
  { id: 'circulars', label: 'חוזרי מנכ"ל',  icon: FileText },
];

export default function PortalMinistryPage() {
  const { user } = useAuth();
  const params = new URLSearchParams(window.location.search);
  const initialTab = params.get('tab') || 'codes';
  const [activeTab, setActiveTab] = useState(initialTab);

  const municipalityId = user?.municipality_id;
  const userId = user?.id;

  return (
    <PortalWrapper>
      <div dir="rtl" className="max-w-5xl mx-auto space-y-6 px-2">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-hebrew font-bold text-slate-800">🏛️ מידע ממשרד החינוך</h1>
          <p className="font-hebrew text-sm text-slate-500 mt-1">חוזרים, שינויי מדיניות וקודי תקצוב</p>
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
        <div className="pb-12">
          {activeTab === 'codes' && <CodesTab userId={userId} />}
          {activeTab === 'policy' && <PolicyChangesTab municipalityId={municipalityId} />}
          {activeTab === 'circulars' && <CircularsTab userId={userId} />}
        </div>
      </div>
    </PortalWrapper>
  );
}
