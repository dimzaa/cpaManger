# 🧹 Production Scrub Guide

## Overview
This guide documents the process for cleaning up test/demo data from the CPA budget application to prepare it for production and client demos.

---

## Quick Start: One-Command Cleanup

```bash
python production_scrub.py
```

This single command will:
1. ❌ Remove fake municipalities (pattern: "עיריית בדיקה מעודכנת XXXX")
2. ❌ Delete test employee accounts (autotest_*, tempemp_*, @test.com)
3. ❌ Remove placeholder reminders with blank dates
4. ✅ Add `is_test` columns to municipalities and users tables
5. 📊 Generate a cleanup summary report

---

## What Gets Cleaned

### Municipalities
**Removed:** Any municipality with name containing "עיריית בדיקה מעודכנת"  
**Kept:** Real municipalities (Kafr Qara, Nazareth, etc.)

**Example:**
- ❌ `עיריית בדיקה מעודכנת 0001`
- ❌ `עיריית בדיקה מעודכנת 0002`
- ✅ `עיריית כפר קרע` (Kafr Qara - KEPT)

### Employee Accounts
**Removed:** Users matching any of these patterns:
- `autotest_*@*.com`
- `tempemp_*@*.com`
- `*@test.com`
- `*@example.com` (demo accounts)

**Example:**
- ❌ `autotest_001@test.com`
- ❌ `tempemp_user@test.com`
- ❌ `employee@example.com`
- ✅ `cpa_admin@organization.gov.il` (KEPT)

### Deadline Reminders
**Removed:** Reminders titled "מועד הגשה מעודכן" with NULL or blank dates

**Example:**
- ❌ Title: "מועד הגשה מעודכן" | Date: (blank)
- ✅ Title: "Gan Yeladim Quota Request" | Date: "2026-05-15" (KEPT)

---

## Implementation Details

### Backend: is_test Column

Two new boolean columns added for future prevention:

```python
# Municipality Model
is_test = Column(Boolean, default=False, index=True)

# User Model
is_test = Column(Boolean, default=False, index=True)
```

### Backend API: Filtering Logic

All API endpoints now support filtering:

```python
# GET /api/municipalities?include_test=false (default)
# Returns only production municipalities (is_test=0)

# GET /api/municipalities?include_test=true (admin only)
# Returns all municipalities including test data
```

Similarly for employees:
```python
# GET /api/employees?include_test=false (default)
# Returns only production employees
```

### Frontend: Dev Mode Toggle

Admins can enable "Dev Mode" to see test data:

```jsx
import DevModeToggle from '../components/DevModeToggle';

// In navbar or admin panel:
<DevModeToggle isAdmin={currentUser.role === 'admin'} />
```

**Dev Mode Behavior:**
- Stored in `localStorage` → persists across sessions
- When ON: Shows all data including test entries
- When OFF (default): Filters out test data
- Only visible to admin users

### Frontend Utilities: devMode.js

```javascript
import { filterTestData, isDevModeEnabled } from '../utils/devMode';

// Filter a list of municipalities
const productionOnly = filterTestData(municipalities);

// Check if dev mode is on
if (isDevModeEnabled()) {
  console.log('Dev mode enabled - showing all data');
}

// Listen for dev mode changes
onDevModeChange((enabled) => {
  console.log('Dev mode is now:', enabled);
  // Re-fetch data or refresh display
});
```

---

## Recommended Seeding Practices

### When Creating Test Data

Always set `is_test = True`:

```python
# Backend - Seed test municipality
test_muni = Municipality(
    name="Test Municipality",
    code="9999",
    is_test=True  # ← KEY!
)
db.add(test_muni)
db.commit()

# Backend - Seed test employee
test_employee = User(
    email="autotest_demo@test.com",
    role=UserRole.EMPLOYEE,
    is_test=True  # ← KEY!
)
db.add(test_employee)
db.commit()
```

### Seeding Script Template

```python
#!/usr/bin/env python3
from backend.database import SessionLocal, init_db
from backend.models import Municipality, User

db = SessionLocal()
init_db()

# Create test municipality
test_muni = Municipality(
    name="Test City",
    code="9999",
    is_test=True  # Flag as test data
)
db.add(test_muni)

# Create test employee
test_emp = User(
    email="testuser@test.com",
    role="employee",
    is_test=True  # Flag as test data
)
db.add(test_emp)

db.commit()
db.close()

print("✅ Test data created with is_test=True flags")
```

---

## Database Migration

### SQL-Only Approach

```sql
-- Add columns
ALTER TABLE municipalities ADD COLUMN is_test BOOLEAN DEFAULT 0;
ALTER TABLE users ADD COLUMN is_test BOOLEAN DEFAULT 0;

-- Clean up old test data
DELETE FROM municipalities WHERE name LIKE '%עיריית בדיקה מעודכנת%';
DELETE FROM users WHERE email LIKE '%autotest_%' OR email LIKE '%@test.com%';
```

See [migrations/20260417_add_test_flags_and_cleanup.sql](migrations/20260417_add_test_flags_and_cleanup.sql) for full SQL.

---

## Step-by-Step: Manual Cleanup (If Needed)

### 1. Backup Database
```bash
cp backend/cpa.db backend/cpa.db.backup
```

### 2. Run Python Script
```bash
python production_scrub.py
```

### 3. Verify Cleanup
```bash
python check_db.py
```

Expected output:
```
✅ Municipalities: 4 production (was 24 before)
✅ Employees: 2 production (was 42 before)
✅ Reminders: 7 real reminders (17 placeholder removed)
```

### 4. Test with Dev Mode Toggle
```
1. Login as admin
2. Click "Dev Mode: OFF" toggle in navbar
3. Verify only production data shows
4. Click toggle again to enable dev mode
5. Verify test data becomes visible
```

---

## Verification Checklist

- [ ] Run `production_scrub.py` successfully
- [ ] Check that only real municipalities appear in Dashboard
- [ ] Verify employee list shows only production accounts
- [ ] Test Dev Mode toggle (admin navbar)
- [ ] Confirm localStorage saves dev mode preference
- [ ] Build frontend: `npm run build`
- [ ] Run integration tests: `pytest`
- [ ] Demo to client with clean data

---

## Troubleshooting

### "Column 'is_test' already exists"
This is fine! The script handles it gracefully. Just proceed.

### "No municipalities/employees deleted"
Check the patterns. Your test data might not match the expected naming:
```bash
# Query existing test data:
python -c "
from backend.database import SessionLocal
from backend.models import Municipality
db = SessionLocal()
print(db.query(Municipality).filter(Municipality.name.ilike('%test%')).all())
"
```

### Dev Mode toggle not showing
Make sure you're logged in as admin:
```javascript
// In browser console:
console.log(currentUser.role); // Should be "admin"
```

---

## Future: Automated Cleanup

Consider scheduling cleanup in CI/CD before demos:

```yaml
# Example GitHub Actions workflow
- name: Clean test data before demo
  run: python production_scrub.py
```

---

## Questions?

For issues or improvements, update this guide or create an issue in the repository.

**Last Updated:** April 17, 2026  
**Version:** 1.0
