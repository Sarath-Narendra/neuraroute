#!/usr/bin/env bash
# NeuraRoute — the inference module: bring up the three per-device /infer servers.
#
#   ./scripts/infer_up.sh
#
# Starts:  laptop (GenieX/Qwen) :8000 · cloud (Groq/Llama-70B) :8001 · phone (llama.cpp) :8002
# Each exposes `POST /infer {"patient": "<text>"}`. Point the engine at them with
# NEURAROUTE_REGISTRY=venue (see .env.example) and run ./scripts/dev_up.sh separately.
#
# These are the REAL model servers, so each needs its backend reachable:
#   laptop -> the `geniex` CLI on PATH        (else that tier fails over down the ladder)
#   cloud  -> GROQ_API_KEY in .env            (else the cloud tier fails over)
#   phone  -> NEURAROUTE_PHONE_LLM_URL         (an OpenAI-compatible llama.cpp / LM Studio)
# A server with a missing backend still BOOTS and returns a clean error, so the ladder
# fails over instead of hanging. To verify the wiring with no models at all, skip this
# script and run tools/mock_infer.py on the three ports instead (see README).
#
# Ctrl-C tears everything down.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PIDS_DIR="$REPO_ROOT/run/pids"
LOGS_DIR="$REPO_ROOT/run/logs"
mkdir -p "$PIDS_DIR" "$LOGS_DIR"

# Load .env so GROQ_API_KEY / phone URL / model names live in one file.
if [[ -f "$REPO_ROOT/.env" ]]; then
  set -a; source "$REPO_ROOT/.env"; set +a
  echo "  loaded $REPO_ROOT/.env"
fi

# Prefer the repo venv's python (Windows: .venv/Scripts, macOS/Linux: .venv/bin).
if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
  PY="$REPO_ROOT/.venv/bin/python"
elif [[ -x "$REPO_ROOT/.venv/Scripts/python.exe" ]]; then
  PY="$REPO_ROOT/.venv/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
else
  PY="python"
fi

launch() {  # name  module:app  port
  local name="$1" app="$2" port="$3"
  local log="$LOGS_DIR/$name.log" pid="$PIDS_DIR/$name.pid"
  : > "$log"
  bash -lc "cd '$REPO_ROOT' && exec '$PY' -m uvicorn $app --host 0.0.0.0 --port $port" >>"$log" 2>&1 &
  echo $! > "$pid"
  printf '  %-14s pid %-7s :%s   log %s\n' "$name" "$!" "$port" "$log"
}

cleanup() {
  echo; echo "Stopping /infer servers..."
  for name in infer_laptop infer_cloud infer_phone; do
    pf="$PIDS_DIR/$name.pid"
    [[ -f "$pf" ]] || continue
    kill "$(cat "$pf")" 2>/dev/null || true
    rm -f "$pf"
  done
  echo "Down."
}
trap cleanup INT TERM

echo "NeuraRoute inference module — starting /infer servers:"
launch "infer_laptop" "servers.laptop_server:app" 8000
launch "infer_cloud"  "servers.cloud_server:app"  8001
launch "infer_phone"  "servers.phone_server:app"  8002

echo
echo "Up. Verify a tier:"
echo "  curl -s localhost:8001/infer -H 'Content-Type: application/json' \\"
echo "       -d '{\"patient\":\"Patient P-03. CURRENT sensor reading: hr 176, spo2 79, temp_c 37, resp_rate 32.\"}'"
echo "Then start the engine in venue mode:  NEURAROUTE_REGISTRY=venue ./scripts/dev_up.sh"
echo "Ctrl-C to stop the /infer servers."
echo
while true; do sleep 3600; done
