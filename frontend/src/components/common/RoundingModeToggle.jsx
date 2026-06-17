import React from 'react';
import { ROUNDING_MODES } from '../../utils/formatShekel';

const OPTIONS = [
  { value: ROUNDING_MODES.EXACT, label: 'מדויק' },
  { value: ROUNDING_MODES.THOUSANDS, label: 'אלפי' },
  { value: ROUNDING_MODES.MILLIONS, label: 'מיליוני' },
  { value: ROUNDING_MODES.AUTO, label: 'אוטומטי' },
];

export default function RoundingModeToggle({ mode, onChange }) {
  return (
    <div className="flex items-center gap-2" dir="rtl">
      <span className="text-sm text-slate-600 font-hebrew">תצוגה</span>
      <div className="inline-flex rounded-lg border border-slate-300 bg-white p-1 shadow-sm">
        {OPTIONS.map((option) => {
          const selected = mode === option.value;
          return (
            <button
              key={option.value}
              type="button"
              onClick={() => onChange(option.value)}
              className={`px-3 py-1.5 text-xs md:text-sm rounded-md font-hebrew transition ${
                selected
                  ? 'bg-slate-800 text-white'
                  : 'text-slate-700 hover:bg-slate-100'
              }`}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
