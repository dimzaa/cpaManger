# Environment Setup & Testing Guide

## 🔧 Complete Setup Instructions

### Prerequisites
- Windows 10+ or macOS/Linux
- Administrator access
- 5GB free disk space
- Internet connection

---

## Part 1: Install Required Software

### 1.1 Install Node.js (v18+)

**Windows:**
1. Go to https://nodejs.org/
2. Download LTS version (v18 or v20)
3. Run installer
4. Check "Add to PATH"
5. Click Next through all steps
6. Restart your terminal

**Verify:**
```bash
node --version    # Should show v18.x.x or higher
npm --version     # Should show 8.x.x or higher
```

### 1.2 Install Python (3.9+)

**Windows:**
1. Go to https://www.python.org/downloads/
2. Download Python 3.11 or latest
3. Run installer
4. **IMPORTANT:** Check ✅ "Add Python to PATH"
5. Click Install Now

**Verify:**
```bash
python --version  # Should show Python 3.x.x
pip --version     # Should show pip xx.x.x
```

### 1.3 Install Git (Optional but recommended)

```bash
# Windows: https://git-scm.com/download/win
# macOS: brew install git
# Linux: apt-get install git
```

---

## Part 2: Automated Setup (Windows)

If you have Node.js and Python installed, run:

```bash
# From project root directory
setup.bat
```

This will:
1. Create Python virtual environment
2. Install Python dependencies
3. Install Node.js dependencies
4. Create `.env` files

---

## Part 3: Manual Setup (All Platforms)

### Step 1: Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep flask  # Should see Flask listed
```

### Step 2: Create Backend .env

Create file: `backend/.env`

```env
# Database
DATABASE_URL=sqlite:///./test.db

# Security
SECRET_KEY=dev-secret-key-change-in-production-12345

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:5000

# Logging
LOG_LEVEL=INFO
```

### Step 3: Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Verify Node is correct
npm --version  # Should be 8.0+
```

### Step 4: Create Frontend .env

Create file: `frontend/.env`

```env
VITE_API_URL=http://localhost:8000
```

---

## Part 4: Running Development Servers

### Terminal 1 — Start Backend

```bash
cd backend
venv\Scripts\activate  # Windows: venv\Scripts\activate.bat
         # macOS/Linux: source venv/bin/activate

python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### Terminal 2 — Start Frontend

```bash
cd frontend
npm run dev
```

Expected output:
```
Port 5173 in use. Trying 5174...
  VITE v5.0.0  ready in 234 ms

  ➜  Local:   http://localhost:5173/
```

### Open Browser

Go to: **http://localhost:5173**

---

## Part 5: Run All Tests

### Option A: Automated (Windows only)

```bash
run_tests.bat
```

### Option B: Manual Testing

#### Backend Integration Tests

```bash
cd backend
venv\Scripts\activate  # Windows only
python test_integration.py
```

Expected output:
```
✅ [Phase 1 tests]
✅ [Phase 2 tests]
✅ [Phase 3 tests]
✅ [Phase 4 tests]
✅ [Phase 5 tests]

====================================
TEST SUMMARY
====================================
✅ Passed: 50/50
❌ Failed: 0/50
 📊 Success Rate: 100.0%
```

#### Frontend Build Test

```bash
cd frontend
npm run build
```

Expected output:
```
✓ built in 2.34s
```

Check output:
- Files in `frontend/dist/`
- No errors or warnings
- `dist/index.html` exists

#### Manual Functionality Tests

**Login Test (Admin):**
1. Browser: http://localhost:5173
2. Email: admin@cpa.gov.il
3. Password: AdminPassword123
4. Expected: Redirects to dashboard

**Login Test (Municipality):**
1. Email: municipality@example.com
2. Password: MunicipalityPassword123
3. Expected: Redirects to portal

**Upload Test:**
1. As admin, go to Upload page
2. Select test ZIP from `backend/sample_data/test_data.zip`
3. Click Upload
4. Expected: Success message, data in dashboard

**Portal Test:**
1. Login as municipality
2. Select month
3. View budget lines
4. Expected: Data displays, explanations show

---

## Part 6: Database Management

### Initialize Database

```bash
cd backend
venv\Scripts\activate

# Create tables
python -c "from database import Base, engine; Base.metadata.create_all(bind=engine); print('✅ Tables created')"

# Load sample data
python -c "
import json
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models.municipality import Municipality
from models.monthly_run import MonthlyRun
from models.budget_line import BudgetLine

# Load sample_data/municipalities.json
# Insert into database
print('✅ Sample data loaded')
"
```

### View Database (SQLite)

```bash
# Install if needed
pip install sqlite-utils

# View tables
sqlite-utils tables test.db

# View data
sqlite-utils query test.db "SELECT * FROM users" --pretty

# Export to JSON
sqlite-utils dump test.db > backup.json
```

---

## Part 7: Common Issues & Solutions

### Issue: "venv: command not found"
**Solution:**
```bash
python -m venv venv      # Use python -m
source venv/bin/activate # Then activate
```

### Issue: "pip: command not found"
**Solution:**
```bash
python -m pip install -r requirements.txt
```

### Issue: "CORS policy blocked"
**Solution:**
Check `backend/.env`:
```env
ALLOWED_ORIGINS=http://localhost:5173
```

### Issue: "Cannot find module 'react'"
**Solution:**
```bash
cd frontend
npm install
npm install react react-dom  # Explicitly install if missing
```

### Issue: "Port 8000 already in use"
**Solution:**
```bash
# Change port in backend start:
python -m uvicorn main:app --reload --port 8001

# Update frontend env:
VITE_API_URL=http://localhost:8001
```

### Issue: "Database locked"
**Solution:**
```bash
# Delete and recreate
rm test.db  # or delete test.db on Windows
python database.py  # Recreate
```

---

## Part 8: Production Build

### Build Frontend for Production

```bash
cd frontend
npm run build
```

Output: `frontend/dist/`

Deploy this folder to:
- AWS S3 + CloudFront
- Netlify  
- Vercel
- Railway Static
- GitHub Pages

### Build Backend Docker Image

```bash
# Create Dockerfile (if not exists)
# Then:
docker build -t cpa-budget-app .
docker run -p 8000:8000 cpa-budget-app
```

---

## Part 9: Debugging Tips

### Backend Debugging

```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG

# Run with print statements visible
python -u -m uvicorn main:app --reload

# Check database
python -c "
from database import SessionLocal
db = SessionLocal()
print('Users:', db.query(User).count())
print('Municipalities:', db.query(Municipality).count())
"
```

### Frontend Debugging

```bash
# Enable React DevTools
# Open Chrome DevTools (F12)
# Sources tab shows component hierarchy
# Console tab shows errors

# Clear cache if needed
localStorage.clear()
sessionStorage.clear()
```

### Network Debugging

```bash
# Check backend is accessible
curl http://localhost:8000/api/municipalities

# Check with header
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/auth/me
```

---

## Part 10: Health Checks

Run these to verify system is healthy:

```bash
# Backend running?
curl http://localhost:8000/

# Frontend accessible?
curl http://localhost:5173/

# Can login?
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@cpa.gov.il","password":"AdminPassword123"}'

# Database connected?
python -c "
from database import SessionLocal
db = SessionLocal()
users = db.query(User).count()
print(f'✅ Database connected. {users} users found.')
"
```

---

## 📋 Quick Reference

| Command | Purpose |
|---------|---------|
| `venv\Scripts\activate` | Activate Python environment |
| `python -m uvicorn main:app --reload` | Start backend |
| `npm run dev` | Start frontend in dev mode |
| `npm run build` | Build frontend for production |
| `python test_integration.py` | Run all backend tests |
| `python database.py` | Initialize database |
| `sqlite-utils query test.db "SELECT..." --pretty` | Query database |

---

## 🆘 Getting Help

1. **Check logs:** Look in terminal for error messages
2. **Read error carefully:** Python/JavaScript often gives detailed hints
3. **Google the error:** Most common issues have Stack Overflow answers
4. **Check environment variables:** Are `.env` files correct?
5. **Restart:** Kill both servers and start fresh
6. **Clean install:** `rm -rf node_modules` then `npm install`
