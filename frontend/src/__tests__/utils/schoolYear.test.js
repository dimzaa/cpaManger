import { describe, expect, it } from 'vitest';
import {
  buildRetroSchoolYearGroups,
  formatHebrewYearLabel,
  getSchoolYearFromGregorian,
  isRetroLine,
} from '../../utils/schoolYear';

describe('getSchoolYearFromGregorian boundary months', () => {
  it('maps Aug 2025 to תשפ"ה', () => {
    const result = getSchoolYearFromGregorian(2025, 8);
    expect(result?.label).toBe('תשפ"ה');
    expect(result?.subtitle).toBe('תשפ"ה • ספטמבר 2024 – אוגוסט 2025');
  });

  it('maps Sep 2025 to תשפ"ו', () => {
    const result = getSchoolYearFromGregorian(2025, 9);
    expect(result?.label).toBe('תשפ"ו');
    expect(result?.subtitle).toBe('תשפ"ו • ספטמבר 2025 – אוגוסט 2026');
  });

  it('maps Dec 2025 to תשפ"ו', () => {
    const result = getSchoolYearFromGregorian(2025, 12);
    expect(result?.label).toBe('תשפ"ו');
    expect(result?.subtitle).toBe('תשפ"ו • ספטמבר 2025 – אוגוסט 2026');
  });

  it('maps Jan 2026 to תשפ"ו', () => {
    const result = getSchoolYearFromGregorian(2026, 1);
    expect(result?.label).toBe('תשפ"ו');
    expect(result?.subtitle).toBe('תשפ"ו • ספטמבר 2025 – אוגוסט 2026');
  });

  it('maps Aug 2026 to תשפ"ו', () => {
    const result = getSchoolYearFromGregorian(2026, 8);
    expect(result?.label).toBe('תשפ"ו');
    expect(result?.subtitle).toBe('תשפ"ו • ספטמבר 2025 – אוגוסט 2026');
  });

  it('maps Sep 2026 to תשפ"ז', () => {
    const result = getSchoolYearFromGregorian(2026, 9);
    expect(result?.label).toBe('תשפ"ז');
    expect(result?.subtitle).toBe('תשפ"ז • ספטמבר 2026 – אוגוסט 2027');
  });
});

describe('formatHebrewYearLabel', () => {
  it('formats required reference years', () => {
    expect(formatHebrewYearLabel(5780)).toBe('תש"פ');
    expect(formatHebrewYearLabel(5781)).toBe('תשפ"א');
    expect(formatHebrewYearLabel(5785)).toBe('תשפ"ה');
    expect(formatHebrewYearLabel(5786)).toBe('תשפ"ו');
    expect(formatHebrewYearLabel(5787)).toBe('תשפ"ז');
    expect(formatHebrewYearLabel(5788)).toBe('תשפ"ח');
  });
});

describe('buildRetroSchoolYearGroups', () => {
  const fixtureLines = [
    {
      id: 1,
      topic_code: '19',
      budget_topic: 'גני ילדים',
      amount: 1000,
      period_month: '2026-01',
      line_type: 'retro',
      is_retro: true,
    },
    {
      id: 2,
      topic_code: '50',
      budget_topic: 'הסעות',
      amount: 2000,
      period_month: '2025-09',
      line_type: 'retro',
      is_retro: true,
    },
    {
      id: 3,
      topic_code: '50',
      budget_topic: 'הסעות',
      amount: 1500,
      period_month: '2025-08',
      line_type: 'retro',
      is_retro: true,
    },
    {
      id: 4,
      topic_code: '99',
      budget_topic: 'לא רטרו',
      amount: 900,
      period_month: '2026-01',
      line_type: 'regular',
      is_retro: false,
    },
  ];

  it('creates two school-year groups sorted newest first', () => {
    const groups = buildRetroSchoolYearGroups(fixtureLines);
    expect(groups).toHaveLength(2);
    expect(groups[0].label).toBe('תשפ"ו');
    expect(groups[1].label).toBe('תשפ"ה');
  });

  it('keeps non-retro lines out of school-year section', () => {
    const groups = buildRetroSchoolYearGroups(fixtureLines);
    const ids = groups.flatMap((g) => g.codes.flatMap((c) => c.lines.map((l) => l.id)));
    expect(ids).not.toContain(4);
  });

  it('returns empty array when there are zero retro lines', () => {
    const groups = buildRetroSchoolYearGroups([
      {
        id: 10,
        topic_code: '88',
        amount: 300,
        period_month: '2026-03',
        line_type: 'regular',
        is_retro: false,
      },
    ]);
    expect(groups).toEqual([]);
  });

  it('isRetroLine matches both flags', () => {
    expect(isRetroLine({ line_type: 'retro', is_retro: false })).toBe(true);
    expect(isRetroLine({ line_type: 'regular', is_retro: true })).toBe(true);
    expect(isRetroLine({ line_type: 'regular', is_retro: false })).toBe(false);
  });
});
