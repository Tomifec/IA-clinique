import json
import pathlib
import re
from typing import Dict, Any, List

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]

FM_RX = re.compile(r"^---\n(.*?)\n---\n", re.S)


def load_fm(p: pathlib.Path) -> Dict[str, Any]:
    txt = p.read_text(encoding="utf-8", errors="ignore")
    m = FM_RX.match(txt)
    if not m:
        return {}
    return yaml.safe_load(m.group(1)) or {}


def main() -> int:
    evdir = ROOT / "evidence"
    rows: List[Dict[str, Any]] = []
    for p in sorted(evdir.rglob("*.md")):
        fm = load_fm(p)
        if not fm or fm.get("statut") != "valide":
            continue
        rows.append({
            "id": fm.get("id") or p.stem,
            "theme": fm.get("theme"),
            "type_etude": fm.get("type_etude"),
            "doi_url": fm.get("doi_url"),
            "pmid": fm.get("pmid"),
            "publication_date": fm.get("publication_date"),
            "retraction_status": fm.get("retraction_status"),
            "path": str(p.relative_to(ROOT)),
        })

    out_dir = ROOT / "artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "evidence_inventory.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    # simple CSV
    header = ["id","theme","type_etude","doi_url","pmid","publication_date","retraction_status","path"]
    lines = [",".join(header)]
    for r in rows:
        line = ",".join([str(r.get(k, "") or "").replace(",", " ") for k in header])
        lines.append(line)
    (out_dir / "evidence_inventory.csv").write_text("\n".join(lines), encoding="utf-8")
    print(f"count={len(rows)} -> artifacts/evidence_inventory.json, artifacts/evidence_inventory.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

