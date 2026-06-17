@echo off
REM Test runner script for Education Budget Platform
REM Run this AFTER running setup.bat

echo.
echo ===================================
echo CPA Budget Platform — Test Suite
echo ===================================
echo.

REM Check if venv is set up
if not exist "backend\venv" (
    echo ❌ Virtual environment not found!
    echo Please run setup.bat first
    exit /b 1
)

REM Activate venv
call backend\venv\Scripts\activate.bat

echo [1/5] Checking environment...
echo ✅ Backend environment ready

REM Run integration tests
echo.
echo [2/5] Running backend integration tests...
echo.
cd backend
python test_integration.py
if errorlevel 1 (
    echo.
    echo ❌ Backend tests FAILED
    exit /b 1
)
echo.
echo ✅ Backend tests PASSED
cd ..

REM Build frontend
echo.
echo [3/5] Building frontend...
cd frontend
call npm run build
if errorlevel 1 (
    echo.
    echo ❌ Frontend build FAILED
    exit /b 1
)
echo ✅ Frontend build PASSED
cd ..

REM Check build artifacts
echo.
echo [4/5] Verifying build artifacts...
if not exist "frontend\dist\index.html" (
    echo ❌ Build output missing
    exit /b 1
)
echo ✅ Build artifacts found

echo.
echo ===================================
echo ✅ ALL TESTS PASSED!
echo ===================================
echo.
echo Build summary:
echo - Backend: Integration tests passing
echo - Frontend: Production build successful
echo - Output: frontend/dist/
echo.
echo Ready for deployment!
echo.
pause
