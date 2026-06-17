# Data Improvement Plan — Ministry ZIP Ingestion

Status as of 2026-04-18. Focus: every remaining Ministry CSV, what it contains, and exactly what it buys us when wired in.

---

## Where we are now

The parser currently handles CHESHBONIT + GY003/019/033 + MUTAVIM + SHARATIM + SHEFI + HASAOT + MUCARIM with per-code tie-out. For muni 4 / 2026-03 that leaves **4 CHESHBONIT codes unresolved** (17 rows, ₪1,444,820 of activity):

| code | name                              | gap (₪)      | source of the gap              |
|-----:|-----------------------------------|-------------:|--------------------------------|
|    1 | שכ"ל על-יסודי (HS tuition)       | 1,097,653.22 | SACAL — ties exactly           |
|  140 | הסעות ח.מיוחד חיפה              |   231,993.57 | HASAOT (17,993.57) + YADANIIM (214,000) |
|  631 | תכנית ניצנים - גנ"י              |   100,530.40 | MUCARIM (-5,276.60) + YADANIIM (105,807) |
|  242 | מועדוניות ברשויות                |    14,642.39 | MOADON — ties exactly          |

Wire these three files in (YADANIIM, MOADON, SACAL) and every shekel of CHESHBONIT maps to a detailed line — zero opaque roll-ups.

---

## Phase 1 — Close the breakdown loop (highest value, lowest risk)

### 1.1 YADANIIM — manual advance payments
- **Schema**: `קוד נושא`, `סכום מחושב`, `נושא`, `סוג תשלום` (e.g. "מקדמת מערכת"), `סמל מוסד`
- **No הפרש column** — these are one-shot ad-hoc payments, not formula-driven deltas. The `סכום מחושב` IS the settlement value for this invoice.
- **Implementation**: new `prepare_yadaniim()` using `סכום מחושב` as amount. Tie-out logic becomes additive: allow detail files to combine with YADANIIM per code before comparing to CHESHBONIT gap.
- **Line type**: `yadaniim` — UI can show these as "Manual Advance" with the Ministry's `סיבת תשלום` (payment reason) in notes.
- **Payoff**: closes codes 140 and 631, totalling ₪319,807 of currently-opaque CHESHBONIT value.

### 1.2 MOADON — after-school clubs
- **Schema**: no `קוד נושא` (always maps to Ministry code 242 — מועדוניות ברשויות), has `הפרש מחושב`, per-club detail (סוג מועדונית, שעות הפעלה, מספר מועדוניות, אחוז השתתפות).
- **Implementation**: new `prepare_moadon()` that hard-codes `topic_code=242` and stores per-club rows. Each row becomes a `line_type='moadon'` budget line carrying club-type, hours, and count as structured metadata.
- **Payoff**: code 242 breakdown (₪14,642.39) surfaces as 19 clubs instead of one opaque CHESHBONIT line — useful for "which club is driving the variance."

### 1.3 SACAL — high-school basket
- **Schema**: no `קוד נושא` (always maps to Ministry code 1 — שכ"ל על-יסודי), has `הפרש מחושב`, 930 rows of per-class × per-subject detail.
- **Key formula inputs per row**: `(1) מספר תלמידים`, `(2) שעות לתלמיד`, `(3) עלות שעה שבועית`, `(4) עלות מרכיב קבוע`, `(5) עלות חומרים`, `מסלול`, `מגמה`, `סמל מוסד`.
- **Implementation**: new `prepare_sacal()` with hard-coded `topic_code=1`, emits one row per class × subject, stores institution code, student count, hours, and cost-component breakdown.
- **Payoff**: largest single CHESHBONIT code (₪1,097,653 — 76% of the residual) becomes fully transparent. Every agora of high-school tuition explainable by class and subject.

**End-of-Phase-1 outcome**: 0 opaque CHESHBONIT lines, every code has per-institution or per-subtopic detail.

---

## Phase 2 — Formula variance inputs (the "why" behind the numbers)

These files don't carry amounts — they carry the **inputs** that drive the Ministry formulas. Wiring them lets us answer "why did code X change" quantitatively.

### 2.1 ICHLUSKITOT — class enrollment by month
- **Schema**: per-institution × per-class × 12 monthly columns (Sept–Aug) with student counts.
- **New table**: `class_enrollment(municipality_id, run_id, institution_code, class_level, stream, month, student_count)`.
- **Use cases**:
  - Populate the existing student_count_delta variance driver (currently classifies by aggregate; this gives per-class granularity).
  - Flag classes below minimum or above maximum (min/max columns are in the file).
- **Payoff**: turns "enrollment down 14 kids" into "class 10-3 went from 18 → 17, class 10-4 went from 17 → 0 (closed)" — the core of formula-variance attribution.

### 2.2 MISROT — per-institution staff positions
- **Schema**: per-institution × per-role × 12 monthly columns with FTE values (0.21 = 21% of a position).
- **New table**: `staff_positions(municipality_id, run_id, institution_code, role, month, fte)`.
- **Use cases**:
  - Explain variance in codes driven by position counts (mazkirim/שרתים/psychologists) — these are the SHARATIM + SHEFI codes already on the Ministry formula grid.
  - "Positions change × rate" reconciles SHARATIM row deltas.

### 2.3 MISROTGY — per-village GY position allocations
- **Schema**: same shape as MISROT but for kindergartens (per-village level, not per-institution). Negative values = offsets (e.g. "קיזוז גננות").
- **Table**: extend `staff_positions` with a `scope='gy'` flag, institution_code nullable.
- **Use cases**: GY code 3/19/33 formula variance — ties position changes to the GY subtopic breakdown we already ingest.

### 2.4 HASMASLULIM — route-by-route transportation detail
- **Schema**: 38 columns per route (company, vehicle, route km, daily cost, participation %, VAT, compounding, accumulated escalation). No הפרש (current state, not delta).
- **New table**: `transport_routes(municipality_id, run_id, route_id, topic_code, institution, company, vehicle_type, km, daily_cost, participation_pct, total)`.
- **Use cases**:
  - Deep-dive on transportation codes (52, 140) — "which 3 routes drove the ₪40K increase?"
  - Vendor / vehicle-class audit (pinpoint expensive contractors).

**End-of-Phase-2 outcome**: every breakdown line can be clicked through to its formula inputs (enrollment, positions, route kilometers) for a genuine driver attribution.

---

## Phase 3 — Surface the new depth in the UI

Backend detail is worthless if the UI still shows roll-ups. Three specific additions:

### 3.1 Expandable rows in the budget table
- Current: one row per topic code with an aggregated amount.
- New: expand a row to see its per-institution / per-subtopic lines (already in `budget_lines` after Phase 1). Each line shows amount + any captured metadata (num_children, positions, participation %).

### 3.2 Formula-variance drill-down panel
- For any topic code tied to a formula (all GY + MUTAVIM + SHARATIM + SHEFI codes), show "inputs changed since last month":
  - enrollment Δ (from ICHLUSKITOT joined across runs)
  - position Δ (from MISROT / MISROTGY joined across runs)
  - rate Δ (formula coefficients — already partly modelled via purple booklet reference)

### 3.3 Route-level transportation audit
- Modal or separate route-explorer page rendering `transport_routes` filtered by topic code and month.
- Columns: route, company, vehicle, km, daily cost, monthly total, Δ vs prior month.

---

## Phase 4 — Parser hygiene / tests (safety rail)

Once more files are wired, drift risks increase. Three guardrails:

### 4.1 End-to-end ingestion test per ZIP
- `tests/test_ingest_horada.py` loads `Horada (3).zip` through the parser and asserts:
  - total breakdown == known ₪4,702,530.10
  - retro == known ₪66,026.15
  - row count > 3,000 (sentinel that detail files stayed wired)
  - no opaque CHESHBONIT codes left uncovered (`line_type='cheshbonit'` rows < 5)
- Same for `Horada (2).zip` with its own expected totals.

### 4.2 Tie-out tolerance in logs
- Today: mismatches print `⚠️` and keep CHESHBONIT. That's safe but silent in production.
- Add: emit a structured "reconciliation warning" row in a new `ingestion_warnings` table so the admin UI can surface "3 codes didn't tie out in this upload" without grepping stdout.

### 4.3 Invariant-preserving property tests
- Parametrize with codes covered by multiple sources: detail-file-sum + YADANIIM-sum + MOADON/SACAL-adjustments should always equal CHESHBONIT `הפרש לתשלום` per code within 1 agora.
- Fail loudly if it ever stops being true for a real ZIP.

---

## Ordering & effort estimate

| Phase | Effort | Unlocks | Risk |
|-------|--------|---------|------|
| 1.1 YADANIIM + 1.2 MOADON + 1.3 SACAL | ~1 day | 100% CHESHBONIT coverage, 3 new line types | low — additive to existing tie-out |
| 2.1 ICHLUSKITOT | ~0.5 day | per-class student delta | low — new table only, no change to `budget_lines` |
| 2.2 MISROT + 2.3 MISROTGY | ~0.5 day | per-role position delta | low — new table |
| 2.4 HASMASLULIM | ~1 day | transportation audit | medium — 38 cols, edge cases |
| 3.1 expandable rows | ~1 day | unblocks all detail visibility | medium — frontend changes |
| 3.2 drill-down panel | ~2 days | formula-variance story | medium — joins across runs |
| 3.3 route-level audit | ~1 day | niche but valuable | low |
| 4.1–4.3 tests + warnings | ~1 day | regression safety | low |

**Recommended sequence**: finish Phase 1 in one pass (it's the reconciliation closing), then Phase 4.1 immediately (lock it in), then Phase 2 files in any order, then Phase 3 as the polish.
