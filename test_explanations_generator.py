#!/usr/bin/env python3
"""
Test the change explanation generation logic
"""

def format_currency(amount):
    """Format amount as shekel currency"""
    if amount is None or amount == 0:
        return '₪0'
    num = int(amount) if isinstance(amount, (int, float)) else amount
    return f'₪{num:,.0f}'.replace(',', '،')

def generate_change_explanation(change, custom_explanation=None):
    """Generate automatic Hebrew explanation for a budget change"""
    
    # If CPA has added custom explanation, use that instead
    if custom_explanation and isinstance(custom_explanation, str) and custom_explanation.strip():
        return {
            'text': custom_explanation.strip(),
            'is_custom': True
        }

    topic_name = change.get('topic_name', '')
    topic_code = change.get('topic_code', '')
    items_change = change.get('items_change', 0)
    amount_change = change.get('amount_change', 0)
    amount_change_pct = change.get('amount_change_pct', 0)

    # Determine if this is a negative impact item
    is_negative_impact = (topic_code == '33' or 
                         'הנחה' in topic_name or 
                         'ניכוי' in topic_name or
                         'גננות' in topic_name)

    # Case 1: Items increased
    if items_change > 0:
        if is_negative_impact:
            return {
                'text': f'הניכוי גדל ב-{items_change} פריטים — ייתכן גננת עובדת מדינה נוספת שובצה לרשות או תשלום רטרו',
                'is_custom': False
            }

        if topic_code == '19' or 'עוזרות' in topic_name:
            return {
                'text': f'נוספו {items_change} פריטי עוזרות — ייתכן משרות חדשות או תשלומי רטרו',
                'is_custom': False
            }

        if topic_code == '3' or 'ילדי ח"מ' in topic_name:
            return {
                'text': f'{items_change} פריטים נוספו — ייתכן רישום ילדים חדשים או תשלומי רטרו נוספים',
                'is_custom': False
            }

        return {
            'text': f'{items_change} פריטים נוספו בקטגוריה זו — ייתכן הוספת משרות חדשות או תשלומי רטרו',
            'is_custom': False
        }

    # Case 2: Items decreased
    if items_change < 0:
        if is_negative_impact:
            return {
                'text': f'הניכוי קטן ב-{abs(items_change)} פריטים — ייתכן סגירת משרות או סיום תשלומי רטרו',
                'is_custom': False
            }

        return {
            'text': f'{abs(items_change)} פריטים הוסרו — ייתכן סגירת משרות או סיום תשלומים',
            'is_custom': False
        }

    # Case 3: Only amount changed
    if items_change == 0 and amount_change != 0:
        direction = 'עלה' if amount_change > 0 else 'ירד'
        abs_amount = format_currency(abs(amount_change))
        abs_pct = f'{abs(amount_change_pct):.1f}'

        if is_negative_impact:
            return {
                'text': f'הניכוי {direction} ב-{abs_amount} ({abs_pct}%) — ייתכן שינוי באחוז התרומה או עדכון סכום הניכוי',
                'is_custom': False
            }

        if topic_code == '3' or 'ילדי ח"מ' in topic_name:
            return {
                'text': f'הסכום {direction} ב-{abs_amount} ({abs_pct}%) — ייתכן עדכון עלות לילד או שינוי אחוז השתתפות',
                'is_custom': False
            }

        if topic_code == '19' or 'עוזרות' in topic_name:
            return {
                'text': f'הסכום {direction} ב-{abs_amount} ({abs_pct}%) — ייתכן עדכון שכר או שינוי בתנאי התשלום',
                'is_custom': False
            }

        return {
            'text': f'הסכום {direction} ב-{abs_amount} ({abs_pct}%) — ייתכן עדכון תעריפים או שנוי בתנאי התשלום',
            'is_custom': False
        }

    # Case 4: Both changed
    if items_change != 0 and amount_change != 0:
        items_direction = 'עלה' if items_change > 0 else 'ירד'
        amount_direction = 'עלה' if amount_change > 0 else 'ירד'
        abs_pct = f'{abs(amount_change_pct):.1f}'

        if is_negative_impact:
            return {
                'text': f'הניכוי {items_direction} בכמות ({abs(items_change)} פריטים) ו{amount_direction} בסכום ({abs_pct}%) — ייתכן שינוי במיון העובדים וכן בתעריף',
                'is_custom': False
            }

        return {
            'text': f'{abs(items_change)} פריטים {("נוספו" if items_change > 0 else "הוסרו")} והסכום {amount_direction} ב-{abs_pct}% — ייתכן שינוי כמותי וגם בתעריפים',
            'is_custom': False
        }

    return {
        'text': 'אין שינוי משמעותי בקטגוריה זו',
        'is_custom': False
    }

# Test cases
tests = [
    {
        'name': 'Items increased (4 new items)',
        'change': {
            'topic_code': '3',
            'topic_name': 'ילדי ח"מ 5י\' קשה',
            'items_change': 4,
            'amount_change': 361783,
            'prev_lines_count': 24,
            'curr_lines_count': 28,
            'prev_total': 2044675,
            'curr_total': 2406458,
            'amount_change_pct': 17.7
        },
        'custom': None
    },
    {
        'name': 'Amount increased only',
        'change': {
            'topic_code': '3',
            'topic_name': 'ילדי ח"מ 5י\' קשה',
            'items_change': 0,
            'amount_change': 100000,
            'prev_total': 1000000,
            'curr_total': 1100000,
            'amount_change_pct': 10
        },
        'custom': None
    },
    {
        'name': 'Kindergarten deduction increased (negative impact)',
        'change': {
            'topic_code': '33',
            'topic_name': 'גננות — הנחה מ"א',
            'items_change': 2,
            'amount_change': 50000,
            'prev_lines_count': 10,
            'curr_lines_count': 12,
            'prev_total': -500000,
            'curr_total': -550000,
            'amount_change_pct': 10
        },
        'custom': None
    },
    {
        'name': 'Helper services (עוזרות) added',
        'change': {
            'topic_code': '19',
            'topic_name': 'עוזרות',
            'items_change': 3,
            'amount_change': 200000,
            'prev_lines_count': 5,
            'curr_lines_count': 8,
            'prev_total': 500000,
            'curr_total': 700000,
            'amount_change_pct': 40
        },
        'custom': None
    },
    {
        'name': 'Custom explanation provided',
        'change': {
            'topic_code': '3',
            'topic_name': 'ילדי ח"מ 5י\' קשה',
            'items_change': 4,
            'amount_change': 361783
        },
        'custom': 'נוספו 4 ילדים חדשים לתחילת החודש'
    }
]

print("=" * 80)
print("📊 TESTING CHANGE EXPLANATION GENERATION")
print("=" * 80)
print()

for idx, test in enumerate(tests, 1):
    result = generate_change_explanation(test['change'], test['custom'])
    
    print(f"Test {idx}: {test['name']}")
    print("-" * 80)
    print(f"💡 Generated: {result['text']}")
    print(f"🔑 Is Custom: {result['is_custom']}")
    print()

print("=" * 80)
print("✅ All tests generated explanations successfully!")
print()
print("Integration complete:")
print("  1️⃣  changeExplanations.js created with generateChangeExplanation()")
print("  2️⃣  PortalBudgetPage.jsx updated to display explanations")
print("  3️⃣  AdminBudgetDetailPage.jsx updated to display explanations")
print("  4️⃣  Explanations auto-generated based on change type or show CPA custom text")
print()
print("How it works:")
print("  • If CPA has added a custom explanation → displays that in italics")
print("  • Otherwise → auto-generates Hebrew explanation based on change type")
print("  • Shows in light blue info box with 💡 icon")
print("  • Displayed right below each change card in month changes section")
