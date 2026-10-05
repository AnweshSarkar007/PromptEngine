@echo off
rem ---------------------------------------------------------------------------
rem  Builds "Product Image Prompt Builder" into a Windows executable.
rem
rem    build.bat            one-folder build (recommended, used by the installer)
rem    build.bat onefile    single .exe build
rem
rem  Needs Python 3.10+ on PATH (the "py" launcher is fine). Everything else is
rem  installed into a local .venv automatically.
rem ---------------------------------------------------------------------------
setlocal EnableExtensions
cd /d "%~dp0"

set "APP_NAME=Product Image Prompt Builder"
set "MODE=onedir"
if /I "%~1"=="onefile" set "MODE=onefile"

set "PY=.venv\Scripts\python.exe"

if not exist "%PY%" (
    echo [1/4] Creating virtual environment...
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -m venv .venv
    ) else (
        python -m venv .venv
    )
    if errorlevel 1 goto :nopython
)

echo [2/4] Installing dependencies...
"%PY%" -m pip install --upgrade pip --quiet
"%PY%" -m pip install -r requirements.txt --quiet
if errorlevel 1 goto :fail

if not exist "assets\icon.ico" (
    echo [3/4] Generating application icon...
    "%PY%" tools\make_icon.py
    if errorlevel 1 goto :fail
) else (
    echo [3/4] Icon already present.
)

echo [4/4] Building %MODE% executable with PyInstaller...
if /I "%MODE%"=="onefile" (
    "%PY%" -m PyInstaller --noconfirm --clean --windowed --onefile --name "%APP_NAME%" --icon "assets\icon.ico" --add-data "assets;assets" main.py
) else (
    "%PY%" -m PyInstaller --noconfirm --clean --windowed --onedir --name "%APP_NAME%" --icon "assets\icon.ico" --add-data "assets;assets" main.py
)
if errorlevel 1 goto :fail

echo.
echo ===========================================================================
if /I "%MODE%"=="onefile" (
    echo  Done:  dist\%APP_NAME%.exe
) else (
    echo  Done:  dist\%APP_NAME%\%APP_NAME%.exe
    echo  Optional installer: open installer\setup.iss in Inno Setup and press Compile.
)
echo ===========================================================================
exit /b 0

:nopython
echo [ERROR] Python 3 was not found. Install it from https://www.python.org/downloads/ ^(tick "Add python.exe to PATH"^) and run this file again.
exit /b 1

:fail
echo.
echo [ERROR] The build failed. Scroll up for the first error message.
exit /b 1
