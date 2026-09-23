# AF-READ-003 unattended sequence: pilot -> full -> judge -> score.
#
#   powershell -ExecutionPolicy Bypass -File experiments\probes\anchor_reader\run_all003.ps1
#
# Spin the coding agent down first (GPU must be free). Resumable: re-run the
# same command after any crash/reboot; captured calls are never re-issued.
# Transcript: artifacts\af_read003\run_all.log
$ErrorActionPreference = 'Stop'
$MaxAttempts = 5

$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
Set-Location $root
$dir = 'experiments\probes\anchor_reader'
$py = '.\.venv\Scripts\python.exe'
$script = "$dir\af_read003.py"
$art = "$root\$dir\artifacts\af_read003"
New-Item -ItemType Directory -Force -Path $art | Out-Null
Start-Transcript -Path "$art\run_all.log" -Append

function JsonStatus($path) {
    if (-not (Test-Path $path)) { return $null }
    try { return (Get-Content $path -Raw | ConvertFrom-Json).status } catch { return $null }
}

try {
    if ((JsonStatus "$art\pilot.json") -ne 'PASS') {
        Write-Host "=== PILOT $(Get-Date -Format 's') ===" -ForegroundColor Cyan
        & $py $script pilot
        if ($LASTEXITCODE -ne 0) { throw 'pilot failed (calibration gate)' }
    }
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        if ((JsonStatus "$art\reader_complete.json") -eq 'PASS') { break }
        Write-Host "--- reader attempt $i ---"
        & $py $script full
        Start-Sleep -Seconds 30
    }
    if ((JsonStatus "$art\reader_complete.json") -ne 'PASS') { throw 'readers incomplete after retries' }
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        if ((JsonStatus "$art\judge_complete.json") -ne 'PASS') {
            Write-Host "--- judge attempt $i ---"
            & $py $script judge
            Start-Sleep -Seconds 30
        } else { break }
    }
    if ((JsonStatus "$art\judge_complete.json") -ne 'PASS') { throw 'judges incomplete after retries' }
    & $py $script score
    if ($LASTEXITCODE -ne 0) { throw 'score failed' }
    Write-Host '=== AF-READ-003 COMPLETE ===' -ForegroundColor Green
    Write-Host 'results: artifacts\af_read003\results.json'
}
catch {
    Write-Host "STOPPED: $_" -ForegroundColor Red
    Write-Host 'Re-run the same command after fixing the cause; nothing captured is re-issued.'
    exit 1
}
finally {
    Stop-Transcript | Out-Null
}
