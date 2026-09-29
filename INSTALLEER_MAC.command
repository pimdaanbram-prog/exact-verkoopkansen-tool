#!/bin/bash
# Exact Verkoopkansen Tool - installatie op de Mac
# Dubbelklik dit bestand. Het maakt 'ExactTool.app' en zet die in Programma's.
cd "$(dirname "$0")"
clear
echo ""
echo "================================================"
echo "  Exact Verkoopkansen Tool - Mac installatie"
echo "================================================"
echo ""

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 is niet gevonden."
    echo "Er verschijnt zo een venster om de Apple ontwikkelaarstools te installeren."
    echo "Klik op 'Installeer', wacht tot het klaar is en dubbelklik dit bestand opnieuw."
    xcode-select --install 2>/dev/null
    read -p "Druk Enter om te sluiten..."
    exit 1
fi

set -e
echo "[1/4] Python omgeving maken..."
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip --quiet

echo "[2/4] Flask, Playwright en PyInstaller installeren..."
python -m pip install flask playwright pyinstaller --quiet

echo "[3/4] Chromium browser installeren (eenmalig, ca. 150 MB)..."
python -m playwright install chromium

echo "[4/4] ExactTool.app bouwen (1-3 minuten)..."
rm -rf build dist ExactTool.spec
python -m PyInstaller \
    --noconfirm \
    --windowed \
    --name "ExactTool" \
    --collect-all playwright \
    --hidden-import flask \
    --add-data "bedrijven_data.json:." \
    app.py >/dev/null

if [ ! -d "dist/ExactTool.app" ]; then
    echo ""
    echo "MISLUKT - geen app gebouwd. Start de tool dan met START.command."
    read -p "Druk Enter om te sluiten..."
    exit 1
fi

mkdir -p "$HOME/Documents/ExactTool"
cp -n bedrijven_data.json "$HOME/Documents/ExactTool/" 2>/dev/null || true

if rm -rf "/Applications/ExactTool.app" 2>/dev/null && cp -R "dist/ExactTool.app" "/Applications/" 2>/dev/null; then
    PLEK="/Applications/ExactTool.app"
else
    mkdir -p "$HOME/Applications"
    rm -rf "$HOME/Applications/ExactTool.app"
    cp -R "dist/ExactTool.app" "$HOME/Applications/"
    PLEK="$HOME/Applications/ExactTool.app"
fi

echo ""
echo "================================================"
echo "  KLAAR!"
echo "  De app staat in: $PLEK"
echo "  Logs en opgeslagen voortgang: ~/Documents/ExactTool"
echo "  Tip: sleep de app naar je Dock."
echo "================================================"
echo ""
open "$PLEK"
read -p "Druk Enter om te sluiten..."
