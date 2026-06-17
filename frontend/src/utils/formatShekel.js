/**
 * Executive rounding for financial display only.
 *
 * Disclosure rationale is aligned with common financial-reporting practice
 * (IAS 1 / US GAAP style presentation in thousands or millions with explicit unit disclosure).
 * Keep arithmetic on raw values and apply this formatter only at render time.
 */

export const ROUNDING_MODES = {
  EXACT: 'exact',
  THOUSANDS: 'thousands',
  MILLIONS: 'millions',
  AUTO: 'auto',
};

function toNumber(value) {
  if (value === null || value === undefined || value === '') return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function formatNumber(value, locale, minimumFractionDigits = 0, maximumFractionDigits = 0) {
  const formatted = new Intl.NumberFormat(locale, {
    minimumFractionDigits,
    maximumFractionDigits,
  }).format(value);

  // Remove directionality marks so output is stable in tests and string comparisons.
  return formatted.replace(/[\u200e\u200f\u061c]/g, '');
}

export function formatShekel(amount, { mode = ROUNDING_MODES.EXACT, locale = 'he-IL' } = {}) {
  const numericAmount = toNumber(amount);

  if (numericAmount === null) {
    return '₪ 0';
  }

  if (numericAmount === 0) {
    return '0';
  }

  if (mode === ROUNDING_MODES.THOUSANDS) {
    const value = numericAmount / 1000;
    return `${formatNumber(value, locale, 1, 1)} אלפי ₪`;
  }

  if (mode === ROUNDING_MODES.MILLIONS) {
    const value = numericAmount / 1_000_000;
    return `${formatNumber(value, locale, 2, 2)} מיליוני ₪`;
  }

  return `₪ ${formatNumber(numericAmount, locale, 0, 0)}`;
}

export function resolveAutoMode(amounts) {
  if (!Array.isArray(amounts) || amounts.length === 0) {
    return ROUNDING_MODES.EXACT;
  }

  const maxAbs = amounts.reduce((maxValue, amount) => {
    const numericAmount = toNumber(amount);
    if (numericAmount === null) return maxValue;
    const absValue = Math.abs(numericAmount);
    return absValue > maxValue ? absValue : maxValue;
  }, 0);

  if (maxAbs === 0 || maxAbs < 10_000) {
    return ROUNDING_MODES.EXACT;
  }

  if (maxAbs / 1000 < 1000) {
    return ROUNDING_MODES.THOUSANDS;
  }

  return ROUNDING_MODES.MILLIONS;
}

export function resolveConcreteMode(selectedMode, amounts) {
  if (selectedMode !== ROUNDING_MODES.AUTO) {
    return selectedMode;
  }
  return resolveAutoMode(amounts);
}

export function getRoundingDisclosureText(concreteMode) {
  if (concreteMode === ROUNDING_MODES.THOUSANDS) {
    return 'בסכומים באלפי ש״ח — העיגול מוצג לצורך נוחות בלבד. לחצו "מדויק" להצגת הערכים המלאים.';
  }
  if (concreteMode === ROUNDING_MODES.MILLIONS) {
    return 'בסכומים במיליוני ש״ח — העיגול מוצג לצורך נוחות בלבד. לחצו "מדויק" להצגת הערכים המלאים.';
  }
  return '';
}
