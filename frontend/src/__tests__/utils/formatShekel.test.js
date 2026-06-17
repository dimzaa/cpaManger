import { describe, it, expect } from 'vitest';
import { formatShekel, resolveAutoMode, ROUNDING_MODES } from '../../utils/formatShekel';

describe('formatShekel executive rounding', () => {
  it('keeps exact mode output style', () => {
    expect(formatShekel(5_243_712, { mode: ROUNDING_MODES.EXACT })).toBe('₪ 5,243,712');
  });

  it('formats thousands with one decimal and suffix', () => {
    expect(formatShekel(5_243_712, { mode: ROUNDING_MODES.THOUSANDS })).toBe('5,243.7 אלפי ₪');
  });

  it('formats millions with two decimals and suffix', () => {
    expect(formatShekel(5_243_712, { mode: ROUNDING_MODES.MILLIONS })).toBe('5.24 מיליוני ₪');
  });

  it('preserves negative sign in millions mode', () => {
    expect(formatShekel(-5_243_712, { mode: ROUNDING_MODES.MILLIONS })).toBe('-5.24 מיליוני ₪');
  });

  it('renders zero as plain 0 in every mode', () => {
    expect(formatShekel(0, { mode: ROUNDING_MODES.EXACT })).toBe('0');
    expect(formatShekel(0, { mode: ROUNDING_MODES.THOUSANDS })).toBe('0');
    expect(formatShekel(0, { mode: ROUNDING_MODES.MILLIONS })).toBe('0');
  });

  it('renders tiny values in thousands mode', () => {
    expect(formatShekel(12, { mode: ROUNDING_MODES.THOUSANDS })).toBe('0.0 אלפי ₪');
  });
});

describe('resolveAutoMode', () => {
  it('resolves millions for max 5,243,712', () => {
    expect(resolveAutoMode([5_243_712])).toBe(ROUNDING_MODES.MILLIONS);
  });

  it('resolves thousands for max 243,712', () => {
    expect(resolveAutoMode([243_712])).toBe(ROUNDING_MODES.THOUSANDS);
  });

  it('resolves exact for max 4,800', () => {
    expect(resolveAutoMode([4_800])).toBe(ROUNDING_MODES.EXACT);
  });

  it('returns exact for empty arrays', () => {
    expect(resolveAutoMode([])).toBe(ROUNDING_MODES.EXACT);
  });

  it('uses absolute values when negatives exist', () => {
    expect(resolveAutoMode([-5_243_712, -10])).toBe(ROUNDING_MODES.MILLIONS);
  });
});
