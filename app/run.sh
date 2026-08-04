#!/usr/bin/env bash
set -euo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$APP_DIR/.." && pwd)"
export PYTHONPATH="$ROOT/src:${PYTHONPATH:-}"
exec streamlit run "$APP_DIR/app.py" "$@"
