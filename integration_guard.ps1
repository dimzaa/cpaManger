param(
  [switch]$SkipBuild,
  [switch]$SkipDevServer,
  [switch]$Quick,
  [int]$DevServerTimeoutSeconds = 25
)

$ErrorActionPreference = 'Stop'

function Write-Section {
  param([string]$Name)
  Write-Host ""
  Write-Host "== $Name ==" -ForegroundColor Cyan
}

function Add-Result {
  param(
    [string]$Check,
    [bool]$Passed,
    [string]$Details
  )

  $script:Results += [PSCustomObject]@{
    Check   = $Check
    Passed  = $Passed
    Details = $Details
  }

  if ($Passed) {
    Write-Host "PASS: $Check" -ForegroundColor Green
  }
  else {
    Write-Host "FAIL: $Check" -ForegroundColor Red
  }

  if ($Details) {
    Write-Host "  $Details"
  }
}

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendRoot = Join-Path $repoRoot 'frontend'
$reportPath = Join-Path $repoRoot 'logs\integration_guard_report.txt'
$script:Results = @()

if (-not (Test-Path $frontendRoot)) {
  throw "Frontend folder not found: $frontendRoot"
}

Write-Section "Hotspot File Presence"
$hotspots = @(
  'frontend/src/services/api.js',
  'frontend/src/App.jsx',
  'frontend/package.json',
  'frontend/vite.config.js',
  'frontend/src/pages/PortalAnalyticsPage.jsx',
  'frontend/src/pages/PortalPositionsPage.jsx',
  'frontend/src/pages/AdminAnalyticsPage.jsx',
  'frontend/src/services/store.js',
  'frontend/src/utils/format.js'
)

$missing = @()
foreach ($rel in $hotspots) {
  $abs = Join-Path $repoRoot $rel
  if (-not (Test-Path $abs)) {
    $missing += $rel
  }
}

$hotspotDetails = if ($missing.Count -eq 0) {
  'All hotspot files found.'
}
else {
  "Missing: $($missing -join ', ')"
}

Add-Result -Check 'Hotspot files exist' -Passed ($missing.Count -eq 0) -Details $hotspotDetails

Write-Section "Conflict Marker Scan"
$scanRoots = @(
  (Join-Path $repoRoot 'frontend/src'),
  (Join-Path $repoRoot 'backend/routes'),
  (Join-Path $repoRoot 'backend/services'),
  (Join-Path $repoRoot 'backend/models'),
  (Join-Path $repoRoot 'backend/schemas'),
  (Join-Path $repoRoot 'backend/utils')
) | Where-Object { Test-Path $_ }

$conflicts = @()
foreach ($root in $scanRoots) {
  $conflicts += Get-ChildItem -Path $root -Recurse -File |
    Select-String -Pattern '^\s*<{7} .*|^\s*={7}$|^\s*>{7} .*'
}

if ($conflicts.Count -eq 0) {
  Add-Result -Check 'No merge conflict markers' -Passed $true -Details 'No conflict markers found.'
}
else {
  $sample = ($conflicts | Select-Object -First 5 | ForEach-Object { "$(($_.Path).Replace($repoRoot + '\\','')):$($_.LineNumber)" }) -join '; '
  Add-Result -Check 'No merge conflict markers' -Passed $false -Details "Found $($conflicts.Count) markers. Sample: $sample"
}

Write-Section "ESM Safety Scan"
$esmTargets = @(
  (Join-Path $repoRoot 'frontend/src'),
  (Join-Path $repoRoot 'frontend/vite.config.js'),
  (Join-Path $repoRoot 'frontend/postcss.config.js'),
  (Join-Path $repoRoot 'frontend/tailwind.config.js')
)

$cjsMatches = @()
foreach ($target in $esmTargets) {
  if (Test-Path $target) {
    if ((Get-Item $target).PSIsContainer) {
      $cjsMatches += Get-ChildItem -Path $target -Recurse -File -Include *.js,*.jsx |
        Select-String -Pattern 'require\(|module\.exports|exports\.'
    }
    else {
      $cjsMatches += Select-String -Path $target -Pattern 'require\(|module\.exports|exports\.'
    }
  }
}

if ($cjsMatches.Count -eq 0) {
  Add-Result -Check 'No CommonJS regressions in frontend code' -Passed $true -Details 'No require/module.exports/exports usage found.'
}
else {
  $sample = ($cjsMatches | Select-Object -First 5 | ForEach-Object { "$(($_.Path).Replace($repoRoot + '\\','')):$($_.LineNumber)" }) -join '; '
  Add-Result -Check 'No CommonJS regressions in frontend code' -Passed $false -Details "Found $($cjsMatches.Count) matches. Sample: $sample"
}

Write-Section "Month State Wiring Checks"

$analyticsFile = Join-Path $repoRoot 'frontend/src/pages/PortalAnalyticsPage.jsx'
$positionsFile = Join-Path $repoRoot 'frontend/src/pages/PortalPositionsPage.jsx'

$analyticsText = if (Test-Path $analyticsFile) { Get-Content -Path $analyticsFile -Raw } else { '' }
$positionsText = if (Test-Path $positionsFile) { Get-Content -Path $positionsFile -Raw } else { '' }

$analyticsChecks = @(
  ($analyticsText -match 'selectedMonth\s*,\s*setSelectedMonth'),
  ($analyticsText -match 'AnomaliesTab\s+municipalityId=\{municipalityId\}\s+selectedMonth=\{selectedMonth\}'),
  ($analyticsText -match 'RetroAgingTab\s+municipalityId=\{municipalityId\}\s+selectedMonth=\{selectedMonth\}')
)

$positionsChecks = @(
  ($positionsText -match 'selectedMonth\s*,\s*setSelectedMonth'),
  ($positionsText -match 'positionsAPI\.getAnalysis\(selectedMunicipality,\s*selectedMonth\)'),
  ($positionsText -match 'PriorityTab\s+municipalityId=\{selectedMunicipality\}\s+selectedMonth=\{selectedMonth\}')
)

$monthChecksPassed = ($analyticsChecks -notcontains $false) -and ($positionsChecks -notcontains $false)
$monthDetails = if ($monthChecksPassed) {
  'selectedMonth state appears connected to analytics and positions data flows.'
}
else {
  'At least one expected selectedMonth usage pattern is missing.'
}
Add-Result -Check 'Month selector state wiring analytics + positions' -Passed $monthChecksPassed -Details $monthDetails

Write-Section "Frontend Build"
if ($SkipBuild) {
  Add-Result -Check 'Frontend build' -Passed $true -Details 'Skipped by parameter.'
}
else {
  Push-Location $frontendRoot
  try {
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $buildOutput = & cmd.exe /c "npm run build" 2>&1
    $ErrorActionPreference = $previousErrorActionPreference
    $buildSucceeded = ($LASTEXITCODE -eq 0)
    if ($buildSucceeded) {
      Add-Result -Check 'Frontend build' -Passed $true -Details 'npm run build completed successfully.'
    }
    else {
      $tail = ($buildOutput | Select-Object -Last 10) -join ' | '
      Add-Result -Check 'Frontend build' -Passed $false -Details "npm run build failed. Tail: $tail"
    }
  }
  finally {
    $ErrorActionPreference = 'Stop'
    Pop-Location
  }
}

Write-Section "Dev Server Smoke"
if ($SkipDevServer -or $Quick) {
  Add-Result -Check 'Dev server startup smoke test' -Passed $true -Details 'Skipped by parameter.'
}
else {
  $runId = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
  $outFile = Join-Path $repoRoot "logs\devserver_smoke_out_$runId.txt"
  $errFile = Join-Path $repoRoot "logs\devserver_smoke_err_$runId.txt"

  $proc = Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', 'npm run dev' -WorkingDirectory $frontendRoot -RedirectStandardOutput $outFile -RedirectStandardError $errFile -PassThru

  $timedOut = $false
  try {
    Wait-Process -Id $proc.Id -Timeout $DevServerTimeoutSeconds -ErrorAction Stop
  }
  catch {
    $timedOut = $true
  }

  $outText = if (Test-Path $outFile) { Get-Content $outFile -Raw } else { '' }
  $errText = if (Test-Path $errFile) { Get-Content $errFile -Raw } else { '' }
  $combined = $outText + "`n" + $errText

  $hasReadySignal = $combined -match 'Local:\s+http://|ready in|VITE'
  $hasFatal = $combined -match 'ERR!|Error:|Failed to|EADDRINUSE|Cannot find module|SyntaxError'

  if ($timedOut) {
    # Timeout usually means dev server kept running. That is expected for a startup smoke test.
    if (-not $proc.HasExited) {
      Stop-Process -Id $proc.Id -Force
    }
  }

  if ($hasReadySignal -and -not $hasFatal) {
    Add-Result -Check 'Dev server startup smoke test' -Passed $true -Details 'Dev server reached startup signal and no fatal startup errors were detected.'
  }
  else {
    $tail = ($combined -split "`r?`n" | Select-Object -Last 12) -join ' | '
    Add-Result -Check 'Dev server startup smoke test' -Passed $false -Details "Startup signal not verified or fatal output detected. Tail: $tail"
  }
}

Write-Section "Summary"
$failCount = ($Results | Where-Object { -not $_.Passed }).Count
$passCount = ($Results | Where-Object { $_.Passed }).Count

$Results | Format-Table -AutoSize

"Integration Guard Report - $(Get-Date -Format s)" | Set-Content -Path $reportPath
$Results | ForEach-Object { "[$($_.Passed)] $($_.Check) :: $($_.Details)" } | Add-Content -Path $reportPath

Write-Host ""
Write-Host "Report saved: $reportPath"
Write-Host "Passed: $passCount | Failed: $failCount"

if ($failCount -gt 0) {
  exit 1
}

exit 0
