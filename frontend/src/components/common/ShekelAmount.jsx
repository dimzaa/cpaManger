import React from 'react';
import { formatShekel, ROUNDING_MODES } from '../../utils/formatShekel';

export default function ShekelAmount({ amount, mode = ROUNDING_MODES.EXACT, className = '' }) {
  const displayValue = formatShekel(amount, { mode });
  const exactValue = formatShekel(amount, { mode: ROUNDING_MODES.EXACT });
  const title = mode !== ROUNDING_MODES.EXACT ? exactValue : undefined;

  return (
    <span className={className} title={title}>
      {displayValue}
    </span>
  );
}
