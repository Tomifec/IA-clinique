param(
  [switch]$Watch = $true,
  [switch]$RunAgentsOnStart,
  [int]$DebounceMs = 1500
)

$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -ge 7) { $PSNativeCommandUseErrorActionPreference = $true }

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
Push-Location $RepoRoot
try {
  Write-Host '== Local CI :: start =='
  # One immediate run (optionally with agents), then watchers if requested
  if ($Watch) {
    & (Join-Path $PSScriptRoot 'watch_and_build.ps1') -DebounceMs $DebounceMs -RunAgentsOnStart:$RunAgentsOnStart
  } else {
    # Single run
    # Import curated YAML/JSON if present under artifacts/imports/*
    $importsRoot = Join-Path $RepoRoot 'artifacts\imports'
    if (Test-Path $importsRoot) {
      $stagingDirs = Get-ChildItem $importsRoot -Directory -Recurse | Where-Object {
        (Get-ChildItem $_.FullName -Filter '*.yaml' -File -ErrorAction SilentlyContinue | Select-Object -First 1) -or
        (Get-ChildItem $_.FullName -Filter '*.json' -File -ErrorAction SilentlyContinue | Select-Object -First 1)
      }
      foreach ($stage in $stagingDirs) {
        Write-Host "Import curated: $($stage.FullName)"
        python tools/agents_online/import_curated.py $stage.FullName
      }
    }
    if ($RunAgentsOnStart) {
      python tools/agents_online/run.py evidence --write
    }
    python scripts/checks.py
    python scripts/etl_graph.py
    python scripts/build_index.py
    Write-Host 'OK'
  }
}
finally {
  Pop-Location
}
