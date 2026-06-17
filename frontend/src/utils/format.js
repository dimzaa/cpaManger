// Hebrew month names
import { formatShekel as formatShekelCore } from './formatShekel';

// Hebrew month names
const hebrewMonths = {
  '01': 'ינואר',
  '02': 'פברואר',
  '03': 'מרץ',
  '04': 'אפריל',
  '05': 'מאי',
  '06': 'יוני',
  '07': 'יולי',
  '08': 'אוגוסט',
  '09': 'ספטמבר',
  '10': 'אוקטובר',
  '11': 'נובמבר',
  '12': 'דצמבר',
};

/**
 * Format YYYY-MM to Hebrew month name
 * Example: "2024-03" → "מרץ 2024"
 */
export function formatHebrewDate(dateStr) {
  if (!dateStr) return '';
  const [year, month] = dateStr.split('-');
  const monthName = hebrewMonths[month] || month;
  return `${monthName} ${year}`;
}

/**
 * Format number as Israeli shekel amount
 * Example: 450000 → "₪ 450,000"
 */
export function formatShekel(amount) {
  return formatShekelCore(amount);
}

/**
 * Calculate difference between two amounts
 * Returns: { amount, percentage, isPositive }
 */
export function calculateDifference(current, previous) {
  if (!previous || previous === 0) {
    return {
      amount: current,
      percentage: 0,
      isPositive: current >= 0,
    };
  }

  const diff = current - previous;
  const percentage = ((diff / previous) * 100).toFixed(1);

  return {
    amount: diff,
    percentage: Math.abs(parseFloat(percentage)),
    isPositive: diff >= 0,
  };
}

/**
 * Get status badge color based on line type
 */
export function getLineTypeColor(lineType) {
  switch (lineType) {
    case 'retro':
      return { bg: 'bg-warning/10', border: 'border-l-4 border-warning', badge: 'bg-warning text-white' };
    case 'shortage':
      return { bg: 'bg-danger/10', border: 'border-l-4 border-danger', badge: 'bg-danger text-white' };
    case 'adjustment':
      return { bg: 'bg-primary-500/10', border: 'border-l-4 border-primary-500', badge: 'bg-primary-500 text-white' };
    case 'regular':
    default:
      return { bg: 'bg-white', border: '', badge: '' };
  }
}

/**
 * Get line type label in Hebrew
 */
export function getLineTypeLabel(lineType) {
  const labels = {
    regular: 'רגיל',
    retro: 'תשלום רטרו',
    shortage: 'חוסר',
    adjustment: 'התאמה',
  };
  return labels[lineType] || lineType;
}

/**
 * Get status badge color based on month status
 */
export function getStatusColor(isBalanced, hasRetro) {
  if (hasRetro) return { bg: 'bg-warning/10', text: 'text-warning', label: 'תשלום רטרו' };
  if (!isBalanced) return { bg: 'bg-danger/10', text: 'text-danger', label: 'חריגה' };
  return { bg: 'bg-success/10', text: 'text-success', label: 'מאוזן' };
}

/**
 * Last 6 months from current date
 */
export function getLast6Months() {
  const months = [];
  const now = new Date();
  
  for (let i = 5; i >= 0; i--) {
    const date = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    months.push({
      value: `${year}-${month}`,
      label: formatHebrewDate(`${year}-${month}`),
    });
  }
  
  return months;
}

/**
 * Last 12 months from current date
 */
export function getLast12Months() {
  const months = [];
  const now = new Date();
  
  for (let i = 11; i >= 0; i--) {
    const date = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    months.push({
      value: `${year}-${month}`,
      label: formatHebrewDate(`${year}-${month}`),
    });
  }
  
  return months;
}

/**
 * Current month in YYYY-MM format
 */
export function getCurrentMonth() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  return `${year}-${month}`;
}

/**
 * Format currency amount as Israeli shekel
 * Example: 450000 → "₪ 450,000"
 */
export const formatCurrency = (amount) => {
  return `₪ ${Number(amount).toLocaleString('he-IL')}`;
};

/**
 * Format month string to Hebrew month name
 * Example: "2024-03" → "מרץ 2024"
 */
export const formatMonth = (monthStr) => {
  const months = {
    '01': 'ינואר', '02': 'פברואר', '03': 'מרץ',
    '04': 'אפריל', '05': 'מאי', '06': 'יוני',
    '07': 'יולי', '08': 'אוגוסט', '09': 'ספטמבר',
    '10': 'אוקטובר', '11': 'נובמבר', '12': 'דצמבר'
  };
  const [year, month] = monthStr.split('-');
  return `${months[month]} ${year}`;
};

/**
 * Format date string to Hebrew locale date
 * Example: "2024-03-15" → "15.3.2024"
 */
export const formatDate = (dateStr) => {
  return new Date(dateStr).toLocaleDateString('he-IL');
};
