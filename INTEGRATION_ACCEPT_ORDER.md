# Integration Accept Order (10-Agent Workflow)

This runbook is for safe acceptance of concurrent agent sessions.

## Primary Hotspots (manual review required)

- frontend/src/services/api.js
- frontend/src/App.jsx
- frontend/package.json
- frontend/vite.config.js
- frontend/src/pages/PortalAnalyticsPage.jsx
- frontend/src/pages/PortalPositionsPage.jsx

## Acceptance Order

1. Accept low-risk page/component changes that do not touch hotspots.
2. Run quick gate:
   - `powershell -ExecutionPolicy Bypass -File .\integration_guard.ps1 -Quick`
3. Accept Month Selector foundation changes.
4. Accept Analytics page changes.
5. Accept Positions page changes.
6. Run full gate:
   - `powershell -ExecutionPolicy Bypass -File .\integration_guard.ps1 -SkipDevServer`
7. Accept API service changes in frontend/src/services/api.js (manual merge order):
   - API client/interceptors
   - auth-related API functions
   - feature endpoint changes
   - exported API namespaces
8. Run full gate:
   - `powershell -ExecutionPolicy Bypass -File .\integration_guard.ps1 -SkipDevServer`
9. Accept App routing shell changes in frontend/src/App.jsx.
10. Accept ESM/config changes last:
    - frontend/package.json
    - frontend/vite.config.js
11. Run full startup gate:
    - `powershell -ExecutionPolicy Bypass -File .\integration_guard.ps1`

## ESM Safety Rules

- Keep frontend/package.json with `"type": "module"`.
- Do not allow `require(`, `module.exports`, or `exports.` in frontend source/config.
- If imports are moved, ensure App routes and page imports resolve before accepting.

## Month State Rules

- Analytics page must keep selectedMonth wired to anomalies/retro data calls.
- Positions page must keep selectedMonth wired to analysis and priority data calls.
- Any shared month utility changes must be consumed consistently in both pages.

## Done Criteria

A session batch is accepted only when all are true:

- `integration_guard.ps1` returns exit code 0
- Frontend build passes
- Dev server startup smoke check passes
- No conflict markers in source
- Month state wiring checks pass
