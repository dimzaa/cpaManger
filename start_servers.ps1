# Start development servers - PowerShell Version

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "CPA Budget Platform - Development Servers" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check venv exists
if (!(Test-Path "backend\venv")) {
    Write-Host "❌ Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run setup.ps1 first" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Starting backend server..." -ForegroundColor Yellow
Write-Host "This will open in a new terminal window" -ForegroundColor Gray
Write-Host "" -ForegroundColor Gray

# Start backend in new window
$backendScript = @"
cd `"$(Get-Location)\backend`"
`& `"$(Get-Location)\backend\venv\Scripts\Activate.ps1`"
Write-Host `"Backend running on http://localhost:8000`" -ForegroundColor Green
python -m uvicorn main:app --reload
"@

$backendScriptPath = Join-Path $env:TEMP "start_backend.ps1"
$backendScript | Out-File $backendScriptPath -Encoding UTF8
Start-Process powershell -ArgumentList "-NoExit -File `"$backendScriptPath`""

Write-Host "✅ Backend terminal opened`n" -ForegroundColor Green

Write-Host "Starting frontend dev server..." -ForegroundColor Yellow
Write-Host "This will open in another new terminal window`n" -ForegroundColor Gray

# Start frontend in new window
$frontendScript = @"
cd `"$(Get-Location)\frontend`"
Write-Host `"Frontend running on http://localhost:5173`" -ForegroundColor Green
npm run dev
"@

$frontendScriptPath = Join-Path $env:TEMP "start_frontend.ps1"
$frontendScript | Out-File $frontendScriptPath -Encoding UTF8
Start-Process powershell -ArgumentList "-NoExit -File `"$frontendScriptPath`""

Write-Host "✅ Frontend terminal opened`n" -ForegroundColor Green

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🚀 Both servers are starting..." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`nOpen your browser and go to: http://localhost:5173" -ForegroundColor Yellow
Write-Host "Backend API: http://localhost:8000" -ForegroundColor Yellow
Write-Host "`nPress Ctrl+C in each terminal to stop servers`n" -ForegroundColor Gray

Read-Host "Press Enter to close this window"
