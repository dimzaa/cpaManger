# 🚀 Pre-Deployment Checklist — Education Budget Platform

## Phase: ALL 7 PHASES (1-7)

**Date:** March 30, 2026  
**Status:** Ready for Testing  
**Last Updated:** This session

---

## 📋 ENVIRONMENT SETUP (REQUIRED FIRST)

### Step 1: Install Node.js & Backend Dependencies

```bash
# Windows - Install Node.js v18+ from https://nodejs.org/
# Then verify:
node --version    # v18.0.0 or higher
npm --version     # 8.0.0 or higher

# Backend dependencies
cd backend
# Create virtual environment (if not exists)
python -m venv venv
# Activate it
venv\Scripts\activate  # Windows
# Or: source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Frontend Dependencies

```bash
cd frontend
npm install
```

### Step 3: Environment Variables

```bash
# Backend — create backend/.env
DATABASE_URL=sqlite:///./test.db
SECRET_KEY=test-secret-key-change-in-production
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Frontend — create frontend/.env
VITE_API_URL=http://localhost:8000
```

---

## 🧪 LOCAL TESTING — RUN ALL TESTS

### Run Backend Tests

```bash
cd backend
# Activate venv first
venv\Scripts\activate

# Run integration tests
python test_integration.py

# Expected output:
# ✅ [Phase 1 tests pass]
# ✅ [Phase 2 tests pass]
# ✅ [Phase 3 tests pass]
# ✅ [Phase 4 tests pass]
# ✅ [Phase 5 tests pass]
# ✅ [Phase 6 tests pass]
# ✅ [Auth & security tests pass]
```

### Run Frontend Build

```bash
cd frontend
npm run build

# Expected:
# ✓ built in ... ms
# No errors or warnings
```

### Start Local Servers (for manual testing)

```bash
# Terminal 1 — Backend
cd backend
venv\Scripts\activate
uvicorn main:app --reload

# Terminal 2 — Frontend  
cd frontend
npm run dev
```

---

## ✅ TEST RESULTS CHECKLIST

### Phase 1 — Engine
- [ ] CSV parser handles Hebrew text correctly
- [ ] Mock data generates for all 3 municipalities
- [ ] Budget lines parsed with correct amounts, codes, types
- [ ] All 3 line types detected (regular, retro, shortage, adjustment)
- [ ] Cross-reference logic validates correctly
- [ ] MySQL/SQLite saves all data without errors
- [ ] API routes return correct JSON structure

### Phase 2 — Security & Auth
- [ ] User can login with correct credentials
- [ ] Wrong credentials return "Invalid credentials" error
- [ ] JWT token generated on successful login
- [ ] Token stored in localStorage
- [ ] Token sent in Authorization header for protected routes
- [ ] Invalid/expired token returns 401 Unauthorized
- [ ] Passwords hashed with bcrypt (never stored plain)
- [ ] Municipality user cannot see other municipalities' data
- [ ] Non-authenticated user cannot access /api endpoints

### Phase 3 — CPA Admin Dashboard
- [ ] Login page loads at /
- [ ] Login redirects to /dashboard on success
- [ ] Dashboard lists all municipalities with counts
- [ ] Upload page accepts ZIP files
- [ ] ZIP file processes and data appears in database
- [ ] Municipality detail page shows all budget lines
- [ ] Line type badges have correct colors (retro=yellow, shortage=red, etc.)
- [ ] Sorting by amount, topic works
- [ ] CSV export downloads all data
- [ ] Excel export includes all sheets with formatting

### Phase 4 — Municipality Portal
- [ ] Municipality login redirects to /portal
- [ ] Portal only shows that municipality's data
- [ ] Cannot access /dashboard or admin pages
- [ ] Month selector works and loads data
- [ ] Budget totals calculate correctly
- [ ] Status banner shows correct (balanced/unbalanced)
- [ ] Retro explainer shows when retro lines present
- [ ] History chart displays 6 months
- [ ] Responsive on mobile (iPhone, Android)
- [ ] RTL text alignment correct for Hebrew

### Phase 5 — Explanations Engine
- [ ] Auto-generated explanations appear for each budget line
- [ ] Explanations match budget topic (e.g., kindergarten explanation for topic 101)
- [ ] Different explanations for different line types (retro, shortage, etc.)
- [ ] CPA admin can click edit and see textarea
- [ ] Custom explanation saves to database
- [ ] "✏️ מותאם אישית" badge appears after save
- [ ] Delete custom explanation reverts to auto-generated
- [ ] Municipality users see explanation (whether auto or custom)
- [ ] Explanations in Hebrew
- [ ] Admin-only edit (municipality users cannot edit)

### Phase 6 — Advanced Features (if implemented)
- [ ] Anomaly detection works for outliers
- [ ] Dashboard shows statistical comparisons
- [ ] Filtering by topic/type works
- [ ] Search functionality returns results
- [ ] Pagination works for large datasets

### Phase 7 — Mobile & Performance
- [ ] App loads in < 3 seconds on desktop
- [ ] App loads in < 5 seconds on mobile 3G
- [ ] No console errors when performing normal operations
- [ ] Loading spinners appear during data fetch
- [ ] Data displays correctly on:
  - [ ] Windows Chrome (desktop)
  - [ ] Windows Edge
  - [ ] iPhone Safari
  - [ ] Android Chrome
- [ ] No layout shifts or broken Hebrew text

---

## 🔐 SECURITY VERIFICATION

- [ ] Passwords meet minimum requirements (8+ chars, mixed case, number)
- [ ] JWT tokens expire after 24 hours
- [ ] CORS only allows frontend origin
- [ ] SQL injection prevented (using ORM)
- [ ] CSRF tokens present on forms
- [ ] No sensitive data in localStorage except JWT
- [ ] No API keys or secrets in frontend code
- [ ] Environment variables used for all secrets
- [ ] Database credentials not in version control

---

## 📊 DATA VALIDATION

### Sample Test Data (Already Created)
- Location: `backend/sample_data/`
- Files: Mock CSV files for 3 municipalities
- Months: 2024-01, 2024-02, 2024-03

### After Upload, Verify:
- [ ] 3 municipalities in `municipalities` table
- [ ] 9 monthly_runs total (3 municipalities × 3 months)
- [ ] 108+ budget_lines total (36+ per month × 3 months)
- [ ] No duplicate entries
- [ ] All amounts in NIS (₪)
- [ ] All dates in YYYY-MM format

---

## 🚀 GO-LIVE VERIFICATION (BEFORE DEPLOY)

1. **Database Connectivity**
   - [ ] Can connect to production database
   - [ ] Tables created (or migrations run)
   - [ ] Backups configured

2. **Frontend Build**
   - [ ] `npm run build` completes with no errors
   - [ ] No warnings in build output
   - [ ] `dist/` folder contains all static files
   - [ ] Map files generated for debugging

3. **Backend Health**
   - [ ] No Python import errors
   - [ ] All environment variables loaded
   - [ ] Database connection successful
   - [ ] Sample data loads without errors

4. **Environment Configuration**
   - [ ] VITE_API_URL points to production backend
   - [ ] Backend DATABASE_URL points to production database
   - [ ] ALLOWED_ORIGINS includes frontend domain
   - [ ] SECRET_KEY is unique and strong (32+ characters)

---

## 📈 MONITORING AFTER GO-LIVE

### Week 1 — Daily Checks
- [ ] No crashes in Railway logs
- [ ] Database size growing normally
- [ ] File uploads completing
- [ ] JWT token generation working
- [ ] No CORS errors in browser console

### Week 2-4 — Every 3 Days
- [ ] Response times normal (< 2 seconds)
- [ ] CSV parsing still working for new uploads
- [ ] Backups running successfully
- [ ] No disk space issues

### Ongoing
- [ ] Check Railway dashboard once weekly
- [ ] Review error logs for patterns
- [ ] Monitor database size quarterly
- [ ] Update dependencies every 3 months

---

## 🔧 COMMON ERRORS & FIXES

| Error | Cause | Fix |
|-------|-------|-----|
| `CORS policy blocked` | Frontend trying to call backend, CORS not configured | Add frontend URL to `ALLOWED_ORIGINS` in backend |
| `Hebrew text shows as ????` | Encoding issue in CSV parsing | Ensure `encoding='utf-8-sig'` in pandas |
| `JWT token invalid` | Token expired or SECRET_KEY changed | User logs out and logs back in |
| `relation "users" does not exist` | Database tables not created | Run `python database.py` to create tables |
| `connection refused: 127.0.0.1:8000` | Backend not running | Start backend: `uvicorn main:app --reload` |
| `Module not found: python` | Python not in PATH | Activate venv: `venv\Scripts\activate` |
| `npm command not found` | Node.js not installed | Install from https://nodejs.org/ |
| `413 Request Entity Too Large` | File upload too big | Increase `client_max_body_size` in server config |

---

## 📝 SIGN-OFF

When all tests pass:

```
✅ Phase 1 (Engine) — VERIFIED
✅ Phase 2 (Auth) — VERIFIED
✅ Phase 3 (CPA Dashboard) — VERIFIED
✅ Phase 4 (Municipality Portal) — VERIFIED
✅ Phase 5 (Explanations) — VERIFIED
✅ Phase 6 (Advanced Features) — VERIFIED
✅ Phase 7 (Mobile & Performance) — VERIFIED

✅ Security Checks — PASSED
✅ Data Validation — PASSED
✅ Build Production — NO ERRORS
✅ Ready for Deployment — YES
```

**Deployment Date:** _______________  
**Deployed By:** _______________  
**Production URL:** _______________  

---

**Next Steps After Verification:**
1. Notify stakeholders that system is ready
2. Schedule go-live date
3. Set up production monitoring
4. Prepare user documentation & training
5. Create support contact list
