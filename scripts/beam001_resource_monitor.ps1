param(
    [Parameter(Mandatory = $true)]
    [int]$RootProcessId,
    [Parameter(Mandatory = $true)]
    [string]$OutputPath,
    [int]$IntervalSeconds = 5
)

$ErrorActionPreference = 'Stop'
$started = [DateTimeOffset]::UtcNow
$samples = 0
$peakProcesses = 0
$peakWorkingSet = 0L
$peakPrivateBytes = 0L
$peakCpuSeconds = 0.0

function Get-DescendantIds([int]$RootId) {
    $all = @(Get-CimInstance Win32_Process)
    $ids = [System.Collections.Generic.HashSet[int]]::new()
    [void]$ids.Add($RootId)
    do {
        $changed = $false
        foreach ($process in $all) {
            if ($ids.Contains([int]$process.ParentProcessId) -and
                -not $ids.Contains([int]$process.ProcessId)) {
                [void]$ids.Add([int]$process.ProcessId)
                $changed = $true
            }
        }
    } while ($changed)
    return @($ids)
}

function Write-Snapshot([string]$Status) {
    $parent = Split-Path -Parent $OutputPath
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    $snapshot = [ordered]@{
        schema = 'beam001-resource-monitor-v1'
        status = $Status
        root_process_id = $RootProcessId
        started_utc = $started.ToString('o')
        updated_utc = [DateTimeOffset]::UtcNow.ToString('o')
        interval_seconds = $IntervalSeconds
        samples = $samples
        peak_process_count = $peakProcesses
        peak_aggregate_working_set_bytes = $peakWorkingSet
        peak_aggregate_private_bytes = $peakPrivateBytes
        peak_aggregate_cpu_seconds = $peakCpuSeconds
        gpu_required = $false
        embedding_model_loaded = $false
        api_calls = 0
    }
    $temporary = "$OutputPath.tmp"
    $snapshot | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $temporary -Encoding utf8
    Move-Item -LiteralPath $temporary -Destination $OutputPath -Force
}

while (Get-Process -Id $RootProcessId -ErrorAction SilentlyContinue) {
    $ids = Get-DescendantIds $RootProcessId
    $processes = @(Get-Process -Id $ids -ErrorAction SilentlyContinue)
    $workingSet = [long](($processes | Measure-Object WorkingSet64 -Sum).Sum)
    $privateBytes = [long](($processes | Measure-Object PrivateMemorySize64 -Sum).Sum)
    $cpuSeconds = [double](($processes | Measure-Object CPU -Sum).Sum)
    $samples += 1
    $peakProcesses = [Math]::Max($peakProcesses, $processes.Count)
    $peakWorkingSet = [Math]::Max($peakWorkingSet, $workingSet)
    $peakPrivateBytes = [Math]::Max($peakPrivateBytes, $privateBytes)
    $peakCpuSeconds = [Math]::Max($peakCpuSeconds, $cpuSeconds)
    Write-Snapshot 'RUNNING'
    Start-Sleep -Seconds $IntervalSeconds
}

Write-Snapshot 'COMPLETE'
