#!/usr/bin/env sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' || {
  echo "Please install Python 3.10 or newer."
  exit 1
}
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install -r requirements.txt
echo "Open http://127.0.0.1:5000 after startup. Press Ctrl+C to stop."
exec .venv/bin/python -u app.py
