.PHONY: ingest lint index sanity all triage

# Import extraits and create YAML/MD and inventory
ingest:
	python scripts/ingest_extraits.py

# Run sanity linter
lint:
	python scripts/lint_sanity.py

# Build indexes
index:
	python scripts/build_indexes.py

# Perform lint and build indexes
sanity: lint index

# Run full pipeline (ingest then sanity checks)
all: ingest sanity

triage:
	mkdir -p tmp items
	python tools/extract_snippets.py docs/triage_pack_2025-09-13/core/knowledge_crossref.json > tmp/xref.csv
	python tools/map2annotations.py tmp/xref.csv knowledge_items_clean.yaml --output items/annotations.yaml
	python tools/json2yaml_rules.py docs/triage_pack_2025-09-13/core/decision_rules.json items/annotations.yaml --output items/decision_rules.yaml
	python scripts/merge2codex.py --allow annotation --allow decision_rule items/annotations.yaml items/decision_rules.yaml
	pytest
	python scripts/check_orphans.py
	python scripts/etl_graph.py
	python scripts/build_index.py
