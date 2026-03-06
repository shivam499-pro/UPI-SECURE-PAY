@echo off
REM UPI Secure Pay AI - Backend Setup for Windows

echo ==========================================
echo   UPI Secure Pay AI - Backend Setup
echo ==========================================

REM Check Python
echo.
echo [1/5] Checking Python...
python --version
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found. Please install Python 3.10+
    pause
    exit /b 1
)
echo OK: Python is installed

REM Create virtual environment
echo.
echo [2/5] Creating virtual environment...
python -m venv venv
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)
echo OK: Virtual environment created

REM Activate virtual environment
echo.
echo [3/5] Activating virtual environment...
call venv\Scripts\activate.bat
echo OK: Virtual environment activated

REM Install dependencies
echo.
echo [4/5] Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo OK: Dependencies installed

REM Copy environment file
echo.
echo [5/5] Setting up environment...
if not exist .env (
    copy .env.example .env
    echo OK: Environment file created
) else (
    echo OK: Environment file already exists
)

echo.
echo ==========================================
echo   Setup Complete!
echo ==========================================
echo.
echo Next steps:
echo.
echo 1. Start services with Docker:
echo    docker-compose up -d
echo.
echo 2. Run the server:
echo    uvicorn app.main:app --reload
echo.
echo 3. Test the API:
echo    curl http://localhost:8000/api/v1/health
echo.
echo ==========================================

pause
