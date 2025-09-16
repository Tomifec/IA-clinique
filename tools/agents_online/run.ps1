param(
  [switch]$Write,
  [int]$MaxWorkers = 6,
  [string[]]$Targets = @('evidence'),
  [switch]$Install
)

$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -ge 7) { $PSNativeCommandUseErrorActionPreference = $true }

Write-Host '== Agents réseau =='

# Resolve repo root (this script lives in tools/agents_online)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir '..\..')
Push-Location $RepoRoot
try {
  # 1) Ensure required entries in requirements.txt
  if (Test-Path 'tools/agents_online/ensure_requirements.py') {
    Write-Host '-> Ensuring requirements entries (requests, pyyaml)'
    python tools/agents_online/ensure_requirements.py
  }

  # 2) Optional: install dependencies (network)
  if ($Install) {
    Write-Host '-> Installing Python deps from requirements.txt (--user)'
    python -m pip install --user -r requirements.txt
  }

  # 3) Run curation (Crossref/PubMed network calls)
  $args = @('tools/agents_online/curate.py', '--max-workers', $MaxWorkers)
  if ($Write) { $args += '--write' }
  if ($Targets -and $Targets.Count -gt 0) { $args += $Targets }

  Write-Host "-> Running curate: python $($args -join ' ')"
  python @args

  Write-Host 'Done.'
}
finally {
  Pop-Location
}

