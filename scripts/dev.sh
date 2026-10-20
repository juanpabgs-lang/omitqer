#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$ROOT"
mkdir -p "$HOME/Norfront/demos"
ln -sfn "$ROOT" "$HOME/Norfront/demos/omint-reintegros"

if [[ ! -f "$ROOT/data/omint.db" ]]; then
  echo "Seeding synthetic world…"
  python3 -m backend.app.seed
fi

if [[ ! -d "$ROOT/frontend/node_modules" ]]; then
  (cd "$ROOT/frontend" && npm install)
fi

SESSION=omint-reintegros
tmux -f /exec-daemon/tmux.portal.conf has-session -t "=$SESSION" 2>/dev/null && tmux -f /exec-daemon/tmux.portal.conf kill-session -t "$SESSION"
tmux -f /exec-daemon/tmux.portal.conf new-session -d -s "$SESSION" -c "$ROOT" -- bash -lc "python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8018"
tmux -f /exec-daemon/tmux.portal.conf new-window -t "$SESSION" -c "$ROOT/frontend" -- bash -lc "npm run dev"
echo "API  http://127.0.0.1:8018"
echo "UI   http://127.0.0.1:5178"
echo "tmux attach -t $SESSION"
