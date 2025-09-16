
param([switch]$Write)
$ErrorActionPreference="Stop"
Write-Host "== Agents réseau =="
$a=@(); if($Write){$a+="--write"}
python tools/agents_online/run.py @a evidence
Write-Host "== Checks =="
python scripts/checks.py
Write-Host "== Graphe =="
python scripts/etl_graph.py
Write-Host "== Index  =="
python scripts/build_index.py
Write-Host "OK"
