#!/usr/bin/env python3
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple


ROOT = Path(__file__).resolve().parents[1]


def read_fm(p: Path) -> Tuple[Dict, str]:
    import yaml
    t = p.read_text(encoding="utf-8", errors="ignore")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", t, flags=re.S)
    if not m:
        return {}, t
    head, body = m.group(1), m.group(2)
    try:
        fm = yaml.safe_load(head) or {}
    except Exception:
        fm = {}
    return fm, body


def title_from_snapshot(md: Path, fm: Dict) -> str | None:
    snap_rel = fm.get("sources_snapshot")
    if not snap_rel:
        return None
    try:
        snap = (md.parent / snap_rel).resolve()
        data = json.loads(snap.read_text(encoding="utf-8"))
        cr = (data.get("sources") or {}).get("crossref") or {}
        title = cr.get("title")
        if isinstance(title, list):
            return title[0] if title else None
        if isinstance(title, str):
            return title
    except Exception:
        return None
    return None


def main() -> int:
    evdir = ROOT / "evidence"
    sdir = ROOT / "strategies"
    all_valid: List[Tuple[str, Path, Dict]] = []
    if evdir.exists():
        for p in evdir.rglob("*.md"):
            fm, _ = read_fm(p)
            if fm.get("statut") == "valide":
                evid = fm.get("id", p.stem)
                all_valid.append((evid, p, fm))

    linked: Set[str] = set()
    if sdir.exists():
        for p in sdir.rglob("*.md"):
            fm, _ = read_fm(p)
            liens = fm.get("liens_evidence") or []
            for e in liens:
                linked.add(str(e))

    rows: List[str] = ["id,doi_url,title,path"]
    for evid, path, fm in sorted(all_valid, key=lambda x: x[0]):
        if evid in linked:
            continue
        doi = fm.get("doi_url", "")
        title = title_from_snapshot(path, fm) or ""
        # basic CSV escaping
        esc = lambda s: '"' + str(s).replace('"', '""') + '"' if ("," in str(s) or '"' in str(s)) else str(s)
        rows.append(
            ",".join([esc(evid), esc(doi), esc(title), esc(str(path.relative_to(ROOT)))])
        )

    out = ROOT / "artifacts" / "reports"
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "unlinked_evidence.csv"
    csv_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"unlinked={len(rows)-1} -> {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

