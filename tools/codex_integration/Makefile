.PHONY: ingest lint index sanity all

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
