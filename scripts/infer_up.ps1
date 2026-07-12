# NeuraRoute — Windows port of infer_up.sh: bring up the three /infer servers.
#
#   powershell -ExecutionPolicy Bypass -File scripts\infer_up.ps1
#
# Starts:  laptop (GenieX/Qwen) :8000 · cloud (Groq/Llama-70B) :8001 · phone (llama.cpp) :8002
# Each exposes POST /infer {"patient":"<text>"}. A server whose backend is missing
# (no geniex / no GROQ_API_KEY / no on-device model) still BOOTS and returns a clean
# error, so the ladder fails over instead of hanging.
#
# Point the engine at them with NEURAROUTE_REGISTRY=venue and run dev_up.ps1 separately.
# Stop with scripts\infer_down.ps1.
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$PidsDir  = Join-Path $RepoRoot "run\pids"
$LogsDir  = Join-Path $RepoRoot "run\logs"
New-Item -ItemType Directory -Force -Path $PidsDir, $LogsDir | Out-Null

$envFile = Join-Path $RepoRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]*)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
        }
    }
    Write-Host "  loaded $envFile"
}

$Py = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { throw "venv not found. Create it: py -3.12 -m venv .venv" }

function Launch($name, $app, $port) {
    $log = Join-Path $LogsDir "$name.log"
    $proc = Start-Process -FilePath $Py `
        -ArgumentList @("-m","uvicorn",$app,"--host","0.0.0.0","--port",$port) `
        -WorkingDirectory $RepoRoot -RedirectStandardOutput $log -RedirectStandardError "$log.err" `
        -NoNewWindow -PassThru
    $proc.Id | Out-File -Encoding ascii (Join-Path $PidsDir "$name.pid")
    "{0,-14} pid {1,-7} :{2}   log {3}" -f $name, $proc.Id, $port, $log | Write-Host
}

Write-Host "NeuraRoute inference module - starting /infer servers:"
Launch "infer_laptop" "servers.laptop_server:app" 8000
Launch "infer_cloud"  "servers.cloud_server:app"  8001
Launch "infer_phone"  "servers.phone_server:app"  8002

Write-Host ""
Write-Host "Up. Verify the cloud tier (real Groq):"
Write-Host '  Invoke-RestMethod http://localhost:8001/infer -Method POST -ContentType application/json -Body ''{"patient":"Patient P-03. CURRENT sensor reading: hr 176, spo2 79, temp_c 37, resp_rate 32."}'''
Write-Host "Then run the engine in venue mode:  `$env:NEURAROUTE_REGISTRY='venue'; scripts\dev_up.ps1"
