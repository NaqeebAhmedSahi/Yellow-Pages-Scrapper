@echo off
setlocal
cd /d "%~dp0"

echo Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo Failed to create venv. Ensure Python 3.10+ is installed.
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Setup complete!
echo.
echo Run GUI:  run_gui.bat
echo Run CLI:  run_cli.bat
echo.
