"""
Database migration: Add missing columns to users table.

Safely adds columns to users table if they don't exist.
This migration is idempotent and can be run multiple times.
"""

from sqlalchemy import text, inspect
from backend.database import engine, SessionLocal


def migrate_users_table():
    """
    Add missing columns to users table:
    - created_by (nullable integer, foreign key to users.id)
    - first_name (nullable string)
    - last_name (nullable string)
    - is_active (boolean, default true)
    - last_login (nullable datetime)
    """
    
    try:
        # Get inspector to check existing columns
        inspector = inspect(engine)
        existing_columns = {col['name'] for col in inspector.get_columns('users')}
        
        migrations = [
            ("first_name", "ALTER TABLE users ADD COLUMN first_name VARCHAR(255) DEFAULT NULL"),
            ("last_name", "ALTER TABLE users ADD COLUMN last_name VARCHAR(255) DEFAULT NULL"),
            ("is_active", "ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE"),
            ("created_by", "ALTER TABLE users ADD COLUMN created_by INTEGER DEFAULT NULL"),
            ("last_login", "ALTER TABLE users ADD COLUMN last_login DATETIME DEFAULT NULL"),
            ("is_test", "ALTER TABLE users ADD COLUMN is_test BOOLEAN DEFAULT 0"),
        ]
        
        with SessionLocal() as session:
            for column_name, sql_command in migrations:
                if column_name not in existing_columns:
                    try:
                        session.execute(text(sql_command))
                        session.commit()
                        print(f"✅ Added column: {column_name}")
                    except Exception as e:
                        session.rollback()
                        print(f"⚠️  Column {column_name} migration failed: {str(e)}")
                else:
                    print(f"✅ Column {column_name} already exists")
        
        print("✅ Database migration completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Migration error: {str(e)}")
        return False


def migrate_budget_lines_table():
    """
    Add missing columns to budget_lines table:
    - num_children (nullable integer) — actual children count from ministry file
    - participation_pct (nullable float) — participation percentage from ministry file
    """
    try:
        inspector = inspect(engine)
        existing_columns = {col['name'] for col in inspector.get_columns('budget_lines')}

        migrations = [
            ("num_children", "ALTER TABLE budget_lines ADD COLUMN num_children INTEGER DEFAULT NULL"),
            ("participation_pct", "ALTER TABLE budget_lines ADD COLUMN participation_pct REAL DEFAULT NULL"),
            ("variance_driver", "ALTER TABLE budget_lines ADD COLUMN variance_driver VARCHAR(20) DEFAULT NULL"),
        ]

        with SessionLocal() as session:
            for column_name, sql_command in migrations:
                if column_name not in existing_columns:
                    try:
                        session.execute(text(sql_command))
                        session.commit()
                        print(f"✅ Added column: {column_name} to budget_lines")
                    except Exception as e:
                        session.rollback()
                        print(f"⚠️  Column {column_name} migration failed: {str(e)}")
                else:
                    print(f"✅ Column {column_name} already exists in budget_lines")

        print("✅ Budget lines migration completed successfully")
        return True

    except Exception as e:
        print(f"❌ Budget lines migration error: {str(e)}")
        return False


def migrate_ministry_codes_table():
    """
    Add missing columns to ministry_codes table:
    - purple_book_column (nullable string) — column marker in the Purple Book
    """
    try:
        inspector = inspect(engine)
        existing_columns = {col['name'] for col in inspector.get_columns('ministry_codes')}

        migrations = [
            ("purple_book_column", "ALTER TABLE ministry_codes ADD COLUMN purple_book_column VARCHAR(50) DEFAULT NULL"),
        ]

        with SessionLocal() as session:
            for column_name, sql_command in migrations:
                if column_name not in existing_columns:
                    try:
                        session.execute(text(sql_command))
                        session.commit()
                        print(f"✅ Added column: {column_name} to ministry_codes")
                    except Exception as e:
                        session.rollback()
                        print(f"⚠️  Column {column_name} migration failed: {str(e)}")
                else:
                    print(f"✅ Column {column_name} already exists in ministry_codes")

        print("✅ Ministry codes migration completed successfully")
        return True

    except Exception as e:
        print(f"❌ Ministry codes migration error: {str(e)}")
        return False


def migrate_municipalities_table():
    """
    Add missing columns to municipalities table:
    - is_test (boolean, default false) — flag for test/demo municipalities
    """
    try:
        inspector = inspect(engine)
        existing_columns = {col['name'] for col in inspector.get_columns('municipalities')}

        migrations = [
            ("is_test", "ALTER TABLE municipalities ADD COLUMN is_test BOOLEAN DEFAULT 0"),
        ]

        with SessionLocal() as session:
            for column_name, sql_command in migrations:
                if column_name not in existing_columns:
                    try:
                        session.execute(text(sql_command))
                        session.commit()
                        print(f"✅ Added column: {column_name} to municipalities")
                    except Exception as e:
                        session.rollback()
                        print(f"⚠️  Column {column_name} migration failed: {str(e)}")
                else:
                    print(f"✅ Column {column_name} already exists in municipalities")

        print("✅ Municipalities migration completed successfully")
        return True

    except Exception as e:
        print(f"❌ Municipalities migration error: {str(e)}")
        return False


def migrate_monthly_runs_table():
    """
    Add missing columns to monthly_runs table for CPA review sign-off:
    - review_status (string, default 'pending')
    - review_status_note (string, nullable)
    - reviewed_by_user_id (integer, nullable, FK to users.id)
    - reviewed_at (datetime, nullable)
    """
    try:
        inspector = inspect(engine)
        existing_columns = {col['name'] for col in inspector.get_columns('monthly_runs')}

        migrations = [
            ("review_status",
             "ALTER TABLE monthly_runs ADD COLUMN review_status VARCHAR(20) NOT NULL DEFAULT 'pending'"),
            ("review_status_note",
             "ALTER TABLE monthly_runs ADD COLUMN review_status_note VARCHAR(1000)"),
            ("reviewed_by_user_id",
             "ALTER TABLE monthly_runs ADD COLUMN reviewed_by_user_id INTEGER"),
            ("reviewed_at",
             "ALTER TABLE monthly_runs ADD COLUMN reviewed_at DATETIME"),
        ]

        with SessionLocal() as session:
            for column_name, sql_command in migrations:
                if column_name not in existing_columns:
                    try:
                        session.execute(text(sql_command))
                        session.commit()
                        print(f"✅ Added column: {column_name} to monthly_runs")
                    except Exception as e:
                        session.rollback()
                        print(f"⚠️  Column {column_name} migration failed: {str(e)}")
                else:
                    print(f"✅ Column {column_name} already exists in monthly_runs")

        print("✅ Monthly runs migration completed successfully")
        return True

    except Exception as e:
        print(f"❌ Monthly runs migration error: {str(e)}")
        return False
