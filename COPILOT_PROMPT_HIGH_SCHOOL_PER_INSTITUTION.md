# Copilot Prompt — Per-Institution High-School (חטיבה עליונה) Breakdown

> Paste everything below the line into VS Code Copilot Chat. The prompt is self-contained: Copilot should rediscover the codebase itself so tokens aren't wasted on context I already gathered.

---

## Task

Add a **per-institution (per–סמל מוסד) breakdown view for high-school (חטיבה עליונה) budget lines** to this Israeli Ministry of Education budget app. Right now the UI aggregates budget by ministry code across the whole municipality. That's fine for elementary / kindergarten / services, because those codes are paid at the municipality level. But חט"ע money is allocated **per school (per מוסד)**, and local authority accountants need to see it broken out that way. This task builds that breakdown — backend model change, ingestion pipeline update, API endpoint, and a UI drill-down.

---

## Step 0 — Discover before coding (do NOT skip)

Before you plan or write a single line, run these discovery steps and include the findings in your plan.

1. **Map the budget-line schema.** Read `backend/models/budget_line.py`. Confirm it has `budget_topic`, `topic_code`, `amount`, `period_month`, `current_month`, `line_type`, `is_retro`, `num_children`, `participation_pct`. Confirm it does **not** yet have any institution / school / סמל מוסד column.
2. **Read the ministry-code catalog.** Open `backend/utils/seed_ministry_codes.py` and list every code whose `category` is `"חטיבה עליונה"` or whose `name_short` / `name_full` contains `חט"ע` / `חטיבה עליונה` / `על-יסודי` / `על יסודי`. Also include `"001"` (שכ"ל על-יסודי), `"035"`, `"071"`, `"173"`, `"237"`, `"361"`, `"456"`, `"611"`, `"654"`, `"660"`, `"707"`. These are the codes the per-institution breakdown applies to.
3. **Find the raw institution data.** Under `backend/uploads/` (or wherever `services/file_parser.py` reads from), the zipped `Horada` bundles contain CSVs. At least `SHARATIM.csv` (auxiliary staff per school) has `סמל מוסד` (institution code, typically 6 digits) and `שם מוסד` (institution name) columns. Grep all CSV-parsing code in `services/file_parser.py` for `סמל מוסד`, `שם מוסד`, and for any code that already reads per-school rows — even if it only uses the data transiently. Report every place it appears.
4. **Understand how lines are built today.** In `services/file_parser.py` trace the function that builds `BudgetLine` rows. Is there a loop that collapses per-school rows into a single per-municipality sum? Quote the exact lines.
5. **Check the UI.** Read `frontend/src/pages/PortalBudgetPage.jsx` and `frontend/src/pages/AdminBudgetDetailPage.jsx` — both already group codes by category (recent change). Note the current rendering of the `חטיבה עליונה` category so you know where to inject the drill-down.
6. **Check for an existing institutions table or model.** Grep for `institution`, `School`, `Semel`, `מוסד` in `backend/models/` and `backend/routes/`. Report nothing if nothing exists.

Pause after Step 0, print a short discovery summary (≤ 25 lines), then present the plan in Step 1. **Do not start implementation until I reply with "go".**

---

## Background — why this feature exists

Israeli high-school funding is not distributed by municipality; it is allocated per institution (per סמל מוסד / institution symbol) using a per-pupil "שכר לימוד" (tuition) model. The Ministry of Education's budget allocation mechanism for חטיבה עליונה ties hours and money to each school individually, based on size, nurturing index, class type (regular / small / affirmative-action), and study tracks (academic / technological). This is well documented in the Taub Center's research and in the Ministry's own tuition-funding documents:

- The Ministry's formula is **per-institution**, driven by the school's enrichment index (מדד טיפוח), number of pupils, and track mix; funds are transferred to the authority where the pupil studies **keyed to סמל מוסד**. ([Taub Center — Expenditure per Student in High Schools](https://www.taubcenter.org.il/en/research/highschool-expenditure/); [Ministry participation document — הִשתתפות משרד החינוך בתקציב הרשויות המקומיות והבעלויות, תשפ"א](https://meyda.education.gov.il/files/MinhalCalcala/hishtatfutmisrad_tashpa.pdf))
- For upper-secondary, "שכר לימוד" bundles **teaching hours, auxiliary-staff wages, and non-salary expenses**. That's why multiple ministry codes (e.g. `001`, `035`, `361`, `456`, `611`, `654`, `660`, `707`) all need to be attributable back to a specific סמל מוסד for audit. ([Avney Rosha high-schools budget summary, 2021](https://avneyrosha.org.il/wp-content/uploads/2024/11/high-schools-budget-2021.pdf))
- A high-school institution is defined as grades 9–12 or 10–12; several authorities run more than one חט"ע, so breakdown at the `סמל מוסד` level is the only way to reconcile what the Ministry paid per school versus what the authority expected. ([Taub Center policy paper, April 2024](https://www.taubcenter.org.il/wp-content/uploads/2024/03/Ed-expenditure-2024-ENG.pdf))
- The Knesset Research Center's budget-glossary confirms that per-institution teacher-hour standards are the primary lever the Ministry uses for upper-secondary funding, and that reporting responsibility rolls up from school principals to the authority. ([Knesset Research — מונחון לביאור תקציב מערכת החינוך](https://fs.knesset.gov.il/globaldocs/MMM/fc793c1b-6855-eb11-811a-00155d0af32a/2_fc793c1b-6855-eb11-811a-00155d0af32a_11_18149.pdf))

**Implication for the app:** today, if a municipality has three high schools (say סמל `317115`, `317230`, `317487`), the app shows one combined amount for code `001` / `035` / `361` / etc. The accountant has to open the raw CSV to see which school drove a change. After this change, the user can click into the חטיבה עליונה category and see, for each ministry code, a per-school mini-table.

---

## Spec

### 1) Data model

Add a new table `budget_line_institutions`:

```
id                  int  PK
budget_line_id      int  FK -> budget_lines.id  (on delete CASCADE), indexed
institution_code    str  (e.g. "317115")  — סמל מוסד, 6 digits typical, keep as STRING to preserve leading zeros
institution_name    str  nullable         — שם מוסד (best-effort from source CSVs)
amount              float                 — shekels attributed to this institution within the parent budget line
num_children        int  nullable         — per-school pupil count if available
participation_pct   float nullable        — per-school percentage if the CSV carries it
source_file         str  nullable         — which uploaded CSV the row came from (e.g. "SHARATIM.csv")
created_at          datetime  server_default now()
```

- Add `relationship("BudgetLine", back_populates="institution_breakdown")` on both sides.
- Do **not** delete existing `BudgetLine` fields. The per-line totals must still equal the sum of their institution rows (see tests).
- Register the new model in `backend/models/__init__.py`.
- `backend/database.py`'s `init_db()` must create the table on startup. Do **not** write a separate Alembic migration unless the project already uses Alembic (grep first).

### 2) Ingestion

In `services/file_parser.py`, wherever a `BudgetLine` is built for a code that matches the high-school set (see Step 0 item 2 for the authoritative code list), also build `BudgetLineInstitution` rows:

- If the source CSV has per-row `סמל מוסד` / `שם מוסד` columns, use them directly.
- If not, fall back to `SHARATIM.csv` (or whatever institution roster the bundle has) to get the list of institutions for this municipality, and distribute the total **proportionally to `num_children`** per institution if available, else split equally. Annotate `source_file = "proportional:<roster_file>"` in that case.
- Preserve the leading-zero convention already established for `topic_code` (`.astype(str)` then `zfill(3)` where applicable, but sources of סמל מוסד are already 6-digit strings — keep them as-is and never int-cast).
- If no institution data can be recovered for a line, skip the breakdown silently — do not fail the whole upload.
- The sum of child `amount` values must equal the parent `BudgetLine.amount` within ±0.01 shekel. Log a warning if not; do not throw.

### 3) API

Add to `backend/routes/budget.py` (or the closest existing router — grep for where per-line endpoints live):

```
GET /api/budget/runs/{run_id}/municipalities/{municipality_id}/institutions?topic_code={code}
```

Response shape:

```json
{
  "run_id": 42,
  "municipality_id": 7,
  "topic_code": "001",
  "topic_name": "שכ\"ל על-יסודי",
  "total": 184230.55,
  "institutions": [
    { "institution_code": "317115", "institution_name": "תיכון מקיף...", "amount": 84120.00, "num_children": 612, "participation_pct": null, "source_file": "SHARATIM.csv" },
    { "institution_code": "317230", "institution_name": "...",            "amount": 62110.55, "num_children": 451, "participation_pct": null, "source_file": "SHARATIM.csv" },
    { "institution_code": "317487", "institution_name": "...",            "amount": 38000.00, "num_children": 277, "participation_pct": null, "source_file": "SHARATIM.csv" }
  ]
}
```

Add a second endpoint returning the breakdown for **all** high-school codes in one call (for the drill-down panel):

```
GET /api/budget/runs/{run_id}/municipalities/{municipality_id}/high-school-breakdown
```

Response is a map keyed by `topic_code`, each value identical to the shape above. Keep payload size sane — this is bounded by ~15 codes × ~few dozen institutions.

Both endpoints must respect the existing auth / RBAC: only users who can already view that run for that municipality can see the breakdown.

### 4) UI

In `frontend/src/pages/PortalBudgetPage.jsx` **and** `frontend/src/pages/AdminBudgetDetailPage.jsx`, inside the `חטיבה עליונה` category card (already grouped — don't re-architect grouping), each budget-code row gets:

- A small `פירוט לפי מוסד ▾` button on the row (RTL layout — button on the left of the row).
- Clicking fetches the per-topic endpoint (lazy — don't preload all). Show a nested table under the row: columns `סמל מוסד | שם מוסד | מספר תלמידים | אחוז | סכום`, sorted by `amount` DESC.
- Row footer: `סה״כ: ₪{sum}` that must match the parent row's `amount` to the agora. If it doesn't, show a small `⚠` tooltip: `"סכום הפירוט אינו תואם לשורה — בדיקה נדרשת"`.
- Add one top-level category button `פירוט כל התיכון` that hits the all-codes endpoint and renders a wide table: institutions as rows, codes as columns, cells are amounts, plus a grand-total column on the far left (RTL).
- All Hebrew copy stays in Hebrew. Use the same Tailwind classes already used for category cards — do not introduce a new design system.
- If the breakdown endpoint returns 404 / empty (e.g. legacy runs ingested before this feature), render `אין פירוט לפי מוסד לריצה זו` in muted text. Never throw.

### 5) Admin view

In `AdminBudgetDetailPage.jsx` also add a read-only "Source of attribution" column to the nested table showing `source_file`. Regular users in the portal view don't need this — hide it behind a prop.

---

## Tests

Add in `backend/tests/` (or wherever existing pytest files live — grep):

- `test_high_school_breakdown_ingestion.py` — given a fixture ZIP containing `SHARATIM.csv` with 3 institutions and budget CSVs for codes `001`, `361`, `456`, assert the resulting `BudgetLineInstitution` rows sum to the parent `BudgetLine.amount` for each of those codes, and that non-high-school codes (e.g. `003` gan yeladim) produce **zero** institution rows.
- `test_high_school_breakdown_api.py` — seed a run with 2 municipalities and 2 institutions each, hit both endpoints, assert status, shape, sort order, and that a user scoped to one municipality cannot see another's data.
- `test_high_school_breakdown_fallback.py` — CSV without per-row `סמל מוסד` but with a roster and `num_children` → amounts must split proportionally; without `num_children` → equal split; without any roster → zero rows, upload still succeeds.
- Frontend: add one Vitest test per page (`PortalBudgetPage.test.jsx`, `AdminBudgetDetailPage.test.jsx`) with a mocked fetch returning the breakdown shape; assert the drill-down renders rows in descending amount order and the mismatch warning appears when the stub sum is off by 1 shekel.

Run `pytest backend/tests/ -q` and `cd frontend && npm test -- --run` and both must be green before you report done.

---

## What NOT to do

- Do **not** change `topic_code` format or touch the ministry-code seed. If you need to know which codes are חט"ע, read the seed — don't hard-code a list in more than one place; put it in `backend/utils/high_school_codes.py` and import from there in both the ingestion path and the router.
- Do **not** modify the shared category-grouping logic in the two pages — only add the drill-down inside the `חטיבה עליונה` card.
- Do **not** normalize or zero-pad `institution_code`. Real Israeli סמל מוסד values are 6-digit numeric strings but some historical schools have 5-digit codes; preserve whatever the source CSV gives you.
- Do **not** cascade-delete institution rows except when the parent `BudgetLine` itself is deleted. Reprocessing a run should wipe and rebuild both together inside one transaction.
- Do **not** add Alembic unless it's already in the repo.
- Do **not** add any new npm or pip dependencies unless absolutely necessary; the app is already React + Tailwind + FastAPI + SQLAlchemy + pandas.
- Do **not** emit `console.log` / `print` debug output in production paths. Use the existing logger (`backend/services/logger.py`).
- Do **not** change file-upload UX; ingestion must remain fully backward compatible with already-uploaded runs (those just won't have breakdown rows).

---

## Deliverables

1. A **plan** (≤ 40 lines) listing: discovery findings from Step 0, the files you will touch, the new files you will create, and the migration approach. **Pause here and wait for "go".**
2. Once approved, the actual changes, organized as separate logical commits if Copilot supports that: `feat(model): add BudgetLineInstitution`, `feat(ingest): build per-institution rows for חט"ע codes`, `feat(api): per-institution breakdown endpoints`, `feat(ui): per-institution drill-down in budget views`, `test: coverage for breakdown`.
3. All tests green. Paste the tail of the pytest + vitest output in the final message.
4. A short Hebrew release note (≤ 8 lines) that can be pasted into the changelog, explaining the new view for end users (accountants in the authority).

Begin with Step 0 now.
