#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
if [ ! -d .venv ]; then python -m venv .venv; fi
. .venv/bin/activate
pip install -r requirements-build.txt
pyinstaller pyinstaller_backend.spec --noconfirm --clean
echo "Backend bundle at $ROOT/backend/dist/tax-calculator-backend"
