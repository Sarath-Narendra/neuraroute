#!/usr/bin/env bash
# Expected usage:
#   ./scripts/dev_up.sh
# Run this from the repository root. It starts Mosquitto (if needed), launches
# the runtime device agents from runtime/configs/*.yaml, and prints the PID/log
# status for each process it starts.
# Note: this is intended to work on macOS/Linux and in Git Bash/WSL on Windows.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PIDS_DIR="$REPO_ROOT/run/pids"
LOGS_DIR="$REPO_ROOT/run/logs"

mkdir -p "$PIDS_DIR" "$LOGS_DIR"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Error: python not found in PATH" >&2
  exit 1
fi

if [[ -n "${NEURAROUTE_BROKER:-}" ]]; then
  export NEURAROUTE_BROKER
else
  export NEURAROUTE_BROKER="localhost:1883"
fi

broker_up() {
  if command -v nc >/dev/null 2>&1; then
    if nc -z localhost 1883 >/dev/null 2>&1; then
      return 0
    fi
  fi

  if command -v pgrep >/dev/null 2>&1; then
    if pgrep -af "mosquitto" >/dev/null 2>&1; then
      return 0
    fi
  else
    if ps -ef | grep -v grep | grep -q "mosquitto"; then
      return 0
    fi
  fi

  if command -v mosquitto >/dev/null 2>&1; then
    mosquitto -d
    sleep 1
    if command -v nc >/dev/null 2>&1; then
      if nc -z localhost 1883 >/dev/null 2>&1; then
        echo "Mosquitto started on localhost:1883"
        return 0
      fi
    fi
    echo "Error: Mosquitto was launched but localhost:1883 is not accepting connections" >&2
    exit 1
  fi

  echo "Error: Mosquitto could not be started; install mosquitto or start it manually" >&2
  exit 1
}

cleanup() {
  echo "Stopping launched processes..."
  if compgen -G "$PIDS_DIR"/*.pid >/dev/null 2>&1; then
    for pid_file in "$PIDS_DIR"/*.pid; do
      if [[ -f "$pid_file" ]]; then
        pid="$(cat "$pid_file")"
        if [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1; then
          kill "$pid" 2>/dev/null || true
        fi
        rm -f "$pid_file"
      fi
    done
  fi
  echo "Cleanup complete"
}
trap cleanup INT TERM

broker_up

started_entries=()
launch_process() {
  local name="$1"
  local command="$2"
  local log_file="$3"
  local pid_file="$4"

  mkdir -p "$(dirname "$log_file")"
  : > "$log_file"
  bash -lc "$command" >>"$log_file" 2>&1 &
  local pid=$!
  echo "$pid" > "$pid_file"
  started_entries+=("$name|$pid|$log_file|$pid_file")
  echo "Started $name (PID $pid, log $log_file)"
}

for config in "$REPO_ROOT"/runtime/configs/*.yaml; do
  if [[ ! -f "$config" ]]; then
    continue
  fi
  device_id="$("$PYTHON_BIN" - <<'PY' "$config"
import sys, yaml
from pathlib import Path
with open(sys.argv[1], 'r', encoding='utf-8') as handle:
    data = yaml.safe_load(handle) or {}
print(data.get('device_id', Path(sys.argv[1]).stem))
PY
)"
  log_file="$LOGS_DIR/${device_id}.log"
  pid_file="$PIDS_DIR/${device_id}.pid"
  launch_process "$device_id" "cd '$REPO_ROOT' && '$PYTHON_BIN' runtime/agent.py '$config'" "$log_file" "$pid_file"
  sleep 0.5
done

if [[ -f "$REPO_ROOT/contracts/fake_engine.py" ]]; then
  launch_process "fake_engine" "cd '$REPO_ROOT' && '$PYTHON_BIN' contracts/fake_engine.py" "$LOGS_DIR/fake_engine.log" "$PIDS_DIR/fake_engine.pid"
else
  echo "fake_engine.py not found yet — skipping, ask Sarath"
fi

printf '\nStarted processes:\n'
printf '%-20s %-8s %s\n' "device_id" "PID" "log_file"
for entry in "${started_entries[@]}"; do
  IFS='|' read -r name pid log_file _ <<< "$entry"
  printf '%-20s %-8s %s\n' "$name" "$pid" "$log_file"
done
