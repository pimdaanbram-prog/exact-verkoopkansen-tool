@echo off
cd /d "%~dp0"
chcp 65001 >nul
title Exact Verkoopkansen Tool

set PLAYWRIGHT_BROWSERS_PATH=%~dp0_browsers
set PYTHON_EXE=%~dp0_python\python.exe

if not exist "%PYTHON_EXE%" (
    echo.
    echo  Nog niet geinstalleerd. Voer eerst SETUP.bat uit!
    echo.
    pause
    exit /b 1
)

"%PYTHON_EXE%" app.py
