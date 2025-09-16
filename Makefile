.PHONY: validate graph index verify apply_edges all test all_edges all_online report suggest_edges apply_suggested_edges
validate: ; python scripts/checks.py
verify:   ; python scripts/verify_evidence_stub.py
graph:    ; python scripts/etl_graph.py
index:    ; python scripts/build_index.py
test:     ; pytest -q
all: validate verify graph index test
report:   ; python scripts/report_unlinked_evidence.py
suggest_edges: ; python scripts/suggest_edges.py --min-score 3
apply_suggested_edges: ; python scripts/apply_edges.py artifacts/reports/edges_suggestions.clean.txt && $(MAKE) graph index
apply_edges:
	python scripts/apply_edges.py artifacts/imports/IA_clinique_outputs_2025-09-09/graph_edges.txt
all_edges: apply_edges validate graph index
all_online:
	pwsh -NoLogo -NoProfile -File scripts/run_agents_and_build.ps1 -Write

# Normalize -> Select new -> Seed (topic = import_refs_<date>)
.PHONY: normalize
normalize:
	pwsh -NoLogo -NoProfile -Command "$$date = (Get-Date).ToString('yyyy-MM-dd'); $$files = Get-ChildItem artifacts/imports -Filter 'extracted_dois_sources_*.txt' | %% {$$_.FullName}; if (-not $$files) { Write-Host 'No extracted DOI files found'; exit 0 }; $$clean = 'artifacts/imports/dois_clean_'+$$date+'.txt'; $$todo = 'artifacts/imports/dois_to_seed_'+$$date+'.txt'; python scripts/normalize_dois.py -o $$clean @files; python scripts/select_new_dois.py $$clean -o $$todo; $$dois = Get-Content $$todo; if ($$dois) { $$topic = 'import_refs_'+$$date.Replace('-','_'); python tools/agents_online/seed_by_doi.py --topic $$topic $$dois } else { Write-Host 'No new DOIs to seed' }"

.PHONY: normalize_all
normalize_all:
	$(MAKE) normalize
	python tools/agents_online/curate.py --write evidence
	python scripts/checks.py
	python scripts/verify_evidence_stub.py
	python scripts/etl_graph.py
	python scripts/build_index.py
