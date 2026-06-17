"""
Seed all default reasons into reasons_library table.
Runs on application startup if table is empty.
"""

from backend.database import SessionLocal
from backend.models.reason_library import ReasonLibrary
from sqlalchemy import select


def seed_reasons_library():
    """Seed all default reasons — runs once on startup"""
    db = SessionLocal()
    
    try:
        # Check if reasons already exist
        existing = db.execute(select(ReasonLibrary).limit(1)).first()
        if existing:
            print("✓ Reasons library already seeded")
            return
        
        # All 30 reasons from specification
        reasons = [
            # --- קוד 3 — גני ילדים (5 reasons) ---
            ReasonLibrary(
                code="KID_REG_NEW",
                topic_codes=["3"],
                category="ילדים",
                title_hebrew="ילד/ה חדש/ה נרשמ/ה",
                explanation_template="נרשמ/ה ילד/ה חדש/ה לגן החינוך ברשות. מספר הילדים המתוקצבים עלה בהתאם.",
                direction="increase",
                severity="routine",
                requires_detail=True,
                detail_prompt="כמה ילדים נרשמו?",
                sort_order=1,
            ),
            ReasonLibrary(
                code="KID_TRANSFER_OUT",
                topic_codes=["3"],
                category="ילדים",
                title_hebrew="ילד/ה עבר/ה לרשות אחרת",
                explanation_template="ילד/ה אחד/ת או יותר עבר/ו לרשות מקומית אחרת. מספר הילדים המתוקצבים ירד בהתאם.",
                direction="decrease",
                severity="routine",
                requires_detail=True,
                detail_prompt="כמה ילדים עברו?",
                sort_order=2,
            ),
            ReasonLibrary(
                code="KID_TRANSFER_IN",
                topic_codes=["3"],
                category="ילדים",
                title_hebrew="ילד/ה הגיע/ה מרשות אחרת",
                explanation_template="ילד/ה אחד/ת או יותר הצטרפ/ו לגן מרשות אחרת עם אישור העברה.",
                direction="increase",
                severity="routine",
                requires_detail=True,
                detail_prompt="כמה ילדים הגיעו?",
                sort_order=3,
            ),
            ReasonLibrary(
                code="KID_AGE_MOVED",
                topic_codes=["3"],
                category="ילדים",
                title_hebrew="מעבר ממסלול 3-4 למסלול 5-6",
                explanation_template="ילדים עברו ממסלול גיל 3-4 (90% השתתפות) למסלול גיל חובה 5-6 (100% השתתפות). השינוי משפיע על עלות לילד.",
                direction="increase",
                severity="routine",
                requires_detail=False,
                sort_order=4,
            ),
            ReasonLibrary(
                code="KID_COMPLETION_ADDED",
                topic_codes=["3"],
                category="ילדים",
                title_hebrew="ילדי השלמה אושרו",
                explanation_template="אושרו ילדי השלמה לגן עם פחות מ-28 תלמידים, בהתאם לאישור האגף הבכיר אמח״י.",
                direction="increase",
                severity="routine",
                requires_detail=True,
                detail_prompt="כמה ילדי השלמה אושרו?",
                sort_order=5,
            ),
            
            # --- קוד 3, 19 — גן (2 more reasons) ---
            ReasonLibrary(
                code="KID_COMPLETION_REMOVED",
                topic_codes=["3"],
                category="ילדים",
                title_hebrew="ילדי השלמה בוטלו",
                explanation_template="ילדי השלמה שאושרו בעבר הוסרו מהתקצוב לאחר שמספר הילדים בגן עלה על 28.",
                direction="decrease",
                severity="attention",
                requires_detail=False,
                sort_order=6,
            ),

            # --- קוד 3, 19 — מדיניות (2 reasons) ---
            ReasonLibrary(
                code="GRANT_STATUS_CHANGED_31",
                topic_codes=["3", "19"],
                category="מדיניות",
                title_hebrew="שינוי מעמד מענק — עכשיו 31",
                explanation_template="הרשות קיבלה מעמד של מקבלת מענק איזון. החישוב עבר מ-33 ל-31 ילדים למשרה — עלות לילד עלתה בהתאם.",
                direction="increase",
                severity="attention",
                requires_detail=False,
                sort_order=10,
            ),
            ReasonLibrary(
                code="GRANT_STATUS_CHANGED_33",
                topic_codes=["3", "19"],
                category="מדיניות",
                title_hebrew="שינוי מעמד מענק — עכשיו 33",
                explanation_template="הרשות איבדה מעמד של מקבלת מענק איזון. החישוב עבר מ-31 ל-33 ילדים למשרה — עלות לילד ירדה בהתאם.",
                direction="decrease",
                severity="attention",
                requires_detail=False,
                sort_order=11,
            ),

            # --- קוד 19 — עוזרות גננות (5 reasons) ---
            ReasonLibrary(
                code="ASST_NEW_POSITION",
                topic_codes=["19"],
                category="משרות",
                title_hebrew="משרת עוזרת חדשה אושרה",
                explanation_template="אושרה משרת עוזרת גננת חדשה על ידי משרד החינוך. התשלום כולל את העלות המלאה של המשרה החדשה.",
                direction="increase",
                severity="routine",
                requires_detail=True,
                detail_prompt="לאיזה גן נוספה המשרה?",
                sort_order=20,
            ),
            ReasonLibrary(
                code="ASST_MATERNITY_RETURN",
                topic_codes=["19"],
                category="משרות",
                title_hebrew="עוזרת חזרה מחופשת לידה",
                explanation_template="עוזרת גננת חזרה לעבודה לאחר חופשת לידה. התשלום חודש לאחר הפסקה.",
                direction="increase",
                severity="routine",
                requires_detail=False,
                sort_order=21,
            ),
            ReasonLibrary(
                code="ASST_MATERNITY_START",
                topic_codes=["19"],
                category="משרות",
                title_hebrew="עוזרת יצאה לחופשת לידה",
                explanation_template="עוזרת גננת יצאה לחופשת לידה. התשלום הופסק זמנית עד לחזרתה.",
                direction="decrease",
                severity="routine",
                requires_detail=False,
                sort_order=22,
            ),
            ReasonLibrary(
                code="ASST_6DAY_ADDED",
                topic_codes=["19"],
                category="גן",
                title_hebrew="גן עבר ל-6 ימים בשבוע",
                explanation_template="הגן עבר לפעילות 6 ימים בשבוע. נוספה תוספת של 17.85% בגין יום ו'.",
                direction="increase",
                severity="routine",
                requires_detail=False,
                sort_order=23,
            ),
            ReasonLibrary(
                code="ASST_6DAY_REMOVED",
                topic_codes=["19"],
                category="גן",
                title_hebrew="גן חזר ל-5 ימים בשבוע",
                explanation_template="הגן חזר לפעילות 5 ימים בשבוע. תוספת יום ו' (17.85%) הוסרה.",
                direction="decrease",
                severity="routine",
                requires_detail=False,
                sort_order=24,
            ),
            ReasonLibrary(
                code="ASST_POSITION_REMOVED",
                topic_codes=["19"],
                category="משרות",
                title_hebrew="משרת עוזרת בוטלה",
                explanation_template="משרת עוזרת גננת בוטלה על ידי משרד החינוך. התשלום הופחת בהתאם.",
                direction="decrease",
                severity="attention",
                requires_detail=True,
                detail_prompt="מה הסיבה לביטול המשרה?",
                sort_order=25,
            ),

            # --- קוד 33 — גננות עובדות מדינה (4 reasons) ---
            ReasonLibrary(
                code="TEACHER_STATE_NEW",
                topic_codes=["33"],
                category="משרות",
                title_hebrew="גננת עובדת מדינה חדשה שובצה",
                explanation_template="גננת עובדת מדינה חדשה שובצה לגן ברשות. ניכוי שכרה מתווסף לתקצוב החודשי.",
                direction="decrease",
                severity="routine",
                requires_detail=False,
                sort_order=30,
            ),
            ReasonLibrary(
                code="TEACHER_STATE_RETIRED",
                topic_codes=["33"],
                category="משרות",
                title_hebrew="גננת עובדת מדינה יצאה לגמלאות",
                explanation_template="גננת עובדת מדינה יצאה לגמלאות. הניכוי בגינה הוסר מהתקצוב.",
                direction="increase",
                severity="routine",
                requires_detail=False,
                sort_order=31,
            ),
            ReasonLibrary(
                code="TEACHER_STATE_MATERNITY",
                topic_codes=["33"],
                category="משרות",
                title_hebrew="גננת עובדת מדינה בחופשת לידה",
                explanation_template="גננת עובדת מדינה יצאה לחופשת לידה. הניכוי הופחת זמנית.",
                direction="increase",
                severity="routine",
                requires_detail=False,
                sort_order=32,
            ),
            ReasonLibrary(
                code="TEACHER_STATE_RETURN",
                topic_codes=["33"],
                category="משרות",
                title_hebrew="גננת עובדת מדינה חזרה מחופשה",
                explanation_template="גננת עובדת מדינה חזרה לעבודה. הניכוי חודש.",
                direction="decrease",
                severity="routine",
                requires_detail=False,
                sort_order=33,
            ),
            ReasonLibrary(
                code="TEACHER_SENIORITY_CHANGE",
                topic_codes=["33"],
                category="שכר",
                title_hebrew="שינוי בדרגת ותק של גננת",
                explanation_template="חלה עלייה בדרגת הוותק של גננת עובדת מדינה. שכרה עלה ולכן הניכוי גדל בהתאם.",
                direction="decrease",
                severity="routine",
                requires_detail=False,
                sort_order=34,
            ),

            # --- כל הקודים — סיבות כלליות (13 reasons) ---
            ReasonLibrary(
                code="SALARY_TABLE_UPDATE",
                topic_codes=["all"],
                category="שכר",
                title_hebrew="עדכון טבלת שכר",
                explanation_template="משרד החינוך עדכן את טבלת השכר הבסיסית. עלות המשרה / עלות לילד השתנתה בהתאם לעדכון ההסכם הקיבוצי.",
                direction="neutral",
                severity="routine",
                requires_detail=False,
                sort_order=40,
            ),
            ReasonLibrary(
                code="KINDERGARTEN_OPENED",
                topic_codes=["3", "19"],
                category="גן",
                title_hebrew="גן ילדים חדש נפתח",
                explanation_template="נפתח גן ילדים חדש ברשות. התקצוב כולל כעת גם את ילדי הגן החדש ואת משרת העוזרת.",
                direction="increase",
                severity="routine",
                requires_detail=True,
                detail_prompt="מה שם/מיקום הגן החדש?",
                sort_order=41,
            ),
            ReasonLibrary(
                code="KINDERGARTEN_CLOSED",
                topic_codes=["3", "19"],
                category="גן",
                title_hebrew="גן ילדים נסגר",
                explanation_template="גן ילדים ברשות נסגר. ילדיו הועברו לגנים אחרים ברשות.",
                direction="decrease",
                severity="attention",
                requires_detail=True,
                detail_prompt="לאן הועברו הילדים?",
                sort_order=42,
            ),
            ReasonLibrary(
                code="RETRO_DELAYED_APPROVAL",
                topic_codes=["all"],
                category="רטרו",
                title_hebrew="תשלום רטרו — אישור מאוחר",
                explanation_template="תשלום עבור חודש בעבר שאישורו התעכב במשרד החינוך. זהו תשלום תקין ואינו מצביע על בעיה.",
                direction="neutral",
                severity="routine",
                requires_detail=False,
                sort_order=50,
            ),
            ReasonLibrary(
                code="RETRO_REGISTRATION_LATE",
                topic_codes=["all"],
                category="רטרו",
                title_hebrew="תשלום רטרו — רישום מאוחר",
                explanation_template="נתוני הרישום הגיעו למשרד החינוך באיחור. התשלום עבור החודשים שהיו ממתינים שולם כרטרו.",
                direction="neutral",
                severity="routine",
                requires_detail=False,
                sort_order=51,
            ),
            ReasonLibrary(
                code="RETRO_SYSTEM_CORRECTION",
                topic_codes=["all"],
                category="רטרו",
                title_hebrew="תשלום רטרו — תיקון מערכת",
                explanation_template="תיקון שגיאת מערכת במשרד החינוך הוביל לתשלום רטרואקטיבי.",
                direction="neutral",
                severity="attention",
                requires_detail=False,
                sort_order=52,
            ),
            ReasonLibrary(
                code="CORRECTION_OVERPAYMENT",
                topic_codes=["all"],
                category="תיקון",
                title_hebrew="תיקון — תשלום כפול בחודש קודם",
                explanation_template="בוצע תשלום כפול בטעות בחודש קודם. הסכום קוזז בחודש הנוכחי.",
                direction="decrease",
                severity="attention",
                requires_detail=True,
                detail_prompt="איזה חודש שולם בטעות?",
                sort_order=53,
            ),
            ReasonLibrary(
                code="CORRECTION_UNDERPAYMENT",
                topic_codes=["all"],
                category="תיקון",
                title_hebrew="תיקון — תשלום חסר בחודש קודם",
                explanation_template="תשלום חסר שזוהה בחודש קודם תוקן בחודש הנוכחי.",
                direction="increase",
                severity="routine",
                requires_detail=True,
                detail_prompt="איזה חודש היה חסר?",
                sort_order=54,
            ),
            ReasonLibrary(
                code="SYSTEM_ERROR_MINISTRY",
                topic_codes=["all"],
                category="תיקון",
                title_hebrew="שגיאת מחשוב במשרד החינוך",
                explanation_template="זוהתה שגיאת מחשוב במערכת המת״מ של משרד החינוך. הסכום תוקן בהתאם לאחר פנייה לאגף.",
                direction="neutral",
                severity="attention",
                requires_detail=False,
                sort_order=55,
            ),
            ReasonLibrary(
                code="AUDIT_CORRECTION",
                topic_codes=["all"],
                category="תיקון",
                title_hebrew="תיקון לאחר ביקורת חשבונאית",
                explanation_template="ביקורת חשבונאית זיהתה סטייה מהנדרש. הסכום תוקן בהתאם לממצאי הביקורת.",
                direction="neutral",
                severity="urgent",
                requires_detail=False,
                sort_order=56,
            ),
            ReasonLibrary(
                code="COURT_RULING",
                topic_codes=["all"],
                category="משפטי",
                title_hebrew="תשלום בהתאם לפסיקת בית משפט",
                explanation_template="התשלום בוצע בהתאם להחלטת בית משפט או פסיקה משפטית מחייבת.",
                direction="neutral",
                severity="urgent",
                requires_detail=False,
                sort_order=60,
            ),
            ReasonLibrary(
                code="POLICY_CHANGE",
                topic_codes=["all"],
                category="מדיניות",
                title_hebrew="שינוי מדיניות משרד החינוך",
                explanation_template="משרד החינוך שינה את כללי ההשתתפות בנושא זה. השינוי בסכום נובע מהמדיניות המעודכנת.",
                direction="neutral",
                severity="attention",
                requires_detail=False,
                sort_order=61,
            ),
            ReasonLibrary(
                code="PENDING_INVESTIGATION",
                topic_codes=["all"],
                category="אחר",
                title_hebrew="ממתין לבירור",
                explanation_template="הסכום נמצא בבדיקה מול משרד החינוך. הסבר מפורט יסופק לאחר השלמת הבירור.",
                direction="neutral",
                severity="urgent",
                requires_detail=True,
                detail_prompt="מה נמצא בבירור?",
                sort_order=70,
            ),
        ]
        
        db.add_all(reasons)
        db.commit()
        print(f"✅ Seeded {len(reasons)} reasons into reasons_library")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding reasons: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_reasons_library()
