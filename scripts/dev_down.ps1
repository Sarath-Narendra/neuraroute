# Stop everything dev_up.ps1 started (engine, mock LLM, all four tier agents) - INCLUDING
# any duplicates left behind by running dev_up.ps1 more than once. Identity is the command
# line, not just the recorded PID, so nothing is missed and no orphan keeps heartbeating.
# Leaves the /infer servers (mock_infer.py / infer_up.ps1) and the mosquitto service alone.
#   powershell -File scripts\dev_down.ps1
$RepoRoot = Split-Path -Parent $PSScriptRoot
$PidsDir  = Join-Path $RepoRoot "run\pids"

# match the dev-stack python processes by WHAT they run; mock_infer.py is deliberately excluded.
$stack = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match 'python' -and (
        $_.CommandLine -match 'engine\.app' -or
        $_.CommandLine -match 'mock_llm\.py' -or
        $_.CommandLine -match 'agent\.py'
    )
})

$killed = 0
foreach ($p in $stack) {
    taskkill /F /T /PID $p.ProcessId 2>&1 | Out-Null   # /T also takes out each launcher's worker child
    $killed++
}

# clear the (now stale) pid files for the dev stack
foreach ($name in @("mock_llm", "engine", "cloud-01", "pc-01", "phone-01", "arduino-01")) {
    Remove-Item (Join-Path $PidsDir "$name.pid") -Force -ErrorAction SilentlyContinue
}

Write-Host "Down. stopped $killed dev-stack process(es). (/infer servers + mosquitto service left running)"
