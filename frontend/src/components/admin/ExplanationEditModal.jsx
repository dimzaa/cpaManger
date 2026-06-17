import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { explanationsAPI } from '../../services/api';

/**
 * ExplanationEditModal - Modal for CPA to edit custom explanations
 * Opens when pen icon is clicked on a budget line
 */
export default function ExplanationEditModal({
  isOpen,
  municipalityId,
  month,
  topicCode,
  topicName,
  currentExplanation,
  onClose,
  onSave
}) {
  const [customText, setCustomText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // Initialize with current explanation
  useEffect(() => {
    if (isOpen && currentExplanation) {
      setCustomText(currentExplanation);
      setError(null);
      setSuccessMessage(null);
    } else if (isOpen) {
      setCustomText('');
      setError(null);
      setSuccessMessage(null);
    }
  }, [isOpen, currentExplanation]);

  const handleSave = async () => {
    if (!customText.trim()) {
      setError('נא להקליד הסבר');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setSuccessMessage(null);

      // Log for debugging
      console.log('📝 [ExplanationEditModal] Saving explanation...', {
        municipalityId,
        month,
        topicCode,
        textLength: customText.length,
        endpoint: `/api/explanations/${municipalityId}/${month}/${topicCode}`
      });

      // Save explanation
      const response = await explanationsAPI.saveExplanation(
        municipalityId,
        month,
        topicCode,
        customText
      );

      console.log('✅ [ExplanationEditModal] Save successful:', response?.data);
      setSuccessMessage('ההסבר נשמר בהצלחה! ✅');
      
      // Call onSave callback
      if (onSave) {
        console.log('📢 [ExplanationEditModal] Calling onSave callback');
        onSave(customText);
      }

      // Close modal after short delay
      setTimeout(() => {
        handleClose();
      }, 1500);
    } catch (err) {
      console.error('❌ [ExplanationEditModal] Error saving explanation:', {
        error: err,
        message: err.message,
        response: err.response?.data,
        status: err.response?.status,
        config: {
          method: err.config?.method,
          url: err.config?.url,
          data: err.config?.data,
          headers: err.config?.headers
        }
      });
      setError(err.response?.data?.detail || err.message || 'שגיאה בשמירת ההסבר');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setCustomText('');
    setError(null);
    setSuccessMessage(null);
    onClose();
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-96 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-neutral-200">
          <div>
            <h2 className="text-2xl font-bold text-neutral-900 font-hebrew">
              ✏️ עריכת הסבר
            </h2>
            <p className="text-sm text-neutral-600 font-hebrew mt-1">
              {topicName} (קוד {topicCode})
            </p>
          </div>
          <button
            onClick={handleClose}
            disabled={loading}
            className="p-2 hover:bg-neutral-100 rounded-lg transition text-neutral-600 hover:text-neutral-900"
          >
            <X size={24} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6">
          <div>
            <label className="block text-sm font-hebrew font-semibold text-neutral-700 mb-3">
              הסבר מותאם אישית
            </label>
            <textarea
              value={customText}
              onChange={(e) => setCustomText(e.target.value)}
              disabled={loading}
              placeholder="כתוב הסבר בעברית עבור בנק הנתונים המוניציפלי..."
              className="w-full h-32 p-4 border border-neutral-300 rounded-lg font-hebrew text-base resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-neutral-100"
            />
            <p className="text-xs text-neutral-500 font-hebrew mt-2">
              {customText.length} תווים
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm font-hebrew">
              ❌ {error}
            </div>
          )}

          {/* Success Message */}
          {successMessage && (
            <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm font-hebrew">
              {successMessage}
            </div>
          )}
        </div>

        {/* Footer - Buttons */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-neutral-200 bg-neutral-50">
          <button
            onClick={handleClose}
            disabled={loading}
            className="px-6 py-2 border border-neutral-300 rounded-lg text-neutral-700 font-hebrew font-semibold hover:bg-neutral-100 transition disabled:opacity-50"
          >
            ביטול
          </button>
          <button
            onClick={handleSave}
            disabled={loading || !customText.trim()}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-hebrew font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                שומר...
              </span>
            ) : (
              '💾 שמור'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
