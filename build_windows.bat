@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================
echo  Yellow Pages Scraper - Windows Build
echo ============================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python was not found on PATH.
    echo Install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure "Add python.exe to PATH" is checked.
    exit /b 1
)

if not exist "venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create venv.
        exit /b 1
    )
)

call venv\Scripts\activate.bat

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing runtime + build dependencies...
pip install -r requirements.txt
pip install -r requirements-build.txt
if errorlevel 1 (
    echo Dependency install failed.
    exit /b 1
)

echo Cleaning previous build folders...
if exist build rmdir /s /q build
if exist dist\YellowPagesScraper rmdir /s /q dist\YellowPagesScraper

echo.
echo Running PyInstaller (this may take a few minutes)...
python -m PyInstaller --noconfirm --clean YellowPagesScraper.spec
if errorlevel 1 (
    echo.
    echo BUILD FAILED.
    exit /b 1
)

echo.
echo Writing portable README into dist folder...
(
echo Yellow Pages Scraper - Portable App
echo ==================================
echo.
echo Requirements on this PC:
echo   1. Google Chrome installed
echo   2. Windows 10/11 64-bit recommended
echo.
echo How to run:
echo   Double-click YellowPagesScraper.exe
echo.
echo Output files are created next to the EXE in:
echo   output\data\
echo   output\logs\
echo   output\app\
echo.
echo You do NOT need Python or pip on this PC.
echo Keep the whole YellowPagesScraper folder together.
echo Do not move only the .exe out of the folder.
) > "dist\YellowPagesScraper\README_PORTABLE.txt"

echo.
echo ============================================
echo  BUILD SUCCESS
echo ============================================
echo.
echo App folder:
echo   %cd%\dist\YellowPagesScraper\
echo.
echo Main EXE:
echo   %cd%\dist\YellowPagesScraper\YellowPagesScraper.exe
echo.
echo Next steps:
echo   1. Zip the folder dist\YellowPagesScraper
echo   2. Copy the ZIP to another PC
echo   3. Extract and run YellowPagesScraper.exe
echo   4. Ensure Google Chrome is installed on that PC
echo.
pause
