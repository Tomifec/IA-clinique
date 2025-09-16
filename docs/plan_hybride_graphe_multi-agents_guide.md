attention aucun fichier n'a été fait en 2024 erreur 

 # Plan hybride Graphe + Multi-agents — Guide complet (CI locale) 

Dernière mise à jour : 2025-09-09 02:24 (Europe/Paris)
Périmètre : dépôt **local**, pipeline **offline** déterministe, curation **en ligne** via **GPT-5 dans Codex (compte ChatGPT Plus)**. Aucune API ni clé requise.

> **Sources d’horodatage**
> - DECISION_LOG — 2025-09-08 23:58 (Europe/Paris)
> - Consolidation initiale — 2025-09-09 00:04 (Europe/Paris)
> - Artefacts build — 2025-09-09 02:24 (Europe/Paris)


---

## 1. Objectif et livrables

* But : transformer des fiches Markdown validées en artefacts locaux audités.
* Livrables :

  * `graph/export.json` : nœuds {Evidence|Strategie|Risque} + arêtes {ETAYE}.
  * `index/index.json` : index texte sans front-matter.
  * CI locale : hooks `pre-commit` + `pytest` + **gate** `verify_evidence_stub.py`.

---

## 2. Architecture et responsabilités

* **Phase connectée (hors scripts)** : recherche PubMed/DOI, contrôle rétractions, ROB2/ROBINS-I/AMSTAR-2, attribution OCEBM/GRADE avec **GPT-5** (Codex ou navigateur).
* **Phase offline (scripts)** : validation schémas → ETL graphe → index. Zéro réseau.
* **Multi-agents** :

  * IngestionAgent : normalise, assigne `statut`.
  * SchemaValidator : applique schémas JSON.
  * GraphBuilder : `graph/export.json`.
  * Indexer : `index/index.json`.
  * EvidenceVerifier : curation en ligne puis dépôt des preuves locales.
  * ClinicalWriter : texte clinique avec GPT-5 (hors scripts).

---

## 3. Structure du dépôt

```
/evidence/   /strategies/   /safety/         # contenu Markdown
/schemas/    /scripts/      /graph/ /index/  # schémas + artefacts
/tests/      /tools/        /docs/           
/logs/       /artifacts/                          
Makefile  .pre-commit-config.yaml  requirements.txt  README.md
```

---

## 4. Règles de gouvernance

* Schémas stricts : `additionalProperties:false`.
* Seul `statut: valide` alimente graphe et index.
* **Aucun** appel réseau dans `scripts/*`.
* Nommage : fichiers ASCII `snake_case.md`. UTF-8.
* Traçabilité : `RUNS.md` facultatif + logs CI.

---

## 5. Schémas JSON (spécification)

### 5.1 `schemas/evidence.schema.json`

* Obligatoires : `id`, `theme`, `type_etude`, `message_clinique`, `statut`.
* Si `statut: valide` ⇒ exiger **au choix** `doi_url` **ou** `pmid` **et** `publication_date`, `last_verified`, `retraction_status`, `evidence_level{scale,value}`.
* Conseillés : `pdf_sha256`, `sources_snapshot`.

### 5.2 `schemas/strategies.schema.json`

* Obligatoires : `id`, `profil`, `securite.score`, `test_sentinelle[]`, `liens_evidence[]`, `statut`.

### 5.3 `schemas/safety.schema.json`

* Obligatoires : `id`, `zone`, `liste[]`, `conduite`, `statut: valide`.

---

## 6. Modèles de front-matter

### 6.1 Evidence

```yaml
---
id: evid_lombalgie_dp_001
theme: lombalgie
type_etude: RCT
message_clinique: "Amélioration ODI ~8–12 points à 6–8 semaines chez profils DP extension."
doi_url: "https://doi.org/10.xxxx/xxxxx"   # ou pmid: "12345678"
publication_date: "2023-05-14"
last_verified: "2025-09-09"
retraction_status: "ok"                     # ok|concern|retracted
evidence_level: { scale: OCEBM, value: "2b", justification: "ECR multicentrique" }
pdf_sha256: "<sha256-optionnel>"
sources_snapshot: "evidence/_audit/evid_lombalgie_dp_001.json"
statut: valide
---
```

### 6.2 Strategie

```yaml
---
id: strat_dp_extension_001
profil: lombalgie discogénique, préférence directionnelle extension
securite: { score: vert, stop_rules: ["douleur distalise de 2 dermatomes", "drapeaux rouges"] }
test_sentinelle: ["NRS flexion"]
mcid: { NRS: 2, ODI: 10 }
protocoles: ["EIL 10x, 5 séries, 2-3/j"]
liens_evidence: ["evid_lombalgie_dp_001"]
statut: valide
---
```

### 6.3 Safety

```yaml
---
id: safety_rachis_001
zone: rachis lombaire
liste: ["syndrome de la queue de cheval", "perte de poids inexpliquée"]
conduite: "référer en urgence"
statut: valide
---
```

---

## 7. Scripts offline

* `scripts/checks.py` : valide les front-matters YAML avec jsonschema. Retour ≠ 0 si erreur.
* `scripts/verify_evidence_stub.py` : **gate CI**. Pour chaque evidence `statut: valide`, vérifie localement : champs de datation, `retraction_status`, `evidence_level`, présence `sources_snapshot`, et, si fourni, intégrité PDF via `pdf_sha256`. Zéro réseau.
* `scripts/etl_graph.py` : génère `graph/export.json` avec nœuds {Evidence|Strategie|Risque} et arêtes {ETAYE} depuis `strategies[].liens_evidence`.
* `scripts/build_index.py` : retire le front-matter, produit `index/index.json` avec `{path,length,preview}`.

---

## 8. CI locale

### 8.1 Dépendances

`requirements.txt` :

```
pyyaml
jsonschema
markdown-it-py
pytest
pre-commit
```

### 8.2 Hooks

`.pre-commit-config.yaml` :

```yaml
repos:
- repo: local
  hooks:
    - id: checks
      name: validate-schemas
      entry: python scripts/checks.py
      language: system
      pass_filenames: false
    - id: verify-evidence
      name: verify-evidence-stub
      entry: python scripts/verify_evidence_stub.py
      language: system
      pass_filenames: false
    - id: tests
      name: pytest
      entry: pytest -q
      language: system
      pass_filenames: false
```

### 8.3 Makefile

```
.PHONY: validate graph index verify all test
validate: ; python scripts/checks.py
verify:   ; python scripts/verify_evidence_stub.py
graph:    ; python scripts/etl_graph.py
index:    ; python scripts/build_index.py
test:     ; pytest -q
all: validate verify graph index test
```

---

## 9. Utilisation Codex (GPT-5, sans API)

Dans Codex :

```
/provider openai
/model gpt-5
/status
```

* Laisse “Network: restricted” pour le pipeline.
* Pour la **curation**, utilise ChatGPT web (ou une session Codex séparée autorisée au réseau), puis reporte les champs dans `evidence/*.md`.

---

## 10. Runbook

```bash
pip install -r requirements.txt
pre-commit install --hook-type pre-commit --hook-type pre-push

python scripts/checks.py
python scripts/verify_evidence_stub.py
python scripts/etl_graph.py
python scripts/build_index.py
pytest -q
```

---

## 11. Flux de curation → promotion

1. Rechercher et vérifier en ligne : DOI/PMID, rétractions (RetractionWatch/PubPeer), ROB2/ROBINS-I/AMSTAR-2, OCEBM/GRADE.
2. Compléter le front-matter + déposer `evidence/_audit/<id>.json` (+ `evidence/_pdf/<id>.pdf` si dispo, avec `pdf_sha256`).
3. Passer `statut: valide`.
4. Lancer `make all`. Le gate `verify_evidence_stub.py` bloque si les preuves locales manquent.

---

## 12. Conventions et QA

* Commits : `evidence: …`, `strategies: …`, `safety: …`, `graph: …`, `docs: …`.
* Revue : sortie de `checks.py`, delta nœuds/arêtes si pertinent.
* Sortie attendue : `graph/export.json` et `index/index.json` à jour, hooks verts.

---

## 13. Dépannage

* **Schema fail** : champ manquant ou type erroné → corriger front-matter.
* **Verify fail** : compléter `last_verified`, `publication_date`, `retraction_status`, `evidence_level{}`, `sources_snapshot`, et PDF+hash si utilisé.
* **Graphe incomplet** : vérifier `strategies[].liens_evidence` et l’existence des `evidence.id`.
* **Index vide** : vérifier qu’un corps Markdown existe après le front-matter.

---

## 14. Feuille de route

* Déduplication inter-docs (MinHash/Jaccard).
* Score qualité pondéré (récence, niveau de preuve, cohérence).
* UI locale de visualisation du graphe.

---

## 15. Définition de prêt / terminé

* **Ready** : front-matter complet, champs de curation saisis, `statut` défini.
* **Done** : `make all` vert, artefacts régénérés, logs à jour.  
