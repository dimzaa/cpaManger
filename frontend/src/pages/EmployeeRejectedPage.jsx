import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { suggestionsAPI } from '../services/api';
import { formatHebrewDate } from '../utils/format';
import ExplanationSuggestionModal from '../components/portal/ExplanationSuggestionModal';

/**
 * Employee Rejected Suggestions Page
 * Shows all rejected suggestions with option to edit and resubmit
 */
export default function EmployeeRejectedPage() {
  const navigate = useNavigate();
  const [rejectedSuggestions, setRejectedSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedSuggestion, setSelectedSuggestion] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadRejectedSuggestions();
  }, []);

  const loadRejectedSuggestions = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await suggestionsAPI.getMyRejected();
      setRejectedSuggestions(response.data || []);
    } catch (err) {
      setError('שגיאה בטעינת ההצעות שנדחו');
      console.error('Error loading rejected suggestions:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleEditAndResubmit = (suggestion) => {
    setSelectedSuggestion(suggestion);
    setModalOpen(true);
  };

  const handleModalClose = () => {
    setModalOpen(false);
    setSelectedSuggestion(null);
  };

  const handleResubmit = async (suggestionData) => {
    if (!selectedSuggestion) return;

    try {
      setSubmitting(true);
      setError(null);

      // Submit as new suggestion with same budget line
      await suggestionsAPI.submit({
        budget_line_id: selectedSuggestion.budget_line_id || 0,
        municipality_id: selectedSuggestion.municipality_id || 0,
        month: selectedSuggestion.month,
        topic_code: selectedSuggestion.topic_code,
        ...suggestionData
      });

      // Success - reload and close modal
      await loadRejectedSuggestions();
      handleModalClose();
      
      // Show success message (optional - could add toast)
      console.log('✅ Suggestion resubmitted successfully');
    } catch (err) {
      setError('שגיאה בהגשת ההסבר מחדש');
      console.error('Error resubmitting:', err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-gray-50">
      {/* Header */}
      <div className="sticky top-0 z-40 bg-gradient-to-r from-slate-900 to-slate-800 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white font-hebrew">❌ הצעות שנדחו</h1>
            <p className="text-slate-300 font-hebrew text-sm mt-1">הצעות שדורשות עריכה והגשה מחדש</p>
          </div>
          <button
            onClick={() => navigate('/portal/budget')}
            className="px-4 py-2 bg-white text-slate-900 font-hebrew font-semibold rounded-lg hover:bg-slate-100 transition"
          >
            ← חזור לתקציב
          </button>
        </div>
      </div>

      <main className="max-w-6xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Error message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-700 font-hebrew font-semibold">❌ {error}</p>
          </div>
        )}

        {/* Loading state */}
        {loading && (
          <div className="flex items-center justify-center py-16">
            <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        )}

        {/* Empty state */}
        {!loading && rejectedSuggestions.length === 0 && (
          <div className="text-center py-12 bg-green-50 rounded-xl border border-green-200">
            <p className="text-lg text-green-700 font-hebrew font-semibold">
              ✅ אין הצעות שנדחו!
            </p>
            <p className="text-slate-600 font-hebrew mt-2">
              כל ההצעות שלך אושרו או עדיין בהמתנה לאישור
            </p>
          </div>
        )}

        {/* Rejected suggestions list */}
        {!loading && rejectedSuggestions.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-slate-900 font-hebrew">
                📋 הצעות בהמתנה לעריכה
              </h2>
              <span className="inline-flex items-center px-3 py-1 text-sm font-bold leading-none text-white bg-red-600 rounded-full">
                {rejectedSuggestions.length}
              </span>
            </div>

            {rejectedSuggestions.map((suggestion) => (
              <div
                key={suggestion.id}
                className="p-6 bg-white border-2 border-red-200 rounded-xl shadow-sm hover:shadow-md transition"
              >
                {/* Header row */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-red-600 font-bold text-lg">❌ נדחתה</span>
                      <span className="text-sm font-hebrew text-slate-700">
                        {suggestion.municipality_name || 'מוניציפליטה'}
                      </span>
                    </div>
                    <p className="text-sm text-slate-600 font-hebrew">
                      {suggestion.month} | קוד {suggestion.topic_code} |{' '}
                      {suggestion.budget_line_name || 'פריט תקציבי'}
                    </p>
                  </div>
                  <span
                    className={`px-3 py-1 rounded-full text-sm font-hebrew font-bold ${
                      suggestion.suggestion_type === 'preset'
                        ? 'bg-blue-100 text-blue-700'
                        : 'bg-purple-100 text-purple-700'
                    }`}
                  >
                    {suggestion.suggestion_type === 'preset' ? '📋 מספרייה' : '✍️ כתוב'}
                  </span>
                </div>

                {/* Suggested text */}
                <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-sm text-blue-700 font-hebrew font-semibold mb-2">
                    💡 הההסבר שהגשת:
                  </p>
                  <p className="text-slate-900 font-hebrew text-base leading-relaxed">
                    "{suggestion.custom_text || suggestion.preset_text || 'לא קיים טקסט'}"
                  </p>
                </div>

                {/* Rejection reason */}
                {suggestion.review_note && (
                  <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-sm text-red-700 font-hebrew font-semibold mb-2">
                      🔴 סיבת הדחייה מרואה החשבון:
                    </p>
                    <p className="text-slate-900 font-hebrew text-base leading-relaxed">
                      {suggestion.review_note}
                    </p>
                  </div>
                )}

                {/* Meta info */}
                <div className="text-xs text-slate-500 font-hebrew mb-4">
                  דחויה ב-{suggestion.updated_at ? new Date(suggestion.updated_at).toLocaleDateString('he-IL') : '—'}
                </div>

                {/* Edit button */}
                <button
                  onClick={() => handleEditAndResubmit(suggestion)}
                  className="w-full px-4 py-2 bg-blue-600 text-white font-hebrew font-semibold rounded-lg hover:bg-blue-700 transition flex items-center justify-center gap-2"
                >
                  ✏️ ערוך והגש מחדש
                </button>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Modal for editing and resubmitting */}
      {selectedSuggestion && (
        <ExplanationSuggestionModal
          isOpen={modalOpen}
          onClose={handleModalClose}
          budgetLine={{
            item_name: selectedSuggestion.budget_line_name,
            topic_code: selectedSuggestion.topic_code
          }}
          topicCode={selectedSuggestion.topic_code}
          onSubmit={handleResubmit}
          isLoading={submitting}
          prefilledText={selectedSuggestion.custom_text || selectedSuggestion.preset_text}
          isEdit={true}
        />
      )}
    </div>
  );
}
