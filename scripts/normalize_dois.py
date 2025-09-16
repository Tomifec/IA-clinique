#!/usr/bin/env python3
"""
Normalize and dedupe DOIs from existing lists (offline).

Usage:
  python scripts/normalize_dois.py -o artifacts/imports/dois_clean_YYYY-MM-DD.txt artifacts/imports/extracted_dois_sources_*.txt

Outputs:
  - Cleaned unique DOIs to the output path
  - A CSV of dropped/noisy lines next to the output (same stem + _dropped.csv)
"""
from __future__ import annotations

import argparse
import pathlib
import re
from typing import List, Set, Tuple


DOI_RX = re.compile(r"10\.\d{4,9}/\S+", re.I)
DOI_URL_RX = re.compile(r"https?://(?:dx\.)?doi\.org/(10\.\d{4,9}/\S+)", re.I)


def normalize_line(line: str) -> Tuple[str | None, str | None]:
    raw = line.strip()
    if not raw:
        return None, "empty"
    # Prefer DOI found in URL form, else bare DOI inside the line
    m_url = DOI_URL_RX.search(raw)
    if m_url:
        doi = m_url.group(1)
    else:
        m = DOI_RX.search(raw)
        if not m:
            return None, "no_doi_match"
        doi = m.group(0)
    # Trim common enclosing characters and trailing punctuation/spaces
    doi = doi.strip().strip("<>[](){}\"' ")
    doi = doi.rstrip(").,;:*\u201d\u2019\u00bb")
    doi = doi.replace(" ", "")
    # Normalize unicode hyphens/minus to ASCII '-'
    trans = {
        ord("\u2010"): ord('-'),  # hyphen
        ord("\u2011"): ord('-'),  # non-breaking hyphen
        ord("\u2012"): ord('-'),
        ord("\u2013"): ord('-'),  # en dash
        ord("\u2014"): ord('-'),  # em dash
        ord("\u2015"): ord('-'),
        ord("\u2212"): ord('-'),  # minus sign
    }
    doi = doi.translate(trans)
    # Final validation: must strictly match DOI pattern
    if not DOI_RX.fullmatch(doi):
        return None, "invalid_format"
    return doi, None


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Normalize DOIs from lists")
    ap.add_argument("inputs", nargs="+", help="Input text files with one DOI or mixed lines each")
    ap.add_argument("-o", "--out", required=True, help="Output path for cleaned DOIs")
    args = ap.parse_args(argv)

    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    dropped_path = out_path.with_name(out_path.stem + "_dropped.csv")

    seen: Set[str] = set()
    dropped: List[Tuple[str, str]] = []

    for inp in args.inputs:
        p = pathlib.Path(inp)
        if not p.exists():
            continue
        try:
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                doi, err = normalize_line(line)
                if doi:
                    seen.add(doi)
                else:
                    dropped.append((line.strip(), err or "unknown"))
        except Exception:
            continue

    out_path.write_text("\n".join(sorted(seen)) + "\n", encoding="utf-8")
    # Write dropped report
    # Basic CSV with quoted original; escape quotes by doubling them
    def _csv_escape(s: str) -> str:
        return '"' + s.replace('"', '""') + '"'
    dropped_lines = ["original,reason"] + [f"{_csv_escape(o)},{r}" for o, r in dropped if o]
    dropped_path.write_text("\n".join(dropped_lines) + "\n", encoding="utf-8")

    print(f"cleaned_dois={len(seen)} -> {out_path}")
    print(f"dropped={len(dropped)} -> {dropped_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
