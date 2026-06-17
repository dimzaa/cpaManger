"""
Seed default preset explanations into the database.

Run this once to initialize the system with Ministry-approved explanation templates.
"""

from sqlalchemy.orm import Session
from backend.models.preset_explanation import PresetExplanation
from backend.models.user import User


DEFAULT_PRESETS = [
    # === CODE 3: גני ילדים ===
    {
        "topic_code": "3",
        "category": "correction",
        "preset_text": "שינוי במספר הילדים הרשומים בהתאם לעדכון ממשרד החינוך"
    },
    {
        "topic_code": "3",
        "category": "retro",
        "preset_text": "תיקון רטרואקטיבי לאחר בדיקת נתוני רישום"
    },
    {
        "topic_code": "3",
        "category": "correction",
        "preset_text": "עדכון עלות לילד בעקבות שינוי טבלת שכר"
    },
    {
        "topic_code": "3",
        "category": "increase",
        "preset_text": "הוספת ילדי השלמה שאושרו על ידי האגף"
    },
    {
        "topic_code": "3",
        "category": "new_position",
        "preset_text": "תשלום עבור גן חדש שנפתח ברשות"
    },
    
    # === CODE 19: עוזרות ===
    {
        "topic_code": "19",
        "category": "new_position",
        "preset_text": "הוספת משרת עוזרת לגן חדש שנפתח"
    },
    {
        "topic_code": "19",
        "category": "increase",
        "preset_text": "תשלום עבור עוזרת שחזרה מחופשת לידה"
    },
    {
        "topic_code": "19",
        "category": "correction",
        "preset_text": "תיקון תשלום עקב שגיאה בחישוב חודש קודם"
    },
    {
        "topic_code": "19",
        "category": "correction",
        "preset_text": "עדכון עלות משרה לפי הסכם קיבוצי מעודכן"
    },
    {
        "topic_code": "19",
        "category": "increase",
        "preset_text": "הוספת תוספת יום ו' לגן שעבר ל-6 ימים"
    },
    
    # === CODE 33: גננות עובדות מדינה ===
    {
        "topic_code": "33",
        "category": "correction",
        "preset_text": "תיקון ניכוי בעקבות שינוי מספר גננות עובדות מדינה"
    },
    {
        "topic_code": "33",
        "category": "new_position",
        "preset_text": "גננת עובדת מדינה חדשה שובצה לרשות"
    },
    {
        "topic_code": "33",
        "category": "decrease",
        "preset_text": "גננת עובדת מדינה יצאה לגמלאות — ניכוי הופחת"
    },
    
    # === GENERAL (applies to all codes) ===
    {
        "topic_code": "general",
        "category": "retro",
        "preset_text": "תשלום רטרואקטיבי שאושר באיחור על ידי משרד החינוך"
    },
    {
        "topic_code": "general",
        "category": "correction",
        "preset_text": "תיקון שגיאת מחשוב במערכת משרד החינוך"
    },
    {
        "topic_code": "general",
        "category": "correction",
        "preset_text": "שינוי בעקבות ביקורת חשבונאית"
    },
    {
        "topic_code": "general",
        "category": "correction",
        "preset_text": "תשלום בהתאם להחלטת בית משפט / פסיקה"
    },
    {
        "topic_code": "general",
        "category": "other",
        "preset_text": "ממתין לבירור מול משרד החינוך"
    },
]


def seed_default_presets(db: Session):
    """
    Create default preset explanations if they don't exist.
    
    This should be called during app initialization.
    """
    # Get or create system admin user for audit trail
    system_admin = db.query(User).filter(User.email == "system@admin").first()
    
    if not system_admin:
        system_admin = User(
            email="system@admin",
            hashed_password="",  # System user, no login
            role="admin",
            first_name="System",
            last_name="Admin",
            is_active=True
        )
        db.add(system_admin)
        db.commit()
        db.refresh(system_admin)
    
    # Count existing presets
    existing_count = db.query(PresetExplanation).count()
    
    if existing_count == 0:
        # Seed all default presets
        for preset_data in DEFAULT_PRESETS:
            preset = PresetExplanation(
                topic_code=preset_data["topic_code"],
                preset_text=preset_data["preset_text"],
                category=preset_data["category"],
                created_by=system_admin.id,
                is_active=True
            )
            db.add(preset)
        
        db.commit()
        return len(DEFAULT_PRESETS)
    
    return 0
