@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Exact Tool - Installatie
chcp 65001 >nul

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║     Exact Verkoopkansen Tool  -  Installatie     ║
echo  ╚══════════════════════════════════════════════════╝
echo.

set PYTHON_DIR=%~dp0_python
set PYTHON_EXE=%PYTHON_DIR%\python.exe
set BROWSERS_DIR=%~dp0_browsers

if exist "%PYTHON_EXE%" (
    echo  Al geinstalleerd!
    echo  Gebruik START.bat om de app te openen.
    echo.
    pause
    exit /b 0
)

echo  Benodigdheden: internetverbinding, ca. 200 MB ruimte.
echo  Dit duurt 3-6 minuten.
echo.
pause

:: ── Stap 1: Python downloaden ─────────────────────────────────────────────
echo.
echo  [1/5] Python downloaden...
powershell -NoProfile -Command ^
  "& {[Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip' -OutFile '_py.zip'}"
if not exist "_py.zip" (
    echo.
    echo  FOUT: Download mislukt. Controleer je internetverbinding.
    pause & exit /b 1
)

:: ── Stap 2: Python uitpakken ──────────────────────────────────────────────
echo  [2/5] Python installeren...
mkdir "%PYTHON_DIR%" 2>nul
powershell -NoProfile -Command "Expand-Archive -Path '_py.zip' -DestinationPath '%PYTHON_DIR%' -Force"
del "_py.zip"

:: Site-packages inschakelen (nodig voor pip)
for %%f in ("%PYTHON_DIR%\python*._pth") do (
    powershell -NoProfile -Command ^
      "(Get-Content '%%f') -replace '#import site','import site' | Set-Content '%%f'"
)

:: ── Stap 3: pip installeren ───────────────────────────────────────────────
echo  [3/5] pip installeren...
powershell -NoProfile -Command ^
  "& {[Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '_pip.py'}"
"%PYTHON_EXE%" _pip.py --quiet
del "_pip.py"

:: ── Stap 4: Python packages ───────────────────────────────────────────────
echo  [4/5] Packages installeren (flask, playwright)...
"%PYTHON_EXE%" -m pip install flask playwright --quiet

:: ── Stap 5: Chromium browser ──────────────────────────────────────────────
echo  [5/5] Browser installeren (ca. 150 MB)...
set PLAYWRIGHT_BROWSERS_PATH=%BROWSERS_DIR%
"%PYTHON_EXE%" -m playwright install chromium

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║          Installatie geslaagd!                   ║
echo  ║   Dubbelklik op START.bat om de app te starten.  ║
echo  ╚══════════════════════════════════════════════════╝
echo.
pause
