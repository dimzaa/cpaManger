#!/usr/bin/env python3
"""
Migration: add/backfill Ministry budget codes from the Purple Book.

What this script does:
1. Ensures the ministry_codes table has the `purple_book_column` field.
2. Inserts critical missing high-value codes (1, 81, 171, 345).
3. Backfills required metadata fields on existing critical codes when missing:
   - participation_percent
   - category
   - purple_book_column

Run:
    python migrate_add_purple_book_codes.py
"""

import json
from datetime import datetime

from backend.database import SessionLocal, init_db
from backend.models.ministry_code import MinistryCode
from backend.utils.migrate_users_table import migrate_ministry_codes_table


PURPLE_BOOK_CRITICAL_CODES = [
    {
        "code": "1",
        "name_short": "שכ\"ל על-יסודי",
        "name_full": "שכר לימוד על-יסודי",
        "category": "חטיבה עליונה",
        "description": "השתתפות משרד החינוך בשכר לימוד לחינוך העל-יסודי.",
        "participation_percent": 100.0,
        "payment_type": "monthly",
        "applies_to": "all",
        "booklet_page": 15,
        "purple_book_column": "ד",
        "booklet_section": "חינוך על-יסודי",
        "formula": "מספר תלמידים זכאים x עלות תקן x אחוז השתתפות",
        "keywords": "שכר לימוד, על יסודי, תיכון",
        "is_deduction": False,
        "sub_topics": ["שכר לימוד", "עלויות תקן"],
        "change_triggers": ["שינוי מספר תלמידים", "עדכון תעריף תקן"],
        "related_codes": ["3", "33"],
    },
    {
        "code": "81",
        "name_short": "פס' מתמחים",
        "name_full": "פסיכולוגים מתמחים",
        "category": "שירותים פסיכולוגיים",
        "description": "השתתפות עבור תקני פסיכולוגים מתמחים ברשות.",
        "participation_percent": 75.0,
        "payment_type": "monthly",
        "applies_to": "all",
        "booklet_page": 38,
        "purple_book_column": "ב",
        "booklet_section": "שירותים פסיכולוגיים",
        "formula": "מספר מתמחים מאושר x עלות משרה x אחוז השתתפות",
        "keywords": "פסיכולוג, מתמחה, שפ\"ח",
        "is_deduction": False,
        "sub_topics": ["מתמחים", "שירות פסיכולוגי"],
        "change_triggers": ["שינוי מספר תקנים", "עדכון עלות משרה"],
        "related_codes": ["47"],
    },
    {
        "code": "171",
        "name_short": "סייעות כיתתיות",
        "name_full": "סייעות כיתתיות בחינוך מיוחד",
        "category": "חינוך מיוחד",
        "description": "מימון סייעות כיתתיות במסגרות חינוך מיוחד.",
        "participation_percent": 100.0,
        "payment_type": "monthly",
        "applies_to": "all",
        "booklet_page": 42,
        "purple_book_column": "ג",
        "booklet_section": "חינוך מיוחד",
        "formula": "מספר כיתות זכאיות x תקן סייעת x עלות משרה",
        "keywords": "סייעת, חינוך מיוחד, כיתה",
        "is_deduction": False,
        "sub_topics": ["סייעות כיתתיות", "תקני סיוע"],
        "change_triggers": ["פתיחת כיתה", "סגירת כיתה", "עדכון תעריף"],
        "related_codes": ["345"],
    },
    {
        "code": "345",
        "name_short": "חוק שילוב",
        "name_full": "תקצוב חוק שילוב",
        "category": "חינוך מיוחד",
        "description": "תקצוב שילוב תלמידים בעלי צרכים מיוחדים בחינוך הרגיל.",
        "participation_percent": 100.0,
        "payment_type": "monthly",
        "applies_to": "all",
        "booklet_page": 43,
        "purple_book_column": "ג",
        "booklet_section": "חינוך מיוחד",
        "formula": "מספר תלמידים משולבים x סל שילוב מאושר",
        "keywords": "שילוב, חינוך מיוחד, תלמידים",
        "is_deduction": False,
        "sub_topics": ["שילוב פרטני", "שילוב כיתתי"],
        "change_triggers": ["שינוי זכאות תלמידים", "עדכון סל שילוב"],
        "related_codes": ["171"],
    },
]


BACKFILL_METADATA = {
    "3": {"category": "גני ילדים", "participation_percent": 90.0, "purple_book_column": "ד"},
    "5": {"category": "נושאים רשותיים", "participation_percent": 75.0, "purple_book_column": "ב"},
    "19": {"category": "גני ילדים", "participation_percent": 100.0, "purple_book_column": "ד"},
    "33": {"category": "גני ילדים", "participation_percent": 100.0, "purple_book_column": "ד"},
    "45": {"category": "נושאים רשותיים", "participation_percent": 75.0, "purple_book_column": "ב"},
    "47": {"category": "שירותים פסיכולוגיים", "participation_percent": 68.0, "purple_book_column": "ב"},
    "50": {"category": "הסעות", "participation_percent": 80.0, "purple_book_column": "ג"},
}


def _json(value):
    return json.dumps(value or [], ensure_ascii=False)


def _apply_entry(target: MinistryCode, entry: dict, fill_only_missing: bool = False) -> None:
    """Copy entry data into model fields."""
    for field in [
        "name_short",
        "name_full",
        "category",
        "description",
        "formula",
        "participation_percent",
        "payment_type",
        "applies_to",
        "booklet_page",
        "purple_book_column",
        "booklet_section",
        "keywords",
        "is_deduction",
    ]:
        if field in entry:
            if fill_only_missing and getattr(target, field, None) not in (None, ""):
                continue
            setattr(target, field, entry[field])

    if "sub_topics" in entry and (not fill_only_missing or not target.sub_topics):
        target.sub_topics = _json(entry["sub_topics"])
    if "change_triggers" in entry and (not fill_only_missing or not target.change_triggers):
        target.change_triggers = _json(entry["change_triggers"])
    if "related_codes" in entry and (not fill_only_missing or not target.related_codes):
        target.related_codes = _json(entry["related_codes"])


def main():
    print("Starting migration: Purple Book ministry codes")

    init_db()
    migrate_ministry_codes_table()

    db = SessionLocal()
    try:
        inserted = 0
        updated = 0

        for entry in PURPLE_BOOK_CRITICAL_CODES:
            code = entry["code"]
            existing = db.query(MinistryCode).filter(MinistryCode.code == code).first()

            if existing:
                _apply_entry(existing, entry, fill_only_missing=True)
                existing.last_updated = datetime.utcnow()
                existing.is_active = True
                updated += 1
                print(f"Updated metadata for code {code}")
                continue

            obj = MinistryCode(
                code=code,
                name_short=entry["name_short"],
                name_full=entry["name_full"],
                category=entry["category"],
                description=entry.get("description"),
                formula=entry.get("formula"),
                participation_percent=entry.get("participation_percent"),
                payment_type=entry.get("payment_type", "monthly"),
                applies_to=entry.get("applies_to", "all"),
                booklet_page=entry.get("booklet_page"),
                purple_book_column=entry.get("purple_book_column"),
                booklet_section=entry.get("booklet_section"),
                is_deduction=entry.get("is_deduction", False),
                sub_topics=_json(entry.get("sub_topics")),
                change_triggers=_json(entry.get("change_triggers")),
                related_codes=_json(entry.get("related_codes")),
                keywords=entry.get("keywords"),
                is_active=True,
                last_updated=datetime.utcnow(),
            )
            db.add(obj)
            inserted += 1
            print(f"Inserted missing code {code}: {entry['name_short']}")

        # Backfill required metadata fields on existing high-impact baseline codes.
        for code, fields in BACKFILL_METADATA.items():
            existing = db.query(MinistryCode).filter(MinistryCode.code == code).first()
            if not existing:
                continue
            changed = False
            for field, value in fields.items():
                if getattr(existing, field, None) in (None, ""):
                    setattr(existing, field, value)
                    changed = True
            if changed:
                existing.last_updated = datetime.utcnow()
                updated += 1
                print(f"Backfilled required metadata for existing code {code}")

        db.commit()

        total = db.query(MinistryCode).count()
        print("Migration complete")
        print(f"Inserted: {inserted}")
        print(f"Updated/backfilled: {updated}")
        print(f"Total ministry codes: {total}")

    except Exception as exc:
        db.rollback()
        print(f"Migration failed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
