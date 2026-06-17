"""
Purple Booklet Rules (חוברת תקצוב ה"שת)

Contains all topic codes and explanation templates from the
Ministry of Education budget booklet (Purple Booklet - Sefer Sagol).

Based on REAL Ministry file structure with actual topic codes:
- 3: שכל"מ גנ'י (Kindergarten teaching fees)
- 19: תורזוע לתוננג (Teacher assistants)
- 33: תוננג תודבוע הנידמ (State employee kindergarten teachers)
- 50: תועסה (Student transport)
- 47: שירותים פסיכולוגיים (Psychological services)
- 5: ס.ב.ק - קצין ביקור סדיר (Attendance officers)

Auto-generates explanations for:
- Regular payments (תשלום רגיל)
- Retro payments (תשלום רטרואקטיבי)
- Shortage payments (חוסר / קיצוץ)
- Adjustment payments (התאמה טכנית)
"""

HEBREW_MONTHS = {
    "01": "ינואר",
    "02": "פברואר",
    "03": "מרץ",
    "04": "אפריל",
    "05": "מאי",
    "06": "יוני",
    "07": "יולי",
    "08": "אוגוסט",
    "09": "ספטמבר",
    "10": "אוקטובר",
    "11": "נובמבר",
    "12": "דצמבר",
}

BUDGET_TOPIC_RULES = {
    
    # === KINDERGARTENS (גני ילדים) ===
    "3": {
        "code": "3",
        "name": "שכל\"מ גנ'י",
        "full_name": "שכר לימוד מוסד — גני ילדים",
        "category": "גני ילדים",
        "page_in_booklet": 45,
        "hebrew_description": "תשלום בגין שכר לימוד בגני הילדים הרשמיים",
        "formula": "מספר ילדים × עלות לדלי × אחוז השתתפות",
        
        "sub_topics": {
            "ילדי ח\"מ 5'י": {
                "description": "ילדי חינוך מחויב גיל 5-6",
                "participation_pct": 100,
                "change_reasons": [
                    "שינוי במספר הילדים הרשומים",
                    "עדכון טבלת שכר",
                    "שינוי מדרגת הסיוע",
                ]
            },
            "גיל 3-4 ג'י": {
                "description": "ילדי גיל 3-4 בגן חינוך חובה",
                "participation_pct": 90,
                "change_reasons": [
                    "שינוי במספר ילדים גיל 3-4",
                    "עדכון עלות לדלי",
                ]
            }
        },
        
        "regular_explanation": "תשלום שוטף עבור שכר לימוד בגני ילדים",
        "retro_explanation": "השלמת תשלום שכר לימוד בגני ילדים עבור {period_month}",
        "shortage_explanation": "חוסר בתשלום גני ילדים של ₪{difference}",
        "adjustment_explanation": "התאמה בתשלום גני ילדים",
    },

    # === TEACHER ASSISTANTS (תורזוע לתוננג) ===
    "19": {
        "code": "19",
        "name": "תורזוע לתוננג",
        "full_name": "תורזוע לתוננג",
        "category": "גני ילדים",
        "page_in_booklet": 48,
        "hebrew_description": "תשלום עבור תקן תורזוע תוננג בגני הילדים",
        "formula": "מספר תורזוע × עלות תרשמ × 90%",
        "participation_pct": 90,
        "regular_explanation": "תשלום שוטף עבור תורזוע בגני הילדים",
        "retro_explanation": "השלמת תשלום תורזוע בגני ילדים עבור {period_month}",
        "shortage_explanation": "חוסר בתשלום תורזוע של ₪{difference}",
        "adjustment_explanation": "התאמה בתשלום תורזוע",
    },

    # === STATE EMPLOYEE KINDERGARTEN TEACHERS ===
    "33": {
        "code": "33",
        "name": "תוננג תודבוע הנידמ",
        "full_name": "תוננג תודבוע הנידמ",
        "category": "גני ילדים",
        "page_in_booklet": 51,
        "hebrew_description": "ניכוי בגין תוננגה עובדות המדינה",
        "regular_explanation": "ניכוי שוטף בגין תוננגה עובדות המדינה",
        "retro_explanation": "השלמת ניכוי בגין תוננג תודבוע הנידמ עבור {period_month}",
        "shortage_explanation": "חוסר בניכוי של ₪{difference}",
        "adjustment_explanation": "התאמה בניכוי תוננג תודבוע",
    },

    # === STUDENT TRANSPORT (תועסה) ===
    "50": {
        "code": "50",
        "name": "תועסה",
        "full_name": "תועסה תלדימ לחינוך הרגיל",
        "category": "תועסה",
        "page_in_booklet": 22,
        "hebrew_description": "החזר הוצאות נסיעה לתלמידים הזכאים בחינוך הרגיל",
        "formula": "מספר תלמידים × עלות נסיעה × אחוז השתתפות",
        "regular_explanation": "תשלום שוטף עבור תועסה תלמידים בחינוך הרגיל",
        "retro_explanation": "השלמת תשלום תועסה תלמידים עבור {period_month}",
        "shortage_explanation": "חוסר בתשלום תועסה של ₪{difference}",
        "adjustment_explanation": "התאמה בתשלום תועסה",
        
        "change_reasons": [
            "שינוי במספר תלמידים זכאים לנסיעה",
            "עדכון מחיר הנסיעה",
            "שינוי בכתובת המגורים של תלמידים",
        ]
    },

    # === PSYCHOLOGICAL SERVICES (שירותים פסיכולוגיים) ===
    "47": {
        "code": "47",
        "name": "שירותים פסיכולוגיים",
        "full_name": "שירותים פסיכולוגיים חינוכיים",
        "category": "שירותים פסיכולוגיים",
        "page_in_booklet": 14,
        "hebrew_description": "תשלום עבור פסיכולוגים חינוכיים המועסקים על ידי הרשות",
        "formula": "מספר פסיכולוגים מאושרים × עלות תרשמ × 68%",
        "participation_pct": 68,
        "regular_explanation": "תשלום שוטף עבור פסיכולוגים חינוכיים",
        "retro_explanation": "השלמת תשלום פסיכולוגים חינוכיים עבור {period_month}",
        "shortage_explanation": "חוסר בתשלום פסיכולוגים של ₪{difference}",
        "adjustment_explanation": "התאמה בתשלום פסיכולוגים",
    },

    # === ATTENDANCE OFFICERS (ס.ב.ק) ===
    "5": {
        "code": "5",
        "name": "ס.ב.ק",
        "full_name": "קצין ביקור סדיר",
        "category": "נושאים כלל-רשותיים",
        "page_in_booklet": 10,
        "hebrew_description": "השתתפות בעלות קצין ביקור סדיר",
        "formula": "מספר ס.ב.ק מאושרים × עלות תרשמ × 75%",
        "participation_pct": 75,
        "regular_explanation": "תשלום שוטף עבור קצין ביקור סדיר",
        "retro_explanation": "השלמת תשלום קצין ביקור סדיר עבור {period_month}",
        "shortage_explanation": "חוסר בתשלום ס.ב.ק של ₪{difference}",
        "adjustment_explanation": "התאמה בתשלום ס.ב.ק",
    },
}


def get_budget_topic(topic_code):
    """Get the rules for a specific budget topic code."""
    return BUDGET_TOPIC_RULES.get(str(topic_code))


def get_all_budget_topics():
    """Get all budget topics."""
    return BUDGET_TOPIC_RULES


def get_explanation_template(topic_code, line_type):
    """
    Get the explanation template for a specific topic and line type.
    
    Args:
        topic_code: e.g., "3", "19", "50"
        line_type: "regular", "retro", "shortage", "adjustment"
    
    Returns:
        str: The explanation template in Hebrew
    """
    rules = BUDGET_TOPIC_RULES.get(str(topic_code))
    
    if not rules:
        return "תשלום לנושא זה"
    
    key = f"{line_type}_explanation"
    return rules.get(key, "פרטים נוספים יסופקו על ידי רואה החשבון")


def get_hebrew_month(month_str):
    """
    Convert YYYY-MM format to Hebrew month name.
    Example: "2026-03" → "מרץ 2026"
    """
    if not month_str or '-' not in month_str:
        return month_str
    try:
        year, month = month_str.split('-')
        hebrew_month = HEBREW_MONTHS.get(month, month)
        return f"{hebrew_month} {year}"
    except:
        return month_str
