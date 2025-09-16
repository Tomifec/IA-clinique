param(
  [switch]$Write,
  [string]$EdgesFile
)

$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -ge 7) { $PSNativeCommandUseErrorActionPreference = $true }

Write-Host '== Agents réseau =='
$agentArgs = @('tools/agents_online/run.py')
if ($Write) { $agentArgs += '--write' }
$agentArgs += 'evidence'
python @agentArgs

# Optional: apply edges from a links file if present
function Get-LatestEdgesFile {
  param([string]$Hint)
  if ($Hint -and (Test-Path $Hint)) { return (Resolve-Path $Hint).Path }
  $base = Join-Path (Get-Location) 'artifacts\imports'
  if (Test-Path $base) {
    $cand = Get-ChildItem $base -Recurse -Filter 'graph_edges.txt' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($cand) { return $cand.FullName }
  }
  return $null
}

$edges = Get-LatestEdgesFile -Hint $EdgesFile
if ($edges) {
  Write-Host '== Edges  =='
  python scripts/apply_edges.py $edges
}

Write-Host '== Checks =='
python scripts/checks.py

Write-Host '== Graphe =='
python scripts/etl_graph.py

Write-Host '== Index  =='
python scripts/build_index.py

Write-Host 'OK'
