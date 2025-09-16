#!/usr/bin/env python3
"""Build simple index files (by_theme.json and by_class.json) from YAML evidence files."""
import yaml
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "01_evidence"
INV = ROOT / "04_inventory"


def main() -> None:
    by_theme: dict[str, list[str]] = {}
    by_class: dict[str, list[str]] = {}
    if not BASE.exists():
        print(f"Directory {BASE} does not exist; nothing to index")
        return
    for fp in BASE.rglob("*.yaml"):
        data = yaml.safe_load(fp.read_text(encoding="utf-8")) or {}
        eid = data.get("id")
        theme = data.get("theme_principal", "unknown")
        cls = data.get("content_class", "evidence")
        by_theme.setdefault(theme, []).append(eid)
        by_class.setdefault(cls, []).append(eid)
    INV.mkdir(parents=True, exist_ok=True)
    with open(INV / "by_theme.json", "w", encoding="utf-8") as f:
        json.dump(by_theme, f, ensure_ascii=False, indent=2)
    with open(INV / "by_class.json", "w", encoding="utf-8") as f:
        json.dump(by_class, f, ensure_ascii=False, indent=2)
    print(f"Generated index files with {len(by_theme)} themes and {len(by_class)} classes.")

if __name__ == "__main__":
    main()
