#!/usr/bin/env bash
# Usage:
#   ./scripts/kill_device.sh <device_id>
# Hard-kill a tier's agent so it stops heartbeating — the engine marks it stale after
# ~3 s and the next reading slides down the connectivity ladder. The on-stage failover
# trigger. e.g.  ./scripts/kill_device.sh cloud-01
#
# Why this is more than `kill $(cat pid)`:
#   On Git Bash for Windows, `exec` does NOT replace the launcher shell — dev_up.sh's
#   `bash -lc "... exec python ..."` leaves the bash WRAPPER alive as the parent of the
#   python agent. A plain kill of the recorded PID hits the wrapper and orphans the python,
#   which keeps heartbeating so the tier never drops. So we (1) kill the recorded PID and its
#   whole child tree, and (2) sweep any python still running this tier's config — which also
#   catches a duplicate/orphan agent left behind by an earlier, un-torn-down run.
#
# (v2 has no telemetry/battery override, so there is no "soft" kill — a tier is either
#  running or it isn't.)

set -uo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: ./scripts/kill_device.sh <device_id>   (e.g. cloud-01)" >&2
  exit 1
fi

DEVICE_ID="$1"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$REPO_ROOT/run/pids/${DEVICE_ID}.pid"

# device_id -> config filename (pc-01 -> pc.yaml), so we can match the python by its arg.
CFG_BASE=""
cfg="$(grep -lE "^[[:space:]]*device_id:[[:space:]]*${DEVICE_ID}([[:space:]]|\$)" "$REPO_ROOT"/runtime/configs/*.yaml 2>/dev/null | head -n1 || true)"
[[ -n "$cfg" ]] && CFG_BASE="$(basename "$cfg")"

PID=""
[[ -f "$PID_FILE" ]] && PID="$(tr -dc '0-9' < "$PID_FILE" 2>/dev/null || true)"

killed=0
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    # Windows: sweep every *python* running this tier's config — the tracked agent AND any
    # orphan/duplicate from an earlier run. Matching on Name python* is what keeps the sweep
    # from ever hitting the powershell doing the matching (whose own command line contains
    # 'agent.py' + the config) or the shell that launched us.
    killed="$(NEURAROUTE_PID="${PID:-}" NEURAROUTE_CFG="${CFG_BASE:-}" powershell -NoProfile -Command '
      $cfg = $env:NEURAROUTE_CFG
      $targets = @()
      if ($cfg) {
        $targets += Get-CimInstance Win32_Process | Where-Object {
          $_.Name -like "python*" -and $_.CommandLine -like "*agent.py*" -and $_.CommandLine -like ("*" + $cfg + "*")
        }
      }
      # Fallback if the config could not be resolved: the recorded PID, but only if it is
      # itself an agent python (never a recycled PID or a wrapper shell).
      if ($targets.Count -eq 0 -and $env:NEURAROUTE_PID) {
        $rp = Get-CimInstance Win32_Process -Filter "ProcessId=$($env:NEURAROUTE_PID)" -ErrorAction SilentlyContinue
        if ($rp -and $rp.Name -like "python*" -and $rp.CommandLine -like "*agent.py*") { $targets += $rp }
      }
      $killed = 0
      foreach ($t in ($targets | Sort-Object ProcessId -Unique)) {
        if (Stop-Process -Id $t.ProcessId -Force -PassThru -ErrorAction SilentlyContinue) { $killed++ }
      }
      $killed
    ' 2>/dev/null | tr -dc '0-9')"
    [[ -z "$killed" ]] && killed=0
    ;;
  *)
    # POSIX: exec collapses, so the recorded PID is the python. Kill it, then sweep for
    # orphans/duplicates by config.
    if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
      kill -9 "$PID" 2>/dev/null && killed=$((killed + 1)) || true
    fi
    if [[ -n "$CFG_BASE" ]]; then
      while read -r p; do
        [[ -n "$p" ]] || continue
        kill -9 "$p" 2>/dev/null && killed=$((killed + 1)) || true
      done < <(pgrep -f "agent.py.*$CFG_BASE" 2>/dev/null || true)
    fi
    ;;
esac

rm -f "$PID_FILE"

if [[ "$killed" -gt 0 ]] 2>/dev/null; then
  echo "[$(date '+%H:%M:%S')] Hard-killed $DEVICE_ID (${killed} ${CFG_BASE:-config} python agent(s), incl. any duplicate/orphan) — next reading fails over down the ladder"
else
  echo "Error: no live process found for $DEVICE_ID (already dead, or wrong device id?)" >&2
  exit 1
fi
