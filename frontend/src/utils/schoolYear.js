import { formatHebrewDate, formatShekel } from './format';

const HEBREW_ONES = {
  1: 'א',
  2: 'ב',
  3: 'ג',
  4: 'ד',
  5: 'ה',
  6: 'ו',
  7: 'ז',
  8: 'ח',
  9: 'ט',
};

const HEBREW_TENS = {
  10: 'י',
  20: 'כ',
  30: 'ל',
  40: 'מ',
  50: 'נ',
  60: 'ס',
  70: 'ע',
  80: 'פ',
  90: 'צ',
};

const HEBREW_HUNDREDS = {
  100: 'ק',
  200: 'ר',
  300: 'ש',
};

export function isRetroLine(line) {
  return Boolean(line?.is_retro || line?.line_type === 'retro');
}

export function parsePeriodMonth(periodMonth) {
  if (typeof periodMonth !== 'string') return null;
  const match = periodMonth.trim().match(/^(\d{4})-(\d{1,2})/);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  if (!Number.isInteger(year) || !Number.isInteger(month) || month < 1 || month > 12) {
    return null;
  }
  return { year, month };
}

function toHebrewNumeralLetters(number) {
  let n = Math.floor(Math.abs(number));
  let letters = '';

  while (n >= 400) {
    letters += 'ת';
    n -= 400;
  }

  const hundreds = Math.floor(n / 100) * 100;
  if (hundreds > 0) {
    letters += HEBREW_HUNDREDS[hundreds] || '';
    n -= hundreds;
  }

  if (n === 15) {
    letters += 'טו';
    n = 0;
  } else if (n === 16) {
    letters += 'טז';
    n = 0;
  }

  const tens = Math.floor(n / 10) * 10;
  if (tens > 0) {
    letters += HEBREW_TENS[tens] || '';
    n -= tens;
  }

  if (n > 0) {
    letters += HEBREW_ONES[n] || '';
  }

  return letters;
}

export function formatHebrewYearLabel(hebrewYear) {
  const shortYear = Math.floor(hebrewYear) % 1000;
  const letters = toHebrewNumeralLetters(shortYear);
  if (!letters) return String(hebrewYear);
  if (letters.length === 1) return `${letters}'`;
  return `${letters.slice(0, -1)}"${letters.slice(-1)}`;
}

export function getSchoolYearFromGregorian(year, month) {
  const normalizedYear = Number(year);
  const normalizedMonth = Number(month);
  if (!Number.isInteger(normalizedYear) || !Number.isInteger(normalizedMonth)) return null;
  if (normalizedMonth < 1 || normalizedMonth > 12) return null;

  const startYear = normalizedMonth >= 9 ? normalizedYear : normalizedYear - 1;
  const hebrewYear = normalizedMonth >= 9 ? normalizedYear + 3761 : normalizedYear + 3760;
  const label = formatHebrewYearLabel(hebrewYear);
  const subtitle = `${label} • ספטמבר ${startYear} – אוגוסט ${startYear + 1}`;

  return {
    key: String(startYear),
    startYear,
    endYear: startYear + 1,
    hebrewYear,
    label,
    subtitle,
  };
}

export function formatEffectiveMonth(periodMonth) {
  const parsed = parsePeriodMonth(periodMonth);
  if (!parsed) return periodMonth || '';
  return `${String(parsed.month).padStart(2, '0')}/${parsed.year}`;
}

export function buildRetroSchoolYearGroups(lines) {
  const groupsByKey = {};

  (lines || []).forEach((line) => {
    if (!isRetroLine(line)) return;

    const parsed = parsePeriodMonth(line.period_month);
    if (!parsed) return;

    const schoolYear = getSchoolYearFromGregorian(parsed.year, parsed.month);
    if (!schoolYear) return;

    if (!groupsByKey[schoolYear.key]) {
      groupsByKey[schoolYear.key] = {
        ...schoolYear,
        retroTotal: 0,
        retroLineCount: 0,
        byCode: {},
      };
    }

    const code = String(line.topic_code || '0');
    if (!groupsByKey[schoolYear.key].byCode[code]) {
      groupsByKey[schoolYear.key].byCode[code] = [];
    }

    groupsByKey[schoolYear.key].byCode[code].push(line);
    groupsByKey[schoolYear.key].retroTotal += Number(line.amount || 0);
    groupsByKey[schoolYear.key].retroLineCount += 1;
  });

  return Object.values(groupsByKey)
    .map((group) => {
      const sortedCodes = Object.keys(group.byCode).sort((a, b) => a.localeCompare(b, 'he'));
      const codes = sortedCodes.map((code) => {
        const codeLines = group.byCode[code];
        const codeTotal = codeLines.reduce((sum, line) => sum + Number(line.amount || 0), 0);
        return {
          code,
          lines: codeLines,
          total: codeTotal,
        };
      });

      return {
        ...group,
        retroTotalFormatted: formatShekel(group.retroTotal),
        codes,
      };
    })
    .sort((a, b) => b.startYear - a.startYear);
}

export function getSchoolYearHeader(topicName, code) {
  return topicName || `קוד ${code}`;
}

export function getEffectivePeriodLabel(periodMonth) {
  const parsed = parsePeriodMonth(periodMonth);
  if (!parsed) return periodMonth || '';
  return formatHebrewDate(`${parsed.year}-${String(parsed.month).padStart(2, '0')}`);
}
