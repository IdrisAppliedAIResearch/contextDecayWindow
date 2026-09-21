# AF-READ-001 runner — run each phase as a separate command, in this order.
# The script starts and stops llama-server itself; nothing else may use the GPU
# while pilot/full/judge are running (close the coding agent first).
#
#   powershell -ExecutionPolicy Bypass -File run_read.ps1 -Phase pilot
#   powershell -ExecutionPolicy Bypass -File run_read.ps1 -Phase full
#   powershell -ExecutionPolicy Bypass -File run_read.ps1 -Phase judge
#   powershell -ExecutionPolicy Bypass -File run_read.ps1 -Phase score
#
# status/build are safe any time (no server): -Phase status, -Phase build.
param([Parameter(Mandatory = $true)][ValidateSet('build', 'pilot', 'full', 'judge', 'score', 'status')]$Phase)

$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..\..\..'))
$py = '.\.venv\Scripts\python.exe'
$script = 'experiments\probes\anchor_reader\af_read001.py'

Write-Host "=== AF-READ-001 phase: $Phase  $(Get-Date -Format 's') ===" -ForegroundColor Cyan
$sw = [Diagnostics.Stopwatch]::StartNew()
& $py $script $Phase
$code = $LASTEXITCODE
$sw.Stop()
Write-Host "=== $Phase exit $code after $([int]$sw.Elapsed.TotalMinutes) min ===" -ForegroundColor Cyan
exit $code
