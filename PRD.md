# PRD.md — CPA Budget Platform

> **Step 2 output.** Forward-looking Product Requirements Document built on
> `HANDOFF.md` (what exists) and `MARKET_RESEARCH.md` (market context).
> Owner: dimza (zahalkadimzaa@gmail.com). Revision date: 2026-04-19.
> Scope horizon: next ~3 months (v1.0 GA).

---

## 1. What this product is (one sentence)

A Hebrew-first, RTL web platform that lets Israeli CPAs and municipal
treasurers **ingest the Ministry of Education's monthly HORADA ZIP**,
**reconcile every shekel** against detail files, **decompose month-over-month
variance into explainable drivers** (enrollment Δ × rate Δ × residual), and
**publish Ministry-audit-ready PDF/CSV reports** — replacing the 4–8 hour
per-muni Excel reconciliation that CPAs do by hand today.

---

## 2. Users

### 2.1 Primary buyer & primary user (target for v1.0)

**The CPA audit firm** (e.g., a Mishor-style accounting practice). A single
firm audits 3–20 munis per month. They are the buyer *and* the power user.
Why primary:

- Already paid to do this work → clear ROI in hours saved.
- Not subject to Israeli muni public-tender cycle (40–150K NIS ceiling).
- One sale unlocks 3–20 munis worth of usage.

### 2.2 Secondary user (inside the platform)

**The muni treasurer (גזבר)** — reviews the CPA's reconciliation, writes
narrative explanations per topic code (variance_explanations), and signs off
on the monthly report. They authenticate into the "Portal" view scoped to
their own municipality.

### 2.3 Non-users (explicitly out of scope for v1.0)

- Ministry of Education internal staff — they already have MEITAR.
- Large muni IT departments (Haifa/TLV/Jerusalem) — they'll use EPR/SAP.
- General muni finance outside education.

---

## 3. The job to be done (concrete)

> *"As a CPA, every month I receive a ZIP from the Ministry for each muni I
> audit. Today I open 12+ CSVs in Excel, match them by topic code, cross-check
> against the CHESHBONIT invoice total, and write a 1-page memo explaining to
> the muni why each code moved vs. last month. It takes 4–8 hours per muni and
> I can't always explain what drove the change. I want to drop the ZIP into a
> tool and get the reconciliation, variance drivers, and draft memo in under
> 30 minutes."*

---

## 4. Problem statement — what's broken today

1. **Excel chokehold.** CPAs run the work in layered Excel workbooks with
   VLOOKUP/macros. No schema, no version control, no audit trail.
2. **Opaque Ministry roll-ups.** CHESHBONIT gives totals per code. Drilling
   down to *why* a code moved (enrollment? rate? new route?) requires manual
   cross-reference against 6+ detail files.
3. **No formula-driver attribution.** Ministry payments are formula-driven
   (purple booklet). Nobody today tells the CPA "₪X of the Δ is enrollment,
   ₪Y is rate change, ₪Z is new route." Our research shows no competitor does
   this.
4. **No computerized oversight tooling** (per State Comptroller 2022/2023).
5. **Manual report production.** PDFs hand-assembled in Word.
6. **No accessibility compliance.** Hand-made Excel/Word outputs fail IS 5568
   Part 2 (tagged PDFs) → legal risk for munis sharing them publicly.

---

## 5. What's already built (status as of 2026-04-19)

For full detail see `HANDOFF.md`. Summary:

- ✅ Full ingestion pipeline for all Ministry files (CHESHBONIT, GY003/019/033,
  MUTAVIM, SHARATIM, SHEFI, HASAOT, MUCARIM, YADANIIM, MOADON, SACAL,
  ICHLUSKITOT, MISROT, MISROTGY, HASMASLULIM).
- ✅ 100% CHESHBONIT coverage — no opaque roll-ups.
- ✅ Per-topic variance driver classification + student_count_delta service.
- ✅ Expandable topic rows with per-line detail (Phase 3.1).
- ✅ Formula-driver drill-down: enrollment Δ × rate Δ × residual (Phase 3.2).
- ✅ Route-level transportation audit for codes 52 / 140 (Phase 3.3).
- ✅ JWT auth, admin/portal role split, audit logging.
- ✅ PDF + CSV reports.
- ✅ End-to-end ingestion tests, ingestion_warnings table, invariant property
  tests (Phase 4.1–4.3).

The platform already does the **core reconciliation + variance work**. v1.0 is
about making it **shippable to a paying CPA firm**.

---

## 6. v1.0 scope — what we commit to ship

### 6.1 MUST HAVE (launch blockers)

Ordered by priority.

#### M1. Multi-muni CPA dashboard
- A single CPA user logs in and sees a table of all munis they audit.
- Each row: muni name, latest run month, reconciliation status (green/yellow/
  red), count of topics with unexplained variance, days-since-last-report.
- One click → drill into that muni's run → current admin experience.
- **Rationale**: the CPA's workflow is *across* munis, not within one. Without
  this, they can't triage their day.

#### M2. MEITAR parity check
- New endpoint `GET /api/analytics/meitar-parity/{run_id}` that returns per-topic
  comparison of our computed CHESHBONIT vs. the muni's public MEITAR payments
  (scraped or pasted).
- UI banner: "✓ Reconciled to MEITAR" or "⚠ 3 topics differ by >₪100".
- **Rationale**: #1 trust signal for CPAs. If our numbers don't match the
  Ministry's public portal, we're dead on arrival.

#### M3. IS 5568 Part 2 compliance (tagged PDFs + WCAG 2.0 AA)
- Replace ReportLab default output with tagged-PDF generator (e.g.
  `pikepdf` + `pdfua-py` or switch to `weasyprint` in PDF/UA mode).
- Every chart gets alt text; every table gets proper `<th>`/scope tags; reading
  order verified.
- Frontend: run `axe-core` in CI, fix all Level AA violations.
- **Rationale**: statutory. NIS 50K fines + disqualification from public
  tenders. Non-negotiable.

#### M4. CPA white-label branding (logo + letterhead)
- Per-firm upload of logo + firm name + signature block.
- PDF reports render with firm branding, not ours.
- **Rationale**: CPAs deliver reports under their own firm letterhead. If they
  can't, they won't use the tool.

#### M5. Explanation workflow (Muni → CPA → sign-off)
- Today we store variance_explanations. v1.0 adds state machine:
  `draft` → `submitted` → `approved` → `locked`.
- Email notifications at each transition.
- **Rationale**: matches how CPA-muni back-and-forth works today. Also creates
  the audit trail that the State Comptroller will look for.

### 6.2 SHOULD HAVE (launch if time, otherwise v1.1)

#### S1. Historical run comparison (12-month trend per topic)
- Line chart of each topic's amount across last 12 months with variance bands.

#### S2. CSV export matching Excel conventions the CPAs already use
- One-click "Download reconciliation workbook (XLSX)" that mirrors the manual
  spreadsheet they're used to, so switching feels safe.

#### S3. Peer-muni benchmark overlay
- Per topic: "your muni is spending X per student, cluster median is Y."
- Already have `peer_benchmark` endpoint → just surface it more prominently.

#### S4. Stale explanation flag (already built — needs UI promotion)
- Flag explanations that haven't been updated in 2+ months. Already computed;
  needs a dashboard chip.

### 6.3 WON'T HAVE (explicitly out of scope for v1.0)

- ❌ Payroll processing / integration with Chilan.
- ❌ General muni ERP / arnona / collections (EPR's turf).
- ❌ Non-education muni budgets (welfare, infrastructure).
- ❌ Ministry-direct API integration (Ministry doesn't expose one).
- ❌ Mobile-native app (mobile web only).
- ❌ Multi-language — Hebrew only.
- ❌ Real-time collaboration (ok for v2+).
- ❌ PostgreSQL migration from SQLite (v1.0 SQLite is fine for <20 munis per
  firm; plan in architecture doc).

---

## 7. Success metrics

v1.0 success = **one CPA firm paying, running 5+ munis end-to-end every
month for 3 consecutive months.**

Secondary metrics to track from day one:

- **Time-to-reconciled**: from ZIP upload to sign-off, median per muni.
  Target: <45 min (vs. 4–8h baseline in Excel).
- **Variance coverage**: % of topic codes with a non-empty
  `variance_explanation` at sign-off. Target: ≥95%.
- **Formula-driver hit rate**: % of material (>₪10K) variances where the
  platform produced a non-residual decomposition. Target: ≥80%.
- **Ingestion tie-out rate**: % of ZIPs where CHESHBONIT reconciles to detail
  files within ₪1 across all codes. Target: 100% (regression: < 1 failure
  per 50 ZIPs).
- **IS 5568 audit score**: axe-core Level AA violations. Target: 0 in CI.

---

## 8. Non-functional requirements

- **Hebrew RTL throughout**, no exceptions.
- **Accessibility**: WCAG 2.0 AA; PDFs tagged per IS 5568 Part 2.
- **Security**: JWT auth; role-based data scoping (muni user can't read other
  munis); audit trail on every write.
- **Data retention**: keep all runs indefinitely; monthly backup of
  `/tmp/cpa_data/cpa.db` (or the production PG equivalent).
- **Performance**: ingest a typical muni ZIP in <30s; dashboard load <2s.
- **Browser support**: evergreen Chrome/Edge/Firefox/Safari; IE11 explicitly
  not supported.

---

## 9. Open product questions (need user/customer answer before build)

1. **Pricing model**: per-muni / per-CPA-seat / per-firm flat?
2. **Data residency**: must be Israel-hosted? (Azure Israel Central exists.)
3. **MEITAR ingestion**: scrape, ask user to paste CSV, or both?
4. **Who hosts**: SaaS from us, or on-prem at each CPA firm? (Affects
   architecture doc's deployment section.)
5. **Onboarding partner**: Mishor CPA or similar — any warm intro?

---

## 10. Dependencies & risks

| Risk | Mitigation |
|---|---|
| Ministry changes HORADA schema mid-year | Phase 4.1 E2E tests catch it; add per-year schema version to config. |
| IS 5568 audit fails before launch | Do M3 first; buy one external accessibility audit before GA. |
| CPA prefers Excel export over our UI | S2 (Excel export) becomes a must-have. |
| SQLite hits scale wall | Architecture doc plans Postgres migration path. |
| MEITAR page changes breaking parity check | Keep parity as a CSV-paste fallback. |

---

## 11. Launch checklist (v1.0 GA)

- [ ] M1–M5 shipped, QA'd in Hebrew.
- [ ] IS 5568 external audit passed.
- [ ] One paying CPA firm contracted (design partner → paid).
- [ ] 5 munis ingested end-to-end with MEITAR parity ✓.
- [ ] Production backup job running, tested restore.
- [ ] Postmortem-ready: runbook in `HANDOFF.md` for DB restore, ZIP re-ingest,
      token rotation.

---

**Next artifact**: `ARCHITECTURE.md` (Step 3) — translates these requirements
into schema changes, component tree updates, and deployment plan.
