import { useEffect, useState } from 'react';
import { ROUNDING_MODES } from './formatShekel';

const STORAGE_KEY = 'cpa.display.roundingMode';

const ALLOWED_MODES = new Set(Object.values(ROUNDING_MODES));

function sanitizeMode(value) {
  return ALLOWED_MODES.has(value) ? value : ROUNDING_MODES.EXACT;
}

export function loadRoundingMode() {
  try {
    return sanitizeMode(localStorage.getItem(STORAGE_KEY));
  } catch {
    return ROUNDING_MODES.EXACT;
  }
}

export function useRoundingMode() {
  const [mode, setMode] = useState(() => loadRoundingMode());

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, sanitizeMode(mode));
    } catch {
      // Ignore storage errors and keep in-memory state.
    }
  }, [mode]);

  return [sanitizeMode(mode), (nextMode) => setMode(sanitizeMode(nextMode))];
}
