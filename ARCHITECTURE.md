# ARCHITECTURE.md — CPA Budget Platform

> **Step 3 output.** Technical blueprint translating `PRD.md` (v1.0 scope) into
> concrete schema deltas, component structure, tech-stack recommendations, and
> deployment plan. Owner: dimza. Revision: 2026-04-19.

---

## 1. Guiding principles (non-negotiable)

1. **Additive schema.** Never drop columns or tables; ingestion history must
   survive. Migrations add, rename carefully, never destroy.
2. **Hebrew-first, RTL-first.** Every new UI component ships RTL-native.
3. **Stateless backend.** The DB is the only source of truth. No in-memory
   caches that change behavior.
4. **Invariant tests live forever.** Phase 4.3 property tests (CHESHBONIT ≡
   detail sum per code) must stay green on every PR.
5. **No permanent deletes.** Soft-delete with `deleted_at`; Ministry data is
   historical and auditable.
6. **One file, one concern.** Routes thin; services do the work; models only
   describe shape.

---

## 2. Current architecture (what we have)

```
┌───────────────────────────────────────────────────────────────┐
│                        Browser (Hebrew RTL)                    │
│  React 18 + Vite + Tailwind · axios · react-router             │
│  Pages: Portal* (muni) · Admin* (CPA)                          │
└──────────────────────────▲────────────────────────────────────┘
                           │ HTTPS / JSON, JWT in Authorization
┌──────────────────────────┴────────────────────────────────────┐
│                       FastAPI backend                          │
│  backend/main.py                                               │
│  ├─ routes/        (thin HTTP layer — 18 files)                │
│  ├─ services/      (business logic — 18 files)                 │
│  ├─ models/        (SQLAlchemy ORM)                            │
│  └─ database.py    (engine + Session)                          │
└──────────────────────────▲────────────────────────────────────┘
                           │ SQLAlchemy
┌──────────────────────────┴────────────────────────────────────┐
│                       SQLite                                   │
│  /tmp/cpa_data/cpa.db                                          │
│  Tables: monthly_runs, budget_lines, variance_explanations,    │
│  transport_routes, class_enrollment, staff_positions,          │
│  municipalities, users, ingestion_warnings, audit_logs…        │
└───────────────────────────────────────────────────────────────┘
```

**Strengths**: simple, deployable anywhere, tests green, invariants hold.

**Scale ceiling**: SQLite is file-locked on writes. Single backend process =
fine for 1 CPA firm × 20 munis × 12 runs/year = ~240 runs/year. Multi-firm
SaaS needs Postgres.

---

## 3. Data model — deltas for v1.0

### 3.1 New tables

#### `cpa_firms`
Scopes everything for multi-tenant SaaS. Every user, muni, and run belongs to
a firm (except the super-admin).

```python
class CpaFirm(Base):
    __tablename__ = "cpa_firms"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)         # firm legal name
    display_name = Column(String(255), nullable=True)  # on letterhead
    logo_path = Column(String(500), nullable=True)     # uploaded PNG/SVG
    letterhead_footer = Column(Text, nullable=True)    # Hebrew address + license #
    signatory_name = Column(String(255), nullable=True)   # default signer on PDFs
    signatory_title = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    deleted_at = Column(DateTime, nullable=True)       # soft delete
```

Add `cpa_firm_id` foreign key (nullable for backward compat) to:
- `users`
- `municipalities` (a muni is audited *by* a firm)

Backfill rule: all existing rows get `cpa_firm_id = 1` (the implicit default
firm); we create that firm on migration.

#### `explanation_states`
State machine for M5 (draft → submitted → approved → locked).

```python
class ExplanationState(Base):
    __tablename__ = "explanation_states"
    id = Column(Integer, primary_key=True)
    explanation_id = Column(Integer, ForeignKey("variance_explanations.id"),
                            nullable=False, index=True)
    state = Column(String(32), nullable=False)  # draft|submitted|approved|locked
    actor_user_id = Column(Integer, ForeignKey("users.id"))
    note = Column(Text, nullable=True)           # optional comment on transition
    created_at = Column(DateTime, server_default=func.now())
```

Add `current_state` column to `variance_explanations` (denormalized pointer to
the most recent transition for fast reads).

#### `meitar_snapshots`
Persists what the user pasted/uploaded from MEITAR so parity checks are
reproducible.

```python
class MeitarSnapshot(Base):
    __tablename__ = "meitar_snapshots"
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("monthly_runs.id"), nullable=False, index=True)
    source = Column(String(32))  # "paste" | "upload" | "scrape"
    raw_text = Column(Text)      # what we received
    parsed_rows = Column(JSON)   # [{topic_code, amount}, …]
    created_at = Column(DateTime, server_default=func.now())
```

#### `firm_notifications`
Email + in-app notification queue (for M5 workflow transitions).

```python
class FirmNotification(Base):
    __tablename__ = "firm_notifications"
    id = Column(Integer, primary_key=True)
    cpa_firm_id = Column(Integer, ForeignKey("cpa_firms.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    kind = Column(String(64))        # explanation_submitted, etc.
    payload = Column(JSON)
    read_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
```

### 3.2 Column adds (no drops)

- `users`: add `cpa_firm_id`, `default_landing_page` ("dashboard"|"muni-list").
- `municipalities`: add `cpa_firm_id`, `cluster` (socioeconomic cluster 1–10
  from the Ministry purple booklet), `student_total` (current-year total for
  benchmarking).
- `variance_explanations`: add `current_state` (string), `approved_at`,
  `approved_by_user_id`.
- `monthly_runs`: add `reconciliation_status` (string:
  `pending|reconciled|mismatch`), `meitar_parity_status`.

### 3.3 Migration tooling

Switch to **Alembic** for versioned migrations. Today schema seems to be
created via `Base.metadata.create_all`, which is fine for dev but dangerous in
prod (no rename, no column type change). Initial alembic revision = current
schema; each future change = named revision.

---

## 4. Backend — new endpoints

All under `/api`, JWT-authed, scoped by `cpa_firm_id` for non-super-admins.

### 4.1 M1 — multi-muni dashboard

```
GET /api/cpa/dashboard
→ {
    firm: {...},
    municipalities: [
      {
        id, name, cluster,
        latest_run: {id, period_year, period_month},
        reconciliation_status: "reconciled" | "mismatch" | "pending",
        meitar_parity_status: "ok" | "mismatch" | "unknown",
        unexplained_topic_count: int,
        days_since_last_report: int,
      },
      …
    ]
  }
```

Implementation: add `backend/routes/cpa.py` + `backend/services/dashboard.py`.

### 4.2 M2 — MEITAR parity

```
POST /api/analytics/meitar-parity/{run_id}   (paste/upload snapshot)
GET  /api/analytics/meitar-parity/{run_id}   (get latest parity result)
→ {
    snapshot: {...},
    by_topic: [
      {topic_code, our_amount, meitar_amount, delta, status: "ok"|"mismatch"},
      …
    ],
    overall_status: "ok" | "mismatch",
  }
```

Implementation: add `backend/services/meitar_parity.py` with a parser for the
MEITAR CSV export format + a scraping fallback.

### 4.3 M4 — CPA firm branding

```
GET /api/cpa-firm/me
PATCH /api/cpa-firm/me        (update name, signatory, letterhead)
POST /api/cpa-firm/me/logo    (multipart upload)
```

PDF generator reads firm branding before rendering. Logo served from
`/static/firm-logos/{firm_id}.{ext}`.

### 4.4 M5 — explanation workflow

```
POST /api/explanations/{id}/transition
  body: {to_state: "submitted"|"approved"|"locked", note?: string}
```

Rule matrix enforced server-side:
- `draft → submitted`  : muni role.
- `submitted → approved` : CPA (admin) role.
- `approved → locked`  : CPA (admin) role, irreversible until new month.
- any → `draft`        : admin only, for corrections.

Triggers a `FirmNotification` row + (async) email.

### 4.5 M3 — accessibility (backend side)

- Replace ReportLab with **WeasyPrint** in PDF/UA mode (tagged PDF, proper
  table semantics, alt text on embedded charts). Charts become inline SVG
  with `<title>` and `<desc>` instead of rasterized images.
- Or keep ReportLab but add a post-process pass with `pikepdf` to add
  `/StructTreeRoot`, `/MarkInfo`, and language metadata. More work, less
  disruptive.

Recommendation: **WeasyPrint**. We're already HTML-rendering in the frontend;
reusing the same HTML → tagged-PDF path is cleaner than maintaining two
parallel layouts.

---

## 5. Frontend — component tree for v1.0

```
src/
├── App.jsx                            (router)
├── layouts/
│   ├── AdminLayout.jsx                (existing)
│   └── PortalLayout.jsx               (existing)
├── pages/
│   ├── cpa/
│   │   ├── CpaDashboardPage.jsx       (NEW — M1 multi-muni overview)
│   │   └── CpaFirmSettingsPage.jsx    (NEW — M4 branding)
│   ├── AdminBudgetDetailPage.jsx      (existing — CRLF! see HANDOFF §3)
│   ├── PortalBudgetPage.jsx           (existing)
│   └── … (all other existing pages)
├── components/
│   ├── budget/                        (existing — 3.1/3.2/3.3 IIFEs)
│   ├── dashboard/
│   │   ├── MuniStatusRow.jsx          (NEW)
│   │   ├── ReconciliationBadge.jsx    (NEW — green/yellow/red chip)
│   │   └── MeitarParityBadge.jsx      (NEW)
│   ├── explanations/
│   │   └── StateTransitionBar.jsx     (NEW — draft/submitted/approved/locked)
│   ├── a11y/
│   │   └── SkipToContentLink.jsx      (NEW — IS 5568 keyboard nav)
│   └── ui/                            (existing primitives)
├── services/
│   └── api.js                         (extend with cpaAPI, parityAPI)
├── hooks/
│   ├── useCurrentFirm.js              (NEW)
│   └── useA11yAudit.js                (NEW — dev-time axe-core integration)
└── i18n/
    └── he.js                          (move strings out of JSX — prep for v2)
```

**A11y tooling**: add `@axe-core/react` in dev; `eslint-plugin-jsx-a11y` in CI.

**Keep CRLF discipline** on `AdminBudgetDetailPage.jsx` (see HANDOFF §3).

---

## 6. Tech stack — recommendations

### 6.1 Keep as-is (don't rewrite what works)

- FastAPI, SQLAlchemy, pydantic, pytest.
- React 18, Vite, Tailwind, axios, react-router.
- JWT auth via `AuthService.create_token`.
- pytest for backend tests.

### 6.2 Add for v1.0

- **Alembic** — database migrations.
- **WeasyPrint** — replace ReportLab for tagged PDF output.
- **@axe-core/react** + `axe-core` in CI — accessibility enforcement.
- **Playwright** — end-to-end browser tests (currently only API-level).
- **ruff** — Python linting + formatting (single tool).
- **python-dotenv** — if not already; centralize env.

### 6.3 Plan for v1.1 (not v1.0)

- **PostgreSQL** — migrate once we exceed 1 CPA firm. SQLAlchemy is
  dialect-agnostic; the switch is mostly a URI change + Alembic re-baseline.
- **Redis** — only if we add async jobs (MEITAR scraping, email notifications).
  v1.0 can run notifications inline; v1.1 moves them to a queue.
- **OpenTelemetry** — tracing once we're multi-tenant.

---

## 7. Deployment plan

### 7.1 v1.0 target topology

```
┌────────────────────────────────────────────────────────┐
│  nginx (TLS, static)                                   │
│    ↓ /api → uvicorn (gunicorn -k uvicorn.workers)      │
│    ↓ /    → static Vite build                          │
├────────────────────────────────────────────────────────┤
│  single VM (Ubuntu 22.04, 2 vCPU / 4 GB)               │
│  /var/lib/cpa/cpa.db       (SQLite, WAL mode)          │
│  /var/lib/cpa/uploads/     (HORADA ZIPs, quarantined)  │
│  /var/lib/cpa/firm-logos/                              │
│  nightly: restic → S3-compatible (Wasabi or similar)   │
└────────────────────────────────────────────────────────┘
```

### 7.2 Hosting options (to be confirmed with user — PRD §9 Q2)

- **Azure Israel Central** (Tel Aviv region) — best for data-residency story
  with Israeli public bodies.
- **AWS eu-south-1 (Milan)** — cheaper; acceptable if no data-residency
  mandate.
- **On-prem at CPA firm** — single-VM setup above works unchanged; we hand
  them a `docker-compose.yml` and a runbook.

### 7.3 CI/CD

- GitHub Actions:
  - `lint`: ruff + eslint.
  - `test`: pytest + vitest.
  - `a11y`: axe-core on a built frontend.
  - `build`: build backend wheel + frontend static.
  - `deploy`: ssh + `docker compose pull && up -d` for staging;
    manual-approve gate for prod.
- Blue-green not needed at v1.0 volume; simple restart acceptable.

### 7.4 Backups

- SQLite: `sqlite3 .backup` nightly → encrypted with restic → offsite bucket.
- Uploads: rsync / restic same schedule.
- **Test restore every month.** Backups you haven't restored are hope, not a
  plan.

---

## 8. Security posture

- All secrets from env, never in git; rotated quarterly.
- JWTs short-lived (1h) + refresh token (30d, revocable).
- Role matrix: `super_admin` | `cpa_admin` (firm-scoped) | `muni_user`
  (muni-scoped).
- Every write logged through `audit_logger.py`.
- Upload quarantine: HORADA ZIPs stored under `uploads/quarantine/{firm_id}/…`;
  virus-scanned (ClamAV) before parser opens them.
- No PII leaves the Israeli region if hosted in-region.
- Rate-limit login endpoint (10/min/ip).

---

## 9. Testing strategy (v1.0)

- **Unit**: pure functions in `services/` — variance classifier, parser,
  student_count_delta, meitar_parity parser.
- **Integration**: one real HORADA ZIP → full ingestion → assert invariants.
  Already present as Phase 4.1; extend with one `Horada (3).zip`-sized ZIP
  per year.
- **Invariants**: Phase 4.3 property tests — CHESHBONIT ≡ detail sum per
  code, for every run ingested.
- **API**: FastAPI TestClient, covering every new endpoint in §4.
- **E2E**: Playwright — headless Chrome in Hebrew locale, walks CPA through:
  upload ZIP → reconcile → explain → submit → approve → download PDF.
- **A11y**: axe-core CI assertion: zero WCAG 2.0 AA violations on every
  page listed in §5.

---

## 10. Ordering & effort estimate (v1.0)

| # | Work                                        | Effort | Blocks |
|---|---------------------------------------------|--------|--------|
| 1 | Alembic baseline + `cpa_firms` migration    | 0.5 d  | 2,3,4 |
| 2 | M4 firm branding (endpoints + upload + PDF header) | 1.5 d  | 5 |
| 3 | M5 explanation workflow (state machine + UI bar)   | 2 d    | 6 |
| 4 | M1 multi-muni dashboard (endpoint + page)   | 2 d    | — |
| 5 | M2 MEITAR parity (parser + endpoint + badge)| 2 d    | — |
| 6 | M3 a11y sweep: WeasyPrint + axe-core CI + fixes    | 3 d    | launch |
| 7 | Playwright E2E happy path                   | 1 d    | launch |
| 8 | External IS 5568 audit + fixes              | 2 d    | launch |
| 9 | Production VM provision + CI deploy         | 1 d    | launch |

**Total**: ~15 working days (~3 weeks). Plus design-partner onboarding and
iteration — call it 6–8 weeks from kickoff to first paying firm.

---

## 11. Migration paths for later (v1.1+)

When a 2nd CPA firm signs:
1. Alembic migration: add Postgres-specific indexes; switch `DATABASE_URL`.
2. Data migration: `pgloader` from SQLite → Postgres; invariants re-verified.
3. Backend: no code changes — SQLAlchemy abstracts the dialect.
4. Infra: add managed Postgres; decommission SQLite file.

When notifications volume grows:
1. Introduce Redis + RQ or Celery.
2. Move MEITAR scraping + email send out of request path into async workers.

When we need audit-grade accessibility certification:
1. Externally audit by IS 5568 auditor (~15–25K NIS one-off).
2. Annual re-audit budgeted in pricing.

---

**Hand-off bundle for the autonomous coding agent (OpenClaw or successor)**:

```
HANDOFF.md              ← what exists, gotchas, smoke tests
DATA_IMPROVEMENT_PLAN.md← the ingestion plan (done, but shows history)
MARKET_RESEARCH.md      ← why we're building this
PRD.md                  ← what to build next and why
ARCHITECTURE.md         ← how to build it (this file)
```

Those five files are enough for any competent AI or engineer to pick up and
ship v1.0 without re-deriving the project.
