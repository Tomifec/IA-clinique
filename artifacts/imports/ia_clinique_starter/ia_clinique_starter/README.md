
# IA Clinique — Starter local

## Objectif
Organiser des fiches Markdown, valider les schémas, produire un graphe (`graph/export.json`) et un index (`index/index.json`).

## Utilisation rapide
```
pip install -r requirements.txt
python scripts/checks.py
python scripts/etl_graph.py
python scripts/build_index.py
```

## Agents réseau (optionnel)
```
python tools/agents_online/run.py evidence              # snapshots
python tools/agents_online/run.py --write evidence      # patch FM + snapshots
```
