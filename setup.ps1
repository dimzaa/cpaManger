# Setup script for Education Budget Platform - PowerShell Version

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "CPA Budget Platform - Setup" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check Node.js
Write-Host "[1/5] Checking Node.js..." -ForegroundColor Yellow
$nodeCheck = node --version 2>$null
if ($nodeCheck) {
    Write-Host "✅ Node.js found: $nodeCheck" -ForegroundColor Green
} else {
    Write-Host "❌ Node.js not found" -ForegroundColor Red
    Write-Host "   Download from: https://nodejs.org/" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check Python
Write-Host "`n[2/5] Checking Python..." -ForegroundColor Yellow
$pythonCheck = python --version 2>$null
if ($pythonCheck) {
    Write-Host "✅ Python found: $pythonCheck" -ForegroundColor Green
} else {
    Write-Host "❌ Python not found" -ForegroundColor Red
    Write-Host "   Download from: https://python.org/" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Setup backend
Write-Host "`n[3/5] Setting up backend..." -ForegroundColor Yellow

if (!(Test-Path "backend\venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Gray
    python -m venv backend\venv
}

# Activate venv
& "backend\venv\Scripts\Activate.ps1"

Write-Host "Installing Python dependencies..." -ForegroundColor Gray
pip install -q -r backend\requirements.txt

Write-Host "✅ Backend ready" -ForegroundColor Green

# Setup frontend
Write-Host "`n[4/5] Setting up frontend..." -ForegroundColor Yellow
Set-Location frontend
Write-Host "Installing npm dependencies..." -ForegroundColor Gray
npm install -q
Set-Location ..
Write-Host "✅ Frontend ready" -ForegroundColor Green

# Create env files
Write-Host "`n[5/5] Configuring environment..." -ForegroundColor Yellow

if (!(Test-Path "backend\.env")) {
    Write-Host "Creating backend\.env..." -ForegroundColor Gray
    @"
DATABASE_URL=sqlite:///./test.db
SECRET_KEY=dev-secret-key-change-in-production
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
"@ | Out-File "backend\.env" -Encoding UTF8
    Write-Host "✅ Created backend\.env" -ForegroundColor Green
}

if (!(Test-Path "frontend\.env")) {
    Write-Host "Creating frontend\.env..." -ForegroundColor Gray
    @"
VITE_API_URL=http://localhost:8000
"@ | Out-File "frontend\.env" -Encoding UTF8
    Write-Host "✅ Created frontend\.env" -ForegroundColor Green
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "✅ Setup Complete!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Run tests: run_tests.ps1" -ForegroundColor White
Write-Host "2. Or start servers: start_servers.ps1" -ForegroundColor White
Write-Host "`nPress Enter to close..." -ForegroundColor Gray
Read-Host
