param(
    [int]$ExplorationProcessId = 0,
    [int]$MonitorProcessId = 0,
    [int]$Workers = 8
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$runtime = Join-Path $repo 'experiments\comparisons\beam_001\artifacts\runtime'
$summaryPath = Join-Path $repo 'experiments\comparisons\beam_001\artifacts\exploration\summary.json'
$failurePath = Join-Path $runtime 'exploration_failure.json'
$resultPath = Join-Path $runtime 'part1_continuation.json'
$python = Join-Path $repo '.venv\Scripts\python.exe'
$env:PYTHONPATH = Join-Path $repo 'src'
Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue

function Write-Result([string]$Status, [string]$Stage, [string]$Detail) {
    $value = [ordered]@{
        schema = 'beam001-part1-continuation-v1'
        status = $Status
        stage = $Stage
        detail = $Detail
        exploration_process_id = $ExplorationProcessId
        workers = $Workers
        api_calls = 0
        outcomes_opened = $false
        updated_utc = [DateTimeOffset]::UtcNow.ToString('o')
    }
    $temporary = "$resultPath.tmp"
    $value | ConvertTo-Json | Set-Content -LiteralPath $temporary -Encoding utf8
    Move-Item -LiteralPath $temporary -Destination $resultPath -Force
}

try {
    Write-Result 'WAITING' 'exploration' 'Waiting for the active exploration coordinator.'
    if ($ExplorationProcessId -gt 0) {
        Wait-Process -Id $ExplorationProcessId
    }
    if ($MonitorProcessId -gt 0) {
        Wait-Process -Id $MonitorProcessId -ErrorAction SilentlyContinue
    }
    if (Test-Path -LiteralPath $failurePath) {
        throw "Exploration failure artifact exists: $failurePath"
    }
    if (-not (Test-Path -LiteralPath $summaryPath)) {
        throw "Exploration summary is missing: $summaryPath"
    }
    $summary = Get-Content -LiteralPath $summaryPath -Raw | ConvertFrom-Json
    if ($summary.status -ne 'COMPLETE' -or $summary.question_arms -ne 5400) {
        throw "Exploration did not complete all 5,400 arms."
    }

    Write-Result 'RUNNING' 'shuffle' 'Running the frozen shuffled-order replay.'
    & $python -m analysis.beam001_exploration parallel-shuffle --workers $Workers `
        1> (Join-Path $runtime 'shuffle_stdout.log') `
        2> (Join-Path $runtime 'shuffle_stderr.log')
    if ($LASTEXITCODE -ne 0) {
        throw "Shuffled replay failed with exit code $LASTEXITCODE."
    }

    Write-Result 'RUNNING' 'report' 'Building the sealed Part 1 report.'
    & $python -m analysis.beam001_part1_report `
        1> (Join-Path $runtime 'part1_report_stdout.log') `
        2> (Join-Path $runtime 'part1_report_stderr.log')
    if ($LASTEXITCODE -ne 0) {
        throw "Part 1 report failed with exit code $LASTEXITCODE."
    }
    Write-Result 'COMPLETE' 'part1' 'Exploration, shuffled replay, and Part 1 report completed.'
} catch {
    Write-Result 'FAILED' 'part1' $_.Exception.Message
    throw
}
