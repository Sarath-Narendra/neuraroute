# NeuraRoute v2 — Windows one-command dev stack (PowerShell port of dev_up.sh).
#
#   powershell -ExecutionPolicy Bypass -File scripts\dev_up.ps1
#
# Starts, in order:  mosquitto broker (:1883) -> mock LLM (:1234) -> engine (:8080)
#                    -> 4 tier agents (cloud-01, pc-01, phone-01, arduino-01)
# Logs land in run\logs\*.log ; PIDs in run\pids\*.pid so kill_device.ps1 can drop a tier.
#
# Env overrides (set before running, or put in .env):
#   NEURAROUTE_LOCAL_BASE_URL   real LM Studio URL for pc/phone tiers (skips the mock LLM)
#   NEURAROUTE_REGISTRY=venue   point the ladder at the real /infer servers
#   NEURAROUTE_PORT             engine port (default 8080)
#
# Ctrl-C (or run scripts\dev_down.ps1) tears everything down.
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$PidsDir  = Join-Path $RepoRoot "run\pids"
$LogsDir  = Join-Path $RepoRoot "run\logs"
New-Item -ItemType Directory -Force -Path $PidsDir, $LogsDir | Out-Null

# --- load .env (KEY=VALUE lines) so config lives in one file ------------------------
$envFile = Join-Path $RepoRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]*)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
        }
    }
    Write-Host "  loaded $envFile"
}

# --- pick the venv python (Windows layout), else fall back --------------------------
$Py = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
    $Py = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $Py) { throw "No python found. Create the venv: py -3.12 -m venv .venv" }
}

# --- defaults (respect anything already set) ---------------------------------------
function Default-Env($name, $value) {
    if (-not [Environment]::GetEnvironmentVariable($name, "Process")) {
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}
Default-Env "NEURAROUTE_BROKER"     "localhost"
Default-Env "NEURAROUTE_PORT"       "8080"
Default-Env "NEURAROUTE_CLOUD_MOCK" "true"
Default-Env "NEURAROUTE_REGISTRY"   "dev"

function Test-Port($p) {
    try { (New-Object Net.Sockets.TcpClient).Connect("localhost", $p); return $true } catch { return $false }
}

# Guard: refuse to stack a second copy on top of a running one. Duplicate agents share a
# device_id, so kill_device.ps1 would drop one twin while the other keeps heartbeating and
# the tier never fails over. Tear the old stack down first.
$running = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match 'python' -and ($_.CommandLine -match 'agent\.py' -or $_.CommandLine -match 'engine\.app')
})
if ($running.Count -gt 0) {
    throw "A NeuraRoute stack is already running ($($running.Count) process(es)). Stop it first: powershell -File scripts\dev_down.ps1"
}

function Launch($name, $argList) {
    $log = Join-Path $LogsDir "$name.log"
    $proc = Start-Process -FilePath $Py -ArgumentList $argList -WorkingDirectory $RepoRoot `
        -RedirectStandardOutput $log -RedirectStandardError "$log.err" `
        -NoNewWindow -PassThru
    $proc.Id | Out-File -Encoding ascii (Join-Path $PidsDir "$name.pid")
    "{0,-12} pid {1,-7} log {2}" -f $name, $proc.Id, $log | Write-Host
}

# 1) broker
if (Test-Port 1883) {
    Write-Host "  mosquitto    already up on :1883"
} else {
    $mosq = (Get-Command mosquitto -ErrorAction SilentlyContinue).Source
    if (-not $mosq) { $mosq = "C:\Program Files\mosquitto\mosquitto.exe" }
    if (-not (Test-Path $mosq)) { throw "mosquitto not found. winget install EclipseFoundation.Mosquitto" }
    Start-Process -FilePath $mosq -ArgumentList "-p","1883" -NoNewWindow | Out-Null
    Start-Sleep -Seconds 1
    Write-Host "  mosquitto    started on :1883"
}

# 2) mock LLM for the local tiers, unless a real LM Studio URL is provided
if (-not [Environment]::GetEnvironmentVariable("NEURAROUTE_LOCAL_BASE_URL", "Process")) {
    [Environment]::SetEnvironmentVariable("NEURAROUTE_LOCAL_BASE_URL", "http://localhost:1234/v1", "Process")
    Launch "mock_llm" @("tools\mock_llm.py", "1234")
    Start-Sleep -Seconds 1
} else {
    Write-Host "  local LLM    using $env:NEURAROUTE_LOCAL_BASE_URL (mock LLM skipped)"
}

# 3) engine
Launch "engine" @("-m", "engine.app")
Start-Sleep -Seconds 2

# 4) the four tiers (PID files keyed by device_id so kill_device.ps1 <id> can drop a tier)
foreach ($pair in @("cloud:cloud-01","pc:pc-01","phone:phone-01","arduino:arduino-01")) {
    $file, $did = $pair.Split(":")
    Launch $did @("runtime\agent.py", "runtime\configs\$file.yaml")
    Start-Sleep -Milliseconds 400
}

Write-Host ""
Write-Host "NeuraRoute up (registry=$env:NEURAROUTE_REGISTRY). Engine: http://localhost:$env:NEURAROUTE_PORT"
Write-Host "Submit a reading:"
Write-Host "  curl -Method POST http://localhost:$env:NEURAROUTE_PORT/request -ContentType application/json -Body '{\"patient_id\":\"P-03\",\"vitals\":{\"hr\":176,\"spo2\":79,\"temp_c\":37,\"resp_rate\":32}}'"
Write-Host "Kill a tier (drive the failover):  powershell -File scripts\kill_device.ps1 cloud-01"
Write-Host "Stop everything:                   powershell -File scripts\dev_down.ps1"
