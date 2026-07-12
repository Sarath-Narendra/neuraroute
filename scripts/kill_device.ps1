# Usage:
#   powershell -File scripts\kill_device.ps1 <device_id>
# Hard-kill a tier's agent so it stops heartbeating — the engine marks it stale after
# ~3 s and the next reading slides down the connectivity ladder. The on-stage failover
# trigger.  e.g.  powershell -File scripts\kill_device.ps1 pc-01
#
# The tier's identity is its CONFIG FILE (runtime\configs\<tier>.yaml) as seen on the live
# command lines — NOT just the recorded PID. Matching this way reliably catches:
#   * the venv python launcher AND its real child interpreter (two processes per agent), and
#   * any duplicate agents left behind if dev_up.ps1 was run more than once.
# Every match is killed together with its whole process tree (taskkill /T). The recorded
# PID file is only a fallback if no live process is found.
$ErrorActionPreference = "Stop"

if ($args.Count -lt 1) {
    Write-Error "Usage: powershell -File scripts\kill_device.ps1 <device_id>   (e.g. pc-01)"
    exit 1
}
$DeviceId = $args[0]
$RepoRoot = Split-Path -Parent $PSScriptRoot
$PidFile  = Join-Path $RepoRoot "run\pids\$DeviceId.pid"

# device_id (cloud-01) -> config basename (cloud); the config file is the tier's identity.
$Tier     = $DeviceId -replace '-\d+$', ''
$CfgMatch = "configs.$Tier\.yaml"     # matches runtime\configs\<tier>.yaml on the command line

# find every live agent process for this tier (launcher + worker + any duplicates)
$targets = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match 'python' -and $_.CommandLine -match 'agent\.py' -and $_.CommandLine -match $CfgMatch
} | Select-Object -ExpandProperty ProcessId)

if ($targets.Count -eq 0) {
    # fall back to the recorded PID file if the command-line scan found nothing
    if (Test-Path $PidFile) {
        $recorded = (Get-Content $PidFile).Trim()
        if ($recorded -and (Get-Process -Id $recorded -ErrorAction SilentlyContinue)) {
            $targets = @($recorded)
        }
    }
}

if ($targets.Count -eq 0) {
    Write-Warning "no live agent found for $DeviceId (tier '$Tier') - is the stack running?"
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    exit 1
}

foreach ($procId in ($targets | Select-Object -Unique)) {
    # /T also takes out the launcher's worker child; skip PIDs a prior tree-kill already reaped.
    # cmd /c "...>nul 2>&1" fully swallows taskkill's output so no error text leaks to the console.
    if (Get-Process -Id $procId -ErrorAction SilentlyContinue) {
        cmd /c "taskkill /F /T /PID $procId >nul 2>&1"
    }
}
Remove-Item $PidFile -Force -ErrorAction SilentlyContinue

$plural = if ($targets.Count -eq 1) { 'process tree' } else { "$($targets.Count) process trees" }
Write-Host "Hard-killed $DeviceId (tier '$Tier', $plural) - next reading fails over down the ladder"
