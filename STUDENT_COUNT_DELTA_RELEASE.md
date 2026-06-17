# Student-Count Delta Engine — Release Note

**Feature:** Month-over-month variance driver classification for pupil-driven
Ministry of Education budget codes (e.g., 003 גני ילדים, 052 הסעות, חינוך
מיוחד / חטיבה עליונה items whose allocation scales with the מצבת תלמידים
roster on the 25th-of-month cut-off).

## הערה בעברית (Release note in Hebrew)

נוסף מנוע *דלתא מספר ילדים*: עבור כל שורת תקציב לקוד המבוסס על מספר
תלמידים, המערכת משווה אל הריצה הקודמת לאותו חודש תחולה, מחשבת כמה מהשינוי
בסכום מוסבר על-ידי השינוי במספר הילדים, ומסווגת את השורה כ-"שינוי ממספר
ילדים", "שינוי בנוסחה/תעריף", או "מעורב". בעמוד תקציב חודשי (פורטל + CPA)
מופיע צ'יפ 👥 בסעיף "מה השתנה החודש?" עם ההסבר המלא ב-tooltip, ויש תיבת
סימון *"הצג רק שינויים שנגרמו ממספר ילדים"* לסינון. בתצוגת ה-CPA נוסף תג
צבעוני של סוג הגורם (ירוק/כחול/ענבר).

## What's new

- **`GET /api/budget/runs/{run_id}/student-count-deltas?municipality_id=…`**
  — per-code deltas (prev/curr count, delta, expected-from-count, explained
  amount, explained ratio, residual, and driver classification). RBAC uses the
  existing `require_municipality_access`. Sorted by `|delta_amount|` DESC.

- **New DB column** `budget_lines.variance_driver` (nullable, indexed) — one
  of `student_count`, `formula_or_rate`, `mixed`, or `NULL`. ALTER TABLE
  migration wired into `backend/utils/migrate_users_table.py`.

- **Hebrew explanation prefix** automatically prepends to explanation text
  when a delta has a meaningful signal. Three templates:
  - `מספר ילדים: 100 → 120 (+20). השפעה משוערת על הסכום: +₪20,000 ₪ מתוך +₪20,000 ₪ (100%).`
  - `מספר ילדים לא השתנה מהותית — השינוי נובע מגורם אחר.`
  - `חלק מהשינוי נובע משינוי במספר ילדים (100 → 110, +10); היתר נובע מגורם אחר.`

- **UI** — `<StudentCountDeltaChip>` appears in the *"מה השתנה החודש?"* block
  on both `PortalBudgetPage` and `AdminBudgetDetailPage`. Admin view adds the
  colored driver badge (`showDriverBadge`). A checkbox filter hides rows whose
  driver is not `student_count` so reviewers can focus on roster-driven
  movement.

## Policy knobs

Defined in `backend/utils/variance_thresholds.py`:

- `STUDENT_COUNT_DOMINANT_THRESHOLD = 0.80`
- `STUDENT_COUNT_NEGLIGIBLE_THRESHOLD = 0.20`

Tune here (not in service code) to adjust sensitivity.

## Tests

- `tests/student_count_delta/test_student_count_delta.py` — 10 unit tests for
  the engine (prior run selection, driver scenarios, None/zero edge cases,
  period_month scoping).
- `tests/student_count_delta/test_variance_driver_classifier.py` — 15 tests
  covering threshold classification and Hebrew prefix builder.
- `tests/integration/test_student_count_deltas_api.py` — 6 integration tests
  for the endpoint (RBAC, empty-when-no-prior, sorting, driver classification
  end-to-end).
- `frontend/src/__tests__/components/StudentCountDeltaChip.test.jsx` — 8
  component tests (renders/hides, green/red styling, tooltip content, driver
  badge visibility, mixed/formula_or_rate copy).

All 25 backend unit tests pass (`pytest tests/student_count_delta/`), and all
8 frontend component tests pass (`vitest run StudentCountDeltaChip`).

## Files touched

- `backend/models/budget_line.py` — added `variance_driver` column
- `backend/utils/migrate_users_table.py` — ALTER TABLE entry
- `backend/utils/variance_thresholds.py` — **NEW**
- `backend/services/student_count_delta.py` — **NEW**
- `backend/services/variance_driver_classifier.py` — **NEW**
- `backend/services/explanation_generator.py` — `prepend_student_count_prefix`
- `backend/routes/budget.py` — `GET /student-count-deltas` endpoint
- `frontend/src/services/api.js` — `budgetAPI.getStudentCountDeltas`
- `frontend/src/components/common/StudentCountDeltaChip.jsx` — **NEW**
- `frontend/src/pages/PortalBudgetPage.jsx` — chip + filter
- `frontend/src/pages/AdminBudgetDetailPage.jsx` — chip + filter + driver badge

## Rollout checklist

1. Run migrations (`alembic upgrade head` or the in-app migration util that
   calls `migrate_users_table`).
2. Restart backend.
3. Deploy frontend — no breaking API changes.
4. Verify by loading a municipality month with a prior run: the chip should
   appear in the "What changed this month" block for pupil-driven codes.

## Known limitations

- The engine relies on `num_children` being populated on budget lines. Lines
  where ingestion didn't capture the count are silently skipped.
- Comparison is to the single most recent prior run for the same
  `period_month`; multi-run averaging is out of scope.
- No driver label is emitted when both `delta_amount == 0` and
  `delta_children == 0` (nothing to explain).
