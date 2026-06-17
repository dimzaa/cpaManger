import React, { useState, useEffect } from 'react';
import { Edit2, X, Check, AlertCircle } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { explanationsAPI } from '../../services/api';

/**
 * ExplanationBox Component
 * 
 * Displays the explanation for a single budget line item.
 * - Auto-generated from templates (default)
 * - Custom (if CPA admin overrode it)
 * - Shows detected changes from previous month
 * - Shows financial impact
 * - Allows CPA admin to create/edit custom explanations
 */

export default function ExplanationBox({ 
  municipalityId, 
  month, 
  topicCode,
  topicName,
  onSave,
  onUpdate 
}) {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  
  const [explanation, setExplanation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState('');
  const [saving, setSaving] = useState(false);

  // Load the explanation from API
  useEffect(() => {
    loadExplanation();
  }, [municipalityId, month, topicCode]);

  const loadExplanation = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await explanationsAPI.getExplanation(
        municipalityId,
        month,
        topicCode
      );
      setExplanation(response.data || response);
      setEditText(response.data?.explanation || response.explanation || '');
    } catch (err) {
      setError(err.message || 'Failed to load explanation');
      console.error('Error loading explanation:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!editText.trim()) {
      setError('הסבר לא יכול להיות ריק');
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await explanationsAPI.saveCustomExplanation(
        municipalityId,
        month,
        topicCode,
        editText
      );
      
      setIsEditing(false);
      await loadExplanation();
      if (onSave) onSave();
      if (onUpdate) onUpdate();
    } catch (err) {
      setError(err.message || 'Failed to save explanation');
      console.error('Error saving explanation:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setEditText(explanation?.explanation || '');
    setIsEditing(false);
    setError(null);
  };

  const handleDelete = async () => {
    if (!explanation?.is_custom) return;
    
    if (!window.confirm('האם אתה בטוח שברצונך למחוק את ההסבר המותאם?')) {
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await explanationsAPI.deleteCustomExplanation(
        municipalityId,
        month,
        topicCode
      );
      
      await loadExplanation();
      if (onUpdate) onUpdate();
    } catch (err) {
      setError(err.message || 'Failed to delete explanation');
      console.error('Error deleting explanation:', err);
    } finally {
      setSaving(false);
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 animate-pulse">
        <div className="h-4 bg-gray-300 rounded w-3/4 mb-2"></div>
        <div className="h-4 bg-gray-300 rounded w-1/2"></div>
      </div>
    );
  }

  // Error state
  if (error && !explanation) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-center gap-2 text-red-700">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
        <button 
          onClick={loadExplanation}
          className="mt-2 px-3 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 text-sm font-medium"
        >
          נסה שוב
        </button>
      </div>
    );
  }

  // Editing mode
  if (isEditing && isAdmin) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="font-hebrew font-semibold text-sm mb-2">עריכת הסבר</h4>
        <textarea
          value={editText}
          onChange={(e) => setEditText(e.target.value)}
          className="w-full p-3 border border-blue-300 rounded font-hebrew text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
          rows={4}
          dir="rtl"
          disabled={saving}
        />
        {error && (
          <div className="mt-2 text-sm text-red-600 flex items-center gap-1">
            <AlertCircle size={14} />
            {error}
          </div>
        )}
        <div className="flex gap-2 mt-3 justify-end">
          <button
            onClick={handleCancel}
            disabled={saving}
            className="px-3 py-1 text-gray-600 hover:text-gray-900 flex items-center gap-1 text-sm disabled:opacity-50"
          >
            <X size={16} />
            ביטול
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !editText.trim()}
            className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 flex items-center gap-1 text-sm font-medium"
          >
            {saving ? (
              <>
                <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                שמירה...
              </>
            ) : (
              <>
                <Check size={16} />
                שמור
              </>
            )}
          </button>
        </div>
      </div>
    );
  }

  // Display mode
  return (
    <div className={`rounded-lg p-4 border relative group ${
      explanation?.is_custom 
        ? 'bg-amber-50 border-amber-200' 
        : 'bg-blue-50 border-blue-200'
    }`}>
      {/* Header with topic info */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1">
          <h4 className="font-hebrew font-semibold text-sm text-gray-800">
            {topicName}
          </h4>
          <p className="text-xs text-gray-500">קוד {topicCode}</p>
        </div>
        <div className="flex gap-1">
          {explanation?.is_custom && (
            <span className="inline-block px-2 py-1 bg-amber-100 text-amber-700 text-xs font-hebrew rounded">
              ✏️ מותאם
            </span>
          )}
          {explanation?.is_retro && (
            <span className="inline-block px-2 py-1 bg-purple-100 text-purple-700 text-xs font-hebrew rounded">
              ↩️ רטרו
            </span>
          )}
          {explanation?.has_changes && (
            <span className="inline-block px-2 py-1 bg-green-100 text-green-700 text-xs font-hebrew rounded">
              📊 שינויים
            </span>
          )}
        </div>
      </div>

      {/* Explanation text */}
      <p className="font-hebrew text-sm text-gray-700 leading-relaxed mb-3 whitespace-pre-wrap" dir="rtl">
        {explanation?.explanation}
      </p>

      {/* Financial impact */}
      {explanation?.financial_impact && explanation?.financial_impact !== '₪0' && (
        <div className="bg-white rounded px-3 py-2 mb-3 border border-gray-200">
          <p className="text-xs text-gray-600 font-hebrew">
            <strong>השפעה כלכלית:</strong>
            <span className="text-green-700 font-semibold mr-2">
              {explanation.financial_impact}
            </span>
          </p>
        </div>
      )}

      {/* Changes detected */}
      {explanation?.has_changes && explanation?.changes?.length > 0 && (
        <div className="bg-white rounded px-3 py-2 mb-3 border border-gray-200">
          <p className="text-xs font-hebrew font-semibold text-gray-700 mb-1">
            🔍 שינויים מהתקופה הקודמת:
          </p>
          <ul className="text-xs text-gray-600 font-hebrew space-y-1 list-rtl">
            {explanation.changes.map((change, idx) => (
              <li key={idx} className="mr-4">
                • {change.hebrew_description}
                {change.impact_shekel && (
                  <span className="text-green-700 mr-2">({change.impact_shekel})</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Admin actions */}
      {isAdmin && (
        <div className="flex gap-2 justify-end mt-3 pt-3 border-t border-gray-300 opacity-0 group-hover:opacity-100 transition">
          {!explanation?.is_custom ? (
            <button
              onClick={() => {
                setEditText('');
                setIsEditing(true);
              }}
              className="px-3 py-1 text-blue-600 hover:text-blue-700 flex items-center gap-1 text-xs font-hebrew font-medium hover:bg-blue-100 rounded"
              title="צור הסבר מותאם"
            >
              <Edit2 size={14} />
              צור מותאם
            </button>
          ) : (
            <>
              <button
                onClick={() => setIsEditing(true)}
                className="px-3 py-1 text-blue-600 hover:text-blue-700 flex items-center gap-1 text-xs font-hebrew font-medium hover:bg-blue-100 rounded"
                title="ערוך הסבר מותאם"
              >
                <Edit2 size={14} />
                ערוך
              </button>
              <button
                onClick={handleDelete}
                disabled={saving}
                className="px-3 py-1 text-red-600 hover:text-red-700 flex items-center gap-1 text-xs font-hebrew font-medium hover:bg-red-100 rounded disabled:opacity-50"
                title="מחק הסבר מותאם"
              >
                <X size={14} />
                מחק
              </button>
            </>
          )}
        </div>
      )}

      {error && (
        <div className="mt-2 text-xs text-red-600 flex items-center gap-1">
          <AlertCircle size={14} />
          {error}
        </div>
      )}
    </div>
  );
}
