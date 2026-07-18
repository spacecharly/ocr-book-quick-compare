#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_VENV="$ROOT_DIR/.venv"
CAPTURE_DIR="$ROOT_DIR/capture-app"
CAPTURE_VENV="$CAPTURE_DIR/.venv"

SKIP_MODEL=0
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: ./bootstrap.sh [options]

Prepare both local virtual environments and install dependencies:
- root web app venv: .venv
- capture app venv: capture-app/.venv

Options:
  --skip-model   Skip Vosk model download step
  --dry-run      Print commands without executing them
  -h, --help     Show this help
EOF
}

run_cmd() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '[dry-run] %s\n' "$*"
  else
    eval "$@"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-model)
      SKIP_MODEL=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n\n' "$1"
      usage
      exit 1
      ;;
  esac
done

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 not found in PATH"
  exit 1
fi

if [[ ! -d "$CAPTURE_DIR" ]]; then
  echo "Error: capture-app directory not found at $CAPTURE_DIR"
  exit 1
fi

echo "[1/5] Creating/updating web app virtualenv: $WEB_VENV"
run_cmd "python3 -m venv \"$WEB_VENV\""
run_cmd "\"$WEB_VENV/bin/python\" -m pip install --upgrade pip"
run_cmd "\"$WEB_VENV/bin/pip\" install -r \"$ROOT_DIR/requirements.txt\""

echo "[2/5] Creating/updating capture app virtualenv: $CAPTURE_VENV"
run_cmd "python3 -m venv \"$CAPTURE_VENV\""
run_cmd "\"$CAPTURE_VENV/bin/python\" -m pip install --upgrade pip"
run_cmd "\"$CAPTURE_VENV/bin/pip\" install -r \"$CAPTURE_DIR/requirements.txt\""

if [[ "$SKIP_MODEL" -eq 1 ]]; then
  echo "[3/5] Skipping Vosk model download (--skip-model)"
else
  echo "[3/5] Downloading Vosk model for voice trigger"
  run_cmd "\"$CAPTURE_VENV/bin/python\" \"$CAPTURE_DIR/download_vosk_model.py\""
fi

echo "[4/5] Checking Python syntax"
run_cmd "\"$WEB_VENV/bin/python\" -m py_compile \"$ROOT_DIR/app.py\" \"$ROOT_DIR/tests/test_app.py\""
run_cmd "\"$CAPTURE_VENV/bin/python\" -m py_compile \"$CAPTURE_DIR/main.py\" \"$CAPTURE_DIR/capture_core.py\" \"$CAPTURE_DIR/voice_trigger.py\""

echo "[5/5] Running companion app smoke tests"
run_cmd "\"$CAPTURE_VENV/bin/python\" -m unittest discover -s \"$CAPTURE_DIR/tests\""

echo
cat <<EOF
Bootstrap complete.

Run web app:
  source "$WEB_VENV/bin/activate"
  python3 "$ROOT_DIR/app.py"

Run capture app manually:
  source "$CAPTURE_VENV/bin/activate"
  python3 "$CAPTURE_DIR/main.py"
EOF

