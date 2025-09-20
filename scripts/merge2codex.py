#!/usr/bin/env python3
"""Merge knowledge YAML files into a consolidated graph payload."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schema" / "knowledge_types.yaml"
OUTPUT_PATH = ROOT / "graph" / "knowledge.json"


def load_schema() -> Dict[str, Dict[str, Any]]:
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    raw = yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8")) or {}
    schema: Dict[str, Dict[str, Any]] = {}
    for key, value in raw.items():
        if isinstance(key, str) and isinstance(value, dict):
            schema[key] = value
    return schema


def normalise_key(name: str) -> str:
    name = name.strip()
    if name.endswith("s") and name[:-1] in ("annotation", "decision_rule"):
        return name[:-1]
    return name


def validate_entry(entry: Dict[str, Any], schema: Dict[str, Any], source: Path) -> None:
    required = schema.get("required", [])
    optional = schema.get("optional", [])
    missing = [field for field in required if field not in entry]
    if missing:
        raise ValueError(f"{source}: missing required fields {missing}")
    allowed = set(required) | set(optional) | {"condition", "linked_annotations"}
    extras = set(entry) - allowed
    if extras:
        raise ValueError(f"{source}: unexpected fields {sorted(extras)}")


def load_items(
    path: Path,
    allowed: set[str],
    schema: Dict[str, Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if isinstance(data, list):
        if len(allowed) != 1:
            raise ValueError(f"{path}: ambiguous type for list payload")
        key = next(iter(allowed))
        entries = data
    elif isinstance(data, dict):
        entries = []
        key = None
        for raw_key, value in data.items():
            norm_key = normalise_key(str(raw_key))
            if norm_key not in allowed:
                continue
            if not isinstance(value, list):
                raise ValueError(f"{path}: '{raw_key}' must contain a list")
            entries.extend(value)
            key = norm_key
        if key is None:
            raise ValueError(f"{path}: no allowed types found (expected one of {sorted(allowed)})")
    else:
        raise ValueError(f"{path}: unsupported structure")

    schema_def = schema.get(key or next(iter(allowed)))
    if not schema_def:
        raise ValueError(f"Unknown schema for type '{key}'")

    target_key = key or next(iter(allowed))
    validated: Dict[str, List[Dict[str, Any]]] = {target_key: []}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        validate_entry(entry, schema_def, path)
        validated[target_key].append(entry)
    return validated


def merge_payload(files: List[Path], allowed: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    schema = load_schema()
    ordered_allowed = list(dict.fromkeys(allowed))
    allowed_set = set(ordered_allowed)
    merged: Dict[str, List[Dict[str, Any]]] = {name: [] for name in ordered_allowed}
    for path in files:
        loaded = load_items(path, allowed_set, schema)
        for key, items in loaded.items():
            merged.setdefault(key, []).extend(items)
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path, help="Knowledge YAML files")
    parser.add_argument(
        "--allow",
        action="append",
        dest="allowed",
        default=[],
        help="Allowed knowledge types",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help="Destination JSON path",
    )
    args = parser.parse_args()

    if not args.allowed:
        raise SystemExit("At least one --allow type must be provided")

    merged = merge_payload(args.files, args.allowed)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"merged={sum(len(v) for v in merged.values())} types={sorted(merged)} -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
