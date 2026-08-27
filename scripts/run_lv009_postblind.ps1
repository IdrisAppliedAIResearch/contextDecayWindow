$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repo ".venv\Scripts\python.exe"
$runtime = Join-Path $repo "experiments\components\live_validation_009\artifacts\run\runtime"
$stdout = Join-Path $runtime "postblind.stdout.log"
$stderr = Join-Path $runtime "postblind.stderr.log"
$env:PYTHONPATH = Join-Path $repo "src"

function Invoke-Phase([string]$Name) {
    & $python -m analysis.lv009_live $Name 1>> $stdout 2>> $stderr
    if ($LASTEXITCODE -ne 0) { throw "$Name failed with exit code $LASTEXITCODE" }
}

Set-Location $repo
Invoke-Phase "judge"
git add -- experiments/components/live_validation_009/artifacts/scoring/blind_judgments.jsonl experiments/components/live_validation_009/artifacts/scoring/judgment_summary.json
if ($LASTEXITCODE -ne 0) { throw "judgment git add failed" }
git commit -m "study: seal LV-009 blind judgments" -- experiments/components/live_validation_009/artifacts/scoring/blind_judgments.jsonl experiments/components/live_validation_009/artifacts/scoring/judgment_summary.json 1>> $stdout 2>> $stderr
if ($LASTEXITCODE -ne 0) { throw "judgment commit failed" }

Invoke-Phase "analyze"
git add -- experiments/components/live_validation_009/artifacts/result/result.json experiments/components/live_validation_009/artifacts/result/per_item.csv
if ($LASTEXITCODE -ne 0) { throw "result git add failed" }
git commit -m "study: record LV-009 registered result" -- experiments/components/live_validation_009/artifacts/result/result.json experiments/components/live_validation_009/artifacts/result/per_item.csv 1>> $stdout 2>> $stderr
if ($LASTEXITCODE -ne 0) { throw "result commit failed" }
