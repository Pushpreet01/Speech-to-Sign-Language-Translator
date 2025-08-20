@echo off
echo 🤟 Speech-to-Sign MVP Quick Start
echo =====================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.9+ first.
    pause
    exit /b 1
)

echo ✅ Python found

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install requirements
echo 📥 Installing dependencies...
pip install -r requirements.txt

echo.
echo 🚀 Setup complete! Choose an option:
echo.
echo 1. Local Demo (no AWS required) - recommended for quick testing
echo 2. Full AWS Setup (requires AWS credentials)
echo.
set /p choice="Enter your choice (1 or 2): "

if "%choice%"=="1" (
    echo.
    echo 🎭 Starting LOCAL DEMO mode...
    echo This mode uses mock data and doesn't require AWS setup
    echo Open your browser to: http://localhost:5000
    echo.
    python local_demo.py
) else if "%choice%"=="2" (
    echo.
    echo ☁️ Starting AWS mode...
    echo Make sure you have configured your .env file first!
    echo.
    python app.py
) else (
    echo Invalid choice. Starting local demo by default...
    python local_demo.py
)

pause
