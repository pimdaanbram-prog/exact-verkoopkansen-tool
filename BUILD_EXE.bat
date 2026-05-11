@echo off
cd /d "%~dp0"
title Exact Tool - EXE bouwen

set PYTHON_EXE=%~dp0_python\python.exe

if not exist "%PYTHON_EXE%" (
    echo Voer eerst SETUP.bat uit!
    pause
    exit /b 1
)

echo.
echo PyInstaller installeren...
"%PYTHON_EXE%" -m pip install pyinstaller --no-user --quiet --no-warn-script-location

echo EXE bouwen (1-2 minuten)...
"%PYTHON_EXE%" -m PyInstaller --noconfirm --windowed --onedir --name "ExactTool" --collect-data flask --add-data "bedrijven_data.json;." app.py

echo.
if exist "dist\ExactTool\ExactTool.exe" (
    echo ================================================
    echo  EXE gebouwd!
    echo  Te vinden in: dist\ExactTool\ExactTool.exe
    echo  Kopieer de hele map dist\ExactTool\
    echo ================================================
) else (
    echo Bouwen mislukt. Zie foutmeldingen hierboven.
)
echo.
pause
