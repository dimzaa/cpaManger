# Test runner script - PowerShell Version

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "CPA Budget Platform - Test Suite" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check venv exists
if (!(Test-Path "backend\venv")) {
    Write-Host "❌ Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run setup.ps1 first" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[1/5] Checking environment..." -ForegroundColor Yellow
& "backend\venv\Scripts\Activate.ps1"
Write-Host "✅ Backend environment ready" -ForegroundColor Green

# Run integration tests
Write-Host "`n[2/5] Running backend integration tests..." -ForegroundColor Yellow
Write-Host "" -ForegroundColor Gray

python test_integration.py
$testResult = $LASTEXITCODE

if ($testResult -ne 0) {
    Write-Host "`n❌ Backend tests FAILED" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "`n✅ Backend tests PASSED" -ForegroundColor Green

# Build frontend
Write-Host "`n[3/5] Building frontend..." -ForegroundColor Yellow
Set-Location frontend
npm run build
$buildResult = $LASTEXITCODE
Set-Location ..

if ($buildResult -ne 0) {
    Write-Host "`n❌ Frontend build FAILED" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "`n✅ Frontend build PASSED" -ForegroundColor Green

# Check build artifacts
Write-Host "`n[4/5] Verifying build artifacts..." -ForegroundColor Yellow

if (!(Test-Path "frontend\dist\index.html")) {
    Write-Host "❌ Build output missing" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✅ Build artifacts found" -ForegroundColor Green

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "✅ ALL TESTS PASSED!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Build summary:" -ForegroundColor Yellow
Write-Host "✅ Backend: Integration tests passing" -ForegroundColor Green
Write-Host "✅ Frontend: Production build successful" -ForegroundColor Green
Write-Host "✅ Output: frontend/dist/" -ForegroundColor Green
Write-Host "`nReady for deployment!" -ForegroundColor Yellow
Write-Host "" -ForegroundColor Gray

Read-Host "Press Enter to close"
