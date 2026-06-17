# QA Reports Needed

## Audit Context
- Date: 2026-04-17
- Scope: Post multi-agent integration QA pass (conflicts, imports, build/runtime, business-rule cross-check)

## Critical - Ministry Code Coverage Mismatch
- Expected: 64 ministry codes recognized (per audit requirement).
- Found in configured seed source: 7 entries in [backend/utils/seed_ministry_codes.py](backend/utils/seed_ministry_codes.py).
- Found in local DB table: 7 entries in ministry_codes.

### Evidence
- `python -c "from backend.utils.seed_ministry_codes import CODES_DATA; print(len(CODES_DATA))"` -> `7`
- `python -c "import sqlite3; ... select count(*) from ministry_codes ..."` -> `7`

### Impact
- Positions/analytics/ministry lookup behavior may be incomplete for codes not represented in the seed dataset.
- Requirement "64 Ministry codes are being recognized" is not currently satisfied.

### Required Manual Fix
1. Provide authoritative source list for all 64 ministry codes and metadata fields.
2. Expand [backend/utils/seed_ministry_codes.py](backend/utils/seed_ministry_codes.py) to include complete set.
3. Backfill existing DB table `ministry_codes` for environments already seeded.
4. Add regression test asserting expected code count and presence of critical code IDs.

## Medium - Linting Not Configured
- `npm run lint` failed because no `lint` script exists in [frontend/package.json](frontend/package.json).
- Add a lint script and config if style enforcement is required in CI.
