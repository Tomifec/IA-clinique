#!/usr/bin/env python3
"""Transform snippet CSV into annotation YAML for the Codex graph."""

from __future__ import annotations

import argparse
import csv
import unicodedata
import uuid
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence

import yaml

NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://ia-clinique.example/annotations")


def load_rows(csv_path: Path) -> List[Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for idx, row in enumerate(reader):
            row["__index__"] = str(idx)
            rows.append(row)
        return rows


def generate_id(row: Dict[str, str]) -> str:
    payload = "|".join(
        [
            row.get("tag", ""),
            row.get("source_file", ""),
            str(row.get("page", "")),
            str(row.get("line", "")),
            row.get("snippet", ""),
            row.get("__index__", ""),
        ]
    )
    return str(uuid.uuid5(NAMESPACE, payload))


def coerce_int(value: str | None) -> int | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def slugify(value: str | None) -> str | None:
    if not value:
        return None
    normalised = unicodedata.normalize("NFKD", value)
    ascii_text = normalised.encode("ascii", "ignore").decode("ascii")
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in ascii_text.lower())
    slug = "_".join(part for part in cleaned.split("_") if part)
    return slug or None


def iter_knowledge_items(raw: object) -> Iterable[Mapping[str, object]]:
    if isinstance(raw, Mapping):
        items = raw.get("items")
        if isinstance(items, list):
            for entry in items:
                if isinstance(entry, Mapping):
                    yield entry
        else:
            for entry in raw.values():
                if isinstance(entry, Mapping):
                    yield entry
    elif isinstance(raw, list):
        for entry in raw:
            if isinstance(entry, Mapping):
                yield entry


def build_knowledge_index(path: Path) -> Dict[str, set[str]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    index: Dict[str, set[str]] = {}
    for item in iter_knowledge_items(data):
        identifier = str(item.get("id") or "").strip()
        if not identifier:
            continue
        candidates = {identifier}
        title = item.get("title")
        if isinstance(title, str):
            candidates.add(title)
        doi = item.get("doi")
        if isinstance(doi, str):
            candidates.add(doi)
        translations = item.get("translations")
        if isinstance(translations, list):
            for entry in translations:
                if isinstance(entry, Mapping):
                    translated = entry.get("title")
                    if isinstance(translated, str):
                        candidates.add(translated)
        for candidate in candidates:
            slug = slugify(candidate)
            if not slug:
                continue
            bucket = index.setdefault(slug, set())
            bucket.add(identifier)
    return index


def resolve_evidence_id(row: Mapping[str, str], index: Mapping[str, Sequence[str]]) -> str | None:
    source = row.get("source_file", "")
    base = Path(source).stem
    slug = slugify(base)
    if not slug:
        return None
    direct = index.get(slug)
    if direct:
        if len(direct) == 1:
            return next(iter(direct))
    best_id: str | None = None
    best_score: int | None = None
    for key, identifiers in index.items():
        if slug not in key and key not in slug:
            continue
        for identifier in identifiers:
            score = abs(len(key) - len(slug))
            if best_score is None or score < best_score:
                best_score = score
                best_id = identifier
            elif score == best_score and identifier != best_id:
                best_id = None
    return best_id


def build_annotation(
    row: Dict[str, str],
    knowledge_index: Mapping[str, Sequence[str]],
) -> Dict[str, object]:
    data: Dict[str, object] = {
        "id": generate_id(row),
        "type": "clinical_snippet",
        "tag": row.get("tag", "").strip(),
        "snippet": row.get("snippet", "").strip(),
        "source_file": row.get("source_file", "").strip(),
    }
    page = coerce_int(row.get("page"))
    line = coerce_int(row.get("line"))
    if page is not None:
        data["page"] = page
    if line is not None:
        data["line"] = line
    evidence_id = resolve_evidence_id(row, knowledge_index)
    if evidence_id:
        data["evidence_id"] = evidence_id
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path, help="CSV generated by extract_snippets.py")
    parser.add_argument(
        "knowledge_items",
        type=Path,
        help="knowledge_items_clean.yaml path",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Destination file (stdout if omitted)",
    )
    args = parser.parse_args()

    if not args.knowledge_items.exists():
        raise FileNotFoundError(f"Knowledge items file not found: {args.knowledge_items}")

    knowledge_index = build_knowledge_index(args.knowledge_items)

    rows = load_rows(args.csv_path)
    annotations = [build_annotation(row, knowledge_index) for row in rows]

    payload = {"annotations": annotations}
    text = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)

    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
