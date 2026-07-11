#!/usr/bin/env bash
# Usage:
#   ./scripts/kill_device.sh <device_id>
# Hard-kill a tier's agent so it stops heartbeating — the engine marks it stale after
# ~3 s and the next reading slides down the connectivity ladder. This is the on-stage
# failover trigger. e.g.  ./scripts/kill_device.sh cloud-01
#
# (v2 has no telemetry/battery override, so there is no "soft" kill — a tier is either
#  running or it isn't.)

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: ./scripts/kill_device.sh <device_id>   (e.g. cloud-01)" >&2
  exit 1
fi

DEVICE_ID="$1"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$REPO_ROOT/run/pids/${DEVICE_ID}.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "Error: PID file not found for $DEVICE_ID at $PID_FILE" >&2
  echo "  (is the stack running? did dev_up.sh start this tier?)" >&2
  exit 1
fi

PID="$(cat "$PID_FILE")"
if [[ -z "$PID" ]]; then
  echo "Error: empty PID in $PID_FILE" >&2
  exit 1
fi

if ! kill -0 "$PID" >/dev/null 2>&1; then
  echo "Error: process $PID for $DEVICE_ID is already dead" >&2
  rm -f "$PID_FILE"
  exit 1
fi

kill -9 "$PID"
rm -f "$PID_FILE"
echo "[$(date '+%H:%M:%S')] Hard-killed $DEVICE_ID (PID $PID) — next reading fails over down the ladder"
