#!/usr/bin/env bash
# kill_device.sh <device_id> -- stop a running fake device so the engine marks it stale
# (>3 s later) and, once the scheduler lands, re-routes its task. This is THE KILL on stage.
#
#   ./scripts/kill_device.sh phone-01
set -euo pipefail
d="${1:?usage: kill_device.sh <device_id>}"
# each fake device runs as its own process with its id as the last arg -> anchor on end
if pkill -f "contracts.fake_device ${d}$"; then
  echo "[kill] stopped device ${d} -- engine should report STALE within ~3 s"
else
  echo "[kill] no running fake device matching '${d}'"
  exit 1
fi
