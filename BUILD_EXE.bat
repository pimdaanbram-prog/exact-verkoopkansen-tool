@echo off
cd /d "%~dp0"
title Exact Tool - EXE bouwen

set PYTHON_EXE=%~dp0_python\python.exe
set BROWSERS_DIR=%~dp0_browsers

if not exist "%PYTHON_EXE%" (
    echo Voer eerst SETUP.bat uit!
    pause
    exit /b 1
)

if not exist "app.py" (
    echo FOUT: app.py niet gevonden.
    pause
    exit /b 1
)

echo.
echo Stap 1/3: PyInstaller installeren...
"%PYTHON_EXE%" -m pip install pyinstaller --no-user --quiet --no-warn-script-location
if errorlevel 1 (
    echo FOUT: PyInstaller installeren mislukt.
    pause
    exit /b 1
)

echo Stap 2/3: EXE bouwen (2-4 minuten)...
echo.
"%PYTHON_EXE%" -m PyInstaller ^
    --noconfirm ^
    --console ^
    --onedir ^
    --name "ExactTool" ^
    --hidden-import flask ^
    --hidden-import werkzeug ^
    --hidden-import jinja2 ^
    --hidden-import click ^
    --hidden-import playwright ^
    --add-data "bedrijven_data.json;." ^
    app.py

if not exist "dist\ExactTool\ExactTool.exe" (
    echo.
    echo MISLUKT - geen exe gevonden.
    echo Scroll omhoog voor de foutmelding.
    pause
    exit /b 1
)

echo Stap 3/3: Browser en data kopiëren naar exe map...

:: Browsers meekopieren zodat de exe ze kan vinden
if exist "%BROWSERS_DIR%" (
    echo Chromium browsers kopiëren...
    xcopy /e /i /q "%BROWSERS_DIR%" "dist\ExactTool\_browsers"
) else (
    echo Browsers niet gevonden, installeren in exe map...
    set PLAYWRIGHT_BROWSERS_PATH=%~dp0dist\ExactTool\_browsers
    "%PYTHON_EXE%" -m playwright install chromium
)

:: bedrijven_data.json ook in de exe map zetten
copy /y "bedrijven_data.json" "dist\ExactTool\bedrijven_data.json" >nul

echo.
echo ================================================
echo  Gelukt! De app staat klaar in:
echo  dist\ExactTool\ExactTool.exe
echo.
echo  Kopieer de hele dist\ExactTool\ map.
echo  Dubbelklik ExactTool.exe om te starten.
echo ================================================
echo.
explorer dist\ExactTool
pause
