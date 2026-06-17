@echo off
REM Setup script for Education Budget Platform
REM Runs on Windows

echo.
echo ===================================
echo CPA Budget Platform — Setup Script
echo ===================================
echo.

REM Check Node.js
echo [1/5] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js not found. Install from https://nodejs.org/
    exit /b 1
) else (
    echo ✅ Node.js found
    node --version
)

REM Check Python
echo.
echo [2/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Install from https://www.python.org/
    exit /b 1
) else (
    echo ✅ Python found
    python --version
)

REM Create backend virtual environment
echo.
echo [3/5] Setting up backend...
if not exist "backend\venv" (
    echo Creating virtual environment...
    python -m venv backend\venv
)
call backend\venv\Scripts\activate.bat
echo Installing Python dependencies...
pip install -r backend\requirements.txt -q
echo ✅ Backend ready

REM Install frontend dependencies
echo.
echo [4/5] Setting up frontend...
cd frontend
echo Installing npm dependencies...
call npm install -q
cd ..
echo ✅ Frontend ready

REM Create environment files if missing
echo.
echo [5/5] Configuring environment...
if not exist "backend\.env" (
    echo Creating backend/.env...
    (
        echo DATABASE_URL=sqlite:///./test.db
        echo SECRET_KEY=dev-secret-key-change-in-production
        echo ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
    ) > backend\.env
    echo ✅ Created backend/.env
)

if not exist "frontend\.env" (
    echo Creating frontend/.env...
    (
        echo VITE_API_URL=http://localhost:8000
    ) > frontend\.env
    echo ✅ Created frontend/.env
)

echo.
echo ===================================
echo ✅ Setup Complete!
echo ===================================
echo.
echo Next steps:
echo.
echo 1. Run tests:
echo    cd backend
echo    venv\Scripts\activate
echo    python test_integration.py
echo.
echo 2. Start development servers (in separate terminals):
echo    Terminal 1:
echo      cd backend
echo      venv\Scripts\activate
echo      python -m uvicorn main:app --reload
echo.
echo    Terminal 2:
echo      cd frontend
echo      npm run dev
echo.
echo 3. Open browser to http://localhost:5173
echo.
pause
