#!/usr/bin/env python3
"""Extract snippet metadata from triage_pack knowledge cross references."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterator


def normalise_snippet(entry: Dict[str, Any]) -> Dict[str, Any] | None:
    """Return a cleaned copy of a raw snippet entry."""
    snippet = (entry.get("snippet") or "").strip()
    if not snippet:
        return None
    file_path = entry.get("file") or ""
    kind = entry.get("type") or ("pdf" if str(file_path).lower().endswith(".pdf") else "md")
    page = entry.get("page")
    line = entry.get("line") or entry.get("loc")
    pattern = entry.get("pattern") or ""
    return {
        "source_file": str(file_path),
        "source_type": str(kind),
        "page": page,
        "line": line,
        "pattern": str(pattern),
        "snippet": snippet,
    }


def iter_rows(data: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    """Iterate over flat rows with tag and snippet metadata."""
    evidence = data.get("evidence", {})
    if not isinstance(evidence, dict):
        return
    for tag, entries in evidence.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            norm = normalise_snippet(entry)
            if not norm:
                continue
            norm.update({"tag": str(tag)})
            yield norm


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Path to knowledge_crossref.json")
    parser.add_argument("--encoding", default="utf-8", help="File encoding (default: utf-8)")
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding=args.encoding))

    fieldnames = [
        "tag",
        "source_file",
        "source_type",
        "page",
        "line",
        "pattern",
        "snippet",
    ]
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()
    for row in iter_rows(payload):
        writer.writerow(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
