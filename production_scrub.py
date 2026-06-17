#!/usr/bin/env python3
"""
Production Scrub: Clean up test data from the database

This script:
1. Removes fake test municipalities (pattern: "עיריית בדיקה מעודכנת XXXX")
2. Deletes test employee accounts (pattern: autotest_*, tempemp_*)
3. Removes placeholder reminders with blank dates
4. Adds is_test flags for future prevention
5. Generates a summary report

Run: python production_scrub.py
"""

import sys
from datetime import datetime
from sqlalchemy import text
from backend.database import SessionLocal, init_db
from backend.models import Municipality, User, DeadlineReminder

def cleanup_fake_municipalities(db):
    """Remove or archive fake test municipalities."""
    print("\n🗑️  CLEANING MUNICIPALITIES...")
    
    # Find fake municipalities with pattern "עיריית בדיקה מעודכנת"
    fake_pattern = "%עיריית בדיקה מעודכנת%"
    fake_munis = db.query(Municipality).filter(
        Municipality.name.ilike(fake_pattern)
    ).all()
    
    deleted = 0
    for muni in fake_munis:
        name = muni.name.decode() if isinstance(muni.name, bytes) else muni.name
        print(f"  ❌ Deleting: {name}")
        db.delete(muni)
        deleted += 1
    
    db.commit()
    print(f"  ✅ Removed {deleted} fake municipalities\n")
    return deleted


def cleanup_test_employees(db):
    """Remove test employee accounts."""
    print("🗑️  CLEANING TEST EMPLOYEE ACCOUNTS...")
    
    # Find test accounts by email pattern
    test_patterns = [
        "%autotest_%",
        "%tempemp%",
        "%test@test.com%",
        "%demo@example.com%",
    ]
    
    deleted = 0
    for pattern in test_patterns:
        test_users = db.query(User).filter(User.email.ilike(pattern)).all()
        for user in test_users:
            print(f"  ❌ Deleting: {user.email}")
            db.delete(user)
            deleted += 1
    
    db.commit()
    print(f"  ✅ Removed {deleted} test employee accounts\n")
    return deleted


def cleanup_placeholder_reminders(db):
    """Remove placeholder reminders with blank dates."""
    print("🗑️  CLEANING PLACEHOLDER REMINDERS...")
    
    # Find reminders named "מועד הגשה מעודכן" with NULL dates
    # This query finds reminders with the pattern and no actual deadline
    placeholder_pattern = "%מועד הגשה מעודכן%"
    
    # Query for reminders with placeholder name and null/empty dates
    placeholder_reminders = db.query(DeadlineReminder).filter(
        DeadlineReminder.title.ilike(placeholder_pattern),
    ).all()
    
    deleted = 0
    for reminder in placeholder_reminders:
        # Check if dates are null or default
        if not reminder.deadline_date:
            title = reminder.title.decode() if isinstance(reminder.title, bytes) else reminder.title
            print(f"  ❌ Deleting: {title}")
            db.delete(reminder)
            deleted += 1
    
    db.commit()
    print(f"  ✅ Removed {deleted} placeholder reminders\n")
    return deleted


def add_test_flags(db):
    """Add is_test column to municipality and user tables if not already present."""
    print("🔧 ADDING TEST DATA FLAGS...")
    
    try:
        # Check if column already exists (try adding it)
        with db.engine.connect() as conn:
            # Try to add is_test to municipalities
            try:
                conn.execute(text(
                    "ALTER TABLE municipalities ADD COLUMN is_test BOOLEAN DEFAULT FALSE"
                ))
                print("  ✅ Added is_test column to municipalities table")
                conn.commit()
            except Exception as e:
                if "already exists" in str(e) or "duplicate" in str(e).lower():
                    print("  ℹ️  is_test column already exists in municipalities")
                else:
                    print(f"  ⚠️  Error adding to municipalities: {e}")
            
            # Try to add is_test to users
            try:
                conn.execute(text(
                    "ALTER TABLE users ADD COLUMN is_test BOOLEAN DEFAULT FALSE"
                ))
                print("  ✅ Added is_test column to users table")
                conn.commit()
            except Exception as e:
                if "already exists" in str(e) or "duplicate" in str(e).lower():
                    print("  ℹ️  is_test column already exists in users")
                else:
                    print(f"  ⚠️  Error adding to users: {e}")
    
    except Exception as e:
        print(f"  ⚠️  Could not add test flags: {e}")
    
    print()


def main():
    """Execute the production scrub."""
    print("\n" + "="*70)
    print("🧹 PRODUCTION SCRUB — Cleaning Test Data from Database")
    print("="*70)
    
    # Initialize database
    init_db()
    db = SessionLocal()
    
    try:
        # Pre-cleanup counts
        total_munis_before = db.query(Municipality).count()
        total_users_before = db.query(User).count()
        
        print(f"\n📊 PRE-CLEANUP COUNTS:")
        print(f"   Municipalities: {total_munis_before}")
        print(f"   Users: {total_users_before}")
        
        # Run cleanup operations
        deleted_munis = cleanup_fake_municipalities(db)
        deleted_users = cleanup_test_employees(db)
        deleted_reminders = cleanup_placeholder_reminders(db)
        
        # Add test flags for future prevention
        add_test_flags(db)
        
        # Post-cleanup counts
        total_munis_after = db.query(Municipality).count()
        total_users_after = db.query(User).count()
        
        print(f"\n📊 POST-CLEANUP COUNTS:")
        print(f"   Municipalities: {total_munis_after} (removed {deleted_munis})")
        print(f"   Users: {total_users_after} (removed {deleted_users})")
        print(f"   Reminders: removed {deleted_reminders}")
        
        print(f"\n✨ PRODUCTION SCRUB COMPLETE!")
        print(f"   Total changes: {deleted_munis + deleted_users + deleted_reminders} records")
        print(f"\n   ✅ Database is now clean and ready for CPA demo\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
