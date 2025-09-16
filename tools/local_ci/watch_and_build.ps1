param(
  [int]$DebounceMs = 1500,
  [switch]$RunAgentsOnStart
)

$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -ge 7) { $PSNativeCommandUseErrorActionPreference = $true }

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
Push-Location $RepoRoot
try {
  New-Item -ItemType Directory -Path 'logs' -Force | Out-Null
  $logPath = Join-Path $RepoRoot 'logs\local_ci.log'

  function Write-Log([string]$msg) {
    $ts = (Get-Date).ToString('s')
    $line = "[$ts] $msg"
    $line | Tee-Object -FilePath $logPath -Append
  }

  function Get-LatestEdgesFile {
    $base = Join-Path $RepoRoot 'artifacts\imports'
    if (Test-Path $base) {
      $cand = Get-ChildItem $base -Recurse -Filter 'graph_edges.txt' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
      if ($cand) { return $cand.FullName }
    }
    return $null
  }

  function Invoke-Pipeline([string]$reason) {
    Write-Log "Run triggered ($reason)"
    # Import curated YAML/JSON from artifacts/imports/* if present (idempotent)
    $importsRoot = Join-Path $RepoRoot 'artifacts\imports'
    if (Test-Path $importsRoot) {
      $stagingDirs = Get-ChildItem $importsRoot -Directory -Recurse | Where-Object {
        (Get-ChildItem $_.FullName -Filter '*.yaml' -File -ErrorAction SilentlyContinue | Select-Object -First 1) -or
        (Get-ChildItem $_.FullName -Filter '*.json' -File -ErrorAction SilentlyContinue | Select-Object -First 1)
      }
      foreach ($stage in $stagingDirs) {
        Write-Log "Import: python tools/agents_online/import_curated.py $($stage.FullName)"
        python tools/agents_online/import_curated.py $stage.FullName | Tee-Object -FilePath $logPath -Append
      }
    }
    if ($RunAgentsOnStart -and $reason -eq 'startup') {
      Write-Log 'Agents: python tools/agents_online/run.py evidence --write'
      python tools/agents_online/run.py evidence --write | Tee-Object -FilePath $logPath -Append
    }
    $edges = Get-LatestEdgesFile
    if ($edges) {
      Write-Log "Edges: python scripts/apply_edges.py $edges"
      python scripts/apply_edges.py $edges | Tee-Object -FilePath $logPath -Append
    }
    Write-Log 'Checks'; python scripts/checks.py | Tee-Object -FilePath $logPath -Append
    Write-Log 'Graph';  python scripts/etl_graph.py | Tee-Object -FilePath $logPath -Append
    Write-Log 'Index';  python scripts/build_index.py | Tee-Object -FilePath $logPath -Append
    Write-Log 'OK'
  }

  # Initial run
  Invoke-Pipeline 'startup'

  # Debounced watcher
  $timer = [System.Timers.Timer]::new($DebounceMs)
  $timer.AutoReset = $false
  Register-ObjectEvent -InputObject $timer -EventName Elapsed -SourceIdentifier 'LocalCI.Timer' -Action {
    Invoke-Pipeline 'debounced-change'
  } | Out-Null

  $paths = @('evidence','strategies','safety','schemas','scripts')
  # Watch artifacts/imports to react to new ZIPs or files
  if (Test-Path (Join-Path $RepoRoot 'artifacts')) {
    $paths += 'artifacts'
  }
  foreach ($p in $paths) {
    $full = Join-Path $RepoRoot $p
    if (-not (Test-Path $full)) { continue }
    $w = New-Object System.IO.FileSystemWatcher
    $w.Path = $full
    $w.IncludeSubdirectories = $true
    $w.Filter = '*.*'
    $w.EnableRaisingEvents = $true
    $action = { $timer.Stop(); $timer.Start() }
    Register-ObjectEvent -InputObject $w -EventName Changed -SourceIdentifier "LocalCI.$p.Changed" -Action $action | Out-Null
    Register-ObjectEvent -InputObject $w -EventName Created -SourceIdentifier "LocalCI.$p.Created" -Action $action | Out-Null
    Register-ObjectEvent -InputObject $w -EventName Deleted -SourceIdentifier "LocalCI.$p.Deleted" -Action $action | Out-Null
    Register-ObjectEvent -InputObject $w -EventName Renamed -SourceIdentifier "LocalCI.$p.Renamed" -Action $action | Out-Null
  }

  Write-Host 'Local CI watching changes. Press Ctrl+C to stop.'
  while ($true) { Wait-Event -Timeout 3600 | Out-Null }
}
finally {
  Pop-Location
}
