import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  formatHebrewDate,
  formatShekel,
  calculateDifference,
  getLineTypeColor,
  getLineTypeLabel,
  getStatusColor,
  getLast6Months,
  getLast12Months,
  getCurrentMonth,
  formatCurrency,
  formatMonth,
  formatDate,
} from '../../utils/format';

// ── formatHebrewDate ─────────────────────────────────────────────────────────

describe('formatHebrewDate', () => {
  it('converts YYYY-MM to Hebrew month name and year', () => {
    expect(formatHebrewDate('2026-03')).toBe('מרץ 2026');
  });

  it('converts January correctly', () => {
    expect(formatHebrewDate('2024-01')).toBe('ינואר 2024');
  });

  it('converts December correctly', () => {
    expect(formatHebrewDate('2023-12')).toBe('דצמבר 2023');
  });

  it('converts all 12 months without throwing', () => {
    const months = ['01','02','03','04','05','06','07','08','09','10','11','12'];
    months.forEach(m => {
      expect(() => formatHebrewDate(`2024-${m}`)).not.toThrow();
    });
  });

  it('returns empty string for empty input', () => {
    expect(formatHebrewDate('')).toBe('');
    expect(formatHebrewDate(null)).toBe('');
    expect(formatHebrewDate(undefined)).toBe('');
  });
});

// ── formatShekel ─────────────────────────────────────────────────────────────

describe('formatShekel', () => {
  it('formats a typical amount with ₪ prefix', () => {
    const result = formatShekel(450000);
    expect(result).toContain('₪');
    expect(result).toContain('450');
  });

  it('formats zero', () => {
    expect(formatShekel(0)).toBe('₪ 0');
  });

  it('returns ₪ 0 for null', () => {
    expect(formatShekel(null)).toBe('₪ 0');
  });

  it('returns ₪ 0 for undefined', () => {
    expect(formatShekel(undefined)).toBe('₪ 0');
  });

  it('includes comma separators for large amounts', () => {
    const result = formatShekel(1000000);
    expect(result).toContain('1');
    expect(result).toContain('000');
  });
});

// ── calculateDifference ───────────────────────────────────────────────────────

describe('calculateDifference', () => {
  it('calculates positive difference correctly', () => {
    const result = calculateDifference(100, 80);
    expect(result.amount).toBe(20);
    expect(result.percentage).toBe(25);
    expect(result.isPositive).toBe(true);
  });

  it('calculates negative difference correctly', () => {
    const result = calculateDifference(60, 80);
    expect(result.amount).toBe(-20);
    expect(result.isPositive).toBe(false);
  });

  it('handles zero previous value without dividing by zero', () => {
    const result = calculateDifference(100, 0);
    expect(result.percentage).toBe(0);
    expect(result.amount).toBe(100);
  });

  it('handles null previous value', () => {
    const result = calculateDifference(100, null);
    expect(result).toBeDefined();
    expect(result.amount).toBe(100);
  });

  it('returns isPositive true when equal', () => {
    const result = calculateDifference(50, 50);
    expect(result.isPositive).toBe(true);
    expect(result.amount).toBe(0);
  });
});

// ── getLineTypeColor ──────────────────────────────────────────────────────────

describe('getLineTypeColor', () => {
  it('returns object for retro type', () => {
    const result = getLineTypeColor('retro');
    expect(result).toBeTypeOf('object');
    expect(result.bg).toBeDefined();
  });

  it('returns object for shortage type', () => {
    const result = getLineTypeColor('shortage');
    expect(result).toBeTypeOf('object');
  });

  it('returns object for regular type', () => {
    const result = getLineTypeColor('regular');
    expect(result).toBeTypeOf('object');
  });

  it('returns default for unknown type', () => {
    const result = getLineTypeColor('unknown');
    expect(result).toBeTypeOf('object');
  });

  it('has bg, border, badge keys', () => {
    const result = getLineTypeColor('retro');
    expect('bg' in result).toBe(true);
    expect('border' in result).toBe(true);
    expect('badge' in result).toBe(true);
  });
});

// ── getLineTypeLabel ──────────────────────────────────────────────────────────

describe('getLineTypeLabel', () => {
  it('returns Hebrew label for retro', () => {
    expect(getLineTypeLabel('retro')).toBe('תשלום רטרו');
  });

  it('returns Hebrew label for regular', () => {
    expect(getLineTypeLabel('regular')).toBe('רגיל');
  });

  it('returns Hebrew label for shortage', () => {
    expect(getLineTypeLabel('shortage')).toBe('חוסר');
  });

  it('returns Hebrew label for adjustment', () => {
    expect(getLineTypeLabel('adjustment')).toBe('התאמה');
  });

  it('returns the raw value for unknown types', () => {
    expect(getLineTypeLabel('custom_type')).toBe('custom_type');
  });
});

// ── getStatusColor ────────────────────────────────────────────────────────────

describe('getStatusColor', () => {
  it('returns balanced label when isBalanced=true and no retro', () => {
    const result = getStatusColor(true, false);
    expect(result.label).toBe('מאוזן');
  });

  it('returns retro label when hasRetro=true', () => {
    const result = getStatusColor(true, true);
    expect(result.label).toBe('תשלום רטרו');
  });

  it('returns discrepancy label when not balanced', () => {
    const result = getStatusColor(false, false);
    expect(result.label).toBe('חריגה');
  });

  it('retro takes precedence over balanced status', () => {
    const result = getStatusColor(false, true);
    expect(result.label).toBe('תשלום רטרו');
  });

  it('returns object with bg, text, label', () => {
    const result = getStatusColor(true, false);
    expect('bg' in result).toBe(true);
    expect('text' in result).toBe(true);
    expect('label' in result).toBe(true);
  });
});

// ── getLast6Months ────────────────────────────────────────────────────────────

describe('getLast6Months', () => {
  it('returns exactly 6 months', () => {
    expect(getLast6Months()).toHaveLength(6);
  });

  it('each entry has value and label', () => {
    getLast6Months().forEach(m => {
      expect(m.value).toBeDefined();
      expect(m.label).toBeDefined();
    });
  });

  it('values are in YYYY-MM format', () => {
    getLast6Months().forEach(m => {
      expect(m.value).toMatch(/^\d{4}-\d{2}$/);
    });
  });

  it('last item is the current month', () => {
    const months = getLast6Months();
    const current = getCurrentMonth();
    expect(months[months.length - 1].value).toBe(current);
  });
});

// ── getLast12Months ───────────────────────────────────────────────────────────

describe('getLast12Months', () => {
  it('returns exactly 12 months', () => {
    expect(getLast12Months()).toHaveLength(12);
  });

  it('each entry has value and label', () => {
    getLast12Months().forEach(m => {
      expect(m.value).toBeDefined();
      expect(m.label).toBeDefined();
    });
  });

  it('values are in YYYY-MM format', () => {
    getLast12Months().forEach(m => {
      expect(m.value).toMatch(/^\d{4}-\d{2}$/);
    });
  });
});

// ── getCurrentMonth ───────────────────────────────────────────────────────────

describe('getCurrentMonth', () => {
  it('returns string in YYYY-MM format', () => {
    expect(getCurrentMonth()).toMatch(/^\d{4}-\d{2}$/);
  });

  it('matches current year', () => {
    const year = new Date().getFullYear().toString();
    expect(getCurrentMonth().startsWith(year)).toBe(true);
  });
});

// ── formatCurrency ────────────────────────────────────────────────────────────

describe('formatCurrency', () => {
  it('formats a number with ₪ prefix', () => {
    expect(formatCurrency(500)).toContain('₪');
  });

  it('formats 0', () => {
    const result = formatCurrency(0);
    expect(result).toContain('₪');
    expect(result).toContain('0');
  });
});

// ── formatMonth ───────────────────────────────────────────────────────────────

describe('formatMonth', () => {
  it('converts YYYY-MM to Hebrew month name and year', () => {
    expect(formatMonth('2026-03')).toBe('מרץ 2026');
  });

  it('converts January', () => {
    expect(formatMonth('2024-01')).toBe('ינואר 2024');
  });
});

// ── formatDate ────────────────────────────────────────────────────────────────

describe('formatDate', () => {
  it('returns a string', () => {
    expect(typeof formatDate('2024-01-15')).toBe('string');
  });

  it('does not throw for a valid date', () => {
    expect(() => formatDate('2024-03-15')).not.toThrow();
  });
});
