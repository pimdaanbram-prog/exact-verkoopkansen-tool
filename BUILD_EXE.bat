@echo off
cd /d "%~dp0"
chcp 65001 >nul
title Exact Tool - EXE bouwen

set PYTHON_EXE=%~dp0_python\python.exe

if not exist "%PYTHON_EXE%" (
    echo  Voer eerst SETUP.bat uit!
    pause & exit /b 1
)

echo.
echo  PyInstaller installeren...
"%PYTHON_EXE%" -m pip install pyinstaller --quiet

echo  EXE bouwen (dit duurt 1-2 minuten)...
"%PYTHON_EXE%" -m PyInstaller ^
    --noconfirm ^
    --windowed ^
    --onedir ^
    --name "ExactTool" ^
    --collect-data customtkinter ^
    --add-data "bedrijven_data.json;." ^
    app.py

echo.
if exist "dist\ExactTool\ExactTool.exe" (
    echo  ╔══════════════════════════════════════════════╗
    echo  ║  EXE gebouwd!                                ║
    echo  ║  Te vinden in: dist\ExactTool\ExactTool.exe  ║
    echo  ║  Kopieer de hele 'dist\ExactTool\' map.      ║
    echo  ╚══════════════════════════════════════════════╝
) else (
    echo  Bouwen mislukt. Controleer de foutmeldingen hierboven.
)
echo.
pause
