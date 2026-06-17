import { describe, it, expect } from 'vitest';
import { generateChangeExplanation } from '../../utils/changeExplanations.jsx';

// ── Custom explanation override ───────────────────────────────────────────────

describe('generateChangeExplanation — custom explanation', () => {
  it('returns custom text and isCustom=true when customExplanation is provided', () => {
    const change = { topic_code: '3', items_change: 5, amount_change: 10000 };
    const result = generateChangeExplanation(change, 'הסבר מותאם אישית');
    expect(result.text).toBe('הסבר מותאם אישית');
    expect(result.isCustom).toBe(true);
  });

  it('does not use custom explanation when it is empty string', () => {
    const change = { topic_code: '3', items_change: 5, amount_change: 10000 };
    const result = generateChangeExplanation(change, '');
    expect(result.isCustom).toBe(false);
  });

  it('does not use custom explanation when it is null', () => {
    const change = { topic_code: '3', items_change: 5, amount_change: 10000 };
    const result = generateChangeExplanation(change, null);
    expect(result.isCustom).toBe(false);
  });
});

// ── Case 1: Items increased (positive items_change) ───────────────────────────

describe('generateChangeExplanation — items increased', () => {
  it('returns isCustom=false for auto generation', () => {
    const result = generateChangeExplanation({ topic_code: '3', items_change: 3, amount_change: 0 });
    expect(result.isCustom).toBe(false);
  });

  it('returns Hebrew text mentioning addition for topic_code 3', () => {
    const result = generateChangeExplanation({ topic_code: '3', items_change: 3, amount_change: 0 });
    expect(result.text).toMatch(/נוסף|נוספו|חדש/);
  });

  it('returns Hebrew text for generic items increase', () => {
    const result = generateChangeExplanation({
      topic_code: '99',
      topic_name: 'נושא כללי',
      items_change: 2,
      amount_change: 0,
    });
    expect(result.text.length).toBeGreaterThan(5);
  });

  it('handles increase for topic_code 19 (assistants)', () => {
    const result = generateChangeExplanation({
      topic_code: '19',
      topic_name: 'עוזרות',
      items_change: 1,
      amount_change: 0,
    });
    expect(result.text).toMatch(/עוזרות|נוספ/);
  });

  it('handles negative impact topic (code 33) — deduction increased', () => {
    const result = generateChangeExplanation({ topic_code: '33', items_change: 2, amount_change: 0 });
    expect(result.text).toMatch(/ניכוי|גדל/);
  });
});

// ── Case 2: Items decreased (negative items_change) ───────────────────────────

describe('generateChangeExplanation — items decreased', () => {
  it('returns text mentioning removal for items decrease', () => {
    const result = generateChangeExplanation({ topic_code: '3', items_change: -2, amount_change: 0 });
    expect(result.text).toMatch(/הוסר|קטן/);
  });

  it('handles negative impact topic (code 33) — deduction decreased', () => {
    const result = generateChangeExplanation({ topic_code: '33', items_change: -1, amount_change: 0 });
    expect(result.text).toMatch(/ניכוי|קטן/);
  });

  it('returns isCustom=false', () => {
    const result = generateChangeExplanation({ topic_code: '3', items_change: -1, amount_change: 0 });
    expect(result.isCustom).toBe(false);
  });
});

// ── Case 3: Only amount changed ───────────────────────────────────────────────

describe('generateChangeExplanation — amount only change', () => {
  it('mentions "עלה" for positive amount change', () => {
    const result = generateChangeExplanation({
      topic_code: '3',
      items_change: 0,
      amount_change: 5000,
      amount_change_pct: 10,
    });
    expect(result.text).toContain('עלה');
  });

  it('mentions "ירד" for negative amount change', () => {
    const result = generateChangeExplanation({
      topic_code: '3',
      items_change: 0,
      amount_change: -5000,
      amount_change_pct: -10,
    });
    expect(result.text).toContain('ירד');
  });

  it('handles deduction topic amount change (topic_code 33)', () => {
    const result = generateChangeExplanation({
      topic_code: '33',
      items_change: 0,
      amount_change: 3000,
      amount_change_pct: 5,
    });
    expect(result.text).toMatch(/ניכוי/);
  });

  it('handles topic_code 19 amount change', () => {
    const result = generateChangeExplanation({
      topic_code: '19',
      items_change: 0,
      amount_change: 2000,
      amount_change_pct: 3,
    });
    expect(result.text.length).toBeGreaterThan(5);
  });
});

// ── Case 4: No change ─────────────────────────────────────────────────────────

describe('generateChangeExplanation — no change', () => {
  it('returns no-change message when both items_change and amount_change are 0', () => {
    const result = generateChangeExplanation({
      topic_code: '3',
      items_change: 0,
      amount_change: 0,
    });
    expect(result.text).toMatch(/אין שינוי|ללא שינוי/);
  });

  it('returns isCustom=false', () => {
    const result = generateChangeExplanation({ topic_code: '3', items_change: 0, amount_change: 0 });
    expect(result.isCustom).toBe(false);
  });
});

// ── Result shape ──────────────────────────────────────────────────────────────

describe('generateChangeExplanation — result shape', () => {
  it('always returns an object with text and isCustom', () => {
    const cases = [
      { items_change: 5, amount_change: 0 },
      { items_change: -2, amount_change: 0 },
      { items_change: 0, amount_change: 1000 },
      { items_change: 0, amount_change: 0 },
    ];
    cases.forEach(change => {
      const result = generateChangeExplanation({ topic_code: '3', ...change });
      expect(result).toHaveProperty('text');
      expect(result).toHaveProperty('isCustom');
      expect(typeof result.text).toBe('string');
      expect(typeof result.isCustom).toBe('boolean');
    });
  });

  it('text is always a non-empty string', () => {
    const result = generateChangeExplanation({ topic_code: '3', items_change: 1, amount_change: 0 });
    expect(result.text.length).toBeGreaterThan(0);
  });
});
