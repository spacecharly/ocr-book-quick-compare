#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_FLASK="$PROJECT_DIR/.venv/bin/flask"
PORT="${PORT:-5001}"

if [[ ! -x "$VENV_FLASK" ]]; then
  echo "Erreur: Flask n'est pas disponible dans .venv. Lance d'abord:"
  echo "  cd \"$PROJECT_DIR\" && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

# Stop any existing app started from this project on the same port (ignore unrelated listeners).
if command -v lsof >/dev/null 2>&1; then
  while read -r pid cmd; do
    [[ -z "${pid:-}" ]] && continue
    if ps -p "$pid" -o command= | grep -E "(/app\.py|flask --app app|python .*app\.py)" >/dev/null 2>&1; then
      echo "Arrêt du serveur existant (PID $pid)..."
      kill "$pid" || true
    fi
  done < <(lsof -nP -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | while read -r pid; do
    echo "$pid"
  done)
fi

cd "$PROJECT_DIR"
export FLASK_APP="app"
exec "$VENV_FLASK" --app app run --debug --port "$PORT"

