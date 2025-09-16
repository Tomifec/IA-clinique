import argparse
import datetime as dt
import json
import pathlib
import re
from typing import Any, Dict, List

import yaml

try:
    from tools.agents_online.curation_utils import (
        search_crossref_biblio,
        iso_from_crossref,
        read_fm,
        write_fm,
    )
except Exception:
    from curation_utils import (  # type: ignore
        search_crossref_biblio,
        iso_from_crossref,
        read_fm,
        write_fm,
    )


ROOT = pathlib.Path(__file__).resolve().parents[2]


def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "x"


def id_from_doi(topic: str, doi: str) -> str:
    core = re.sub(r"[^a-zA-Z0-9]+", "_", doi)
    return f"evidence_{slugify(topic)}_{core[:40].lower()}"


def seed_one(topic: str, item: Dict[str, Any]) -> Dict[str, Any]:
    doi = item.get("DOI")
    title = " ".join(item.get("title") or []) if isinstance(item.get("title"), list) else (item.get("title") or "")
    pub_iso = iso_from_crossref(item) or dt.date.today().isoformat()
    ev_id = id_from_doi(topic, doi) if doi else f"evidence_{slugify(topic)}_{slugify(title)[:20]}"
    type_etude = "synthese" if re.search(r"review|meta-?analysis", title, re.I) else "etude"
    fm = {
        "id": ev_id,
        "theme": slugify(topic),
        "type_etude": type_etude,
        "message_clinique": "A completer",
        "doi_url": f"https://doi.org/{doi}" if doi else None,
        "publication_date": pub_iso,
        "last_verified": dt.date.today().isoformat(),
        "retraction_status": "ok",
        "evidence_level": {"scale": "OCEBM", "value": "unspecified"},
        "statut": "valide" if doi and pub_iso else "brouillon",
    }
    # remove Nones
    fm = {k: v for k, v in fm.items() if v is not None}
    return fm


def write_evidence_file(fm: Dict[str, Any]) -> pathlib.Path:
    ev_dir = ROOT / "evidence"
    ev_dir.mkdir(parents=True, exist_ok=True)
    md_path = ev_dir / f"{fm['id']}.md"
    body = f"# {fm['id'].replace('_',' ').title()}\n\n"
    if md_path.exists():
        old, body_old = read_fm(md_path)
        old.update(fm)
        write_fm(md_path, old, body_old)
    else:
        write_fm(md_path, fm, body)
    return md_path


def update_strategy_links(strategy_id: str, evidence_ids: List[str]) -> pathlib.Path | None:
    sdir = ROOT / "strategies"
    target: pathlib.Path | None = None
    for p in sdir.rglob("*.md") if sdir.exists() else []:
        fm, body = read_fm(p)
        if fm.get("id") == strategy_id:
            liens = list(fm.get("liens_evidence") or [])
            changed = False
            for evid in evidence_ids:
                if evid not in liens:
                    liens.append(evid)
                    changed = True
            if changed:
                fm["liens_evidence"] = liens
                write_fm(p, fm, body)
            target = p
            break
    return target


def main():
    ap = argparse.ArgumentParser(description="Discover and seed Evidence via Crossref")
    ap.add_argument("--topic", required=True, help="logical theme, e.g., facteurs_pronostiques_tms")
    ap.add_argument("--query", required=True, help="Crossref bibliographic query")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--strategy-id", help="strategy id to link new evidences")
    args = ap.parse_args()

    items = search_crossref_biblio(args.query, rows=args.limit)
    seeded: List[str] = []
    paths: List[str] = []
    for it in items:
        try:
            fm = seed_one(args.topic, it)
            path = write_evidence_file(fm)
            seeded.append(fm["id"])
            paths.append(str(path))
        except Exception as e:
            print(f"[WARN] skip seed: {type(e).__name__}: {e}")

    if args.strategy_id and seeded:
        update_strategy_links(args.strategy_id, seeded)

    print(json.dumps({"seeded": seeded, "paths": paths}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

