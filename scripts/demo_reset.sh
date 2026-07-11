#!/usr/bin/env bash
# Usage:
#   ./scripts/demo_reset.sh
# Run this from the repository root between rehearsal takes to reset the local
# runtime stack to a clean starting point.

set -euo pipefail

START_TIME="$(date +%s)"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIDS_DIR="$REPO_ROOT/run/pids"
LOGS_DIR="$REPO_ROOT/run/logs"
ARCHIVE_DIR="$LOGS_DIR/archive"

mkdir -p "$PIDS_DIR" "$LOGS_DIR" "$ARCHIVE_DIR"

if compgen -G "$PIDS_DIR"/*.pid >/dev/null 2>&1; then
  for pid_file in "$PIDS_DIR"/*.pid; do
    if [[ -f "$pid_file" ]]; then
      pid="$(cat "$pid_file")"
      if [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1; then
        kill -9 "$pid" 2>/dev/null || true
      fi
      rm -f "$pid_file"
    fi
  done
fi

if compgen -G "$LOGS_DIR"/* >/dev/null 2>&1; then
  TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
  ARCHIVE_SUBDIR="$ARCHIVE_DIR/$TIMESTAMP"
  mkdir -p "$ARCHIVE_SUBDIR"
  mv "$LOGS_DIR"/* "$ARCHIVE_SUBDIR"/ 2>/dev/null || true
fi

# Simulated telemetry overrides live in each agent process memory, so restarting
# the agents is the reset mechanism for their scripted drain timers and battery
# override state.

if [[ -x "$REPO_ROOT/scripts/dev_up.sh" ]]; then
  if ! bash "$REPO_ROOT/scripts/dev_up.sh"; then
    echo "Error: dev_up.sh failed; check $LOGS_DIR for details" >&2
    exit 1
  fi
else
  echo "Error: scripts/dev_up.sh not found" >&2
  exit 1
fi

END_TIME="$(date +%s)"
ELAPSED=$((END_TIME - START_TIME))

echo "Demo reset complete in ${ELAPSED}s"
if (( ELAPSED > 60 )); then
  echo "WARNING: reset took longer than 60 seconds" >&2
fi

echo "Note: real models (LM Studio / GPT / UNO Q SLM) reset on their own hosts"
