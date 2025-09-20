# IA Clinique - Guide rapide (local)

[![CI](https://github.com/IA-Clinique/IA-clinique/actions/workflows/github_actions_codex_ci.yml/badge.svg)](https://github.com/IA-Clinique/IA-clinique/actions/workflows/github_actions_codex_ci.yml)

Référence détaillée: `docs/plan_hybride_graphe_multi-agents_guide.md`

Ce dépôt fournit un pipeline local et déterministe (offline) pour valider des fiches Markdown (Evidence/Stratégies/Safety), construire un graphe et un index, et des outils "agents en ligne" (hors scripts/) pour la curation (DOI/PMID, statuts de rétractation, snapshots d'audit).

## Installation
- Python 3.11/3.12 recommandé
- Dépendances:
  - `pip install -r requirements.txt`
  - `pre-commit install --hook-type pre-commit --hook-type pre-push`

## Pipeline offline (déterministe)
- Validation schémas: `python scripts/checks.py`
- Gate evidence (offline): `python scripts/verify_evidence_stub.py`
- Graphe: `python scripts/etl_graph.py`
- Index: `python scripts/build_index.py`
- Makefile: `make validate`, `make verify`, `make graph`, `make index`, `make all`, `make triage`

Notes:
- Le graphe et l'index n'incluent que les fichiers avec `statut: valide`.
- Les arêtes du graphe proviennent de `strategies/*.md` via `liens_evidence: ["<id_evidence>"]`.

## Agents en ligne (curation, hors scripts/)
- Curation par recherche DOI/PMID et snapshots:
  - Cibler un fichier/dossier: `python tools/agents_online/curate.py --search --write evidence`
  - Mode curation simple (sans recherche): `python tools/agents_online/run.py --max-workers 6 evidence --write`
- Wrapper "tout-en-un" (agents + pipeline offline):
  - `pwsh -NoLogo -NoProfile -File scripts/run_agents_and_build.ps1 -Write`
  - Paramètre optionnel pour liens: `-EdgesFile <chemin/graph_edges.txt>`

- Prompt enrichi (recherche web):
  - Voir `docs/prompt_enrichi_curation.md` (à coller dans ChatGPT avec navigation)

## Import d'outputs de recherche (ZIP)
Si vous avez un ZIP contenant des YAML Evidence/Stratégies et des JSON snapshots:
1) Extraire (exemple): `artifacts/imports/IA_clinique_outputs_YYYY-MM-DD/`
2) Importer: `python tools/agents_online/import_curated.py artifacts/imports/IA_clinique_outputs_YYYY-MM-DD`
3) (Optionnel) Appliquer des liens depuis `graph_edges.txt`:
   - `python scripts/apply_edges.py artifacts/imports/IA_clinique_outputs_YYYY-MM-DD/graph_edges.txt`
4) Re‑générer: `python scripts/checks.py && python scripts/etl_graph.py && python scripts/build_index.py`

## Appliquer des liens (edges)
- Fichier texte (une ligne par lien): `strategie_id --ETAYE--> evidence_id`
- Appliquer: `python scripts/apply_edges.py <chemin/graph_edges.txt>`
- Makefile:
  - `make apply_edges` (exemple import inclus)
  - `make all_edges` (apply_edges → validate → graph → index)

## CI locale (watcher)
- Démarrer un watcher local (offline):
  - `pwsh -NoLogo -NoProfile -File tools/local_ci/start.ps1 -Watch`
  - Inclure les agents au démarrage: `-RunAgentsOnStart`
- Journal: `logs/local_ci.log`
- Tâche planifiée (au logon): `tools/local_ci/install_task.ps1 [-RunAgentsOnStart]`
- Alternative sans élévation (Windows Startup): créer un lanceur `.bat` dans le dossier Startup utilisateur. Un script est déjà fourni par l'assistant et lance `tools/local_ci/start.ps1 -Watch` (ou `-Watch -RunAgentsOnStart`).
  - Pour forcer les agents au démarrage: le lanceur utilise `-RunAgentsOnStart`.

Notes PubMed (E-utilities):
- Définir `NCBI_EMAIL` pour réduire les backoffs côté PubMed.
  - Exemple: `setx NCBI_EMAIL "prenom.nom@exemple.com"` puis rouvrir le terminal.

## Extraction multi-format (offline)
- Objectif: extraire des DOIs depuis des sources hétérogènes (.md/.txt/.html/.pdf/.pptx) sans réseau.
- Script: `python scripts/extract_dois_from_sources.py <chemins|dossiers...>`
- Sorties:
  - `artifacts/imports/extracted_dois_sources_YYYY-MM-DD.txt` (DOIs uniques)
  - `artifacts/imports/extracted_dois_sources_YYYY-MM-DD.csv` (file,doi)
- Dépendances optionnelles pour PDF/PPTX: `pip install --user PyPDF2 python-pptx`
- Enchaînement recommandé:
  1) Extraction DOIs (offline)
  2) Seed: `python tools/agents_online/seed_by_doi.py --topic import_refs_YYYY_MM_DD @dois.txt`
  3) Curation (online): `python tools/agents_online/curate.py --write --max-workers 8 evidence`
  4) Rebuild: `python scripts/checks.py && python scripts/etl_graph.py && python scripts/build_index.py`

## Scan progressif de sources utilisateur
- Script: `python scripts/scan_user_sources.py --root C:\\Users\\<toi> --limit 50`
- Fonction: scanne par lots, garde un état (`logs/sources_scan_state.json`), évite les doublons (DOIs déjà présents), et s'arrête après `--limit` nouveaux DOIs.
- Sorties par lot: `artifacts/imports/extracted_dois_sources_YYYY-MM-DD.txt/.csv` + logs.
- Optionnel: `--seed` (crée/maj les Evidence) et `--curate` (lance la curation) avec `--topic import_refs_<date>`.

## Bonnes pratiques
- Respecter les schémas YAML (aucun champ hors schéma).
- Renseigner `doi_url` ou `pmid`, `publication_date`, `last_verified`, `retraction_status`, `evidence_level` avant `statut: valide`.
- Conserver les snapshots d'audit sous `evidence/_audit/<id>.json`.

## Workflow type
1) Rédiger/mettre à jour une Evidence (front‑matter conforme).
2) Curation en ligne pour compléter DOI/PMID et snapshots: `curate.py --search --write evidence`.
3) Lier les stratégies via `liens_evidence` (ou `scripts/apply_edges.py`).
4) Re‑générer: `make all` (ou wrapper PowerShell).

