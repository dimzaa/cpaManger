# HANDOFF — CPA Budget Platform

> Purpose: if a new AI opens this repo cold, this single file should give it enough
> context to continue the work correctly, without re-discovering the project or
> breaking invariants. Read this file first, then `DATA_IMPROVEMENT_PLAN.md`, then
> jump into code.

---

## 1. What this project is (in one paragraph)

This is a full-stack web platform that helps **Israeli CPAs / municipal accountants**
review and reconcile the **monthly education budget settlement** that the Israeli
**Ministry of Education (משרד החינוך)** sends to municipalities. Each month the
Ministry publishes a ZIP of CSV-like files ("HORADA" / הוראה) containing the
breakdown of how much the Ministry pays the municipality for every budget topic
(תקציב / נושא) — kindergartens, special-ed transportation, high-school tuition,
after-school clubs, etc. — plus detail tables that explain how the amounts were
computed (per-class enrollment, per-institution staff positions, per-route
kilometres, etc.). Our platform ingests those ZIPs, reconciles the totals against
the Ministry's summary ("חשבונית" / invoice), stores structured per-line detail,
computes variance drivers vs. the previous month, lets the municipality supply
written explanations for each variance, and produces PDF/CSV reports. The CPA
(accountant) uses the "admin" view; the municipality uses the "portal" view.

---

## 2. Tech stack at a glance

| Layer     | Tech                                                   |
|-----------|--------------------------------------------------------|
| Backend   | Python 3.9+ / FastAPI / SQLAlchemy / pydantic / pytest |
| DB        | SQLite (local dev, actual file below) — SQLAlchemy models are DB-agnostic |
| Frontend  | React 18 + Vite + Tailwind CSS, Hebrew RTL (`dir="rtl"`) |
| Auth      | JWT via `backend/services/auth.py` (`AuthService.create_token(user_id, email, role, municipality_id)`) |
| PDF/CSV   | `backend/services/pdf_generator.py`, export routes in `backend/routes/export.py` |
| Dev ports | Backend :8000, Frontend :5173                          |

Launch (already scripted on Windows via PowerShell):
```
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
# in parallel
cd frontend && npm run dev
```

---

## 3. IMPORTANT environment gotchas (read before touching anything)

These already bit us. Don't repeat.

1. **The live SQLite DB lives at `/tmp/cpa_data/cpa.db`**, NOT at the project
   root. `DATABASE_URL` in env points there. The `cpa.db` sitting at the repo
   root is a stale copy that was used to seed `/tmp/cpa_data/cpa.db`. If
   `/tmp/cpa_data` gets wiped, restore with:
   ```
   mkdir -p /tmp/cpa_data && cp /sessions/brave-affectionate-darwin/mnt/cpa/cpa.db /tmp/cpa_data/cpa.db
   ```
   Any Python snippet that opens the DB directly must use `/tmp/cpa_data/cpa.db`
   or import `backend.database`. Opening the file at project root may fail with
   `sqlite3.OperationalError: unable to open database file` because of Windows
   perms that carried over.

2. **Line endings**:
   - `frontend/src/pages/PortalBudgetPage.jsx` → LF. Edit tool works fine.
   - `frontend/src/pages/AdminBudgetDetailPage.jsx` → **CRLF**. The Edit tool
     will fail on unique-string matches if you pass LF. For this one file, use
     Python binary mode:
     ```python
     with open(path, 'rb') as f: b = f.read()
     b = b.replace(b'old_bytes_with_\\r\\n', b'new_bytes_with_\\r\\n')
     with open(path, 'wb') as f: f.write(b)
     ```
   - If you create a brand-new Jinja-style string block with newlines,
     `.encode('utf-8').replace(b'\n', b'\r\n')` first, then splice.

3. **Active test data** (as of 2026-04-18):
   - Municipality id = **4** (חיפה).
   - Runs of interest: **run 10 (2026-03)**, **run 12 (2026-04)**,
     **run 13 (2026-02)**.
   - These are the only rows we've been hitting in smoke tests. If someone
     re-seeds the DB, those IDs can shift — re-check with
     `SELECT id, municipality_id, period_year, period_month FROM monthly_runs ORDER BY id;`.

4. **No sample ZIP at the repo root by default**. The test fixtures we use are
   `Horada (2).zip` and `Horada (3).zip` which live under the user's local
   folder, not in the repo. If you need to regression-test ingestion, generate
   mock data with `backend/sample_data/mock_generator.py`.

5. **Do not permanently delete anything**. The user cares about data safety.
   Migrations are additive; `budget_lines` rows accumulate; new line types are
   new enum values, never a rename of old ones.

---

## 4. Directory map (the stuff that matters)

```
cpa/
├── backend/
│   ├── main.py                      # FastAPI app factory + router mounting
│   ├── database.py                  # engine / Base / SessionLocal
│   ├── config.py                    # settings, DATABASE_URL
│   ├── models/
│   │   ├── monthly_run.py           # one row per (muni, year, month)
│   │   ├── budget_line.py           # the main fact table — one row per ministry topic/sub-line
│   │   ├── variance_explanation.py  # muni-typed narrative for a topic code
│   │   ├── municipality.py, user.py
│   │   ├── transport_route.py       # Phase 2.4 — per-route HASMASLULIM detail
│   │   ├── class_enrollment.py      # Phase 2.1 — per-class ICHLUSKITOT detail
│   │   └── staff_position.py        # Phase 2.2 / 2.3 — per-institution FTEs
│   ├── routes/
│   │   ├── upload.py                # ZIP ingestion entry-point
│   │   ├── budget.py                # budget lines CRUD, monthly summaries
│   │   ├── analytics.py             # variance drivers, formula-drivers, transport-routes
│   │   ├── explanations.py          # narrative per code per month
│   │   ├── reports.py, export.py    # PDF & CSV
│   │   ├── ministry.py              # purple-booklet reference
│   │   ├── auth.py, municipalities.py, runs.py, etc.
│   ├── services/
│   │   ├── file_parser.py           # ZIP → DB ingestion; prepare_* per Ministry CSV
│   │   ├── cross_reference.py       # CHESHBONIT tie-out
│   │   ├── variance_driver_classifier.py  # rate Δ vs volume Δ attribution
│   │   ├── student_count_delta.py   # enrollment Δ explainer (aggregate + per-class)
│   │   ├── smart_explanation_real.py, explanation_generator.py
│   │   ├── pdf_generator.py, audit_logger.py, auth.py
│   │   └── ...
│   └── sample_data/mock_generator.py
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── PortalBudgetPage.jsx         # muni-side budget detail (LF)
│   │   │   ├── AdminBudgetDetailPage.jsx    # CPA-side budget detail (CRLF!)
│   │   │   ├── PortalAnalyticsPage.jsx, AdminAnalyticsPage.jsx
│   │   │   ├── ReportsPage.jsx, AdminReportsPage.jsx
│   │   │   └── ... (see list above)
│   │   ├── services/api.js          # axios client; has budgetAPI, analyticsAPI, ministryAPI, reportsAPI, explanationsAPI
│   │   └── components/, App.jsx
│   └── vite.config.js
├── DATA_IMPROVEMENT_PLAN.md         # ← THE plan. Canonical phase list.
├── HANDOFF.md                       # ← you are here
├── README.md                        # older, partly stale setup doc
├── START_HERE.md                    # one-pager with PowerShell commands
└── tests/                           # pytest
```

---

## 5. Data model — the short version

- **`monthly_runs`** = one row per (municipality, period_year, period_month). The
  unit of a "month's submission" from the Ministry. Everything joins on `run_id`.
- **`budget_lines`** = the fact table. Each row has a `topic_code` (Ministry's
  "purple booklet" code — see §7), an `amount`, a `line_type` (see enum below),
  plus metadata. Sum of `budget_lines.amount` per topic should reconcile to the
  CHESHBONIT total for that topic.
- **`line_type` values** (ingestion source):
  `gy`, `sharatim`, `mutavim`, `yadaniim`, `moadon`, `sacal`, `mucarim`,
  `hasaot`, `shefi`, `cheshbonit` (opaque roll-up — should be rare after Phase 1).
- **`transport_routes`** (model in `backend/models/transport_route.py`, already
  read — see below) = per-route HASMASLULIM detail. Key fields: `route_number`,
  `direction`, `vehicle_code`, `company_code/name`, `calculated_total`,
  `period_month`, `period_year`. **No `הפרש` column** — these are current-state
  rows, not deltas. De-dup by `(route_number, direction, vehicle_code)` when
  building audit views; aggregate `calculated_total` across months within a run.
- **`class_enrollment`** = per-class × 12 monthly enrollment counts.
- **`staff_positions`** = per-institution × per-role × 12 monthly FTEs.
- **`variance_explanations`** = free-text narrative a municipality writes for a
  given (run, topic_code) explaining why the amount changed vs. prior month.

---

## 6. Completion status — what has been done

Every phase in `DATA_IMPROVEMENT_PLAN.md` is **done**:

| Phase | Status | What it delivered                                                             |
|-------|--------|-------------------------------------------------------------------------------|
| 1.1 YADANIIM       | ✅ | `prepare_yadaniim()` → closes codes 140 & 631. `line_type='yadaniim'`.   |
| 1.2 MOADON         | ✅ | `prepare_moadon()` → per-club rows under code 242. `line_type='moadon'`. |
| 1.3 SACAL          | ✅ | `prepare_sacal()` → per-class × subject rows under code 1. `sacal`.      |
| 2.1 ICHLUSKITOT    | ✅ | `class_enrollment` table + ingestion.                                    |
| 2.2 MISROT         | ✅ | `staff_positions` table (scope=`institution`).                           |
| 2.3 MISROTGY       | ✅ | `staff_positions` table (scope=`gy`).                                    |
| 2.4 HASMASLULIM    | ✅ | `transport_routes` table + ingestion.                                    |
| 3.1 Expandable rows | ✅ | Per-topic line detail toggle in Portal+Admin budget pages.              |
| 3.2 Formula-variance drill-down | ✅ | Drivers endpoint + UI: enrollment Δ × prev_rate + rate Δ × curr_kids + residual, with positions & per-institution enrollment tables. |
| 3.3 Route-level audit  | ✅ | `/api/analytics/transport-routes/{run_id}/{topic_code}` + UI modal only for topics 52/140. |
| 4.1 E2E ingestion test | ✅ | under `tests/`.                                                    |
| 4.2 Ingestion warnings | ✅ | structured reconciliation warnings table.                          |
| 4.3 Property tests     | ✅ | invariant tests for CHESHBONIT ≡ detail sum per code.              |

**100% of CHESHBONIT activity now has a detail-file breakdown**; there should be
effectively zero `line_type='cheshbonit'` rows on a healthy ingestion.

---

## 7. The "Purple Booklet" — Ministry topic codes

The Israeli Ministry of Education publishes an annual **"חוברת סגולה"** (purple
booklet) that defines every budget topic code, the formula used to compute the
payment, and the eligibility rules. We model a subset as reference data; the
codes we touch most:

| Code | Name (Hebrew)               | What it is                               |
|-----:|-----------------------------|------------------------------------------|
|    1 | שכ"ל על-יסודי               | High-school tuition (driven by SACAL)    |
|    3 | גני ילדים – שכר לימוד        | Kindergartens — tuition                  |
|   19 | גני ילדים – סייעות           | Kindergartens — assistant teachers       |
|   33 | גני ילדים – הסעות            | Kindergartens — transportation           |
|   52 | הסעות חינוך רגיל             | Regular-ed transportation (HASMASLULIM)  |
|  140 | הסעות ח.מיוחד                | Special-ed transportation                |
|  242 | מועדוניות ברשויות             | After-school clubs (driven by MOADON)    |
|  631 | תכנית ניצנים - גנ"י          | "Nitzanim" early-childhood program       |

When the new AI needs broader context, see §11 for search terms.

---

## 8. Backend API surface — what exists and how to smoke-test it

All under `http://localhost:8000`, prefixed `/api/...`. Authenticated endpoints
need a JWT:
```python
from backend.services.auth import AuthService
tok = AuthService.create_token(user_id=1, email="admin@cpa.gov.il",
                               role="admin", municipality_id=None)
# header: Authorization: Bearer <tok>
```

Key endpoints:

- `POST /api/upload/zip` — ingest a Ministry ZIP for a run.
- `GET /api/budget/{run_id}` — topic-level summary for a run.
- `GET /api/budget/{run_id}/topic/{topic_code}/lines` — all `budget_lines` for a topic (Phase 3.1).
- `GET /api/analytics/variance-drivers/{run_id}` — aggregate variance drivers.
- `GET /api/analytics/formula-drivers/{run_id}/{topic_code}` — **Phase 3.2**,
  returns enrollment Δ, positions Δ, rate Δ decomposition with
  `prev_rate_per_fte`, `curr_rate_per_fte`, `delta_rate_per_fte`, `kids_source`.
- `GET /api/analytics/transport-routes/{run_id}/{topic_code}` — **Phase 3.3**,
  only valid for `topic_code` in `{52, 140}`. Returns
  `{summary, by_company, by_vehicle, routes}`. Optional
  `period_month`/`period_year` filters.
- `GET /api/reports/{run_id}/pdf` and `/csv` — downloadable reports.
- `GET /api/ministry/topics` — purple-booklet reference.

Smoke-test snippet (bash):
```
TOK=$(python -c "from backend.services.auth import AuthService;print(AuthService.create_token(1,'admin@cpa.gov.il','admin',None))")
curl -s -H "Authorization: Bearer $TOK" http://localhost:8000/api/budget/10 | head -c 500
curl -s -H "Authorization: Bearer $TOK" http://localhost:8000/api/analytics/formula-drivers/10/3 | head -c 800
curl -s -H "Authorization: Bearer $TOK" http://localhost:8000/api/analytics/transport-routes/10/140 | head -c 800
```

Expected sanity numbers on **run 10 (muni 4, 2026-03)**:
- Topic **3** lines detail: 28 rows / ₪361,783.46.
- Topic **3** formula-drivers: delta ≈ −170,127 with rate_delta=7.33.
- Topic **19** rate_delta ≈ −45; topic **33** rate_delta ≈ 39.38.
- Topic **52** transport: 6 routes / ~₪97,570 / 1 company / 2 vehicle types.
- Topic **140** transport: 21 routes / ~₪825,443 / 2 companies / 4 vehicle types.
- Topic **3** on `/transport-routes` → HTTP 400 (correctly rejected).

If those numbers drift, investigate ingestion, don't "fix" the endpoint.

---

## 9. Frontend — where to wire UI changes

Budget detail lives in TWO pages that must stay feature-parity:

- `frontend/src/pages/PortalBudgetPage.jsx` — muni view. LF endings.
- `frontend/src/pages/AdminBudgetDetailPage.jsx` — CPA view. **CRLF endings**.
  Admin uses `Number(id)` from the route param for municipality id, Portal uses
  `selectedMunicipality` from auth context.

Both pages have three IIFE render blocks inside each topic row:
1. **Phase 3.1** — topic-line detail table (expandable rows).
2. **Phase 3.2** — formula-variance drill-down (KPI cards + positions table +
   per-institution enrollment table).
3. **Phase 3.3** — transport-route audit, only renders when
   `topicCode === '52' || topicCode === '140'`.

State stores: `formulaDrivers` and `transportAudit` as objects keyed by
`topicCode`; the toggle handlers `toggleFormulaDrivers(topicCode)` and
`toggleTransportAudit(topicCode)` lazy-load via `analyticsAPI.getFormulaDrivers`
/ `analyticsAPI.getTransportRoutes`.

API client: `frontend/src/services/api.js` exports
`budgetAPI, analyticsAPI, ministryAPI, reportsAPI, explanationsAPI`. The
analytics ones include `getFormulaDrivers` and `getTransportRoutes`.

---

## 10. What the website is **expected** to do (end-to-end)

This is the north star. If a change breaks any of these, stop.

1. **Upload a monthly Ministry ZIP** (HORADA file) for a given (municipality,
   year, month) and get every CSV/DAT inside parsed, normalized and stored.
2. **Reconcile** the detail files against the CHESHBONIT summary per topic code.
   Show a warning (ingestion_warnings table) if anything doesn't tie out within
   1 agora.
3. **Show a topic-level budget view** for any run: topic code, Ministry name,
   amount, Δ vs. prior month, with variance driver classification.
4. **Expand each topic** to see the underlying lines (per-institution,
   per-class, per-route, per-club — depending on line type).
5. **For formula-driven topics**, decompose the Δ into **enrollment Δ ×
   prev_rate** + **rate Δ × curr_kids** + residual, and surface the per-role FTE
   and per-institution enrollment changes that caused it.
6. **For transportation topics (52 / 140)**, show a route-level audit — which
   routes were added, dropped, or changed in cost; which vendors dominate; which
   vehicle classes.
7. **Let the municipality type a written explanation** per (run, topic) and have
   the CPA review/approve it.
8. **Generate a PDF / CSV monthly report** bundling the summary, the variance
   explanations, and the detail tables, that the CPA can deliver to the muni.
9. **Authenticate users**: admins (CPAs) see all munis; muni users see only
   their own municipality.
10. **Audit trail**: every important change is logged via `audit_logger.py`.
11. **Hebrew RTL throughout** — never introduce LTR layout or left-aligned text
    in primary data views.

If you find a request that conflicts with #5 (formula attribution math),
re-check `variance_driver_classifier.py` and `student_count_delta.py` — those
are the ground truth.

---

## 11. Internet search terms (for when context is missing)

### 🎯 Primary source — start here before Googling

**`https://apps.education.gov.il/mtrnet/`** — the Ministry of Education's
municipal-finance portal ("מטרנט"). This is the canonical source for topic-code
definitions, formula references, HORADA file structure, and monthly settlement
data. User flagged it explicitly: "goated site for info". Whenever there's a
question about what a Ministry field means, what a topic code represents, or
how a formula is supposed to work — **open this site first**, before any
third-party blog.

If the new AI needs to verify something about the Ministry's data semantics,
here are high-signal search phrases. These are English + Hebrew mixes on
purpose — the best sources are on the Ministry site and municipal finance blogs
in Hebrew.

- **Hebrew**: `חוברת סגולה משרד החינוך` (Ministry of Education purple
  booklet — defines topic codes and formulas).
- **Hebrew**: `הוראה תקציבית משרד החינוך חודשית` (monthly budget ordinance).
- **Hebrew**: `הסעות תלמידים חוזר מנכ"ל` (student transportation regs — for
  topics 52/140).
- **Hebrew**: `תכנית ניצנים משרד החינוך` (for code 631 semantics).
- **Hebrew**: `מועדוניות ברשויות משרד החינוך` (for code 242 semantics).
- **Hebrew**: `שכ"ל על-יסודי משרד החינוך` (for code 1 formula — SACAL).
- **English**: `Israel Ministry of Education municipal budget breakdown
  HASMASLULIM` — very niche; most hits will be Hebrew.
- **English**: `Israel kindergarten teacher ratio assistants funding formula`
  (for codes 3/19/33 context).
- **English**: `SOX-like audit evidence Israeli municipal education budget` — for
  audit workpaper framing.

Authoritative starting points: `edu.gov.il` (Ministry of Education) and the
individual municipality treasury pages. When in doubt, prefer primary sources
over blog posts.

---

## 12. How to verify everything still works (5-minute smoke test)

1. Make sure `/tmp/cpa_data/cpa.db` exists (see §3).
2. Start backend: `uvicorn backend.main:app --reload --port 8000`.
3. Mint an admin JWT (see §8) and hit:
   - `/api/budget/10` → expect ~20 topic rows for muni 4, period 2026-03.
   - `/api/budget/10/topic/3/lines` → 28 rows, sum ≈ 361,783.46.
   - `/api/analytics/formula-drivers/10/3` → JSON with `rate_delta_block`.
   - `/api/analytics/transport-routes/10/140` → JSON with ~21 routes.
   - `/api/analytics/transport-routes/10/3` → **400** (topic 3 isn't transport).
4. Build frontend: `cd frontend && npm run build` — must emit 0 errors.
5. Run tests: `pytest tests/` from repo root. All green.

If any of the above fail, DO NOT "patch around it" — diagnose. The numbers come
from real Ministry data; the user cares more about correctness than features.

---

## 13. Working principles the user cares about

- **Correct data over shipping features.** If a number looks wrong, stop and
  re-trace through the parser / DB before touching UI.
- **"All by order"** — go phase by phase in `DATA_IMPROVEMENT_PLAN.md`. Don't
  skip ahead.
- **Don't delete user data**, don't drop tables, don't invalidate prior runs.
  Migrations are additive.
- **Keep Hebrew UI, Hebrew labels, RTL layout.**
- **When editing `AdminBudgetDetailPage.jsx`, respect CRLF.** The Edit tool is
  not safe — use Python binary writes.
- **Use `web_search` / documentation** to confirm Ministry terminology before
  naming new fields in Hebrew. Don't invent.

---

## 14. If the user says something that doesn't match §10

Ask. The CPA's workflow evolves; if the next step looks unrelated (e.g.,
"add a chat feature") ask for scope before writing code. The user prefers
short clarifying questions (via the AskUserQuestion tool in Cowork mode) over
large wrong diffs.

---

## 15. Quick reference — most-opened files when debugging

- Variance math wrong → `backend/services/variance_driver_classifier.py`
  + `backend/services/student_count_delta.py`.
- Ingestion row count off → `backend/services/file_parser.py` `prepare_*`
  functions + `cross_reference.py`.
- Transport endpoint returning wrong totals → `_routes_by_key` in
  `backend/routes/analytics.py` (must aggregate by route key across months,
  not keep the largest row).
- Topic name/color missing in UI → `CODE_META` in
  `backend/routes/analytics.py`.
- Frontend shows stale data → `frontend/src/services/api.js` + React Query /
  useEffect dependency arrays in the matching page.
- Auth failing → `backend/services/auth.py` (`AuthService.create_token`
  signature) + `backend/routes/auth.py`.

---

Good luck. Be precise with numbers; be kind to the Hebrew text; and when in
doubt, read `DATA_IMPROVEMENT_PLAN.md` and ask the user before improvising.
