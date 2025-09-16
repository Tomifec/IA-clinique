# README – Intégration IA de triage (Cervicalgies)

Généré le 2025-09-12 16:28 UTC

## Objectif
Prendre un **cas structuré** (JSON) et retourner une **conduite à tenir** validable par schéma, avec **règles** et **citations** vers les sources.

## Fichiers clés
- `core/decision_rules.json` : logique de triage (priorité : red flags → rapid referral → conservateur).
- `core/knowledge_crossref.json` : `file + page/ligne + snippet` pour la traçabilité.
- `core/cervicalgie_synthese_enrichie.md` : wording clinique pour l'output.
- `templates/case_input.schema.json` : schéma d'entrée.
- `templates/triage_output.schema.json` : schéma de sortie.
- `templates/case_input.example.*.json` : exemples.

## Pipeline conseillé
1. **Valider** l'entrée contre `templates/case_input.schema.json`.
2. **Évaluer les règles** de `core/decision_rules.json` (urgence > rapide > conservateur).
3. **RAG** : vectoriser `corpus/sources/` + `ux/playbook_complet.md` + `core/cervicalgie_synthese_enrichie.md`, récupérer 5–10 passages pertinents.
4. **Composer la sortie** selon `templates/triage_output.schema.json`.
5. **Citer** 3–8 références depuis `core/knowledge_crossref.json` (même fichier + page/ligne que les passages utilisés).
6. **Vérifier la sécurité** : si CI/risk détectés → bannir manipulation/traction.

## Règles de priorité (résumé)
- **URGENT_EMERGENCY** si : trauma instable, infection suspecte avec signes généraux, cancer suggéré, myélopathie, red flags vasculaires/dissection.
- **RAPID_SPECIALIST** si : radiculopathie douloureuse persistante ≥4–8 sem, déficit non progressif, douleur réfractaire, suspicion inflammatoire.
- **CONSERVATIVE_MANAGEMENT** si examen rassurant, pas de red flags, pas de déficit évolutif.

## Bonnes pratiques
- Toujours **documenter** `explainability` (règles déclenchées + résumés de sources).
- **Follow-up** par défaut : 2–6 semaines (plus tôt si aggravation).
- **Sécurité** : interdire manipulation cervicale si red flags vasculaires/infection/tumeur/instabilité/myélopathie.

## Exécution (pseudo)
- Input: JSON → validate → rules.apply() → rag.fetch() → compose(output) → validate(output) → return.
