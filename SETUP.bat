@echo off
cd /d "%~dp0"
title Exact Tool - Installatie

echo.
echo ================================================
echo   Exact Verkoopkansen Tool - Installatie
echo ================================================
echo.

set PYTHON_DIR=%~dp0_python
set PYTHON_EXE=%PYTHON_DIR%\python.exe
set BROWSERS_DIR=%~dp0_browsers

if exist "%PYTHON_EXE%" (
    echo Al geinstalleerd! Gebruik START.bat om te starten.
    echo.
    pause
    exit /b 0
)

echo Benodigdheden: internet, ca. 200 MB ruimte, 5 minuten.
echo.
echo Druk op een toets om te beginnen...
pause >nul

echo.
echo [1/5] Python downloaden...
powershell -NoProfile -ExecutionPolicy Bypass -Command "& {[Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip' -OutFile '_py.zip'}"
if not exist "_py.zip" (
    echo FOUT: download mislukt. Controleer je internetverbinding.
    pause
    exit /b 1
)

echo [2/5] Python installeren...
mkdir "%PYTHON_DIR%" 2>nul
mkdir "%PYTHON_DIR%\Lib\site-packages" 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '_py.zip' -DestinationPath '%PYTHON_DIR%' -Force"
del "_py.zip"

for %%f in ("%PYTHON_DIR%\python*._pth") do (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "(Get-Content '%%f') -replace '#import site','import site' | Set-Content '%%f'"
    echo Lib\site-packages>> "%%f"
)

echo [3/5] pip installeren...
powershell -NoProfile -ExecutionPolicy Bypass -Command "& {[Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '_pip.py'}"
if not exist "_pip.py" (
    echo FOUT: pip download mislukt.
    pause
    exit /b 1
)
"%PYTHON_EXE%" _pip.py --quiet --no-warn-script-location
del "_pip.py"

echo [4/5] Flask en Playwright installeren...
"%PYTHON_EXE%" -m pip install flask playwright --no-user --quiet --no-warn-script-location
if errorlevel 1 (
    echo FOUT: packages installeren mislukt.
    pause
    exit /b 1
)

echo [5/5] Chromium browser installeren (ca. 150 MB)...
set PLAYWRIGHT_BROWSERS_PATH=%BROWSERS_DIR%
"%PYTHON_EXE%" -m playwright install chromium
if errorlevel 1 (
    echo FOUT: browser installeren mislukt.
    pause
    exit /b 1
)

echo.
echo ================================================
echo   Installatie geslaagd!
echo   Dubbelklik START.bat om de app te starten.
echo ================================================
echo.
pause
