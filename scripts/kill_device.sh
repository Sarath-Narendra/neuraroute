#!/usr/bin/env bash
# Usage:
#   ./scripts/kill_device.sh <device_id> [--mode hard|soft]
# Run this from the repository root to emulate a device going offline.

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: ./scripts/kill_device.sh <device_id> [--mode hard|soft]" >&2
  exit 1
fi

DEVICE_ID="$1"
MODE="hard"

if [[ $# -ge 2 ]]; then
  if [[ "$2" == "--mode" && $# -ge 3 ]]; then
    MODE="$3"
  else
    echo "Usage: ./scripts/kill_device.sh <device_id> [--mode hard|soft]" >&2
    exit 1
  fi
fi

if [[ "$MODE" != "hard" && "$MODE" != "soft" ]]; then
  echo "Error: unsupported mode '$MODE'" >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIDS_DIR="$REPO_ROOT/run/pids"
PID_FILE="$PIDS_DIR/${DEVICE_ID}.pid"

BROKER_VALUE="${NEURAROUTE_BROKER:-localhost:1883}"
BROKER_HOST="${BROKER_VALUE%%:*}"
BROKER_PORT="${BROKER_VALUE##*:}"

if [[ "$MODE" == "hard" ]]; then
  if [[ ! -f "$PID_FILE" ]]; then
    echo "Error: PID file not found for $DEVICE_ID at $PID_FILE" >&2
    exit 1
  fi

  PID="$(cat "$PID_FILE")"
  if [[ -z "$PID" ]]; then
    echo "Error: empty PID in $PID_FILE" >&2
    exit 1
  fi

  if ! kill -0 "$PID" >/dev/null 2>&1; then
    echo "Error: process $PID for $DEVICE_ID is already dead" >&2
    exit 1
  fi

  kill -9 "$PID"
  rm -f "$PID_FILE"
  echo "[$(date '+%H:%M:%S')] Hard-killed $DEVICE_ID (PID $PID)"
  exit 0
fi

if ! command -v mosquitto_pub >/dev/null 2>&1; then
  echo "Error: mosquitto_pub not found; install mosquitto or use --mode hard" >&2
  exit 1
fi

PAYLOAD="{\"command\": \"simulate_battery_critical\", \"device_id\": \"$DEVICE_ID\"}"
mosquitto_pub -h "$BROKER_HOST" -p "$BROKER_PORT" -t "neuraroute/admin" -m "$PAYLOAD"

echo "[$(date '+%H:%M:%S')] Soft-killed $DEVICE_ID via neuraroute/admin"