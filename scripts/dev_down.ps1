# Stop everything dev_up.ps1 started (engine, mock LLM, all four tier agents).
# Only touches the dev-stack processes by name, so it leaves the /infer servers
# (infer_up.ps1) and the mosquitto Windows service alone.
#   powershell -File scripts\dev_down.ps1
$RepoRoot = Split-Path -Parent $PSScriptRoot
$PidsDir  = Join-Path $RepoRoot "run\pids"
foreach ($name in @("mock_llm","engine","cloud-01","pc-01","phone-01","arduino-01")) {
    $pf = Join-Path $PidsDir "$name.pid"
    if (Test-Path $pf) {
        $procId = (Get-Content $pf).Trim()
        $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if ($p) { Stop-Process -Id $procId -Force; Write-Host "stopped $name (PID $procId)" }
        Remove-Item $pf -Force
    }
}
Write-Host "Down. (/infer servers + mosquitto service left running)"
