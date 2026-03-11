#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/node/.openclaw/workspace/pi-blog-demo"
LOG_DIR="/home/node/.openclaw/workspace/tmp"
mkdir -p "$LOG_DIR"
RUN_TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_PATH="$LOG_DIR/rss-autopublish-${RUN_TS}.log"

cd "$ROOT"

echo "[run-rss-autopublish] start ${RUN_TS}" | tee "$LOG_PATH"
export GITHUB_TOKEN=
export GH_TOKEN=
export PYTHONUNBUFFERED=1

(
  stdbuf -oL -eL python3 tools/rss_autopublish_orchestrator.py \
    --articles "$ROOT/articles.json" \
    --allow-publish \
    --pi-timeout 420 \
    --pi-limit 4 \
    --max-items 3 \
    --git-commit \
    --git-push \
    --strict-publish \
    "$@" 2>&1 | tee -a "$LOG_PATH"
) &
PID=$!

# Heartbeat to avoid "no output" watchdogs
while kill -0 "$PID" 2>/dev/null; do
  sleep 30
  echo "[run-rss-autopublish] heartbeat $(date -u +%H:%M:%S)" | tee -a "$LOG_PATH"
done

wait "$PID"
STATUS=$?
echo "[run-rss-autopublish] exit ${STATUS}" | tee -a "$LOG_PATH"
exit "$STATUS"
