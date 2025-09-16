
# Repository Guidelines

## Structure du projet
- Contenus Markdown: `evidence/`, `strategies/`, `safety/` (front‑matter YAML conforme).
- Schémas: `schemas/` (`evidence.schema.json`, `strategies.schema.json`, `safety.schema.json`).
- Scripts offline: `scripts/` (validation, graphe, index).
- Artefacts: `graph/export.json`, `index/index.json`. Journaux: `logs/`.

## Commandes
- Dépendances: `pip install -r requirements.txt`.
- Valider schémas: `python scripts/checks.py`.
- Graphe: `python scripts/etl_graph.py`.
- Index: `python scripts/build_index.py`.

## Style & règles
- Markdown: `snake_case.md`, UTF‑8; schémas stricts (`additionalProperties: false`).
- `statut: valide` requis pour inclusion dans graphe/index.
- Zéro réseau dans `scripts/`; curation web via `tools/agents_online`.
