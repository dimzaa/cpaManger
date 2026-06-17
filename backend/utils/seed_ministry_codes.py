"""
Seed ministry budget codes into ministry_codes table on startup (if empty).

Covers 89 real ministry codes observed in uploaded MUTAVIM/CHESHBONIT/GY*/SHEFI/
SACAL/HASAOT/HASMASLULIM/MISROT/MUCARIM/MOADON/ICHLUSKITOT/SHARATIM CSV files,
with Hebrew name, full name, and category for every code. Anchor codes (003,
019, 033, 045, 046, 047, 050-family) carry full metadata (formula, participation
percent, change triggers, sub-topics, booklet section). All remaining codes
carry the core fields so downstream UI, filters, preset-matching, deadlines and
explanation suggestions can identify them by code and category.

Code format: 3-digit zero-padded strings (e.g. "003", "019", "045") — matching
the literal values emitted by the Ministry's CSV files and stored by the
file_parser on budget_lines.topic_code.
"""
import json
from sqlalchemy.orm import Session
from backend.models.ministry_code import MinistryCode


# ---------------------------------------------------------------------------
# Anchor codes — rich metadata carried over from earlier release
# ---------------------------------------------------------------------------
CODES_DATA = [
    {
        "code": "003",
        "name_short": 'שכל"מ גנ\'י',
        "name_full": "שכר לימוד מוסד — גני ילדים",
        "category": "גני ילדים",
        "description": (
            "תשלום בגין שכר לימוד בגני הילדים הרשמיים והמוכרים. "
            "המשרד משתתף בעלות הגננת והעוזרת לפי מספר הילדים הרשומים."
        ),
        "formula": (
            "עלות גן = עלות גננת + עלות עוזרת + הוצאות שאינן שכר\n"
            "עלות ילד = עלות גן ÷ [31 או 33]\n"
            "תשלום = עלות ילד × מספר ילדים × אחוז השתתפות"
        ),
        "participation_percent": 90.0,
        "constant_divisor": 31,
        "payment_type": "monthly",
        "applies_to": "all",
        "booklet_page": 45,
        "purple_book_column": "ד",
        "booklet_section": 'גני ילדים — שכל"מ',
        "is_deduction": False,
        "sub_topics": [
            "ילדי ח\"מ 5י' קשה",
            "ילדי ח\"מ 5י' קל",
            "גיל 3-4 5י'",
            "ילדי השלמה 5י'",
        ],
        "change_triggers": [
            "שינוי במספר הילדים הרשומים",
            "עדכון טבלת שכר גננת/עוזרת",
            "שינוי אחוז השתתפות",
            "שינוי מעמד מענק (31/33)",
            "פתיחת/סגירת גן ילדים",
            "אישור ילדי השלמה",
        ],
        "related_codes": ["019", "033"],
        "keywords": "גן ילדים שכר לימוד גננת ילדים חינוך חובה",
    },
    {
        "code": "019",
        "name_short": "עוזרות גננות",
        "name_full": "עוזרות לגננות בגני חובה רשמיים",
        "category": "גני ילדים",
        "description": (
            "תשלום עבור משרות עוזרת לגננת בגני חובה רשמיים. "
            "המשרד משתתף ב-100% מעלות משרת העוזרת."
        ),
        "formula": (
            "5 ימים: מספר משרות × עלות משרה × 100%\n"
            "6 ימים: מספר משרות × עלות משרה × 100% × 1.1785"
        ),
        "participation_percent": 100.0,
        "constant_divisor": None,
        "payment_type": "monthly",
        "applies_to": "all",
        "booklet_page": 48,
        "purple_book_column": "ד",
        "booklet_section": "גני ילדים — עוזרות",
        "is_deduction": False,
        "sub_topics": [
            "עוזרות 5 ימים",
            "עוזרות 6 ימים",
            "עוזר 5י' (חנמ קשה)",
            "עוזר 5י' (חנמ קל)",
        ],
        "change_triggers": [
            "פתיחת משרה חדשה",
            "ביטול משרה",
            "מעבר מ-5 ל-6 ימים (+17.85%)",
            "חופשת לידה של עוזרת",
            "עדכון עלות משרה",
        ],
        "related_codes": ["003", "033"],
        "keywords": "עוזרת גננת סייעת גן ילדים משרה",
    },
    {
        "code": "033",
        "name_short": "גננות עוב' מדינה",
        "name_full": "ניכוי שכר גננות עובדות המדינה",
        "category": "גני ילדים",
        "description": (
            "ניכוי עבור שכר גננות שהן עובדות מדינה. "
            "הרשות מחזירה למשרד את עלות הגננות שמשרד החינוך מעסיק ישירות."
        ),
        "formula": (
            "מספר גננות עובדות מדינה × עלות משרה = ניכוי (סכום שלילי)"
        ),
        "participation_percent": 100.0,
        "constant_divisor": None,
        "payment_type": "monthly",
        "applies_to": "all",
        "booklet_page": 51,
        "purple_book_column": "ד",
        "booklet_section": "גני ילדים — גננות",
        "is_deduction": True,
        "sub_topics": [],
        "change_triggers": [
            "שיבוץ גננת עובדת מדינה חדשה",
            "פרישה לגמלאות",
            "חופשת לידה",
            "שינוי בדרגת ותק (שינוי עלות)",
            "העברה לגן אחר",
        ],
        "related_codes": ["003", "019"],
        "keywords": "גננת עובדת מדינה ניכוי שכר",
    },
    {
        "code": "045",
        "name_short": 'קב"ס',
        "name_full": "קצין ביקור סדיר",
        "category": "נושאים רשותיים",
        "description": (
            "השתתפות בעלות משרת קצין ביקור סדיר האחראי על מניעת נשירה."
        ),
        "formula": 'מספר קב"סים מאושר × עלות משרה × 75%',
        "participation_percent": 75.0,
        "constant_divisor": None,
        "payment_type": "monthly",
        "applies_to": "all",
        "booklet_page": 10,
        "purple_book_column": "ב",
        "booklet_section": 'נושאים רשותיים — קב"ס',
        "is_deduction": False,
        "sub_topics": [],
        "change_triggers": [
            'שינוי במספר קב"סים מאושרים',
            "עדכון עלות משרה",
            "שינוי מתח דרגות",
        ],
        "related_codes": [],
        "keywords": "קצין ביקור סדיר נשירה תלמידים",
    },
    {
        "code": "046",
        "name_short": 'קב"ט',
        "name_full": 'קצין ביטחון — קב"ט',
        "category": "נושאים רשותיים",
        "description": (
            "השתתפות בעלות משרת קצין ביטחון במוסדות חינוך."
        ),
        "formula": 'מספר קב"טים מאושר × עלות משרה × 75%',
        "participation_percent": 75.0,
        "constant_divisor": None,
        "payment_type": "monthly",
        "applies_to": "all",
        "booklet_page": 11,
        "purple_book_column": "ב",
        "booklet_section": "ביטחון מוסדות חינוך",
        "is_deduction": False,
        "sub_topics": [],
        "change_triggers": [
            'שינוי במספר קב"טים',
            "עדכון עלות משרה",
        ],
        "related_codes": [],
        "keywords": 'קב"ט ביטחון מוסדות קצין',
    },
    {
        "code": "047",
        "name_short": "פסיכולוגים",
        "name_full": "פסיכולוגים חינוכיים",
        "category": "שירותים פסיכולוגיים",
        "description": (
            "תשלום עבור פסיכולוגים חינוכיים המועסקים על ידי הרשות המקומית."
        ),
        "formula": "מספר פסיכולוגים × עלות משרה × 68%",
        "participation_percent": 68.0,
        "constant_divisor": None,
        "payment_type": "monthly",
        "applies_to": "all",
        "booklet_page": 14,
        "purple_book_column": "ב",
        "booklet_section": "שירותים פסיכולוגיים",
        "is_deduction": False,
        "sub_topics": [],
        "change_triggers": [
            "שינוי במספר פסיכולוגים מאושרים",
            "עדכון עלות משרה",
        ],
        "related_codes": ["081", "091"],
        "keywords": "פסיכולוג חינוכי שירות נפשי",
    },
    {
        "code": "052",
        "name_short": "הסעות",
        "name_full": "הסעות תלמידים (חינוך רגיל — מסלולים)",
        "category": "הסעות",
        "description": (
            "החזר הוצאות נסיעה לתלמידים הזכאים בחינוך הרגיל."
        ),
        "formula": (
            "לתלמיד: מספר תלמידים × עלות תלמיד × ימי הסעה × אחוז השתתפות\n"
            "למסלול: עלות מסלול × ימי הסעה × אחוז השתתפות"
        ),
        "participation_percent": 80.0,
        "constant_divisor": None,
        "payment_type": "monthly",
        "applies_to": "all",
        "booklet_page": 22,
        "purple_book_column": "ג",
        "booklet_section": "הסעות תלמידים",
        "is_deduction": False,
        "sub_topics": [],
        "change_triggers": [
            "שינוי במספר תלמידים מוסעים",
            "שינוי מחיר נסיעה",
            "שינוי אחוז השתתפות לפי מענק",
        ],
        "related_codes": ["140", "170", "258"],
        "keywords": "הסעה תלמיד אוטובוס נסיעה מסלול",
    },
]


# ---------------------------------------------------------------------------
# Full catalog — 89 codes drawn from live MUTAVIM / CHESHBONIT / GY*/SHEFI /
# SACAL / HASAOT / HASMASLULIM / MISROT / SHARATIM / MOADON / MUCARIM CSVs.
# (code, name_short, name_full, category, is_deduction)
# ---------------------------------------------------------------------------
_CATALOG = [
    ("001", 'שכ"ל על-יסודי', 'שכר לימוד — חטיבה עליונה', "שכר לימוד", False),
    ("002", "שרתים", "שרתים במוסדות חינוך", "נושאים רשותיים", False),
    ("035", 'קרן השתלמות לשכ"ל', 'קרן השתלמות עבור שכר לימוד', "שכר לימוד", False),
    ("071", 'החזר שכ"ל למורים', 'החזר שכר לימוד למורים', "שכר לימוד", False),
    ("081", 'פסיכולוגים מתמחים', "פסיכולוגים מתמחים ברשויות", "שירותים פסיכולוגיים", False),
    ("088", "דמי שתיה", "דמי שתיה לתלמידים", "כללי", False),
    ("091", 'שפ"י', 'שפ"י — שעות הדרכה', "שירותים פסיכולוגיים", False),
    ("092", "רכב מנהלים", 'רכב מנהלי בתי ספר על-יסודיים', "נושאים רשותיים", False),
    ("101", "רכב סגני מנהלים", "רכב סגני מנהלי בתי ספר", "נושאים רשותיים", False),
    ("105", "שרתים - חוות ומרכזים", "שרתים בחוות חקלאיות ומרכזים", "נושאים רשותיים", False),
    ("107", "מזכירים", "מזכירי בתי ספר", "נושאים רשותיים", False),
    ("109", "מזכירים חוות ומרכזים", "מזכירים בחוות ומרכזים", "נושאים רשותיים", False),
    ("140", "הסעות ח.מיוחד", "הסעות חינוך מיוחד (מקדמה)", "הסעות", False),
    ("160", 'הזנת יוח"א', 'הזנת יום חינוך ארוך', "כללי", False),
    ("170", 'סיעות כיתות חריגות', 'סייעות כיתות בית ספר חריגות', "הסעות", False),
    ("171", "סייעות כיתתיות", "סייעות כיתתיות ביסודי", "נושאים רשותיים", False),
    ("172", 'שרותי היקף ח.מיוחד', 'שירותי היקף — חינוך מיוחד', "חינוך מיוחד", False),
    ("173", "גמול בגרות אחוזי", "גמול בגרות — אחוזי הצלחה", "חטיבה עליונה", False),
    ("177", "גמול טיולים", 'גמול טיולים — חוץ בית ספרי', "כללי", False),
    ("185", "תשלומי הורים חומרים", "תשלומי הורים — חומרים", "כללי", False),
    ("214", 'סל תלמיד חט"ב', 'סל תלמיד לחטיבת הביניים', "חטיבת ביניים", False),
    ("223", "חיוב תלמידי חוץ", "חיוב בגין תלמידי חוץ", "תלמידי חוץ", True),
    ("224", "זיכוי תלמידי חוץ", "זיכוי בגין תלמידי חוץ", "תלמידי חוץ", False),
    ("232", "אגרת שכפול יסודי", "אגרת שכפול בחינוך יסודי", "חינוך יסודי", False),
    ("237", "מענק יובל על-יסודי", "מענק יובל — חטיבה עליונה", "חטיבה עליונה", False),
    ("242", "מועדוניות ברשויות", "מועדוניות ברשויות המקומיות", "תכניות העשרה", False),
    ("258", 'ל. הסעות ח"מ', 'לימודי הסעות חינוך מיוחד', "הסעות", False),
    ("277", "חופשות לאוטיסטים", "חופשות לתלמידי הספקטרום האוטיסטי", "חינוך מיוחד", False),
    ("285", 'הבראה וביגוד שכ"ל', 'הבראה וביגוד — שכר לימוד', "שכר לימוד", False),
    ("316", "חינוך תעבורתי", "חינוך תעבורתי וזהירות בדרכים", "תכניות העשרה", False),
    ("338", 'מוביל ב"ס מניעת סמים', 'מוביל בית ספרי למניעת סמים', "נושאים רשותיים", False),
    ("345", "חוק שילוב - סייעות", "חוק שילוב — סייעות לחינוך מיוחד", "חינוך מיוחד", False),
    ("361", "סייעות על-יסודי", "סייעות בחטיבה עליונה", "חטיבה עליונה", False),
    ("388", 'ש.בודדת חופש חנ"מ חט"ע', 'שעה בודדת בחופשות — חינוך מיוחד חט"ע', "חינוך מיוחד", False),
    ("389", 'חופש אחה"צ חט"ע אוטיס', 'חופשות אחה"צ — חט"ע אוטיסטים', "חינוך מיוחד", False),
    ("401", 'ה.נלוות ח"מ גני ערבי', 'הוצאות נלוות — חינוך מיוחד גני ילדים ערבי', "חינוך מיוחד", False),
    ("402", 'העשרה חנ"מ גני ערבי', 'שעות העשרה — חנ"מ גני ילדים ערבי', "חינוך מיוחד", False),
    ("403", "ה.נלוות ח.מיוחד ערבי", "הוצאות נלוות — חינוך מיוחד ערבי", "חינוך מיוחד", False),
    ("404", "העשרה ח.מיוחד ערבי", "שעות העשרה — חינוך מיוחד ערבי", "חינוך מיוחד", False),
    ("446", "מוחזקות פריפריאלי", "מוחזקות חדש — פריפריאלי", "חינוך יסודי", False),
    ("456", 'שעות שילוב חט"ע', 'שעות שילוב בחטיבה עליונה', "חינוך מיוחד", False),
    ("502", "סייעות רפואיות", "סייעות רפואיות לתלמידים", "חינוך מיוחד", False),
    ("504", "עתודה מדעית טכנולוגית", "עתודה מדעית טכנולוגית", "תכניות העשרה", False),
    ("553", "מילוי מקום מוסדות", "מילוי מקום במוסדות חינוך", "שכר לימוד", False),
    ("556", "ש.פרטניות עוז", 'שעות פרטניות — עוז לתמורה', "עוז לתמורה", False),
    ("557", "ש.תומכות עוז", 'שעות תומכות — עוז לתמורה', "עוז לתמורה", False),
    ("558", "מנהל עוז לתמורה", 'גמול מנהל/ת בעוז לתמורה', "עוז לתמורה", False),
    ("559", "שעות תפקיד עוז", 'שעות תפקיד — עוז לתמורה', "עוז לתמורה", False),
    ("561", 'אוריינות מדעית כיתה י', "אוריינות מדעית — כיתה י'", "תכניות העשרה", False),
    ("567", "ש.פרטניות נוספות עוז", 'שעות פרטניות נוספות — עוז', "עוז לתמורה", False),
    ("568", "ש.תומכות נוספות עוז", 'שעות תומכות נוספות — עוז', "עוז לתמורה", False),
    ("571", "ניהול עצמי א-ו", "ניהול עצמי משופר כיתות א-ו", "ניהול עצמי", False),
    ("572", "ניהול עצמי ז-ח", "ניהול עצמי משופר כיתות ז-ח", "ניהול עצמי", False),
    ("575", "מוחזקות עוז", "מוחזקות — עוז לתמורה", "עוז לתמורה", False),
    ("595", "גמול מנהליות נ. עצמי", "גמול מנהליות — ניהול עצמי", "ניהול עצמי", False),
    ("598", "מסגרת קיץ תלמיד רגיל", "מסגרת קיץ — תלמיד חינוך רגיל", "קיץ", False),
    ("599", 'מסגרת קיץ תלמיד חנ"מ', 'מסגרת קיץ — תלמיד חינוך מיוחד', "קיץ", False),
    ("600", "מסגרת קיץ פר מוסד", "מסגרת קיץ — תקצוב לפי מוסד", "קיץ", False),
    ("603", "סייעות רפואיות בקיץ", "סייעות רפואיות בחופשת קיץ", "קיץ", False),
    ("604", "רכז מעורבות חברתית", "רכז מעורבות חברתית בתיכונים", "תכניות העשרה", False),
    ("606", "משרות דרגות קידום", "משרות דרגות קידום מקצועי", "שכר לימוד", False),
    ("611", 'גמול רכז הל"ל', 'גמול רכז הל"ל (הוראה לקראת לימוד)', "שכר לימוד", False),
    ("614", "סייעת 2 והעשרה רשמי", "סייעת שנייה והעשרה — גני רשמי", "גני ילדים", False),
    ("631", 'תכנית ניצנים גנ"י', "תכנית ניצנים — גני ילדים", "תכניות העשרה", False),
    ("632", 'תכנית ניצנים בי"ס', "תכנית ניצנים — בית ספר", "תכניות העשרה", False),
    ("643", "מסג.חינוכיות בחופשות", "מסגרות חינוכיות בחופשות", "תכניות העשרה", False),
    ("654", 'גמול חנ"מ חט"ע', 'גמול חינוך מיוחד — חטיבה עליונה', "חינוך מיוחד", False),
    ("655", "מצוינות בפריפריה", "קרן מצוינות בפריפריה", "תכניות העשרה", False),
    ("660", 'גמול חונך חט"ע', 'גמול חונך — חטיבה עליונה', "חטיבה עליונה", False),
    ("669", "מסיבות כיתה וסל תרבות", "מסיבות כיתתיות וסל תרבות", "תכניות העשרה", False),
    ("671", 'מסגרת קיץ גנ"י רגיל', "מסגרת קיץ — גני ילדים חינוך רגיל", "קיץ", False),
    ("681", "רכזת גנים חופש גדול", "רכזת גנים — חופש הגדול", "קיץ", False),
    ("682", "ל.דפרנצלי בה. הערבית", "לימודים דיפרנציאליים — בהוראה הערבית", "שכר לימוד", False),
    ("704", "גפן קיזוז השתתפות", "גפן — קיזוז השתתפות רשות", "תכניות העשרה", True),
    ("705", 'גפן מוכש"ר', 'גפן — חינוך מוכר שאינו רשמי', "תכניות העשרה", False),
    ("707", 'גפן השתתפות חט"ע', 'גפן — קרן השתתפות רשות חט"ע', "תכניות העשרה", False),
    ("708", "גפן סל רשותי", "גפן — סל רשותי", "תכניות העשרה", False),
    ("710", "מנהל מחלקת נוער", "שכר מנהל מחלקת נוער", "נושאים רשותיים", False),
    ("711", "כיתות מצויינות", "כיתות מצוינות", "תכניות העשרה", False),
    ("729", "רכז מיומנות עוז", "רכז מיומנות — עוז לתמורה", "עוז לתמורה", False),
    ("731", "גפן גיל הרך", "גפן — גיל הרך", "גני ילדים", False),
    ("736", "גמול רכז שכבה", "גמול רכז שכבה", "שכר לימוד", False),
]


def _build_lightweight_entry(code: str, name_short: str, name_full: str,
                              category: str, is_deduction: bool) -> dict:
    """Build a minimal ministry-code record for codes without rich metadata."""
    return {
        "code": code,
        "name_short": name_short,
        "name_full": name_full,
        "category": category,
        "description": None,
        "formula": None,
        "participation_percent": None,
        "constant_divisor": None,
        "payment_type": "monthly",
        "applies_to": "all",
        "booklet_page": None,
        "purple_book_column": None,
        "booklet_section": category,
        "is_deduction": is_deduction,
        "sub_topics": [],
        "change_triggers": [],
        "related_codes": [],
        "keywords": f"{name_short} {category}",
    }


# Merge rich anchors with lightweight catalog entries (skipping anchors already present)
_anchor_codes = {entry["code"] for entry in CODES_DATA}
for code, short, full, category, is_deduction in _CATALOG:
    if code in _anchor_codes:
        continue
    CODES_DATA.append(_build_lightweight_entry(code, short, full, category, is_deduction))


def _normalize_code(code: str) -> str:
    """
    Canonical form of a ministry code: 3-digit zero-padded when the raw value
    is a pure integer (matches the file_parser's topic_code output). Leaves
    non-numeric or already-padded codes untouched.
    """
    s = str(code).strip()
    if s.isdigit() and len(s) < 3:
        return s.zfill(3)
    return s


def seed_ministry_codes(db: Session) -> int:
    """
    Upsert ministry codes.

    - Rows not yet present are inserted.
    - Rows already present are updated in place (name, category, is_deduction,
      and rich anchor metadata overwrite stale values from earlier seeds).
    - Legacy short-form anchors ("3", "19", "33", "45", "47", "50") are
      migrated to their canonical zero-padded form to stay consistent with the
      CSV-derived topic_code values stored on budget_lines.

    Returns the number of rows inserted or updated (0 when nothing changed).
    """
    # Migrate any legacy short codes to their 3-digit canonical form first,
    # so the upsert below lands on the right row.
    legacy_map = {"3": "003", "5": "046", "19": "019", "33": "033",
                  "45": "045", "47": "047", "50": "052"}
    for legacy, canonical in legacy_map.items():
        legacy_row = db.query(MinistryCode).filter(MinistryCode.code == legacy).first()
        if not legacy_row:
            continue
        # If both exist, drop the legacy row; otherwise rename it.
        canonical_row = db.query(MinistryCode).filter(MinistryCode.code == canonical).first()
        if canonical_row:
            db.delete(legacy_row)
        else:
            legacy_row.code = canonical
    db.flush()

    changed = 0
    for entry in CODES_DATA:
        code = _normalize_code(entry["code"])
        mc = db.query(MinistryCode).filter(MinistryCode.code == code).first()

        fields = dict(
            name_short=entry["name_short"],
            name_full=entry["name_full"],
            category=entry["category"],
            description=entry.get("description"),
            formula=entry.get("formula"),
            participation_percent=entry.get("participation_percent"),
            constant_divisor=entry.get("constant_divisor"),
            payment_type=entry.get("payment_type", "monthly"),
            applies_to=entry.get("applies_to", "all"),
            booklet_page=entry.get("booklet_page"),
            purple_book_column=entry.get("purple_book_column"),
            booklet_section=entry.get("booklet_section"),
            is_deduction=entry.get("is_deduction", False),
            sub_topics=json.dumps(entry.get("sub_topics") or [], ensure_ascii=False),
            change_triggers=json.dumps(entry.get("change_triggers") or [], ensure_ascii=False),
            related_codes=json.dumps(entry.get("related_codes") or [], ensure_ascii=False),
            keywords=entry.get("keywords"),
            is_active=True,
        )

        if mc is None:
            db.add(MinistryCode(code=code, **fields))
            changed += 1
        else:
            dirty = False
            for attr, val in fields.items():
                if getattr(mc, attr) != val:
                    setattr(mc, attr, val)
                    dirty = True
            if dirty:
                changed += 1

    db.commit()
    return changed
