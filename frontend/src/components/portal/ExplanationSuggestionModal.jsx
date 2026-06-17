import React, { useState, useEffect, useMemo } from 'react';
import { X } from 'lucide-react';
import { reasonsAPI } from '../../services/api';

/**
 * ExplanationSuggestionModal — Integrated with Reasons Library
 * 
 * Props:
 *   - isOpen: boolean
 *   - onClose: () => void
 *   - budgetLine: budget line object
 *   - topicCode: budget code (for filtering reasons)
 *   - onSubmit: (suggestion) => void
 *   - presets: array (legacy, kept for compatibility)
 *   - isLoading: boolean
 *   - prefilledText: pre-filled custom text (for edits)
 *   - isEdit: boolean (true if editing existing suggestion)
 */
export default function ExplanationSuggestionModal({
  isOpen,
  onClose,
  budgetLine,
  topicCode,
  onSubmit,
  presets = [],
  isLoading = false,
  prefilledText = '',
  isEdit = false
}) {
  const [activeTab, setActiveTab] = useState('reasons'); // 'reasons' or 'custom'
  const [reasonsList, setReasonsList] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedReasonId, setSelectedReasonId] = useState(null);
  const [detailValue, setDetailValue] = useState('');
  const [customText, setCustomText] = useState(prefilledText || '');
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [loadingReasons, setLoadingReasons] = useState(false);
  const [reasonsLoadError, setReasonsLoadError] = useState(null);

  // Determine direction based on amount change
  const getDirection = () => {
    if (!budgetLine?.amount) return null;
    return budgetLine.amount > 0 ? 'increase' : (budgetLine.amount < 0 ? 'decrease' : null);
  };

  // Load reasons when modal opens
  useEffect(() => {
    if (isOpen && topicCode) {
      loadReasons();
    }
    // If editing, pre-fill the custom text and switch to custom tab
    if (isOpen && prefilledText) {
      setCustomText(prefilledText);
      setActiveTab('custom');
    }
  }, [isOpen, topicCode, prefilledText]);

  const loadReasons = async () => {
    try {
      setLoadingReasons(true);
      setReasonsLoadError(null);
      const response = await reasonsAPI.getForTopic(topicCode, getDirection());
      const data = response?.data || [];
      if (!Array.isArray(data)) {
        console.warn('Reasons API returned non-array data:', data);
        setReasonsList([]);
      } else {
        setReasonsList(data);
      }
    } catch (err) {
      console.error('Error loading reasons:', err);
      setReasonsLoadError(err.message || 'שגיאה בטעינת ספריית הסיבות');
      setReasonsList([]);
    } finally {
      setLoadingReasons(false);
    }
  };

  // Group reasons by category and implement smart filtering
  const groupedReasons = useMemo(() => {
    try {
      let filtered = Array.isArray(reasonsList) ? reasonsList : [];

      // Filter by search query
      if (searchQuery.trim()) {
        filtered = filtered.filter(r => {
          if (!r || typeof r !== 'object') return false;
          const titleMatch = r.title_hebrew && r.title_hebrew.toLowerCase().includes(searchQuery.toLowerCase());
          const explMatch = r.explanation_template && r.explanation_template.toLowerCase().includes(searchQuery.toLowerCase());
          return titleMatch || explMatch;
        });
      }

      // Group by category
      const grouped = {};
      filtered.forEach(reason => {
        if (!reason || typeof reason !== 'object' || !reason.category) return;
        if (!grouped[reason.category]) {
          grouped[reason.category] = [];
        }
        grouped[reason.category].push(reason);
      });

      // Return with icon mapping
      return grouped;
    } catch (err) {
      console.error('Error grouping reasons:', err);
      return {};
    }
  }, [reasonsList, searchQuery]);

  const categoryIcons = {
    'ילדים': '👶',
    'משרות': '💼',
    'שכר': '💰',
    'גן': '🏫',
    'רטרו': '↩️',
    'תיקון': '🔧',
    'מדיניות': '📋',
    'משפטי': '⚖️',
    'אחר': '❓',
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'routine': return { bg: 'bg-green-50', text: 'text-green-700', badge: '🟢' };
      case 'attention': return { bg: 'bg-amber-50', text: 'text-amber-700', badge: '🟡' };
      case 'urgent': return { bg: 'bg-red-50', text: 'text-red-700', badge: '🔴' };
      default: return { bg: 'bg-slate-50', text: 'text-slate-700', badge: '⚪' };
    }
  };

  const selectedReason = reasonsList.find(r => r.id === selectedReasonId);

  const handleSubmit = async () => {
    try {
      setError(null);
      setSubmitting(true);

      if (activeTab === 'reasons') {
        // Validate reason selection
        if (!selectedReasonId) {
          setError('בחר סיבה מהרשימה');
          return;
        }

        // Validate detail if required
        if (selectedReason?.requires_detail && !detailValue.trim()) {
          setError(`${selectedReason.detail_prompt || 'בחר פרט'}`);
          return;
        }

        if (!selectedReason) {
          setError('סיבה שנבחרה לא נתונה');
          return;
        }

        const suggestion = {
          reason_id: selectedReason.id,
          reason_code: selectedReason.code || null,
          suggestion_type: 'reason',
          detail_value: detailValue || null,
          // Also include template for immediate display
          custom_text: (selectedReason.explanation_template || '').replace('{detail_value}', detailValue || '')
        };

        await onSubmit(suggestion);
      } else {
        // Custom explanation
        if (!customText.trim()) {
          setError('כתוב הסבר כלשהו בשדה הטקסט');
          return;
        }
        if (customText.length > 500) {
          setError('ההסבר חייב להיות בן פחות מ-500 תווים');
          return;
        }

        const suggestion = {
          reason_id: null,
          suggestion_type: 'custom',
          custom_text: customText
        };

        await onSubmit(suggestion);
      }

      // Reset
      setSelectedReasonId(null);
      setDetailValue('');
      setCustomText('');
      setSearchQuery('');
      setError(null);
    } catch (err) {
      console.error('Error in handleSubmit:', err);
      setError(err.message || 'שגיאה בשליחת ההסבר');
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  const severityOfSelected = selectedReason ? getSeverityColor(selectedReason.severity) : null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-gradient-to-r from-blue-50 to-white px-8 py-6 border-b border-blue-100 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-slate-900 font-hebrew">✏️ הוסף הסבר</h2>
            <p className="text-sm text-slate-600 font-hebrew mt-1">
              {budgetLine?.budget_topic || 'שורה בתקציב'} — קוד {topicCode} — {budgetLine?.amount > 0 ? '📈 עלייה' : '📉 ירידה'}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-100 rounded-lg transition"
          >
            <X size={24} className="text-slate-600" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-200 bg-slate-50">
          <button
            onClick={() => setActiveTab('reasons')}
            className={`flex-1 px-6 py-3 font-hebrew font-semibold transition ${
              activeTab === 'reasons'
                ? 'text-blue-600 border-b-2 border-blue-600 bg-white'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            📚 ספריית סיבות
          </button>
          <button
            onClick={() => setActiveTab('custom')}
            className={`flex-1 px-6 py-3 font-hebrew font-semibold transition ${
              activeTab === 'custom'
                ? 'text-blue-600 border-b-2 border-blue-600 bg-white'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            ✍️ הסבר חופשי
          </button>
        </div>

        {/* Content */}
        <div className="p-8">
          {activeTab === 'reasons' && (
            <div className="space-y-6">
              {/* Error loading reasons */}
              {reasonsLoadError && (
                <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                  <p className="text-amber-800 font-hebrew text-sm">
                    ⚠️ {reasonsLoadError}
                  </p>
                  <p className="text-amber-700 font-hebrew text-xs mt-2">
                    אתה יכול להשתמש בהסבר חופשי בנתיים או לנסות שוב לטעון את הסיבות.
                  </p>
                  <button
                    onClick={() => loadReasons()}
                    disabled={loadingReasons}
                    className="mt-3 px-4 py-2 bg-amber-600 text-white text-sm rounded font-hebrew font-semibold hover:bg-amber-700 transition disabled:opacity-50"
                  >
                    {loadingReasons ? 'טוען...' : 'ננסה שוב'}
                  </button>
                </div>
              )}

              {/* Search */}
              <div>
                <input
                  type="text"
                  placeholder="חפש סיבה..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full px-4 py-3 border border-slate-300 rounded-lg font-hebrew text-right focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Loading state */}
              {loadingReasons && (
                <div className="flex items-center justify-center py-8">
                  <div className="w-6 h-6 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                </div>
              )}

              {/* Reasons grouped by category */}
              {!loadingReasons && Object.keys(groupedReasons).length > 0 && (
                <div className="space-y-6">
                  {Object.entries(groupedReasons).map(([category, reasons]) => (
                    <div key={category}>
                      <h3 className="text-base font-hebrew font-bold text-slate-900 mb-3 flex items-center gap-2">
                        {categoryIcons[category] || '❓'} {category}
                      </h3>
                      <div className="space-y-2">
                        {reasons.map(reason => {
                          try {
                            if (!reason || !reason.id) return null;
                            const severityColors = getSeverityColor(reason.severity);
                            const isSelected = selectedReasonId === reason.id;

                            return (
                              <div
                                key={reason.id}
                                onClick={() => {
                                  setSelectedReasonId(reason.id);
                                  setDetailValue('');
                                }}
                                className={`p-4 border-2 rounded-lg cursor-pointer transition ${
                                  isSelected
                                    ? 'border-blue-500 bg-blue-50'
                                    : 'border-slate-200 hover:border-slate-300 bg-white'
                                }`}
                              >
                                <div className="flex items-start justify-between">
                                  <div className="flex-1">
                                    <div className="flex items-center gap-2 mb-1">
                                      <p className="font-hebrew font-bold text-slate-900">
                                        {reason.title_hebrew || 'ללא כותרת'}
                                      </p>
                                      <span className={`text-xs px-2 py-1 rounded-full font-hebrew font-semibold ${severityColors.text} bg-opacity-20`}>
                                        {severityColors.badge} {reason.severity === 'routine' ? 'שגרה' : reason.severity === 'attention' ? 'לתשומת לב' : 'דחוף'}
                                      </span>
                                    </div>
                                    <p className="text-sm text-slate-600 font-hebrew">
                                      {reason.explanation_template ? reason.explanation_template.substring(0, 80) : 'אין תיאור'}...
                                    </p>
                                    {reason.direction && (
                                      <p className="text-xs text-slate-500 font-hebrew mt-2">
                                        כיוון: {reason.direction === 'increase' ? '📈 עלייה' : '📉 ירידה'}
                                      </p>
                                    )}
                                  </div>
                                  <input
                                    type="radio"
                                    name="reason"
                                    checked={isSelected}
                                    onChange={() => {}}
                                    className="w-5 h-5 cursor-pointer ml-4"
                                  />
                                </div>

                                {/* Detail prompt if selected and required */}
                                {isSelected && reason.requires_detail && (
                                  <div className="mt-4 pt-4 border-t border-blue-200">
                                    <label className="block text-sm font-hebrew font-semibold text-slate-900 mb-2">
                                      {reason.detail_prompt || 'הזן פרטים'}
                                    </label>
                                    <input
                                      type="text"
                                      value={detailValue}
                                      onChange={(e) => setDetailValue(e.target.value)}
                                      placeholder="הזן את הפרטים..."
                                      className="w-full px-3 py-2 border border-blue-300 rounded-lg font-hebrew text-right text-sm focus:ring-2 focus:ring-blue-500"
                                    />
                                  </div>
                                )}
                              </div>
                            );
                          } catch (err) {
                            console.error('Error rendering reason:', reason, err);
                            return null;
                          }
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {!loadingReasons && Object.keys(groupedReasons).length === 0 && (
                <div className="text-center py-8">
                  <p className="text-slate-600 font-hebrew text-sm">
                    לא נמצאו סיבות התואמות את הקריטריונים שלך
                  </p>
                </div>
              )}

              {/* Preview of selected reason */}
              {selectedReason && (
                <div className={`p-4 rounded-lg border-2 ${severityOfSelected?.bg || 'bg-slate-50'}`}>
                  <p className="text-sm text-slate-600 font-hebrew font-semibold mb-2">📝 הסבר מלא:</p>
                  <p className="text-slate-900 font-hebrew whitespace-pre-wrap">
                    {selectedReason.explanation_template 
                      ? selectedReason.explanation_template.replace('{detail_value}', detailValue || '[פרט]')
                      : 'אין הסבר'
                    }
                  </p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'custom' && (
            <div className="space-y-4">
              <textarea
                value={customText}
                onChange={(e) => setCustomText(e.target.value)}
                placeholder="כתוב כאן את ההסבר בעברית..."
                maxLength={500}
                className="w-full h-40 p-4 border border-slate-300 rounded-lg font-hebrew text-right focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              />
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600 font-hebrew">
                  {customText.length} / 500 תווים
                </span>
                {customText.length > 450 && (
                  <span className="text-amber-600 font-hebrew font-semibold">
                    ⚠️ מתקרב לגבול
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Error message */}
          {error && (
            <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-700 font-hebrew text-sm font-semibold">
                ❌ {error}
              </p>
            </div>
          )}

          {/* Info box */}
          <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-blue-900 font-hebrew text-sm">
              <span className="font-semibold">📝 הערה:</span> ההסבר ישלח לבדיקת רואה החשבון לפני פרסום.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="bg-slate-50 px-8 py-6 border-t border-slate-200 flex items-center justify-between gap-4">
          <button
            onClick={onClose}
            disabled={submitting}
            className="px-6 py-3 text-slate-700 font-hebrew font-semibold rounded-lg border border-slate-300 hover:bg-slate-100 transition disabled:opacity-50"
          >
            ביטול
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting || isLoading}
            className="px-8 py-3 bg-blue-600 text-white font-hebrew font-bold rounded-lg hover:bg-blue-700 transition disabled:opacity-50 flex items-center gap-2"
          >
            {submitting ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                שולח...
              </>
            ) : (
              <>
                📝 שלח לאישור CPA
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
