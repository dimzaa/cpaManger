function parseMonthAnchor(month) {
  if (!month || typeof month !== 'string' || month.length !== 7) return null;
  const year = Number(month.slice(0, 4));
  const mon = Number(month.slice(5, 7));
  if (!Number.isFinite(year) || !Number.isFinite(mon) || mon < 1 || mon > 12) return null;

  // Use the first day of the following month as reporting anchor.
  return new Date(year, mon, 1);
}

export function isGapOlderThanDays(month, days = 60, now = new Date()) {
  const anchor = parseMonthAnchor(month);
  if (!anchor) return false;
  const ageMs = now.getTime() - anchor.getTime();
  const ageDays = ageMs / (1000 * 60 * 60 * 24);
  return ageDays > days;
}

export function getBudgetStatus({ dueAmount = 0, paidAmount = 0, month = null, now = new Date() }) {
  const due = Number(dueAmount || 0);
  const paid = Number(paidAmount || 0);

  // Zero due and zero paid should be treated as neutral/balanced.
  if (due === 0 && paid === 0) {
    return { key: 'balanced', diff: 0 };
  }

  const diff = due - paid;
  if (Math.abs(diff) <= 1) {
    return { key: 'balanced', diff };
  }

  // Overpayment is always a deviation.
  if (diff < -1) {
    return { key: 'deviation', diff };
  }

  // Positive gap can be current cycle (neutral) or overdue (deviation).
  if (isGapOlderThanDays(month, 60, now)) {
    return { key: 'deviation_overdue', diff };
  }

  return { key: 'current_gap', diff };
}

export function getBudgetStatusBadge(statusKey) {
  if (statusKey === 'awaiting_data') {
    return {
      icon: '⏳',
      text: 'ממתין לנתונים',
      className: 'bg-slate-50 text-slate-700 border-slate-200',
    };
  }

  if (statusKey === 'balanced') {
    return {
      icon: '✅',
      text: 'מאוזן',
      className: 'bg-green-50 text-green-700 border-green-200',
    };
  }

  if (statusKey === 'current_gap') {
    return {
      icon: 'ℹ️',
      text: 'יתרה לביצוע',
      className: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    };
  }

  if (statusKey === 'deviation_overdue') {
    return {
      icon: '⚠️',
      text: 'חריגה',
      className: 'bg-red-50 text-red-700 border-red-200',
    };
  }

  return {
    icon: '⚠️',
    text: 'חריגה',
    className: 'bg-red-50 text-red-700 border-red-200',
  };
}
