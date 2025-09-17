#!/usr/bin/env bash
# Integrate IA Clinique helper pack into repo root.
# Usage: bash codex_integration.sh [ZIP_PATH]
set -euo pipefail

ZIP="${1:-ia_clinique_files.zip}"
ROOT="$(pwd)"
TMP="$(mktemp -d)"
echo "Repo root: $ROOT"

if [ ! -f "$ZIP" ]; then
  echo "ERROR: Zip '$ZIP' not found in $ROOT" >&2
  echo "Place the zip at the repo root or pass its path as argument." >&2
  exit 1
fi

echo "Unzipping '$ZIP' into $TMP ..."
unzip -oq "$ZIP" -d "$TMP"

# Ensure target dirs
mkdir -p config \
         code/etl code/qa code/index code/utils \
         01_evidence 02_strategies 03_knowledge \
         04_inventory \
         .github/workflows \
         artifacts/imports

move() { # move if exists: move SRC DST
  local SRC="$1"; shift
  local DST="$1"; shift
  if [ -e "$SRC" ]; then
    mkdir -p "$(dirname "$DST")"
    mv -f "$SRC" "$DST"
    echo "→ $(realpath --relative-to="$ROOT" "$DST")"
  fi
}

copy_if_absent() { # copy only if destination missing
  local SRC="$1"; shift
  local DST="$1"; shift
  if [ -e "$SRC" ] && [ ! -e "$DST" ]; then
    mkdir -p "$(dirname "$DST")"
    cp -f "$SRC" "$DST"
    echo "→ $(realpath --relative-to="$ROOT" "$DST")"
  fi
}

# Accept both old and new pack layouts
# Config
move "$TMP/config/pipeline.yaml"               "config/pipeline.yaml"
copy_if_absent "$TMP/pipeline.yaml"            "config/pipeline.yaml"

# Makefile & CI
move "$TMP/Makefile"                           "Makefile"
move "$TMP/.github/workflows/ci.yml"           ".github/workflows/ci.yml"

# Inventory seed
copy_if_absent "$TMP/04_inventory/themes.yaml" "04_inventory/themes.yaml"

# Utils
for f in doi.py crossref_client.py pubmed_client.py themes.py; do
  move "$TMP/code/utils/$f"                    "code/utils/$f"
  move "$TMP/utils/$f"                         "code/utils/$f"
done

# ETL (new names)
move "$TMP/code/etl/ingest_archive.py"         "code/etl/ingest_archive.py"
move "$TMP/code/etl/curate_online.py"          "code/etl/curate_online.py"
move "$TMP/code/etl/complete_fields.py"        "code/etl/complete_fields.py"
# ETL (legacy names → mapped)
move "$TMP/scripts/ingest_extraits.py"         "code/etl/ingest_archive.py"

# QA / Index
move "$TMP/code/qa/lint_sanity.py"             "code/qa/lint_sanity.py"
move "$TMP/code/index/build_indexes.py"        "code/index/build_indexes.py"
# Legacy
move "$TMP/scripts/lint_sanity.py"             "code/qa/lint_sanity.py"
move "$TMP/scripts/build_indexes.py"           "code/index/build_indexes.py"

# Samples / imports
move "$TMP/extraits_json_array.json"           "artifacts/imports/extraits_json_array.json"
move "$TMP/Passage 1.txt"                      "artifacts/imports/Passage 1.txt"

# Requirements
move "$TMP/requirements.txt"                   "requirements.txt"

# Done
echo
echo "Integration complete."
echo "Next steps:"
echo "  1) pip install -r requirements.txt"
echo "  2) make all"
echo
