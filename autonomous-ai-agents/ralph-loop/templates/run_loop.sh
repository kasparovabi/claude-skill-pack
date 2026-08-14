#!/usr/bin/env bash
# Ralph Loop runner — fresh Claude Code session per iteration.
# Stops on: state/STOP file, MAX_ITERS reached, or reports/final.md created by the agent.
#
# Adapt:
#   WD=<your project root>
#   MAX_ITERS, MAX_TURNS_PER_ITER, SLEEP_BETWEEN via env vars
#   The model flag (--model sonnet) and tool restrictions if needed
set -uo pipefail

WD="${WD:-/path/to/your/project}"
PROMPT="$WD/PROMPT.md"
LOG_DIR="$WD/logs"
mkdir -p "$LOG_DIR"  # critical: nohup redirects fail silently if dir is missing

MAX_ITERS="${MAX_ITERS:-500}"
MAX_TURNS_PER_ITER="${MAX_TURNS_PER_ITER:-80}"
SLEEP_BETWEEN="${SLEEP_BETWEEN:-5}"
MODEL="${MODEL:-sonnet}"

cd "$WD" || exit 1

for i in $(seq 1 "$MAX_ITERS"); do
  if [[ -f "$WD/state/STOP" ]]; then
    echo "[$(date -u +%FT%TZ)] STOP file detected, exiting loop." | tee -a "$LOG_DIR/loop.log"
    break
  fi

  TS="$(date -u +%Y%m%dT%H%M%SZ)"
  ITER_LOG="$LOG_DIR/iter_${TS}.log"
  echo "[$(date -u +%FT%TZ)] === Iter wrapper $i / $MAX_ITERS starting ===" | tee -a "$LOG_DIR/loop.log"

  claude -p "Read $PROMPT in full and execute exactly ONE iteration following section 4 (or section 11 BOOTSTRAP if iter_count==0). Update all state files. Then exit." \
    --dangerously-skip-permissions \
    --permission-mode bypassPermissions \
    --max-turns "$MAX_TURNS_PER_ITER" \
    --model "$MODEL" \
    --output-format text \
    --no-session-persistence \
    > "$ITER_LOG" 2>&1
  EC=$?

  echo "[$(date -u +%FT%TZ)] === Iter wrapper $i finished (exit=$EC) log=$ITER_LOG ===" | tee -a "$LOG_DIR/loop.log"

  if [[ -f "$WD/state/STOP" ]]; then
    echo "[$(date -u +%FT%TZ)] STOP file detected after iter, exiting." | tee -a "$LOG_DIR/loop.log"
    break
  fi

  if [[ -f "$WD/reports/final.md" ]]; then
    echo "[$(date -u +%FT%TZ)] reports/final.md exists — loop self-terminated." | tee -a "$LOG_DIR/loop.log"
    break
  fi

  sleep "$SLEEP_BETWEEN"
done

echo "[$(date -u +%FT%TZ)] Loop runner exiting." | tee -a "$LOG_DIR/loop.log"
