#!/usr/bin/env bash
# NeuraRoute v2 — one-command dev stack (the whole system on one laptop, no hardware).
#
#   ./scripts/dev_up.sh
#
# Starts, in order:  mosquitto broker -> mock LLM (:1234) -> engine (:8000)
#                    -> 4 tier agents (cloud, pc, phone, arduino)
# Then point the phone app (mobile/) at this laptop's IP and submit readings.
#
# Env overrides:
#   NEURAROUTE_LOCAL_BASE_URL   real LM Studio URL for the pc/phone tiers (skips the mock LLM)
#   NEURAROUTE_CLOUD_MOCK=false + NEURAROUTE_CLOUD_BASE_URL/API_KEY   real GPT for the cloud tier
#   NEURAROUTE_PORT             engine port (default 8000)
#
# Ctrl-C tears everything down.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PIDS_DIR="$REPO_ROOT/run/pids"
LOGS_DIR="$REPO_ROOT/run/logs"
mkdir -p "$PIDS_DIR" "$LOGS_DIR"

# Prefer the repo venv's python so deps are guaranteed present.
if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
  PY="$REPO_ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
else
  PY="python"
fi

export NEURAROUTE_BROKER="${NEURAROUTE_BROKER:-localhost}"
export NEURAROUTE_PORT="${NEURAROUTE_PORT:-8080}"   # 8000/8001 belong to the /infer servers
export NEURAROUTE_CLOUD_MOCK="${NEURAROUTE_CLOUD_MOCK:-true}"
export NEURAROUTE_REGISTRY="${NEURAROUTE_REGISTRY:-dev}"   # 'venue' -> real /infer servers

started=()
launch() {  # name  command
  local name="$1" cmd="$2"
  local log="$LOGS_DIR/$name.log" pid="$PIDS_DIR/$name.pid"
  : > "$log"
  bash -lc "$cmd" >>"$log" 2>&1 &
  echo $! > "$pid"
  started+=("$name:$!")
  printf '  %-12s pid %-7s log %s\n' "$name" "$!" "$log"
}

cleanup() {
  echo; echo "Stopping..."
  for pf in "$PIDS_DIR"/*.pid; do
    [[ -f "$pf" ]] || continue
    local_pid="$(cat "$pf")"
    kill "$local_pid" 2>/dev/null || true
    rm -f "$pf"
  done
  echo "Down."
}
trap cleanup INT TERM

# 1) broker
if ! nc -z localhost 1883 >/dev/null 2>&1; then
  if command -v mosquitto >/dev/null 2>&1; then
    mosquitto -d; sleep 1
    echo "  mosquitto    started on :1883"
  else
    echo "ERROR: mosquitto not found (brew install mosquitto)"; exit 1
  fi
else
  echo "  mosquitto    already up on :1883"
fi

# 2) mock LLM for the local tiers — unless a real LM Studio URL is provided
if [[ -z "${NEURAROUTE_LOCAL_BASE_URL:-}" ]]; then
  export NEURAROUTE_LOCAL_BASE_URL="http://localhost:1234/v1"
  launch "mock_llm" "cd '$REPO_ROOT' && exec '$PY' tools/mock_llm.py 1234"
  sleep 1
else
  echo "  local LLM    using $NEURAROUTE_LOCAL_BASE_URL (mock LLM skipped)"
fi

# 3) engine
launch "engine" "cd '$REPO_ROOT' && exec '$PY' -m engine.app"
sleep 2

# 4) the four tiers of the ladder. PID files are keyed by device_id so
#    kill_device.sh <device_id> can hard-kill a tier on cue (the failover demo).
for cfg in cloud:cloud-01 pc:pc-01 phone:phone-01 arduino:arduino-01; do
  file="${cfg%%:*}"; did="${cfg##*:}"
  launch "$did" "cd '$REPO_ROOT' && exec '$PY' runtime/agent.py runtime/configs/$file.yaml"
  sleep 0.4
done

echo
echo "NeuraRoute up (registry=$NEURAROUTE_REGISTRY). Engine: http://$(ipconfig getifaddr en0 2>/dev/null || echo localhost):${NEURAROUTE_PORT}"
if [[ "$NEURAROUTE_REGISTRY" == "venue" ]]; then
  echo "  venue mode: laptop tier -> ${NEURAROUTE_INFER_LAPTOP_URL:-http://localhost:8000/infer}, cloud tier -> ${NEURAROUTE_INFER_CLOUD_URL:-http://localhost:8001/infer}"
  echo "  (make sure the /infer inference servers are running separately)"
fi
echo "Phone app: cd mobile && npx expo start   (phone on this laptop's hotspot)"
echo "Submit a reading:"
echo "  curl -XPOST localhost:${NEURAROUTE_PORT}/request -H 'Content-Type: application/json' \\"
echo "       -d '{\"patient_id\":\"P-03\",\"vitals\":{\"hr\":176,\"spo2\":79,\"temp_c\":37,\"resp_rate\":32}}'"
echo "Kill a tier (drive the failover):  ./scripts/kill_device.sh cloud-01"
echo "Ctrl-C to stop everything."
echo
# wait forever (until Ctrl-C)
while true; do sleep 3600; done
