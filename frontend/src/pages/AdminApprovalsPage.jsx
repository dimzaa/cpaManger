import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { suggestionsAPI, reasonsAPI } from '../services/api';
import { formatShekel } from '../utils/format';
import { usePendingSuggestionsCount } from '../hooks/usePendingSuggestionsCount';

/**
 * Admin Approvals Page — CPA interface for reviewing and approving/rejecting explanation suggestions
 */
export default function AdminApprovalsPage() {
  const navigate = useNavigate();
  const { refetch: refetchPendingCount } = usePendingSuggestionsCount();
  const [pending, setPending] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedSuggestion, setSelectedSuggestion] = useState(null);
  const [rejectReason, setRejectReason] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [filterMunicipality, setFilterMunicipality] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [reasonsMap, setReasonsMap] = useState({});

  useEffect(() => {
    loadPendingSuggestions();
    loadReasonsMap();
  }, []);

  const loadReasonsMap = async () => {
    try {
      const response = await reasonsAPI.getAll({ active_only: false });
      const map = {};
      (response.data || []).forEach(reason => {
        map[reason.code] = reason;
      });
      setReasonsMap(map);
    } catch (err) {
      console.error('Error loading reasons:', err);
    }
  };

  const loadPendingSuggestions = async () => {
    try {
      setLoading(true);
      setError(null);
      console.log('🔍 AdminApprovalsPage: Loading pending suggestions...');
      const response = await suggestionsAPI.getPending();
      console.log('✅ AdminApprovalsPage: API Response received:', response);
      console.log('📊 AdminApprovalsPage: Response data:', response.data);
      const suggestionsData = response.data || [];
      console.log(`📋 AdminApprovalsPage: Found ${suggestionsData.length} pending suggestions`);
      if (suggestionsData.length === 0) {
        console.warn('⚠️ AdminApprovalsPage: No pending suggestions returned');
      }
      setPending(suggestionsData);
    } catch (err) {
      setError('שגיאה בטעינת הבקשות');
      console.error('❌ AdminApprovalsPage: Error loading suggestions:', err);
      console.error('Error status:', err.response?.status);
      console.error('Error data:', err.response?.data);
      console.error('Full error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (suggestionId) => {
    try {
      setIsProcessing(true);
      setError(null);
      
      const suggestion = pending.find(s => s.id === suggestionId);
      if (!suggestion || (!suggestion.custom_text && !suggestion.preset_text)) {
        setError('שגיאה: לא קיים טקסט הסבר לאישור');
        setIsProcessing(false);
        return;
      }
      
      await suggestionsAPI.approve(suggestionId);
      
      setSuccessMessage('ההסבר אושר בהצלחה ✅');
      setTimeout(() => setSuccessMessage(''), 3000);
      
      // Reload suggestions and update sidebar badge
      loadPendingSuggestions();
      refetchPendingCount();
      setSelectedSuggestion(null);
      setRejectReason('');
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'שגיאה באישור ההסבר';
      setError(`❌ ${errorMsg}`);
      console.error('Approval error:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReject = async (suggestionId) => {
    if (!rejectReason.trim()) {
      setError('חובה להזין סיבה לדחיה');
      return;
    }

    try {
      setIsProcessing(true);
      setError(null);
      await suggestionsAPI.reject(suggestionId, { review_note: rejectReason });
      
      setSuccessMessage('ההסבר נדחה בהצלחה ❌');
      setTimeout(() => setSuccessMessage(''), 3000);
      
      // Reload suggestions and update sidebar badge
      loadPendingSuggestions();
      refetchPendingCount();
      setSelectedSuggestion(null);
      setRejectReason('');
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'שגיאה בדחיית ההסבר';
      setError(`❌ ${errorMsg}`);
      console.error('Reject error:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  const filteredSuggestions = filterMunicipality
    ? pending.filter(s => s.municipality_id.toString() === filterMunicipality)
    : pending;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-gray-50">
      {/* Header */}
      <div className="sticky top-0 z-40 bg-gradient-to-r from-slate-900 to-slate-800 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white font-hebrew">👨‍💼 ממשק בדיקה ואישור</h1>
            <p className="text-slate-300 font-hebrew text-sm mt-1">ניהול הסברים בהמתנה מעובדים</p>
          </div>
          <button
            onClick={() => navigate('/admin')}
            className="px-4 py-2 bg-white text-slate-900 font-hebrew font-semibold rounded-lg hover:bg-slate-100 transition"
          >
            ← חזור לעמוד הבית
          </button>
        </div>
      </div>

      <main className="max-w-6xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Badge and Info */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-slate-900 font-hebrew">
              📋 הסברים בהמתנה לאישור
            </h2>
            <p className="text-slate-600 font-hebrew mt-1">
              סך הכל: <span className="font-bold text-blue-600">{pending.length}</span> בקשות
            </p>
          </div>
          <div className="flex items-center justify-center w-16 h-16 bg-red-100 rounded-full">
            <span className="text-3xl font-bold text-red-600">{pending.length}</span>
          </div>
        </div>

        {/* Success message */}
        {successMessage && (
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-green-700 font-hebrew font-semibold">{successMessage}</p>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-700 font-hebrew font-semibold">❌ {error}</p>
          </div>
        )}

        {/* Filter */}
        {pending.length > 0 && (
          <div className="flex gap-4">
            <input
              type="text"
              placeholder="סנן לפי מוניציפליטה..."
              value={filterMunicipality}
              onChange={(e) => setFilterMunicipality(e.target.value)}
              className="flex-1 px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
            {filterMunicipality && (
              <button
                onClick={() => setFilterMunicipality('')}
                className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                ✕ נקה
              </button>
            )}
          </div>
        )}

        {/* Loading state */}
        {loading && (
          <div className="flex items-center justify-center py-16">
            <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        )}

        {/* No suggestions */}
        {!loading && filteredSuggestions.length === 0 && (
          <div className="text-center py-12 bg-green-50 rounded-xl border border-green-200">
            <p className="text-lg text-green-700 font-hebrew font-semibold">
              ✅ אין בקשות בהמתנה!
            </p>
            <p className="text-slate-600 font-hebrew mt-2">
              כל ההסברים אושרו או נדחו.
            </p>
          </div>
        )}

        {/* Suggestions list */}
        {!loading && filteredSuggestions.length > 0 && (
          <div className="space-y-4">
            {filteredSuggestions.map(suggestion => (
              <div
                key={suggestion.id}
                className={`p-6 border rounded-xl transition ${
                  selectedSuggestion?.id === suggestion.id
                    ? 'bg-blue-50 border-blue-300'
                    : 'bg-white border-slate-200 hover:border-blue-300'
                }`}
              >
                {/* Summary row */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <h3 className="text-lg font-bold text-slate-900 font-hebrew">
                      {suggestion.suggester_name || 'עובד'}
                    </h3>
                    <p className="text-sm text-slate-600 font-hebrew mt-1">
                      מוניציפליטה: <span className="font-semibold">{suggestion.municipality_id}</span> | 
                      חודש: <span className="font-semibold">{suggestion.month}</span> |
                      קוד: <span className="font-semibold">{suggestion.topic_code}</span>
                    </p>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-sm font-hebrew font-bold ${
                    suggestion.suggestion_type === 'reason'
                      ? 'bg-green-100 text-green-700'
                      : suggestion.suggestion_type === 'preset'
                      ? 'bg-blue-100 text-blue-700'
                      : 'bg-purple-100 text-purple-700'
                  }`}>
                    {suggestion.suggestion_type === 'reason' ? '📚 Reason Library' : suggestion.suggestion_type === 'preset' ? '📋 preset' : '✍️ custom'}
                  </span>
                </div>

                {/* Show reason details if from Reasons Library */}
                {suggestion.suggestion_type === 'reason' && suggestion.reason_code && reasonsMap[suggestion.reason_code] && (
                  <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <p className="text-sm text-slate-600 font-hebrew font-semibold mb-1">מסיבה:</p>
                        <p className="text-lg font-hebrew font-bold text-green-900">
                          {reasonsMap[suggestion.reason_code].title_hebrew}
                        </p>
                        <p className="text-xs text-slate-600 font-hebrew mt-1">
                          קוד: {suggestion.reason_code} | קטגוריה: {reasonsMap[suggestion.reason_code].category}
                        </p>
                      </div>
                      {reasonsMap[suggestion.reason_code].severity && (
                        <span className={`px-2 py-1 rounded text-xs font-hebrew font-semibold ${
                          reasonsMap[suggestion.reason_code].severity === 'routine' ? 'bg-green-200 text-green-800' :
                          reasonsMap[suggestion.reason_code].severity === 'attention' ? 'bg-amber-200 text-amber-800' :
                          'bg-red-200 text-red-800'
                        }`}>
                          {reasonsMap[suggestion.reason_code].severity === 'routine' ? '🟢 שגרה' : 
                           reasonsMap[suggestion.reason_code].severity === 'attention' ? '🟡 לתשומת לב' : '🔴 דחוף'}
                        </span>
                      )}
                    </div>
                    {suggestion.detail_value && (
                      <p className="text-sm text-slate-700 font-hebrew mt-2 bg-white p-2 rounded">
                        <span className="font-semibold">פרט:</span> {suggestion.detail_value}
                      </p>
                    )}
                  </div>
                )}

                {/* Content - Show suggested explanation with comparison */}
                <div className="space-y-4 mb-4">
                  {/* Employee's Suggested Explanation */}
                  <div className="bg-blue-50 border-l-4 border-l-blue-500 p-4 rounded-lg">
                    <p className="text-sm text-blue-700 font-hebrew font-semibold mb-2">💡 הסבר מוצע מהעובד:</p>
                    {suggestion.custom_text || suggestion.preset_text ? (
                      <p className="text-slate-900 font-hebrew text-base leading-relaxed font-bold">
                        "{suggestion.custom_text || suggestion.preset_text}"
                      </p>
                    ) : (
                      <p className="text-red-600 font-hebrew italic">
                        ⚠️ לא מצא הסבר מוצע
                      </p>
                    )}
                    {suggestion.preset_text && (
                      <p className="text-xs text-blue-600 font-hebrew mt-2">
                        (מהספרייה המובנית)
                      </p>
                    )}
                  </div>

                  {/* Comparison with changes (if editing existing) */}
                  {suggestion.previous_text && (
                    <div className="bg-amber-50 border-l-4 border-l-amber-500 p-4 rounded-lg">
                      <p className="text-sm text-amber-700 font-hebrew font-semibold mb-2">🔄 שינויים בהסבר:</p>
                      <div className="space-y-2">
                        <div>
                          <p className="text-xs text-slate-600 font-hebrew mb-1">הסבר קודם:</p>
                          <p className="text-slate-700 font-hebrew line-through text-sm">
                            {suggestion.previous_text}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-blue-600 font-hebrew mb-1">הסבר חדש:</p>
                          <p className="text-blue-900 font-hebrew font-bold text-sm">
                            {suggestion.custom_text || suggestion.preset_text}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Action buttons */}
                {selectedSuggestion?.id === suggestion.id && (
                  <div className="space-y-4 bg-white p-4 rounded-lg border border-slate-200">
                    {/* Approve button */}
                    <button
                      onClick={() => handleApprove(suggestion.id)}
                      disabled={isProcessing}
                      className="w-full px-6 py-3 bg-green-600 text-white font-hebrew font-bold rounded-lg hover:bg-green-700 transition disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      {isProcessing ? (
                        <>
                          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                          מעבד...
                        </>
                      ) : (
                        <>✅ אשר</>
                      )}
                    </button>

                    {/* Reject section */}
                    <div className="space-y-2">
                      <label className="block text-sm font-hebrew font-semibold text-slate-900">
                        סיבת דחיה (אם בחרת לדחות):
                      </label>
                      <textarea
                        value={rejectReason}
                        onChange={(e) => setRejectReason(e.target.value)}
                        placeholder="לדוגמה: ההסבר לא ברור מספיק או שלא תואם את הנתונים"
                        className="w-full p-3 border border-slate-300 rounded-lg font-hebrew text-right focus:ring-2 focus:ring-red-500 resize-none h-24"
                      />
                      <button
                        onClick={() => handleReject(suggestion.id)}
                        disabled={isProcessing || !rejectReason.trim()}
                        className="w-full px-6 py-3 bg-red-600 text-white font-hebrew font-bold rounded-lg hover:bg-red-700 transition disabled:opacity-50 flex items-center justify-center gap-2"
                      >
                        {isProcessing ? (
                          <>
                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                            מעבד...
                          </>
                        ) : (
                          <>❌ דחה</>
                        )}
                      </button>
                    </div>
                  </div>
                )}

                {/* Select button (if not selected) */}
                {selectedSuggestion?.id !== suggestion.id && (
                  <button
                    onClick={() => {
                      setSelectedSuggestion(suggestion);
                      setRejectReason('');
                      setError(null);
                    }}
                    className="w-full px-4 py-2 border border-blue-300 text-blue-600 font-hebrew font-semibold rounded-lg hover:bg-blue-50 transition"
                  >
                    👉 בחר להערכה
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
