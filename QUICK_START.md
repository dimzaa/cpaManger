# 🚀 QUICK START — Pre-Deployment Testing

## 📌 TL;DR (5 Minutes)

### 1. Setup (Run once)
```bash
# Windows
setup.bat

# macOS/Linux
python -m venv backend/venv
source backend/venv/bin/activate
pip install -r backend/requirements.txt
cd frontend && npm install
```

### 2. Run Tests
```bash
# Windows
run_tests.bat

# macOS/Linux
cd backend
source venv/bin/activate
python test_integration.py

# Then
cd frontend
npm run build
```

### 3. Expected Results
```
✅ Backend integration tests: PASS
✅ Frontend build: SUCCESS
✅ No errors or warnings
```

---

## ✅ Pre-Deployment Verification (30 minutes)

### Step 1: Start Servers (2 terminals)

**Terminal 1:**
```bash
cd backend && source venv/bin/activate
python -m uvicorn main:app --reload
```

**Terminal 2:**
```bash
cd frontend && npm run dev
```

### Step 2: Test Each Phase

| Phase | Test | Expected |
|-------|------|----------|
| **1** | Upload CSV | ✅ Data saved to DB |
| **2** | Login (admin) | ✅ JWT token received |
| **2** | Login (municipality) | ✅ Only sees own data |
| **3** | Dashboard | ✅ All municipalities visible |
| **4** | Portal | ✅ Shows only their data |
| **5** | Click "הצג הסבר" | ✅ Explanation appears |
| **5** | Admin clicks ✏️ | ✅ Can edit explanation |
| **6** | Export CSV | ✅ File downloads with Hebrew |

### Step 3: Check Mobile

Open **http://localhost:5173** on:
- [ ] iPhone (Safari) — responsive?
- [ ] Android (Chrome) — responsive?
- [ ] Tablet — landscape mode ok?

### Step 4: Database Verification

```bash
cd backend && source venv/bin/activate
python -c "
from database import SessionLocal
from models.municipality import Municipality
db = SessionLocal()
print(f'✅ {db.query(Municipality).count()} municipalities')
"
```

---

## 🔍 Critical Issues to Check

### Security ✅
- [ ] Can't login twice with wrong password
- [ ] Can't see other municipality data
- [ ] JWT tokens expire properly
- [ ] No API keys in frontend code

### Frontend ✅
- [ ] No red errors in F12 console
- [ ] Hebrew text displays correctly (not ??? boxes)
- [ ] Images/icons load properly
- [ ] Loading spinners appear during data fetch

### Backend ✅
- [ ] No Python errors in terminal
- [ ] Database saves data correctly
- [ ] API responses have correct structure
- [ ] CORS errors don't appear

### Performance ✅
- [ ] App loads in < 3 seconds
- [ ] Data displays after selection < 2 seconds
- [ ] No lag when interacting

---

## 🚨 Top 5 Things That Break

1. **Python not in PATH** → Run `python --version` first
2. **Node modules missing** → Run `npm install` in frontend folder
3. **Database locked** → Delete `test.db` and recreate
4. **Port already in use** → Change port or kill process
5. **VITE_API_URL wrong** → Check `frontend/.env` has correct backend URL

---

## 📊 Test Artifacts

After successful test run, you should have:

```
backend/
  └─ test.db              (SQLite database)
  └─ .env                 (Configuration)

frontend/
  └─ dist/                (Production build)
      ├─ index.html
      ├─ css/
      └─ js/
```

---

## 🟢 Ready to Deploy?

```
✅ Backend tests pass
✅ Frontend builds with no errors
✅ Can login as admin
✅ Can login as municipality
✅ Data displays correctly
✅ Mobile responsive
✅ Hebrew text correct
✅ No console errors

👉 DEPLOY SAFELY
```

---

## Advanced Debugging

### See detailed backend logs
```bash
LOG_LEVEL=DEBUG python -m uvicorn main:app --reload
```

### Check what database queries are being run
```bash
sqlite-utils query test.db "SELECT * FROM budget_lines LIMIT 5" --pretty
```

### Test API endpoint directly
```bash
# Get all municipalities
curl http://localhost:8000/api/municipalities

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@cpa.gov.il","password":"AdminPassword123"}'
```

### View all test logs
```bash
# Show all test output
python test_integration.py 2>&1 | tee test_results.log
```

---

## 📞 Support

If tests fail:
1. Read the error message carefully
2. Check SETUP_GUIDE.md for that specific error
3. Try the "Common Issues" section in DEPLOYMENT_CHECKLIST.md
4. Delete database and re-create: `rm backend/test.db`
5. Fresh npm install: `rm -rf frontend/node_modules && npm install`
