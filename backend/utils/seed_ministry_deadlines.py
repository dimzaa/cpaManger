"""
Seed real Ministry of Education deadlines on first startup.
"""
import json
from backend.models.ministry_deadline import MinistryDeadline


MINISTRY_DEADLINES = [
    {
        "title": "הגשת בקשת תקן עוזרות גננות",
        "description": "יש להגיש בקשה לאגף בכיר אמח'י לאישור תקן עוזרות גננות לשנה הבאה",
        "deadline_type": "annual",
        "deadline_month": "7",
        "deadline_day": 31,
        "reminder_days_before": [60, 30, 14, 7, 1],
        "topic_codes": ["19"],
        "applies_to": "all",
        "ministry_reference": "חוברת התקצוב עמ' 48",
        "action_required": "הגש טופס בקשה לאגף בכיר אמח'י עם רשימת ילדים מעודכנת ואישור בטיחות גן",
    },
    {
        "title": "הגשת בקשת ילדי השלמה",
        "description": "גנים עם פחות מ-28 ילדים זכאים לתקצוב ילדי השלמה",
        "deadline_type": "annual",
        "deadline_month": "12",
        "deadline_day": 31,
        "reminder_days_before": [60, 30, 14, 7, 3, 1],
        "topic_codes": ["3"],
        "applies_to": "all",
        "ministry_reference": "חוברת התקצוב עמ' 47",
        "action_required": "הגש בקשה דרך מערכת גני ילדים-ילדי השלמה בפורטל רשויות ובעלויות",
    },
    {
        "title": "בקשת תקן לגן ילדים נוסף",
        "description": "רשויות המעוניינות לפתוח גן נוסף לשנת הלימודים הבאה",
        "deadline_type": "annual",
        "deadline_month": "4",
        "deadline_day": 30,
        "reminder_days_before": [30, 14, 7, 1],
        "topic_codes": ["3", "19"],
        "applies_to": "all",
        "ministry_reference": "חוברת התקצוב עמ' 46",
        "action_required": "הגש בקשה למחוז לפתיחת גן נוסף עם נתוני רישום מעודכנים",
    },
    {
        "title": "עדכון נתוני רישום גני ילדים",
        "description": "יש לעדכן נתוני הרישום לשנת הלימודים הבאה במערכת",
        "deadline_type": "annual",
        "deadline_month": "3",
        "deadline_day": 30,
        "reminder_days_before": [30, 14, 7],
        "topic_codes": ["3"],
        "applies_to": "all",
        "ministry_reference": "חוברת התקצוב עמ' 45",
        "action_required": "עדכן נתוני רישום ילדים במערכת הממוחשבת של משרד החינוך",
    },
    {
        "title": "בקשת תקן קצין ביקור סדיר",
        "description": "בקשה לאישור תקן קב'ס לשנה הבאה",
        "deadline_type": "annual",
        "deadline_month": "7",
        "deadline_day": 31,
        "reminder_days_before": [60, 30, 14, 7],
        "topic_codes": ["45"],
        "applies_to": "all",
        "ministry_reference": "חוברת התקצוב עמ' 10",
        "action_required": "הגש בקשה למחוז עם נתוני תלמידים ומספר נושרים",
    },
    {
        "title": "דיווח על גן הפועל 6 ימים בשבוע",
        "description": "גנים שעברו ל-6 ימי פעילות זכאים לתוספת 17.85%",
        "deadline_type": "annual",
        "deadline_month": "9",
        "deadline_day": 30,
        "reminder_days_before": [30, 14, 7],
        "topic_codes": ["19"],
        "applies_to": "all",
        "ministry_reference": "חוברת התקצוב עמ' 48",
        "action_required": "דווח למשרד החינוך על גנים הפועלים 6 ימים בשבוע",
    },
    {
        "title": "הגשת דוח רבעוני למשרד החינוך",
        "description": "הגשת דוח ביצוע רבעוני לגזברות המחוז",
        "deadline_type": "quarterly",
        "deadline_month": json.dumps([3, 6, 9, 12]),
        "deadline_day": 15,
        "reminder_days_before": [14, 7, 3, 1],
        "topic_codes": ["all"],
        "applies_to": "all",
        "ministry_reference": "הנחיות משרד החינוך",
        "action_required": "הגש דוח ביצוע רבעוני לגזברות המחוז",
    },
]


def seed_ministry_deadlines(db) -> int:
    """
    Insert default ministry deadlines if they don't exist yet.
    Returns number of new records inserted.
    """
    existing = db.query(MinistryDeadline).count()
    if existing > 0:
        return 0

    count = 0
    for d in MINISTRY_DEADLINES:
        deadline = MinistryDeadline(
            title=d["title"],
            description=d.get("description"),
            deadline_type=d["deadline_type"],
            deadline_month=d.get("deadline_month"),
            deadline_day=d["deadline_day"],
            reminder_days_before=json.dumps(d["reminder_days_before"]),
            topic_codes=json.dumps(d["topic_codes"]),
            applies_to=d.get("applies_to", "all"),
            ministry_reference=d.get("ministry_reference"),
            action_required=d.get("action_required"),
            is_active=True,
        )
        db.add(deadline)
        count += 1

    db.commit()
    print(f"✅ Seeded {count} ministry deadlines")
    return count
