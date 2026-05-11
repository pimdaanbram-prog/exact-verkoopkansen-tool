@echo off
cd /d "%~dp0"
title Exact Tool - EXE bouwen

set PYTHON_EXE=%~dp0_python\python.exe

if not exist "%PYTHON_EXE%" (
    echo Voer eerst SETUP.bat uit!
    pause
    exit /b 1
)

if not exist "app.py" (
    echo FOUT: app.py niet gevonden. Zorg dat je in de juiste map zit.
    pause
    exit /b 1
)

if not exist "bedrijven_data.json" (
    echo FOUT: bedrijven_data.json niet gevonden.
    pause
    exit /b 1
)

echo.
echo Stap 1/2: PyInstaller installeren...
"%PYTHON_EXE%" -m pip install pyinstaller --no-user --quiet --no-warn-script-location
if errorlevel 1 (
    echo FOUT: PyInstaller installeren mislukt.
    pause
    exit /b 1
)

echo Stap 2/2: EXE bouwen (2-4 minuten)...
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

echo.
if exist "dist\ExactTool\ExactTool.exe" (
    echo ================================================
    echo  Gelukt!
    echo  Dubbelklik: dist\ExactTool\ExactTool.exe
    echo  Kopieer de hele map dist\ExactTool\ mee.
    echo ================================================
    echo.
    explorer dist\ExactTool
) else (
    echo ================================================
    echo  MISLUKT - geen exe gevonden.
    echo  Scroll omhoog voor de foutmelding van PyInstaller.
    echo ================================================
)
echo.
pause
