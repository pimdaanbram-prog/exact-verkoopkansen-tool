#!/bin/bash
cd "$(dirname "$0")"
clear
echo ""
echo "========================================"
echo "  Exact Online - Verkoopkansen Invuller"
echo "========================================"
echo ""

# Controleer of playwright al geinstalleerd is
if ! python3 -c "import playwright" 2>/dev/null; then
    echo "📦  Eerste keer opstarten - even installeren..."
    pip3 install playwright 2>/dev/null || pip3 install playwright --break-system-packages
    python3 -m playwright install chromium
    echo "✅  Installatie klaar!"
    echo ""
fi

python3 exact_autofill.py
