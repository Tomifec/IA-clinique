# Triage Pack – Cervicalgies (IA de triage cas → conduite à tenir)

Généré le 2025-09-12 16:16 UTC

## Structure
- **core/**
  - `decision_rules.json` : règles de triage exécutables (Urgences / Réf. rapide / Conservateur / CI / Chir).
  - `cervicalgie_synthese_enrichie.md` : réponses cliniques prêtes à formuler (explications/wording).
  - `knowledge_crossref.json` : ancrages page/ligne pour justifier chaque décision.
- **corpus/**
  - `merged_archive_manifest.json` : liste compacte des sources.
  - `sources/` : PDF/DOCX/MD originaux à indexer (retrieval).
- **ebp/**
  - `evidence_full.json` : extraits classés par type d’étude, condition, intervention.
  - `evidence_heatmap.csv` : distribution des types d’études par thème.
- **ux/**
  - `playbook_complet.md` : plans d’action par condition → intervention → type d’étude.
- **qa/**
  - `merged_archive_audit.json` : inventaire complet (extraits, tags).
  - `merged_archive_thematic.json` : regroupement par grands thèmes.
  - `evidence_matrix.csv` : matrice fichier × thème (occurrences).

## Quel fichier pour quel objectif ?
- **Triage automatique** : `core/decision_rules.json` (policy système) + `core/knowledge_crossref.json` (citations).
- **Formulation clinique** : `core/cervicalgie_synthese_enrichie.md`.
- **Retrieval (RAG)** : `corpus/sources/` + `corpus/merged_archive_manifest.json`.
- **EBP / niveau de preuve** : `ebp/evidence_full.json`, `ebp/evidence_heatmap.csv`.
- **Expérience clinicien** : `ux/playbook_complet.md` (par condition/intervention).
- **Gouvernance/qualité** : `qa/merged_archive_audit.json`, `qa/merged_archive_thematic.json`, `qa/evidence_matrix.csv`.

## Intégration (suggestion)
1. Indexer `corpus/sources/` + `ux/playbook_complet.md` + `core/cervicalgie_synthese_enrichie.md` dans un moteur vectoriel.
2. Charger `core/decision_rules.json` en “règles” (contrôle du triage).
3. Lorsque l’IA rend une décision, **citer** via `core/knowledge_crossref.json` (fichier + page/ligne).

## Templates & Schémas ajoutés
- `templates/case_input.schema.json`
- `templates/triage_output.schema.json`
- `templates/case_input.example.radiculopathy.json`
- `templates/case_input.example.dissection.json`
- `README_UX_Triage.md`
- `triage_prompt_system.txt`
