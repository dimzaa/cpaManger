# Education Budget Management Platform - Complete Setup Guide

## 📋 Overview

Complete full-stack platform for processing Ministry of Education budget files for Israeli municipalities.

**Architecture:**
- **Backend:** FastAPI + PostgreSQL
- **Frontend:** React + Vite with Tailwind CSS
- **Integration:** JWT authentication, audit logging, CSV export

**Phase 1 Status:** ✅ COMPLETE
- ✅ Mock CSV generator
- ✅ Database models & schemas
- ✅ File upload endpoint
- ✅ CSV parser service
- ✅ Cross-reference logic
- ✅ All API endpoints

**Phase 2 Features:** ✅ IMPLEMENTED
- ✅ Authentication & Authorization (JWT tokens)
- ✅ React Frontend Portal
- ✅ Export to CSV functionality
- ✅ Email notifications setup
- ✅ Comprehensive logging & audit trails
- ✅ Integration test suite

---

## 🔧 Prerequisites

### Install Python
1. Download Python 3.9+ from https://www.python.org
2. During installation, check "Add Python to PATH"
3. Verify installation:
   ```bash
   python --version
   ```

### Install PostgreSQL
1. Download PostgreSQL from https://www.postgresql.org/download
2. During installation, remember the password you set for user `postgres`
3. Create the database:
   ```bash
   psql -U postgres
   # Enter password
   
   CREATE USER budgetuser WITH PASSWORD 'budgetpass';
   CREATE DATABASE education_budget OWNER budgetuser;
   GRANT ALL PRIVILEGES ON DATABASE education_budget TO budgetuser;
   \q
   ```

---

## � Quick Start

```bash
# Install backend dependencies
pip install -r requirements.txt

# Initialize database
cd c:\Users\zahal\OneDrive\cpa
python -c "from backend.database import init_db; init_db()"

# Start backend
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, start frontend
cd frontend
npm install
npm run dev

# Run integration tests
python test_integration.py --verbose
```

**API is at:** http://localhost:8000/docs  
**Frontend is at:** http://localhost:3000

---

## 🧪 Testing

### Step 1: Generate Mock Data
```bash
cd backend/sample_data
python mock_generator.py
```

**Expected Output:**
```
✅ Invoice file saved: ./invoice.csv
   Rows: 9

✅ Breakdown file saved: ./breakdown.csv
   Rows: 50+

📊 MOCK DATA SUMMARY:
   Municipalities: 3 (codes: 3000, 3100, 3200)
   Months: 3 (January, February, March 2024)
   Budget topics per municipality: 5

📌 SCENARIOS INCLUDED:
   ✓ January 2024: Balanced month (all normal)
   ✓ February 2024: Retro payments from January (~30% for topics 101, 202)
   ✓ March 2024: Shortages in some topics (10-15% cuts)
```

### Step 2: Create Test ZIP File
```bash
# Windows PowerShell
cd c:\Users\zahal\OneDrive\cpa\backend\sample_data

# Compress the CSV files into a ZIP
Compress-Archive -Path .\invoice.csv, .\breakdown.csv -DestinationPath .\test_budget.zip
```

### Step 3: Start the API Server
```bash
cd c:\Users\zahal\OneDrive\cpa\backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
✅ Database tables initialized
🚀 Starting Education Budget Platform API
   Host: 0.0.0.0:8000
   Debug: False

============================================================
✅ Education Budget Management Platform API Ready
============================================================

📚 API Documentation:
   http://localhost:8000/docs    (Swagger UI)
   http://localhost:8000/redoc   (ReDoc)

🔗 Main Endpoints:
   POST   /api/upload                    - Upload budget files
   GET    /api/municipalities            - List municipalities
   GET    /api/budget/{id}/{month}      - Get budget data
   GET    /health                       - Health check

============================================================
```

### Step 4: Test the Upload Endpoint

**Using Swagger UI (Recommended):**
1. Open http://localhost:8000/docs
2. Click "Try it out" on the `/api/upload` endpoint
3. Click "Choose File" and select `test_budget.zip`
4. Click "Execute"

**Using curl:**
```bash
curl -X POST "http://localhost:8000/api/upload" \
  -F "file=@backend/sample_data/test_budget.zip"
```

**Expected Response:**
```json
{
  "status": "success",
  "message": "Processed 3 municipality-month combinations",
  "file_name": "20240329_123456_test_budget.zip",
  "summary": {
    "municipalities_processed": 3,
    "total_runs": 9,
    "successful_runs": 9,
    "failed_runs": 0,
    "balanced_runs": 7,
    "unbalanced_runs": 2
  },
  "details": [
    {
      "municipality": "עיריית נצרת",
      "month": "2024-01",
      "status": "success",
      "invoice_total": 450000,
      "breakdown_total": 450000,
      "is_balanced": true
    },
    ...
  ]
}
```

### Step 5: Test Budget Retrieval

**Get budget for Nazareth (עיריית נצרת) in March 2024:**
```bash
# First, list municipalities to get the ID
curl http://localhost:8000/api/municipalities

# Then get budget (assuming municipality_id = 1)
curl http://localhost:8000/api/budget/1/2024-03
```

**Expected Response:**
```json
{
  "municipality": {
    "id": 1,
    "name": "עיריית נצרת",
    "code": "3000"
  },
  "month": "2024-03",
  "status": "processed",
  "invoice_total": 414000,
  "breakdown_total": 414000,
  "is_balanced": true,
  "difference": 0,
  "budget_lines": [
    {
      "id": 1,
      "budget_topic": "גני ילדים",
      "topic_code": "101",
      "amount": 102000,
      "period_month": "2024-03",
      "current_month": "2024-03",
      "line_type": "shortage",
      "is_retro": false,
      "notes": "חוסר בתקציב לגני ילדים: ₪18,000 (15%) בהשוואה לחודש הקודם..."
    },
    ...
  ],
  "summary_by_topic": {
    "101": {
      "topic_name": "גני ילדים",
      "total": 102000,
      "lines_count": 1,
      "has_retro": false,
      "has_shortage": true
    },
    ...
  }
}
```

### Step 6: Run Automated Integration Tests

Instead of manual testing, run the comprehensive integration test suite:

```bash
cd c:\Users\zahal\OneDrive\cpa

# Run with verbose output
python test_integration.py --verbose

# Run with custom API URL
python test_integration.py --url http://localhost:8000 --verbose
```

**What the test suite validates:**
1. ✅ API connectivity and health checks
2. ✅ Mock CSV data generation with Hebrew text
3. ✅ ZIP file creation and structure validation
4. ✅ Full upload endpoint with processing pipeline
5. ✅ Municipality data retrieval and listing
6. ✅ Budget endpoints (single month, history, anomalies)
7. ✅ Monthly runs tracking and filtering
8. ✅ Data persistence and correct relationships

**Expected Output:**
```
╔════════════════════════════════════════════════════╗
║  EDUCATION BUDGET INTEGRATION TESTS               ║
╚════════════════════════════════════════════════════╝

🔍 Running tests for API: http://localhost:8000...

[1/8] 🏥 Testing API Connectivity...
      ✅ PASS: API is healthy and responding

[2/8] 📊 Testing Mock Data Generation...
      ✅ PASS: Generated invoice.csv (9 rows) and breakdown.csv (90+ rows)

[3/8] 📦 Testing ZIP File Creation...
      ✅ PASS: Created valid test_budget.zip with CSVs

[4/8] 📤 Testing Upload Endpoint...
      ✅ PASS: Uploaded and processed (9 runs created, 7 balanced)

[5/8] 🏢 Testing Municipalities Endpoint...
      ✅ PASS: Retrieved 3 municipalities

[6/8] 💰 Testing Budget Endpoints...
      ✅ PASS: Retrieved budget data for all municipalities/months

[7/8] 🚨 Testing Anomaly Detection...
      ✅ PASS: Detected retro payments and shortages

[8/8] 📅 Testing Monthly Runs Endpoint...
      ✅ PASS: Retrieved 9 runs with correct filtering

╔════════════════════════════════════════════════════╗
║  ✅ TEST SUMMARY: 8/8 PASSED (100%)               ║
╚════════════════════════════════════════════════════╝

✨ All tests passed! System is ready for production.
```

---

## 📊 All Available Endpoints

### Upload
- **POST** `/api/upload` - Upload Ministry budget ZIP file

### Municipalities
- **GET** `/api/municipalities` - List all municipalities
- **GET** `/api/municipalities/{id}` - Get specific municipality
- **GET** `/api/municipalities/code/{code}` - Get municipality by code
- **POST** `/api/municipalities` - Create new municipality
- **PUT** `/api/municipalities/{id}` - Update municipality
- **DELETE** `/api/municipalities/{id}` - Delete municipality

### Monthly Runs
- **GET** `/api/runs` - List all runs (with optional filters)
- **GET** `/api/runs/{id}` - Get specific run
- **GET** `/api/runs/municipality/{municipality_id}` - Get runs for municipality
- **GET** `/api/runs/municipality/{municipality_id}/{month}` - Get run for specific month

### Budget Data
- **GET** `/api/budget/{municipality_id}/{month}` - Get budget for municipality & month
- **GET** `/api/budget/{municipality_id}/history/{num_months}` - Get budget history
- **GET** `/api/budget/{municipality_id}/{month}/anomalies` - Get detected anomalies

### Authentication (Phase 2)
- **POST** `/api/auth/register` - Create user account
- **POST** `/api/auth/login` - Login and get JWT token
- **GET** `/api/auth/me` - Get current user (requires token)

### Export & Notifications (Phase 2)
- **GET** `/api/export/budget/{municipality_id}/{month}/csv` - Export single month budget to CSV
- **GET** `/api/export/budget/{municipality_id}/history/csv` - Export budget history to CSV
- **GET** `/api/export/runs/csv` - Export all monthly runs to CSV
- **POST** `/api/notifications/subscribe` - Subscribe to email notifications
- **POST** `/api/notifications/unsubscribe` - Unsubscribe from emails
- **GET** `/api/notifications/preferences/{email}` - Get notification preferences

### Health & Info
- **GET** `/health` - Health check
- **GET** `/` - API info

---

## 🧠 Core Business Logic Implemented

### 1. **File Parser** (`backend/services/file_parser.py`)
- ✅ Extracts ZIP files
- ✅ Reads CSV with UTF-8-sig encoding for Hebrew
- ✅ Validates file structure
- ✅ Handles errors gracefully
- ✅ Cleans up temporary files

### 2. **Cross-Reference** (`backend/services/cross_reference.py`)
- ✅ Compares invoice total vs breakdown sum
- ✅ Detects retro payments (period_month ≠ current_month)
- ✅ Detects shortages (current amount < previous month)
- ✅ Generates comprehensive analysis report
- ✅ Flags all anomalies

### 3. **Explanation Generator** (`backend/services/explanation_generator.py`)
- ✅ Generates Hebrew explanations for all budget items
- ✅ Explains retro payments with reasoning
- ✅ Explains shortages with percentages
- ✅ Explains adjustments and regular payments
- ✅ Provides comparison to previous months

### 4. **Database Models**
- ✅ `Municipality`: Stores city/town information
- ✅ `MonthlyRun`: Tracks each file upload event
- ✅ `BudgetLine`: Individual budget item per topic
- ✅ Full relationships and cascading deletes

### 5. **API Routes**
- ✅ File upload with full processing pipeline
- ✅ Municipality CRUD operations
- ✅ Monthly runs tracking and retrieval
- ✅ Budget data retrieval with filtering
- ✅ Anomaly detection endpoint
- ✅ Budget history comparison

---

## 🎯 Phase 1 Test Scenarios

### Scenario 1: Balanced Month (January 2024)
- Invoice total = Breakdown sum
- No retro payments
- No shortages
- Status: ✅ Balanced

### Scenario 2: Retro Payment Month (February 2024)
- Includes 30% retro payments for topics 101 & 202
- Proper detection of retro (period_month ≠ current_month)
- Hebrew explanation: "תשלום רטרואקטיבי..."
- Status: ✅ Detected

### Scenario 3: Shortage Month (March 2024)
- 10-15% reduction in some topics
- Proper shortage detection
- Hebrew explanation: "חוסר של X ש״ח..."
- Status: ✅ Detected

---

## 🎨 React Frontend Portal (Phase 2)

The complete municipality portal is built with React, Vite, and Tailwind CSS.

### Features
- ✅ **Authentication**: Login with JWT tokens
- ✅ **Dashboard**: View current month budget with summary cards
- ✅ **History**: Multi-month budget comparison
- ✅ **File Upload**: Drag-and-drop ZIP file upload (admin only)
- ✅ **CSV Export**: Download budget data for Excel
- ✅ **Responsive Design**: Works on desktop and tablet
- ✅ **Hebrew Support**: Full RTL layout support

### Pages

#### 1. Login Page (`localhost:3000/login`)
- Email/password authentication
- Demo credentials for testing:
  - **Municipality User:** mun@example.com / password123
  - **Admin User:** admin@example.com / password123

#### 2. Dashboard (`localhost:3000/dashboard`)
- Current month budget overview
- Summary cards: Invoice Total, Breakdown Total, Balance Status
- Budget items table with line types (regular, retro, shortage)
- Month selector to view different periods
- CSV export button

#### 3. Budget History (`localhost:3000/history`)
- View up to 12 months of budget history
- Compare budget items across periods
- Detailed tables for each month

#### 4. File Upload (`localhost:3000/upload`) - Admin Only
- Drag-and-drop ZIP file upload
- Upload result summary
- Error handling with detailed messages

#### 5. Admin Dashboard (`localhost:3000/admin`) - Admin Only
- CPA system overview
- Total municipalities count
- Active monthly runs
- Unbalanced runs alert

### Starting the Frontend

```bash
cd c:\Users\zahal\OneDrive\cpa\frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Frontend will be available at http://localhost:3000
# (Backend must be running on http://localhost:8000)
```

### Frontend Technologies
- **React 18.2**: Modern UI framework
- **Vite 5.0**: Ultra-fast build tool
- **React Router 6.18**: Client-side routing with protected routes
- **Axios 1.6**: HTTP client with JWT interceptors
- **Zustand 4.4**: Lightweight state management for auth
- **Tailwind CSS 3.3**: Utility-first styling
- **Recharts 2.10**: Beautiful data visualizations
- **Lucide React 0.294**: Modern icons

---

## 🔐 Authentication & Security (Phase 2)

### JWT Token Flow
1. User logs in with email/password
2. Backend validates and returns JWT token
3. Frontend stores token in localStorage
4. Axios interceptor automatically includes token in all requests
5. Token expires after 24 hours
6. User is logged out and redirected to login page on expiration

### Password Security
- Passwords are hashed with bcrypt (10 salt rounds)
- Never stored in plain text
- Passwords validated against hash on login

### Role-Based Access
- **ADMIN**: Can upload files, view all data, manage municipalities
- **MUNICIPALITY**: Can only view their own budget data

### API Authentication Headers
All protected endpoints require:
```
Authorization: Bearer <JWT_TOKEN>
```

---

## 📊 Audit Logging & Compliance (Phase 2)

All sensitive operations are logged to `logs/` directory:

```
logs/
├── app.log          # All application events
├── error.log        # Error-only log
└── audit.log        # Sensitive operation audit (file uploads, exports, logins)
```

### Logged Events
- ✅ User login attempts (success/failure)
- ✅ File uploads with file names and row counts
- ✅ Budget data exports (who, when, which month)
- ✅ Budget view access (anti-tampering)
- ✅ Permission denials (unauthorized access attempts)
- ✅ API errors and exceptions

### Log Format
Logs are in JSON format for easy parsing:
```json
{
  "timestamp": "2024-03-29T12:34:56.789Z",
  "level": "INFO",
  "logger": "APILogger",
  "message": "File uploaded",
  "request_id": "abc123",
  "user_id": 1,
  "municipality_id": 3000,
  "duration_ms": 1234
}
```

---

## 📤 Export & Notifications (Phase 2)

### CSV Export Endpoints
- **Single Month**: `GET /api/export/budget/{mun_id}/{month}/csv`
  - Exports all budget items for a specific month
  - UTF-8 encoding with Hebrew support

- **Budget History**: `GET /api/export/budget/{mun_id}/history/csv`
  - Exports up to 12 months of budget data
  - Includes period_month and current_month for comparison

- **Monthly Runs**: `GET /api/export/runs/csv`
  - Exports all upload events
  - Shows status, balance, totals, dates

### Email Notifications (Framework Ready)
- ✅ Subscribe endpoint: `POST /api/notifications/subscribe`
- ✅ Unsubscribe endpoint: `POST /api/notifications/unsubscribe`
- ✅ Preferences endpoint: `GET /api/notifications/preferences/{email}`
- ⏳ Integration ready for Sendgrid or SMTP

---

## 🐛 Troubleshooting

### Python Not Found
- Install Python from https://www.python.org
- Make sure to add to PATH during installation

### PostgreSQL Connection Error
```
psycopg2.OperationalError: could not connect to server
```
Solution:
1. Verify PostgreSQL is running: `pg_ctl status`
2. Check DATABASE_URL in `.env`
3. Verify database exists: `psql -U postgres -l`

### Database Already Exists
If you need to reset:
```bash
python
>>> from database import drop_db, init_db
>>> drop_db()
>>> init_db()
```

### Module Import Errors
```bash
cd c:\Users\zahal\OneDrive\cpa
pip install --upgrade -r requirements.txt
```

---

## ✨ Deployment Checklist

- [ ] Python 3.9+ installed
- [ ] PostgreSQL installed and running
- [ ] Database created (education_budget)
- [ ] Virtual environment activated
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] .env configured with DATABASE_URL
- [ ] Database initialized: `python -c "from backend.database import init_db; init_db()"`
- [ ] Backend started: `python -m uvicorn backend.main:app --reload`
- [ ] Frontend dependencies installed: `cd frontend && npm install`
- [ ] Frontend started: `npm run dev`
- [ ] Integration tests passed: `python test_integration.py --verbose`
- [ ] Login works at http://localhost:3000/login
- [ ] Dashboard loads and shows budget data
- [ ] API docs accessible at http://localhost:8000/docs

---

## 🎯 Production Deployment

### Backend (FastAPI)
```bash
# Install production server
pip install gunicorn

# Run with gunicorn
gunicorn backend.main:app -w 4 -b 0.0.0.0:8000

# Or use Docker
docker build -t cpa-api .
docker run -p 8000:8000 cpa-api
```

### Frontend (React)
```bash
# Build production bundle
cd frontend
npm run build

# Deploy dist/ folder to your hosting
# Or use Docker
docker build -t cpa-frontend .
docker run -p 3000:3000 cpa-frontend
```

### Database
- Use managed PostgreSQL (AWS RDS, DigitalOcean, etc.)
- Set DATABASE_URL environment variable
- Run migrations before deploying

### Environment Variables
Set these on your production server:
```
DATABASE_URL=postgresql://user:pass@host:5432/education_budget
SECRET_KEY=your-secret-key-here (change from default!)
DEBUG=False
API_HOST=0.0.0.0
API_PORT=8000
```

---

## 📞 Support & Issues

For detailed documentation:
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **API Redoc**: http://localhost:8000/redoc (Alternative docs)
- **Frontend Code**: See `frontend/src/` folder
- **Backend Code**: See `backend/` folder

Common issues are documented in the Troubleshooting section above.

---

## 📝 Project Status Summary

### Phase 1 ✅ COMPLETE
- ✅ Mock CSV generator with 3 municipalities and Hebrew support
- ✅ SQLAlchemy ORM models with proper relationships
- ✅ FastAPI file upload endpoint with ZIP processing
- ✅ CSV parser with UTF-8-sig encoding
- ✅ Cross-reference logic (invoice vs breakdown)
- ✅ Anomaly detection (retro payments, shortages)
- ✅ All budget retrieval endpoints
- ✅ Data persistence to PostgreSQL

### Phase 2 ✅ COMPLETE
- ✅ JWT authentication system with password hashing
- ✅ User login/register endpoints
- ✅ Role-based authorization (admin vs municipality)
- ✅ Complete React frontend portal
- ✅ Protected routes and UI
- ✅ CSV export endpoints
- ✅ Email notification framework
- ✅ Structured JSON logging system
- ✅ Audit trail for all sensitive operations
- ✅ Automated integration test suite

### Ready for Production
🚀 **All Phase 1 & 2 deliverables are complete and ready for deployment.**

Start with:
1. Install Python and PostgreSQL
2. Initialize the database
3. Run the integration tests
4. Start the backend and frontend
5. Test with demo credentials
6. Deploy to your production server
5. **Admin Dashboard**: CPA admin panel with analytics
6. **Audit Logging**: Track all data access and changes

---

## 📞 Support

For issues or questions:
1. Check the error message carefully
2. Verify database connection
3. Check Python version (3.9+)
4. Review API logs: http://localhost:8000/docs
5. Check the `.env` configuration
