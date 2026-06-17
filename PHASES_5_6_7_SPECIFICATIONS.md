# Phases 5, 6 & 7 — Complete Specifications

---

## PHASE 5 — Explanations Engine 🟡

### Purpose
Auto-generate Hebrew explanations for each budget line, with CPA override capability.

### Key Files to Create
**Backend:**
- `services/explanation_service.py` — generates explanations from rules
- `data/purple_booklet_rules.py` — budget topic rules database
- `models/explanation.py` — stores custom explanations
- `routes/explanations.py` — API for CPA to create/edit/delete

**Frontend:**
- `components/portal/ExplanationBox.jsx` — displays explanation

### API Endpoints
```
POST /explanations/{municipality_id}/{month}/{topic_code}
  Input: { custom_text }
DELETE /explanations/{municipality_id}/{month}/{topic_code}
GET /explanations/{municipality_id}/{month}
```

### Data Flow
1. Get budget line
2. Check custom_explanations table
3. If custom exists → use it
4. If not → generate from purple_booklet_rules.py

### Budget Topics (5 Core)
```
101: גני ילדים (kindergarten)
202: חינוך מיוחד (special education)
303: שעות נוסף מורים (teacher overtime)
404: ליקויי למידה (learning disabilities)
505: נסיעות תלמידים (student transportation)
```

### Explanation Types per Budget Line
- **regular** → "תשלום שוטף עבור [topic] לחודש [month]"
- **retro** → "השלמת תשלום עבור [topic] — עבור [period month]"
- **shortage** → "הפחתה ב[topic] — הפרש של ₪[amount]"
- **adjustment** → "התאמה טכנית בנושא [topic]"

### Frontend Behavior
**Municipality (read-only):**
- Shows explanation text in table
- No edit option

**CPA (can edit):**
- Shows explanation text
- Hover reveals ✏️ edit icon
- Click edit → inline text editor
- Save → POST custom explanation
- Shows "מותאם אישית" badge if custom
- Delete button reverts to auto-generated

### Completion Checklist
- ✅ All 5 topics have rules
- ✅ Auto explanations generated
- ✅ Retro lines get retro explanation
- ✅ Shortage lines get shortage explanation
- ✅ Explanations show in municipality portal
- ✅ CPA can edit any explanation
- ✅ Custom saved → municipality sees it
- ✅ Delete custom → reverts to auto
- ✅ "מותאם אישית" badge shows

---

## PHASE 6 — Reports & Exports 🟢

### Purpose
CPA and municipalities download data as PDF or Excel with one click.

### Dependencies
```bash
pip install reportlab openpyxl
```

### Key Files to Create
**Backend:**
- `services/pdf_generator.py` — creates PDF reports
- `services/excel_generator.py` — creates Excel spreadsheets
- `routes/exports.py` — download endpoints

**Frontend:**
- `components/ExportButtons.jsx` — PDF + Excel download buttons

### API Endpoints
```
GET /export/pdf/{municipality_id}/{month}
  Returns: PDF file download
  Auth: admin or that municipality

GET /export/excel/{municipality_id}/{month}
  Returns: Excel file download
  Auth: admin or that municipality

GET /export/excel/all/{month}
  Returns: Excel with ALL municipalities
  Auth: admin only
```

### PDF Report Contents
```
Header:        SmartHub Logo + Date
Title:         דוח תקציב חודשי — עיריית [name] — [month]
Summary:       3 boxes (מגיע, שולם, הפרש)
Budget Table:  All lines with explanations
Footer:        CPA name, generation date, page numbers
RTL Layout:    Full Hebrew right-to-left
```

### PDF Formatting
- A4 paper size
- Navy header (#1E3A5F)
- Table with alternating row colors
- Retro rows highlighted
- Shortage rows highlighted

### Excel Types

**Type 1 — Single Municipality:**
- Sheet 1: Summary data
- Sheet 2: Full budget lines
- Sheet 3: Comparison vs. previous month

**Type 2 — All Municipalities (admin only):**
- One sheet per municipality
- Summary row per municipality
- For CPA's monthly review

### Excel Formatting
- Bold Hebrew headers
- Navy header row (#1E3A5F) with white text
- Alternating gray/white rows
- Currency format: ₪ #,##0
- Retro rows: amber fill (#FFF3CD)
- Shortage rows: red fill (#FFE0E0)
- Auto-width columns
- Freeze top row

### Frontend Behavior
```
Component: ExportButtons
Shows where: 
  - Bottom of MunicipalityPage (Phase 3)
  - Bottom of PortalBudgetPage (Phase 4)

Design:
┌──────────────────────┐
│ הורד דוח:             │
│ [📄 PDF] [📊 Excel]   │
└──────────────────────┘

Logic:
1. User clicks PDF or Excel button
2. Show loading spinner
3. Fetch file from /export/pdf or /export/excel
4. responseType: 'blob' (important!)
5. Create download link
6. Browser auto-downloads file
7. File name: "דוח_[municipality]_[month].[ext]"
```

### Completion Checklist
- ✅ PDF generates with Hebrew text
- ✅ PDF has correct RTL layout
- ✅ PDF includes all budget lines
- ✅ PDF includes explanations
- ✅ PDF downloads when button clicked
- ✅ Excel generates with correct formatting
- ✅ Retro rows amber in Excel
- ✅ Shortage rows red in Excel
- ✅ All municipalities Excel works for admin
- ✅ File names include municipality + month
- ✅ Loading spinner while generating

---

## PHASE 7 — Deployment 🟡

### Purpose
Move the application from your computer to the internet (production).

### Hosting Recommendation
**Railway.app** (simplest option)
- Python + PostgreSQL support
- Auto-deploy from GitHub
- Free tier to start, ~$5-10/month when ready
- No server management

**Alternative: DigitalOcean** ($6/month droplet)
- More control but more setup work

### Architecture on Server
```
Internet
    ↓
[Domain: app.smarthub-dani.com]
    ↓
[Nginx — reverse proxy, SSL/HTTPS]
    ├→ /api/*  → FastAPI backend (port 8000)
    └→ /*      → React frontend (static files)
    ↓
[PostgreSQL database]
[Uploaded files (/uploads or S3)]
```

### New Files Required
```
project root:
├── Dockerfile              (packages backend for deployment)
├── docker-compose.yml      (runs backend + database)
├── nginx.conf              (routes traffic, HTTPS)
├── .env.production         (backend env vars)
└── frontend/
    └── .env.production     (API_URL=https://...)
```

### Dockerfile (Backend)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY ./backend .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml
```yaml
services:
  backend:
    build: .
    ports: ["8000:8000"]
    env_file: .env.production
    depends_on: [db]
  
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: education_budget
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: [strong password]
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### nginx.conf (Key Parts)
```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name app.smarthub-dani.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name app.smarthub-dani.com;
    
    # SSL certificates from Let's Encrypt (free)
    ssl_certificate /etc/letsencrypt/live/app.smarthub-dani.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.smarthub-dani.com/privkey.pem;
    
    # API requests → backend
    location /api {
        proxy_pass http://localhost:8000;
    }
    
    # Everything else → React frontend
    location / {
        root /var/www/frontend/dist;
        try_files $uri $uri/ /index.html;
    }
}
```

### Environment Variables
```bash
# .env.production (backend)
DATABASE_URL=postgresql://admin:password@db:5432/education_budget
SECRET_KEY=very_long_random_string_here_minimum_32_chars
ALLOWED_ORIGINS=https://app.smarthub-dani.com
UPLOAD_DIR=/app/uploads
ENV=production

# frontend/.env.production
VITE_API_URL=https://app.smarthub-dani.com/api
```

### Deployment Steps (In Order)

| Step | Action | Cost/Time |
|------|--------|-----------|
| 1 | Buy domain (namecheap.com or domains.google.com) | ~$10/year, 5 min |
| 2 | Create Railway.app account + connect GitHub | Free, 5 min |
| 3 | Push code to GitHub | — |
| 4 | Create Railway project from GitHub repo | Free, 5 min |
| 5 | Add PostgreSQL plugin to Railway | Free, 2 min |
| 6 | Set .env.production variables in Railway | — |
| 7 | Build frontend: `npm run build` | — |
| 8 | Upload `/dist` folder to Railway static site | — |
| 9 | Point domain CNAME to Railway URL | — |
| 10 | Verify SSL (green 🔒 in browser) | Auto via Let's Encrypt |
| 11 | Test all pages + login | — |
| 12 | Create real CPA + municipality accounts | — |

### Pre-Deployment Security Checklist

| Item | Status |
|------|--------|
| SECRET_KEY is long random string (32+ chars) | ✓ |
| Database password is strong | ✓ |
| .env files NOT in GitHub (.gitignore) | ✓ |
| HTTPS enabled (not just HTTP) | ✓ |
| CORS only allows your domain | ✓ |
| Debug mode OFF in production | ✓ |
| Database not exposed to internet | ✓ |
| Upload folder not publicly accessible | ✓ |
| Rate limiting on login endpoint | ✓ |

### Backup Strategy

**Database:**
- Railway auto-backs up PostgreSQL daily
- Keep last 7 days
- Download monthly backup to your computer

**Uploaded Files:**
- Ministry CSV files in `/uploads`
- Back up weekly
- Consider AWS S3 for reliability

### Monitoring & Maintenance

**Ongoing:**
- Check Railway logs for errors daily first week
- Set up email alerts for crashes
- Monitor database size
- Review user activity

**Regular:**
- Weekly backup downloads
- Monthly security review
- Quarterly performance review

### Completion Checklist
- ✅ App accessible at real domain (https://)
- ✅ Login works from any computer
- ✅ File upload works on live server
- ✅ All pages load correctly
- ✅ Database persists between restarts
- ✅ SSL certificate active (green 🔒)
- ✅ CPA account created and working
- ✅ Minimum 1 municipality account created
- ✅ Error logs accessible
- ✅ Auto-deploy on git push works
- ✅ .env files not in GitHub
- ✅ Backup strategy in place

---

## Full Project Timeline

```
Phase 1 & 2: Backend engine + auth       ✅ DONE (30-40 hours)
Phase 3: CPA admin dashboard            ✅ DONE (20-30 hours)
Phase 4: Municipality portal             ✅ DONE (15-20 hours)
Phase 5: Explanations engine            ⏳ 8-12 hours
Phase 6: Reports & exports              ⏳ 6-10 hours
Phase 7: Deployment                     ⏳ 4-6 hours

TOTAL: ~85-115 hours from zero to live product
```

---

## How to Request Each Phase

### Phase 5 Request
```
"Phases 1-4 are done. Build Phase 5 — Explanations.

Files to create:
1. backend/data/purple_booklet_rules.py
2. backend/services/explanation_service.py
3. backend/models/explanation.py
4. backend/routes/explanations.py
5. frontend/src/components/portal/ExplanationBox.jsx

Make sure:
- All 5 budget topics have rules
- Auto explanations work for all line types
- CPA can edit + save custom explanations
- Municipality sees the final explanation"
```

### Phase 6 Request
```
"Phases 1-5 are done. Build Phase 6 — Reports & Exports.

First install: pip install reportlab openpyxl

Files to create:
1. backend/services/pdf_generator.py
2. backend/services/excel_generator.py
3. backend/routes/exports.py
4. frontend/src/components/ExportButtons.jsx

Test:
- PDF generates with Hebrew + RTL
- Excel has correct formatting + colors
- Buttons in both Phase 3 and Phase 4 pages
- Files download when clicked"
```

### Phase 7 Request
```
"Phases 1-6 are done locally. Help me deploy Phase 7.

I'm using Railway.app for hosting.
Domain: app.smarthub-dani.com

Files to create:
1. Dockerfile
2. docker-compose.yml
3. nginx.conf
4. .env.production (backend)
5. frontend/.env.production

Then walk me through:
- Railway setup
- GitHub push
- Domain pointing
- SSL certificate
- Testing on live server"
```

---

> **All 7 phases documented. Ready to execute whenever you are.**
