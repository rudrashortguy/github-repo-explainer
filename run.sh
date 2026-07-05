#!/usr/bin/env bash
set -e

# Safety: only run from inside the project root
case "$(pwd)" in
  */github-repo-explainer) ;;
  *) echo "ERROR: run.sh must be executed from within github-repo-explainer"; exit 1 ;;
esac

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
  echo "=== Cleaning up temp clones ==="
  rm -rf "$PROJECT_ROOT/backend/temp_clones/"*
  echo "=== Cleanup done ==="
}
trap cleanup EXIT

kill_port() { lsof -ti:"$1" 2>/dev/null | xargs -r kill -9; }

VENV_DIR="$PROJECT_ROOT/backend/venv"
if [ ! -d "$VENV_DIR" ]; then
  echo "=== Setting up venv ==="
  python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install -r "$PROJECT_ROOT/backend/requirements.txt" -q

echo "=== Installing frontend deps ==="
cd "$PROJECT_ROOT/frontend"
npm install --silent

echo "=== Killing old processes on 8000 and 5173 ==="
kill_port 8000
kill_port 5173

echo "=== Starting backend on :8000 ==="
cd "$PROJECT_ROOT/backend"
"$VENV_DIR/bin/uvicorn" main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

echo "=== Starting frontend on :5173 ==="
cd "$PROJECT_ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "Press Ctrl+C to stop both."
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; cleanup; exit" INT TERM
wait
