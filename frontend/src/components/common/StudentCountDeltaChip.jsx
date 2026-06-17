import React from 'react';

/**
 * Chip rendered next to a per-code money delta when the student-count delta
 * engine has something to say. Colors follow the repo's existing Tailwind
 * conventions (green / red for pupil moves, amber / blue for other drivers).
 *
 * The delta prop shape matches the /student-count-deltas API row.
 */
export default function StudentCountDeltaChip({ delta, showDriverBadge = false }) {
  if (!delta) return null;

  const deltaChildren = delta.delta_children ?? 0;
  const hasCountMove = deltaChildren !== 0;

  if (!hasCountMove && !delta.variance_driver) return null;

  const signed = deltaChildren > 0 ? `+${deltaChildren}` : `${deltaChildren}`;
  const color =
    deltaChildren > 0
      ? 'bg-green-50 text-green-700 border-green-200'
      : deltaChildren < 0
      ? 'bg-red-50 text-red-700 border-red-200'
      : 'bg-gray-50 text-gray-700 border-gray-200';

  const driverLabel = {
    student_count: { text: 'מספר ילדים', cls: 'bg-green-100 text-green-800 border-green-300' },
    formula_or_rate: { text: 'נוסחה/תעריף', cls: 'bg-blue-100 text-blue-800 border-blue-300' },
    mixed: { text: 'מעורב', cls: 'bg-amber-100 text-amber-800 border-amber-300' },
  };
  const badge = showDriverBadge && delta.variance_driver ? driverLabel[delta.variance_driver] : null;

  const tooltip = buildTooltipText(delta);

  return (
    <span className="inline-flex items-center gap-1" dir="rtl" title={tooltip}>
      {hasCountMove && (
        <span className={`inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-xs font-medium border ${color}`}>
          <span aria-hidden="true">👥</span>
          <span>
            {signed} ילדים
          </span>
        </span>
      )}
      {badge && (
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border ${badge.cls}`}>
          {badge.text}
        </span>
      )}
    </span>
  );
}

function buildTooltipText(delta) {
  const prev = delta.prev_num_children ?? 0;
  const curr = delta.curr_num_children ?? 0;
  const signed = delta.delta_children > 0 ? `+${delta.delta_children}` : `${delta.delta_children}`;
  const expl = formatSignedShekel(delta.explained_amount ?? 0);
  const actual = formatSignedShekel(delta.delta_amount ?? 0);
  const ratio =
    delta.explained_ratio !== null && delta.explained_ratio !== undefined
      ? Math.round(Math.abs(delta.explained_ratio) * 100)
      : delta.delta_children !== 0
      ? 100
      : 0;
  if (delta.variance_driver === 'formula_or_rate') {
    return 'מספר ילדים לא השתנה מהותית — השינוי נובע מגורם אחר.';
  }
  if (delta.variance_driver === 'mixed') {
    return `חלק מהשינוי נובע משינוי במספר ילדים (${prev} → ${curr}, ${signed}); היתר נובע מגורם אחר.`;
  }
  return `מספר ילדים: ${prev} → ${curr} (${signed}). השפעה משוערת על הסכום: ${expl} ₪ מתוך ${actual} ₪ (${ratio}%).`;
}

function formatSignedShekel(v) {
  const sign = v >= 0 ? '+' : '-';
  const abs = Math.abs(v);
  return `${sign}₪${abs.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
}
