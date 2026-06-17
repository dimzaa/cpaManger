-- Production Scrub: SQL Migration Script
-- This script adds is_test columns and provides cleanup queries
-- For SQLite database

-- ============================================================================
-- STEP 1: Add is_test columns (if they don't already exist)
-- ============================================================================

-- Add is_test to municipalities
ALTER TABLE municipalities ADD COLUMN is_test BOOLEAN DEFAULT 0;

-- Add is_test to users
ALTER TABLE users ADD COLUMN is_test BOOLEAN DEFAULT 0;

-- Create index for better query performance
CREATE INDEX IF NOT EXISTS idx_municipalities_is_test ON municipalities(is_test);
CREATE INDEX IF NOT EXISTS idx_users_is_test ON users(is_test);

-- ============================================================================
-- STEP 2: Clean up fake test data (REVIEW BEFORE RUNNING)
-- ============================================================================

-- Count fake municipalities before deletion
-- SELECT COUNT(*) FROM municipalities WHERE name LIKE '%עיריית בדיקה מעודכנת%';

-- DELETE fake municipalities
DELETE FROM municipalities WHERE name LIKE '%עיריית בדיקה מעודכנת%';

-- Count test employees before deletion
-- SELECT COUNT(*) FROM users WHERE email LIKE '%autotest_%' OR email LIKE '%tempemp%' OR email LIKE '%@test.com';

-- DELETE test employees
DELETE FROM users WHERE 
  email LIKE '%autotest_%' 
  OR email LIKE '%tempemp%' 
  OR email LIKE '%test@test.com%'
  OR email LIKE '%demo@example.com%';

-- Count placeholder reminders before deletion
-- SELECT COUNT(*) FROM deadline_reminders WHERE title LIKE '%מועד הגשה מעודכן%' AND deadline_date IS NULL;

-- DELETE placeholder reminders with blank dates
DELETE FROM deadline_reminders 
WHERE title LIKE '%מועד הגשה מעודכן%' 
  AND (deadline_date IS NULL OR deadline_date = '');

-- ============================================================================
-- STEP 3: Update production records with is_test=0 (if needed)
-- ============================================================================

-- Mark real municipalities as non-test
UPDATE municipalities SET is_test = 0 WHERE is_test IS NULL;

-- Mark real users as non-test
UPDATE users SET is_test = 0 WHERE is_test IS NULL;

-- ============================================================================
-- STEP 4: Verify cleanup
-- ============================================================================

-- Check municipality cleanup
-- SELECT COUNT(*) as total, SUM(CASE WHEN is_test=1 THEN 1 ELSE 0 END) as test_count FROM municipalities;

-- Check user cleanup
-- SELECT COUNT(*) as total, SUM(CASE WHEN is_test=1 THEN 1 ELSE 0 END) as test_count FROM users;

-- Check remaining test data
-- SELECT id, name FROM municipalities WHERE is_test = 1;
-- SELECT id, email FROM users WHERE is_test = 1;

-- ============================================================================
-- NOTES FOR FUTURE DATA SEEDING
-- ============================================================================

-- When creating test data, always set is_test = 1:
-- INSERT INTO municipalities (name, code, is_test) VALUES ('Test City', '9999', 1);
-- INSERT INTO users (email, hashed_password, role, is_test) VALUES ('testuser@test.com', '...', 'employee', 1);

-- This way, the cleanup can be automated and test data won't pollute production reports.
