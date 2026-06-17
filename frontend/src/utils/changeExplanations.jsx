/**
 * Generate automatic Hebrew explanations for budget changes
 */

export const generateChangeExplanation = (change, customExplanation = null) => {
  // If CPA has added custom explanation, use that instead
  if (customExplanation && customExplanation.trim()) {
    return {
      text: customExplanation,
      isCustom: true
    };
  }

  const {
    topic_name = '',
    topic_code = '',
    items_change = 0,
    amount_change = 0,
    prev_lines_count = 0,
    curr_lines_count = 0,
    prev_total = 0,
    curr_total = 0,
    amount_change_pct = 0
  } = change;

  // Determine if this is a negative impact item (like deductions)
  const isNegativeImpact = topic_code === '33' || 
                          topic_name?.includes('הנחה') || 
                          topic_name?.includes('ניכוי') ||
                          topic_name?.includes('גננות');

  // Case 1: Items increased
  if (items_change > 0) {
    if (isNegativeImpact) {
      return {
        text: `הניכוי גדל ב-${items_change} פריטים — ייתכן גננת עובדת מדינה נוספת שובצה לרשות או תשלום רטרו`,
        isCustom: false
      };
    }

    // Different messages for different categories
    if (topic_code === '19' || topic_name?.includes('עוזרות')) {
      return {
        text: `נוספו ${items_change} פריטי עוזרות — ייתכן משרות חדשות או תשלומי רטרו`,
        isCustom: false
      };
    }

    if (topic_code === '3' || topic_name?.includes('ילדי ח"מ')) {
      return {
        text: `${items_change} פריטים נוספו — ייתכן רישום ילדים חדשים או תשלומי רטרו נוספים`,
        isCustom: false
      };
    }

    // Generic for items increase
    return {
      text: `${items_change} פריטים נוספו בקטגוריה זו — ייתכן הוספת משרות חדשות או תשלומי רטרו`,
      isCustom: false
    };
  }

  // Case 2: Items decreased
  if (items_change < 0) {
    if (isNegativeImpact) {
      return {
        text: `הניכוי קטן ב-${Math.abs(items_change)} פריטים — ייתכן סגירת משרות או סיום תשלומי רטרו`,
        isCustom: false
      };
    }

    return {
      text: `${Math.abs(items_change)} פריטים הוסרו — ייתכן סגירת משרות או סיום תשלומים`,
      isCustom: false
    };
  }

  // Case 3: Only amount changed (items count same)
  if (items_change === 0 && amount_change !== 0) {
    const direction = amount_change > 0 ? 'עלה' : 'ירד';
    const abs_amount = formatCurrency(Math.abs(amount_change));
    const abs_pct = Math.abs(amount_change_pct || 0).toFixed(1);

    if (isNegativeImpact) {
      return {
        text: `הניכוי ${direction} ב-${abs_amount} (${abs_pct}%) — ייתכן שינוי באחוז התרומה או עדכון סכום הניכוי`,
        isCustom: false
      };
    }

    if (topic_code === '3' || topic_name?.includes('ילדי ח"מ')) {
      return {
        text: `הסכום ${direction} ב-${abs_amount} (${abs_pct}%) — ייתכן עדכון עלות לילד או שינוי אחוז השתתפות`,
        isCustom: false
      };
    }

    if (topic_code === '19' || topic_name?.includes('עוזרות')) {
      return {
        text: `הסכום ${direction} ב-${abs_amount} (${abs_pct}%) — ייתכן עדכון שכר או שינוי בתנאי התשלום`,
        isCustom: false
      };
    }

    // Generic
    return {
      text: `הסכום ${direction} ב-${abs_amount} (${abs_pct}%) — ייתכן עדכון תעריפים או שנוי בתנאי התשלום`,
      isCustom: false
    };
  }

  // Case 4: Both items and amount changed
  if (items_change !== 0 && amount_change !== 0) {
    const items_direction = items_change > 0 ? 'עלה' : 'ירד';
    const amount_direction = amount_change > 0 ? 'עלה' : 'ירד';

    if (isNegativeImpact) {
      return {
        text: `הניכוי ${items_direction} בכמות (${Math.abs(items_change)} פריטים) ו${amount_direction} בסכום (${Math.abs(amount_change_pct || 0).toFixed(1)}%) — ייתכן שינוי במיון העובדים וכן בתעריף`,
        isCustom: false
      };
    }

    return {
      text: `${Math.abs(items_change)} פריטים ${items_change > 0 ? 'נוספו' : 'הוסרו'} והסכום ${amount_direction} ב-${Math.abs(amount_change_pct || 0).toFixed(1)}% — ייתכן שינוי כמותי וגם בתעריפים`,
      isCustom: false
    };
  }

  // No change detected
  return {
    text: 'אין שינוי משמעותי בקטגוריה זו',
    isCustom: false
  };
};

/**
 * Format shekel amount for display
 */
const formatCurrency = (amount) => {
  if (!amount && amount !== 0) return '₪0';
  const num = typeof amount === 'number' ? amount : parseInt(amount, 10);
  return '₪' + num.toLocaleString('he-IL');
};

/**
 * Change explanation component for display
 */
export const ChangeExplanationBox = ({ explanation, isCustom }) => {
  if (!explanation) return null;

  return (
    <div className="mt-3 bg-blue-50 border border-blue-200 rounded-lg p-3 border-l-4 border-l-blue-500">
      <div className="flex gap-2">
        <span className="text-lg">💡</span>
        <div className="flex-1">
          <p className="text-sm font-hebrew text-blue-900 leading-relaxed">
            {explanation}
          </p>
          {isCustom && (
            <p className="text-xs font-hebrew text-blue-700 mt-1 italic">
              (הסבר מותאם אישי מ-CPA)
            </p>
          )}
        </div>
      </div>
    </div>
  );
};
