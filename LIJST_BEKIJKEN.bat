@echo off
cd /d "%~dp0"
chcp 65001 >nul
title Exact Tool - Bedrijvenlijst bekijken

set PLAYWRIGHT_BROWSERS_PATH=%~dp0_browsers
set PYTHON_EXE=%~dp0_python\python.exe

if not exist "%PYTHON_EXE%" (
    echo.
    echo  Tool nog niet geinstalleerd. Voer eerst SETUP.bat uit!
    echo.
    pause
    exit /b 1
)

echo.
echo  De browser opent nu. Log in bij Exact als dat nodig is.
echo  De bedrijfsnamen worden hierna getoond.
echo.
"%PYTHON_EXE%" lijst_script.py
echo.
echo  Kopieer de namen hierboven en stuur ze naar Claude.
echo  Zeg: "Maak hiervoor een nieuwe bedrijven_data.json"
echo.
pause
