import React, { useMemo, useState } from 'react';
import {
  REVIEW_STATUS_OPTIONS,
  getReviewStatusLabel,
  getReviewStatusPillClass,
  formatReviewDate,
} from '../../utils/reviewStatus';

export default function ReviewStatusControl({
  status = 'pending',
  note = '',
  reviewerName = '',
  reviewedAt = '',
  editable = false,
  onPersist,
}) {
  const [currentStatus, setCurrentStatus] = useState(status || 'pending');
  const [currentNote, setCurrentNote] = useState(note || '');
  const [currentReviewerName, setCurrentReviewerName] = useState(reviewerName || '');
  const [currentReviewedAt, setCurrentReviewedAt] = useState(reviewedAt || '');
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState('');

  const [modalOpen, setModalOpen] = useState(false);
  const [flagNote, setFlagNote] = useState('');
  const [flagError, setFlagError] = useState('');

  const showCaption = ['reviewed', 'flagged'].includes(currentStatus) && currentReviewedAt;

  const selectValue = currentStatus;

  const headerLabel = useMemo(() => getReviewStatusLabel(currentStatus), [currentStatus]);

  const applyPersistResult = (result) => {
    if (!result || typeof result !== 'object') return;
    if (result.reviewed_by_name !== undefined) {
      setCurrentReviewerName(result.reviewed_by_name || '');
    }
    if (result.reviewed_at !== undefined) {
      setCurrentReviewedAt(result.reviewed_at || '');
    }
    if (result.review_status_note !== undefined) {
      setCurrentNote(result.review_status_note || '');
    }
  };

  const persistChange = async (nextStatus, nextNote) => {
    if (!onPersist) return;
    setSaving(true);
    const prev = {
      status: currentStatus,
      note: currentNote,
      reviewerName: currentReviewerName,
      reviewedAt: currentReviewedAt,
    };

    setCurrentStatus(nextStatus);
    if (nextStatus === 'flagged') {
      setCurrentNote(nextNote || '');
    } else if (['pending', 'in_review'].includes(nextStatus)) {
      setCurrentNote('');
    }

    try {
      const result = await onPersist({ status: nextStatus, note: nextNote || '' });
      applyPersistResult(result);
      setToast('✅ סטטוס נשמר בהצלחה');
      setTimeout(() => setToast(''), 2500);
    } catch (err) {
      setCurrentStatus(prev.status);
      setCurrentNote(prev.note);
      setCurrentReviewerName(prev.reviewerName);
      setCurrentReviewedAt(prev.reviewedAt);
      setToast('❌ שמירה נכשלה');
      setTimeout(() => setToast(''), 3000);
    } finally {
      setSaving(false);
    }
  };

  const handleSelectChange = async (event) => {
    const nextStatus = event.target.value;
    if (nextStatus === currentStatus) return;

    if (nextStatus === 'flagged') {
      setFlagNote('');
      setFlagError('');
      setModalOpen(true);
      return;
    }

    await persistChange(nextStatus, '');
  };

  const confirmFlagged = async () => {
    if (!flagNote.trim()) {
      setFlagError('חובה להזין הערה');
      return;
    }
    setFlagError('');
    setModalOpen(false);
    await persistChange('flagged', flagNote.trim());
  };

  return (
    <div className="text-right" dir="rtl">
      <div className="flex flex-col md:flex-row md:items-center gap-2 md:gap-3">
        <span
          data-testid="review-status-pill"
          className={`inline-flex items-center px-3 py-1 rounded-full border text-sm font-hebrew font-semibold ${getReviewStatusPillClass(currentStatus)}`}
        >
          {headerLabel}
        </span>

        {editable && (
          <select
            aria-label="שינוי סטטוס בדיקה"
            data-testid="review-status-select"
            value={selectValue}
            onChange={handleSelectChange}
            disabled={saving}
            className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm font-hebrew bg-white"
          >
            {REVIEW_STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        )}
      </div>

      {showCaption && (
        <p data-testid="review-status-caption" className="text-xs text-slate-600 font-hebrew mt-1">
          נבדק על ידי {currentReviewerName || 'משתמש מערכת'} • {formatReviewDate(currentReviewedAt)}
        </p>
      )}

      {toast && (
        <p data-testid="review-status-toast" className="text-xs font-hebrew mt-1 text-slate-700">
          {toast}
        </p>
      )}

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4" data-testid="flag-note-modal">
          <div className="w-full max-w-md bg-white rounded-2xl p-5 shadow-xl" dir="rtl">
            <h3 className="font-hebrew font-bold text-lg text-slate-900 mb-2">דורש תשומת לב</h3>
            <p className="font-hebrew text-sm text-slate-600 mb-3">יש להזין הערה לפני שמירה</p>
            <textarea
              data-testid="flag-note-input"
              value={flagNote}
              onChange={(e) => setFlagNote(e.target.value)}
              className="w-full h-24 border border-slate-300 rounded-lg p-3 font-hebrew text-sm"
              placeholder="מה דורש תשומת לב?"
            />
            {flagError && <p className="text-red-600 text-xs font-hebrew mt-2">{flagError}</p>}
            <div className="mt-4 flex items-center gap-2 justify-end">
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="px-3 py-2 border border-slate-300 rounded-lg font-hebrew text-sm"
              >
                ביטול
              </button>
              <button
                type="button"
                onClick={confirmFlagged}
                className="px-3 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg font-hebrew text-sm"
              >
                שמירה
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
