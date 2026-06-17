export const REVIEW_STATUS_OPTIONS = [
  { value: 'pending', label: 'ממתין לבדיקה' },
  { value: 'in_review', label: 'בבדיקה' },
  { value: 'reviewed', label: 'נבדק' },
  { value: 'flagged', label: 'דורש תשומת לב' },
];

export function getReviewStatusLabel(status) {
  const option = REVIEW_STATUS_OPTIONS.find((x) => x.value === status);
  return option?.label || 'ממתין לבדיקה';
}

export function getReviewStatusPillClass(status) {
  switch (status) {
    case 'in_review':
      return 'bg-blue-50 text-blue-700 border-blue-200';
    case 'reviewed':
      return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    case 'flagged':
      return 'bg-amber-50 text-amber-800 border-amber-200';
    case 'pending':
    default:
      return 'bg-slate-50 text-slate-700 border-slate-200';
  }
}

export function formatReviewDate(dateStr) {
  if (!dateStr) return '';
  try {
    return new Date(dateStr).toLocaleString('he-IL');
  } catch {
    return '';
  }
}
