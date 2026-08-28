param(
    [int]$GenerationPid = 15024
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repo ".venv\Scripts\python.exe"
$runtime = Join-Path $repo "experiments\components\live_validation_009\artifacts\run\runtime"
$log = Join-Path $runtime "pipeline-supervisor.log"
$env:PYTHONPATH = Join-Path $repo "src"

function Write-Phase([string]$Message) {
    $line = "$(Get-Date -Format o) $Message"
    Add-Content -LiteralPath $log -Value $line
}

function Invoke-Checked([string]$Phase, [string[]]$Arguments) {
    Write-Phase "START $Phase"
    & $python @Arguments *>> $log
    if ($LASTEXITCODE -ne 0) {
        throw "$Phase failed with exit code $LASTEXITCODE"
    }
    Write-Phase "COMPLETE $Phase"
}

function Commit-Exact([string]$Message, [string[]]$Paths) {
    & git -C $repo add -- @Paths *>> $log
    if ($LASTEXITCODE -ne 0) { throw "git add failed for $Message" }
    & git -C $repo commit -m $Message -- @Paths *>> $log
    if ($LASTEXITCODE -ne 0) { throw "git commit failed for $Message" }
    Write-Phase "COMMITTED $Message"
}

New-Item -ItemType Directory -Force -Path $runtime | Out-Null
Write-Phase "WAIT generation pid=$GenerationPid"
Wait-Process -Id $GenerationPid
Write-Phase "GENERATION PROCESS EXITED"

$runBase = "experiments/components/live_validation_009/artifacts/run"
$scoreBase = "experiments/components/live_validation_009/artifacts/scoring"
$resultBase = "experiments/components/live_validation_009/artifacts/result"

Invoke-Checked "generation-validation" @("-m", "analysis.lv009_live", "generate")
Commit-Exact "study: seal LV-009 reader answers" @(
    "$runBase/answers.jsonl",
    "$runBase/generation_summary.json"
)

Invoke-Checked "blind-preparation" @("-m", "analysis.lv009_live", "blind")
Commit-Exact "study: seal LV-009 blind scoring surface" @(
    "$scoreBase/blind_surface.jsonl.gz",
    "$scoreBase/blind_mapping.sealed.json"
)

Invoke-Checked "blind-judging" @("-m", "analysis.lv009_live", "judge")
Commit-Exact "study: seal LV-009 blind judgments" @(
    "$scoreBase/blind_judgments.jsonl",
    "$scoreBase/judgment_summary.json"
)

Invoke-Checked "registered-analysis" @("-m", "analysis.lv009_live", "analyze")
Commit-Exact "study: record LV-009 registered result" @(
    "$resultBase/result.json",
    "$resultBase/per_item.csv"
)
Write-Phase "PIPELINE COMPLETE"
