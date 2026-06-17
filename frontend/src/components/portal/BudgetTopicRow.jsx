import React, { useState } from 'react';
import { formatShekel } from '../../utils/format';
import ExplanationBox from './ExplanationBox';
import { explanationsAPI } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

export default function BudgetTopicRow({ 
  line, 
  invoiceMonth,
  municipalityId,
  explanation,
  isCustomExplanation
}) {
  const { user } = useAuth();
  const [isExplanationOpen, setIsExplanationOpen] = useState(false);
  const [currentExplanation, setCurrentExplanation] = useState(explanation);
  const [isCustom, setIsCustom] = useState(isCustomExplanation || false);
  const [isSaving, setIsSaving] = useState(false);

  let badgeColor = 'bg-neutral-200 text-neutral-800';
  let badgeLabel = 'רגיל';

  if (line.line_type === 'retro') {
    badgeColor = 'bg-yellow-200 text-yellow-900';
    badgeLabel = 'רטרו';
  } else if (line.line_type === 'shortage') {
    badgeColor = 'bg-red-200 text-red-900';
    badgeLabel = 'חוסר';
  } else if (line.line_type === 'adjustment') {
    badgeColor = 'bg-blue-200 text-blue-900';
    badgeLabel = 'התאמה';
  }

  // Determine row background color
  let rowBg = '';
  if (line.line_type === 'retro') rowBg = 'bg-yellow-50';
  else if (line.line_type === 'shortage') rowBg = 'bg-red-50';
  else if (line.line_type === 'adjustment') rowBg = 'bg-blue-50';

  const handleSaveExplanation = async (newText) => {
    try {
      setIsSaving(true);
      await explanationsAPI.saveExplanation(
        municipalityId,
        invoiceMonth,
        line.topic_code,
        newText
      );
      setCurrentExplanation(newText);
      setIsCustom(true);
    } catch (error) {
      console.error('Failed to save explanation:', error);
      throw error;
    } finally {
      setIsSaving(false);
    }
  };

  const hasNotes = currentExplanation && currentExplanation.trim().length > 0;

  return (
    <>
      <tr className={`border-b border-neutral-200 text-right ${rowBg} cursor-pointer hover:bg-opacity-75 transition`}
          onClick={() => hasNotes && setIsExplanationOpen(!isExplanationOpen)}>
        <td className="px-6 py-4 font-medium text-neutral-900 font-hebrew">{line.budget_topic}</td>
        <td className="px-6 py-4 text-sm text-neutral-600 font-hebrew">
          {line.period_month !== invoiceMonth ? (
            <span className="text-yellow-700 font-medium">{line.period_month} (רטרו)</span>
          ) : (
            invoiceMonth
          )}
        </td>
        <td className="px-6 py-4 font-bold">{formatShekel(line.amount)}</td>
        <td className="px-6 py-4">
          <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${badgeColor}`}>
            {badgeLabel}
          </span>
        </td>
        <td className="px-6 py-4 text-sm text-neutral-600 font-hebrew">
          {hasNotes ? (
            <span className="inline-flex items-center gap-2 cursor-pointer hover:text-primary-600">
              📝 {isExplanationOpen ? 'הסתר' : 'הצג'} הסבר
            </span>
          ) : (
            '—'
          )}
        </td>
      </tr>
      {isExplanationOpen && hasNotes && (
        <tr className={`${rowBg}`}>
          <td colSpan="5" className="px-6 py-4">
            <ExplanationBox
              explanation={currentExplanation}
              isCustom={isCustom}
              municipalityId={municipalityId}
              month={invoiceMonth}
              topicCode={line.topic_code}
              onSave={handleSaveExplanation}
              isLoading={isSaving}
            />
          </td>
        </tr>
      )}
    </>
  );
}
