# Usage:
#   powershell -File scripts\kill_device.ps1 <device_id>
# Hard-kill a tier's agent so it stops heartbeating — the engine marks it stale after
# ~3 s and the next reading slides down the connectivity ladder. The on-stage failover
# trigger.  e.g.  powershell -File scripts\kill_device.ps1 cloud-01
$ErrorActionPreference = "Stop"

if ($args.Count -lt 1) {
    Write-Error "Usage: powershell -File scripts\kill_device.ps1 <device_id>   (e.g. cloud-01)"
    exit 1
}
$DeviceId = $args[0]
$RepoRoot = Split-Path -Parent $PSScriptRoot
$PidFile  = Join-Path $RepoRoot "run\pids\$DeviceId.pid"

if (-not (Test-Path $PidFile)) {
    Write-Error "PID file not found for $DeviceId at $PidFile (is the stack running?)"
    exit 1
}
$ProcId = (Get-Content $PidFile).Trim()
$proc = Get-Process -Id $ProcId -ErrorAction SilentlyContinue
if (-not $proc) {
    Write-Warning "process $ProcId for $DeviceId is already dead"
    Remove-Item $PidFile -Force
    exit 1
}
Stop-Process -Id $ProcId -Force
Remove-Item $PidFile -Force
Write-Host "Hard-killed $DeviceId (PID $ProcId) - next reading fails over down the ladder"
