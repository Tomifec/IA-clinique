# Repository Guidelines

Ce guide s’applique à tout le dépôt et encadre les contributions dans un pipeline local, déterministe et hors réseau.

## Structure du projet
- Contenus Markdown: `evidence/`, `strategies/`, `safety/` (front‑matter YAML conforme aux schémas).
- Schémas: `schemas/` (`evidence.schema.json`, `strategies.schema.json`, `safety.schema.json`).
- Scripts offline: `scripts/` (aucun appel réseau).
- Artefacts: `graph/export.json`, `index/index.json`.
- Qualité & suivi: `tests/` (si présent), `logs/`, `docs/`, `artifacts/`.

## Commandes build, test et dev
- Dépendances: `pip install -r requirements.txt`.
- Hooks: `pre-commit install --hook-type pre-commit --hook-type pre-push`.
- Valider schémas: `make validate` (ou `python scripts/checks.py`).
- Gate evidence: `make verify` (ou `python scripts/verify_evidence_stub.py`).
- Graphe: `make graph` (ou `python scripts/etl_graph.py`).
- Index: `make index` (ou `python scripts/build_index.py`).
- Tests: `make test` (ou `pytest -q`).
- Tout le pipeline: `make all`.

## Style de code & nommage
- Python: indentation 4 espaces; imports groupés; petites fonctions pures.
- Markdown: fichiers ASCII `snake_case.md`, encodage UTF‑8; front‑matter minimal, pas de champs hors schéma (équiv. `additionalProperties: false`).
- Zéro réseau dans `scripts/`; toute curation en ligne se fait hors scripts (voir ci‑dessous).

## Tests
- Cadre: `pytest`.
- Emplacement: `tests/`; nommage `test_*.py`.
- Cible: valider parsing du front‑matter, validation schémas, ETL graphe et index. Exécution: `pytest -q`.

## Commits & Pull Requests
- Préfixes de commit: `evidence:`, `strategies:`, `safety:`, `graph:`, `index:`, `docs:`, `tools:`.
- PR: description claire, issues liées, sortie des checks (`checks.py`/`verify_evidence_stub.py`), et si pertinent delta de `graph/export.json` & `index/index.json`.

## Sécurité & agents
- Pipeline local, offline: aucune API/clé requise; scripts sans réseau.
- Curation: utiliser GPT‑5 via ChatGPT/Codex (hors scripts), puis renseigner les champs requis (ex. `doi_url` ou `pmid`, `publication_date`, `last_verified`, `retraction_status`, `evidence_level`, `sources_snapshot`) et passer `statut: valide`.
# Repository Guidelines

Ce guide s'applique à tout le dépôt et encadre les contributions dans un pipeline local, déterministe et hors réseau.

## Structure du projet
- Contenus Markdown: `evidence/`, `strategies/`, `safety/` (front‑matter YAML conforme aux schémas).
- Schémas: `schemas/` (`evidence.schema.json`, `strategies.schema.json`, `safety.schema.json`).
- Scripts offline: `scripts/` (aucun appel réseau).
- Artefacts: `graph/export.json`, `index/index.json`.
- Qualité & suivi: `tests/` (si présent), `logs/`, `docs/`, `artifacts/`.

## Commandes build, test et dev
- Dépendances: `pip install -r requirements.txt`.
- Hooks: `pre-commit install --hook-type pre-commit --hook-type pre-push`.
- Valider schémas: `make validate` (ou `python scripts/checks.py`).
- Gate evidence: `make verify` (ou `python scripts/verify_evidence_stub.py`).
- Graphe: `make graph` (ou `python scripts/etl_graph.py`).
- Index: `make index` (ou `python scripts/build_index.py`).
- Tests: `make test` (ou `pytest -q`).
- Tout le pipeline: `make all`.

## Style de code & nommage
- Python: indentation 4 espaces; imports groupés; petites fonctions pures.
- Markdown: fichiers ASCII `snake_case.md`, encodage UTF‑8; front‑matter minimal, pas de champs hors schéma (équiv. `additionalProperties: false`).
- Zéro réseau dans `scripts/`; toute curation en ligne se fait hors scripts (voir ci‑dessous).

## Tests
- Cadre: `pytest`.
- Emplacement: `tests/`; nommage `test_*.py`.
- Cible: valider parsing du front‑matter, validation schémas, ETL graphe et index. Exécution: `pytest -q`.

## Commits & Pull Requests
- Préfixes de commit: `evidence:`, `strategies:`, `safety:`, `graph:`, `index:`, `docs:`, `tools:`.
- PR: description claire, issues liées, sortie des checks (`checks.py`/`verify_evidence_stub.py`), et si pertinent delta de `graph/export.json` & `index/index.json`.

## Sécurité & agents
- Pipeline local, offline: aucune API/clé requise; scripts sans réseau.
- Curation: utiliser GPT‑5 via ChatGPT/Codex (hors scripts), puis renseigner les champs requis (ex. `doi_url` ou `pmid`, `publication_date`, `last_verified`, `retraction_status`, `evidence_level`, `sources_snapshot`) et passer `statut: valide`.

