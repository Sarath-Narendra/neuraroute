#!/usr/bin/env bash
# Usage:
#   ./scripts/dev_down.sh
# Tear the whole NeuraRoute dev stack DOWN — robustly.
#
# Why not just kill the pidfiles: dev_up.sh / infer_up.sh launch every process via
# `bash -lc "... exec python ..."`, but on Git Bash for Windows `exec` does NOT replace the
# launcher shell, so the recorded PIDs are bash wrappers. Killing a wrapper orphans the real
# python, which keeps holding its port / heartbeating across runs (this is exactly what makes
# the failover demo flaky: an orphaned pc-01 keeps the tier "online", and an orphaned engine
# keeps :8080 bound so the next run can't start). So we tear down by the PYTHON command lines
# themselves, which kills orphans and duplicates the pidfiles can't see.
#
# We deliberately target only python* processes: the exec wrappers exit on their own once the
# python they were waiting on is gone, and matching only python guarantees the sweep can never
# kill the shell (or powershell) that is running this teardown. The MQTT broker (mosquitto) is
# left running — dev_up.sh reuses an existing broker, and it may be one you started yourself.

set -uo pipefail   # not -e: teardown must push through partial failures

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIDS_DIR="$REPO_ROOT/run/pids"

echo "Tearing down NeuraRoute stack (by python command line)..."

case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    powershell -NoProfile -Command '
      $sigs = @(
        "runtime/agent.py","runtime\agent.py",
        "engine.app",
        "mock_llm.py","mock_infer.py",
        "servers.laptop_server","servers.cloud_server","servers.phone_server"
      )
      $procs = Get-CimInstance Win32_Process | Where-Object {
        if ($_.Name -notlike "python*") { return $false }   # never the powershell/shell running this
        if (-not $_.CommandLine) { return $false }
        $cl = $_.CommandLine
        foreach ($s in $sigs) { if ($cl -like ("*" + $s + "*")) { return $true } }
        return $false
      }
      if (-not $procs) { "  (no engine / agent / infer / mock python processes running)" }
      foreach ($p in @($procs | Sort-Object ProcessId -Unique)) {
        try {
          Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
          "  killed pid {0,-7} {1}" -f $p.ProcessId, $p.Name
        } catch {}
      }
    '
    ;;
  *)
    any=0
    for sig in "runtime/agent.py" "engine.app" "mock_llm.py" "mock_infer.py" \
               "servers.laptop_server" "servers.cloud_server" "servers.phone_server"; do
      if pkill -9 -f "$sig" 2>/dev/null; then echo "  killed: $sig"; any=1; fi
    done
    [[ "$any" == "0" ]] && echo "  (no engine / agent / infer / mock python processes running)"
    ;;
esac

# All pidfiles now point at dead or wrapper PIDs — clear them so the next run starts clean.
rm -f "$PIDS_DIR"/*.pid 2>/dev/null || true

echo "Down. (mosquitto broker left running — dev_up.sh reuses it)"
