import React, { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { suggestionsAPI } from '../services/api';
import { useEmployeeSuggestionCounts } from '../hooks/useEmployeeSuggestionCounts';
import ExplanationSuggestionModal from '../components/portal/ExplanationSuggestionModal';
import { Clock, CheckCircle, XCircle, RefreshCw, AlertTriangle } from 'lucide-react';

// ─── Helpers ────────────────────────────────────────────────────────────────

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('he-IL', { year: 'numeric', month: 'short', day: 'numeric' });
}

const STATUS_CONFIG = {
  pending: {
    label: '⏳ ממתין לאישור',
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    badge: 'bg-amber-100 text-amber-800',
  },
  approved: {
    label: '✅ אושר',
    bg: 'bg-green-50',
    border: 'border-green-200',
    badge: 'bg-green-100 text-green-800',
  },
  rejected: {
    label: '❌ נדחה',
    bg: 'bg-red-50',
    border: 'border-red-200',
    badge: 'bg-red-100 text-red-800',
  },
};

// ─── Card component ──────────────────────────────────────────────────────────

function SuggestionCard({ suggestion, onResubmit }) {
  const cfg = STATUS_CONFIG[suggestion.status] || STATUS_CONFIG.pending;
  const displayText = suggestion.custom_text || suggestion.preset_text || '—';

  return (
    <div
      dir="rtl"
      className={`rounded-2xl border p-5 shadow-sm ${cfg.bg} ${cfg.border}`}
    >
      {/* Header row */}
      <div className="flex items-start justify-between mb-3 gap-3">
        <div>
          <div className="font-bold text-gray-900 font-hebrew text-base">
            {suggestion.municipality_name || '—'}
          </div>
          <div className="text-sm text-gray-500 font-hebrew mt-0.5">
            {suggestion.budget_line_name || `קוד ${suggestion.topic_code}`}
            {suggestion.month && (
              <span className="mr-2 text-gray-400">| {suggestion.month}</span>
            )}
          </div>
        </div>
        <span className={`shrink-0 inline-flex items-center px-3 py-1 rounded-full text-xs font-bold ${cfg.badge}`}>
          {cfg.label}
        </span>
      </div>

      {/* Suggested text */}
      <div className="bg-white rounded-xl p-3 border border-gray-200 mb-3">
        <div className="text-xs text-gray-400 font-hebrew mb-1">הטקסט שהוגש:</div>
        <p className="text-sm text-gray-800 font-hebrew leading-relaxed whitespace-pre-line">
          {displayText}
        </p>
      </div>

      {/* Rejection reason */}
      {suggestion.status === 'rejected' && suggestion.review_note && (
        <div className="bg-red-50 border border-red-300 rounded-xl p-3 mb-3">
          <div className="flex items-center gap-2 text-red-700 font-bold text-xs font-hebrew mb-1">
            <AlertTriangle size={14} />
            סיבת הדחייה:
          </div>
          <p className="text-sm text-red-800 font-hebrew">{suggestion.review_note}</p>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between mt-2">
        <span className="text-xs text-gray-400 font-hebrew">
          הוגש: {formatDate(suggestion.created_at)}
          {suggestion.updated_at !== suggestion.created_at && (
            <> | עודכן: {formatDate(suggestion.updated_at)}</>
          )}
        </span>
        {suggestion.status === 'rejected' && (
          <button
            onClick={() => onResubmit(suggestion)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm rounded-xl font-hebrew font-semibold transition"
          >
            ✏️ ערוך והגש מחדש
          </button>
        )}
      </div>
    </div>
  );
}

// ─── Empty state ─────────────────────────────────────────────────────────────

function EmptyState({ tab }) {
  const msgs = {
    pending: { icon: '⏳', title: 'אין הצעות ממתינות', sub: 'כל ההצעות שלך טופלו' },
    approved: { icon: '✅', title: 'אין הצעות שאושרו עדיין', sub: 'הצעות שיאושרו יופיעו כאן' },
    rejected: { icon: '❌', title: 'אין הצעות שנדחו', sub: 'כל ההצעות שלך תקינות' },
  };
  const m = msgs[tab] || msgs.pending;
  return (
    <div className="text-center py-16 text-gray-400">
      <div className="text-5xl mb-3">{m.icon}</div>
      <div className="font-bold text-lg font-hebrew text-gray-600">{m.title}</div>
      <div className="text-sm font-hebrew mt-1">{m.sub}</div>
    </div>
  );
}

// ─── Main page ───────────────────────────────────────────────────────────────

const TABS = [
  { key: 'pending', label: 'ממתינות לאישור', Icon: Clock, badgeKey: 'pending', badgeColor: 'bg-red-500' },
  { key: 'approved', label: 'הצעות שאושרו', Icon: CheckCircle, badgeKey: 'approved', badgeColor: 'bg-green-600' },
  { key: 'rejected', label: 'הצעות שנדחו', Icon: XCircle, badgeKey: 'rejected', badgeColor: 'bg-red-500' },
];

export default function EmployeeSuggestionsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = searchParams.get('tab') || 'pending';
  const [activeTab, setActiveTab] = useState(
    ['pending', 'approved', 'rejected'].includes(initialTab) ? initialTab : 'pending'
  );

  const [allSuggestions, setAllSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const counts = useEmployeeSuggestionCounts();

  // Modal state for resubmit
  const [modalOpen, setModalOpen] = useState(false);
  const [selected, setSelected] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [resubmitError, setResubmitError] = useState(null);
  const [resubmitSuccess, setResubmitSuccess] = useState(false);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await suggestionsAPI.getMyAll();
      setAllSuggestions(res.data || []);
    } catch {
      setError('שגיאה בטעינת ההצעות');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  // Sync tab with URL
  const switchTab = (key) => {
    setActiveTab(key);
    setSearchParams({ tab: key });
    setResubmitSuccess(false);
  };

  const filtered = allSuggestions.filter((s) => s.status === activeTab);

  // Resubmit handlers
  const handleResubmit = (suggestion) => {
    setSelected(suggestion);
    setResubmitError(null);
    setModalOpen(true);
  };

  const handleModalClose = () => {
    setModalOpen(false);
    setSelected(null);
    setResubmitError(null);
  };

  const handleSubmitResubmit = async (suggestionData) => {
    if (!selected) return;
    setSubmitting(true);
    setResubmitError(null);
    try {
      await suggestionsAPI.submit({
        budget_line_id: selected.budget_line_id || 0,
        municipality_id: selected.municipality_id || 0,
        month: selected.month,
        topic_code: selected.topic_code,
        ...suggestionData,
      });
      handleModalClose();
      setResubmitSuccess(true);
      await loadAll();
    } catch {
      setResubmitError('שגיאה בהגשה מחדש — נסה שוב');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-gray-50" dir="rtl">
      {/* Page header */}
      <div className="bg-gradient-to-r from-slate-900 to-slate-800 shadow-lg px-6 py-6">
        <h1 className="text-2xl font-bold text-white font-hebrew">ההצעות שלי</h1>
        <p className="text-slate-300 font-hebrew text-sm mt-1">מעקב אחר הצעות ההסברים שהגשת</p>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6">
        {/* Success banner */}
        {resubmitSuccess && (
          <div className="mb-4 p-4 bg-green-50 border border-green-300 rounded-xl text-green-800 font-hebrew font-semibold flex items-center gap-2">
            <CheckCircle size={18} />
            ההצעה הוגשה מחדש בהצלחה ועברה לסטטוס "ממתין לאישור"
          </div>
        )}

        {/* Error banner */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 font-hebrew flex items-center gap-2">
            <AlertTriangle size={16} />
            {error}
          </div>
        )}

        {/* Tabs */}
        <div className="flex items-center gap-2 mb-6 flex-wrap">
          {TABS.map(({ key, label, Icon, badgeKey, badgeColor }) => {
            const count = counts[badgeKey] || 0;
            const isActive = activeTab === key;
            return (
              <button
                key={key}
                onClick={() => switchTab(key)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition ${
                  isActive
                    ? 'bg-slate-800 text-white shadow-md'
                    : 'bg-white text-gray-600 border border-gray-200 hover:border-slate-400'
                }`}
              >
                <Icon size={16} />
                <span className="font-hebrew">{label}</span>
                {count > 0 && (
                  <span className={`inline-flex items-center justify-center min-w-[18px] px-1 py-0.5 text-xs font-bold leading-none text-white ${badgeColor} rounded-full`}>
                    {count}
                  </span>
                )}
              </button>
            );
          })}
          <button
            onClick={loadAll}
            disabled={loading}
            className="mr-auto flex items-center gap-2 px-3 py-2 text-sm text-gray-500 hover:text-gray-700 transition"
          >
            <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
            <span className="font-hebrew">רענן</span>
          </button>
        </div>

        {/* Content */}
        {loading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="animate-pulse bg-gray-100 rounded-2xl h-36" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState tab={activeTab} />
        ) : (
          <div className="space-y-4">
            {filtered.map((s) => (
              <SuggestionCard key={s.id} suggestion={s} onResubmit={handleResubmit} />
            ))}
          </div>
        )}
      </div>

      {/* Resubmit modal */}
      {modalOpen && selected && (
        <ExplanationSuggestionModal
          isOpen={modalOpen}
          onClose={handleModalClose}
          budgetLine={{ item_name: selected.budget_line_name, topic_code: selected.topic_code }}
          topicCode={selected.topic_code}
          onSubmit={handleSubmitResubmit}
          isLoading={submitting}
          prefilledText={selected.custom_text || selected.preset_text || ''}
          isEdit={true}
        />
      )}
    </div>
  );
}
