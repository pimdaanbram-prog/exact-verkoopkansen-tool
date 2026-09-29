#!/bin/bash
# Start de Exact Verkoopkansen Tool zonder app te bouwen.
cd "$(dirname "$0")"
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif ! python3 -c "import flask, playwright" 2>/dev/null; then
    echo "Eerste keer opstarten - even installeren..."
    python3 -m venv .venv && source .venv/bin/activate
    python -m pip install flask playwright --quiet
    python -m playwright install chromium
fi
python3 app.py
