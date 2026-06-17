import React from 'react';
import { formatShekel } from '../../utils/format';

export default function MonthlySnapshot({ invoiceTotal, breakdownTotal, difference, statusKey }) {
  const hasDifference = Math.abs(Number(difference || 0)) > 1;
  const paidBoxClass = statusKey === 'balanced'
    ? 'bg-green-600'
    : statusKey === 'current_gap'
      ? 'bg-indigo-600'
      : statusKey === 'awaiting_data'
        ? 'bg-slate-500'
        : 'bg-red-600';
  const diffBoxClass = statusKey === 'balanced'
    ? 'bg-green-600'
    : statusKey === 'current_gap'
      ? 'bg-indigo-600'
      : statusKey === 'awaiting_data'
        ? 'bg-slate-500'
        : 'bg-red-600';

  return (
    <div className="grid grid-cols-3 gap-6 mb-8">
      {/* Box 1: סכום מגיע */}
      <div className="bg-primary-500 text-white rounded-lg p-8 shadow-md">
        <div className="text-sm text-primary-100 mb-3 font-hebrew">סכום מגיע</div>
        <div className="text-4xl font-bold mb-2">{formatShekel(breakdownTotal)}</div>
        <div className="text-sm text-primary-100 font-hebrew">לחודש זה</div>
      </div>

      {/* Box 2: סכום שולם */}
      <div className={`rounded-lg p-8 shadow-md text-white ${paidBoxClass}`}>
        <div className="text-sm mb-3 font-hebrew text-white/80">
          סכום שולם
        </div>
        <div className="text-4xl font-bold mb-2">{formatShekel(invoiceTotal)}</div>
        <div className="text-sm font-hebrew text-white/80">
          {statusKey === 'balanced'
            ? 'הועבר במלואו'
            : statusKey === 'awaiting_data'
              ? 'ממתין לנתונים'
              : statusKey === 'current_gap'
                ? 'יתרה לביצוע'
                : 'נדרש בירור'}
        </div>
      </div>

      {/* Box 3: הפרש */}
      <div className={`rounded-lg p-8 shadow-md text-white ${diffBoxClass}`}>
        <div className="text-sm mb-3 font-hebrew text-white/80">
          הפרש
        </div>
        <div className="text-4xl font-bold mb-2">{formatShekel(Math.abs(difference))}</div>
        <div className="text-sm font-hebrew text-white/80">
          {!hasDifference
            ? 'אין הפרש'
            : statusKey === 'current_gap'
              ? 'יתרה לביצוע'
              : difference > 0
                ? 'יתרה פתוחה'
                : 'תשלום יתר'}
        </div>
      </div>
    </div>
  );
}
