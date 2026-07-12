# Stop the three /infer servers started by infer_up.ps1.
#   powershell -File scripts\infer_down.ps1
$RepoRoot = Split-Path -Parent $PSScriptRoot
$PidsDir  = Join-Path $RepoRoot "run\pids"
foreach ($name in @("infer_laptop","infer_cloud","infer_phone")) {
    $pf = Join-Path $PidsDir "$name.pid"
    if (Test-Path $pf) {
        $procId = (Get-Content $pf).Trim()
        $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if ($p) { Stop-Process -Id $procId -Force; Write-Host "stopped $name (PID $procId)" }
        Remove-Item $pf -Force
    }
}
Write-Host "Down."
