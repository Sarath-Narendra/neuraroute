#!/usr/bin/env bash
# dev_up.sh -- bring up the full NeuraRoute system on one laptop (simulated devices).
# Starts: mosquitto broker (if local) -> engine -> 3 fake devices. Ctrl-C tears it all down.
#
#   ./scripts/dev_up.sh                 # 3 default devices: pc-01 phone-01 cloud-01
#   ./scripts/dev_up.sh pc-01 phone-01 arduino-01 cloud-01
#   NEURAROUTE_BROKER=192.168.1.5 ./scripts/dev_up.sh   # use an external broker
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export NEURAROUTE_BROKER="${NEURAROUTE_BROKER:-localhost}"
PY="python3"
[ -x ".venv/bin/python" ] && PY=".venv/bin/python"

DEVICES=("$@")
[ ${#DEVICES[@]} -eq 0 ] && DEVICES=("pc-01" "phone-01" "cloud-01")

PIDS=()
BROKER_PID=""
cleanup() {
  echo
  echo "[dev_up] shutting down..."
  for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
  [ -n "$BROKER_PID" ] && kill "$BROKER_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# 1. broker (only if we're the ones hosting it)
if [ "$NEURAROUTE_BROKER" = "localhost" ] || [ "$NEURAROUTE_BROKER" = "127.0.0.1" ]; then
  if command -v mosquitto >/dev/null 2>&1; then
    echo "[dev_up] starting mosquitto on :1883"
    mosquitto -p 1883 >/tmp/neuraroute-mosquitto.log 2>&1 &
    BROKER_PID=$!
    sleep 1
  else
    echo "[dev_up] ERROR: mosquitto not found. Install it (brew install mosquitto) or set NEURAROUTE_BROKER." >&2
    exit 1
  fi
else
  echo "[dev_up] using external broker at $NEURAROUTE_BROKER"
fi

# 2. engine
echo "[dev_up] starting engine (http://localhost:${NEURAROUTE_PORT:-8000})"
"$PY" -m engine.app &
PIDS+=("$!")
sleep 2

# 3. fake devices
for d in "${DEVICES[@]}"; do
  echo "[dev_up] starting device $d"
  "$PY" -m contracts.fake_device "$d" &
  PIDS+=("$!")
  sleep 0.3
done

echo "[dev_up] up. devices: ${DEVICES[*]}"
echo "[dev_up] kill one with:  ./scripts/kill_device.sh <device_id>   (Ctrl-C stops everything)"
wait
