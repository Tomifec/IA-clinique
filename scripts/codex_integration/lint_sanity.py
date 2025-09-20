#!/usr/bin/env python3
"""Simple sanity checker for YAML evidence files.
Validates DOI format, non-future publication_date, and retraction_status values.
Prints warnings for files that do not meet the criteria.
"""
import yaml
import re
import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_STATUS = {"ok", "retracted", "EoC"}
DOI_RX = re.compile(r"^10\.[0-9]{4,9}/[-._;()/:A-Za-z0-9]+$")

def check_file(fp: Path) -> bool:
    data = yaml.safe_load(fp.read_text(encoding="utf-8")) or {}
    ok = True
    # Check publication_date
    pub_date = data.get("publication_date")
    if pub_date:
        try:
            d = dt.date.fromisoformat(pub_date)
            if d > dt.date.today():
                print(f"{fp}: publication_date {pub_date} is in the future")
                ok = False
        except Exception:
            print(f"{fp}: invalid publication_date {pub_date}")
            ok = False
    # Check DOI
    doi = data.get("doi")
    if doi and not DOI_RX.match(doi):
        print(f"{fp}: invalid DOI {doi}")
        ok = False
    # Check retraction_status
    status = data.get("retraction_status")
    if status and status not in ALLOWED_STATUS:
        print(f"{fp}: invalid retraction_status {status}")
        ok = False
    return ok

def main() -> None:
    base = ROOT / "01_evidence"
    if not base.exists():
        print(f"Directory {base} does not exist; nothing to check")
        return
    n_total = 0
    n_ok = 0
    for fp in base.rglob("*.yaml"):
        n_total += 1
        if check_file(fp):
            n_ok += 1
    print(f"Checked {n_total} YAML files; {n_ok} passed basic sanity checks.")

if __name__ == "__main__":
    main()
