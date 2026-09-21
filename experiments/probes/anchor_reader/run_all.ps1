# AF-READ-001 unattended sequence: pilot -> full -> judge -> score.
#
#   powershell -ExecutionPolicy Bypass -File experiments\probes\anchor_reader\run_all.ps1
#
# Spin the coding agent down first: the GPU must be free. The script keeps a
# transcript in artifacts\run_all.log, retries resumable phases if the server
# or the machine hiccups (retrying re-issues nothing already captured), and
# stops loudly on the first genuine failure. If the box reboots, re-run this
# same command — every phase resumes from committed files.
#
# Bars are pre-registered (plan f75f590d); this script only reads them out.
$ErrorActionPreference = 'Stop'
$MaxAttempts = 5

$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
Set-Location $root
$dir = 'experiments\probes\anchor_reader'
$py = '.\.venv\Scripts\python.exe'
$script = "$dir\af_read001.py"
$art = "$root\$dir\artifacts"
New-Item -ItemType Directory -Force -Path $art | Out-Null
$log = "$art\run_all.log"
Start-Transcript -Path $log -Append

function Step($name, $args_) {
    Write-Host ""
    Write-Host "=== $name  $(Get-Date -Format 's') ===" -ForegroundColor Cyan
    & $py $script @args_
    if ($LASTEXITCODE -ne 0) { throw "$name failed with exit $LASTEXITCODE" }
}

function JsonStatus($path) {
    if (-not (Test-Path $path)) { return $null }
    try { return (Get-Content $path -Raw | ConvertFrom-Json).status } catch { return $null }
}

try {
    # Pilot: calibration gates + 10x3 answers + wall-clock estimate. Any failure
    # (arithmetic, judge fixtures, template suffix) must stop everything.
    if ((JsonStatus "$art\pilot.json") -ne 'PASS') { Step 'PILOT' @('pilot') }

    # Full readers: retry until reader_complete says PASS; attempts resume.
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        if ((JsonStatus "$art\reader_complete.json") -eq 'PASS') { break }
        Write-Host "--- reader attempt $i of $MaxAttempts ---"
        & $py $script full
        Start-Sleep -Seconds 30
    }
    if ((JsonStatus "$art\reader_complete.json") -ne 'PASS') {
        throw 'readers incomplete after retries — re-run this script'
    }

    # Judge: gold opens here, only after answers are committed.
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        if ((JsonStatus "$art\judge_complete.json") -eq 'PASS') { break }
        Write-Host "--- judge attempt $i of $MaxAttempts ---"
        & $py $script judge
        Start-Sleep -Seconds 30
    }
    if ((JsonStatus "$art\judge_complete.json") -ne 'PASS') {
        throw 'judges incomplete after retries — re-run this script'
    }

    Step 'SCORE' @('score')
    Write-Host ""
    Write-Host '=== AF-READ-001 COMPLETE ===' -ForegroundColor Green
    Write-Host 'Summary: artifacts\results.json and git log. GPU released.'
}
catch {
    Write-Host "STOPPED: $_" -ForegroundColor Red
    Write-Host 'Nothing already captured is re-issued. Fix the cause, re-run run_all.ps1.'
    exit 1
}
finally {
    Stop-Transcript | Out-Null
}
