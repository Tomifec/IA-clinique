import argparse
import datetime as dt
import pathlib
import re
from typing import Any, Dict, List
import re

import yaml

try:
    from tools.agents_online.curation_utils import xref_by_doi, write_fm
    from tools.agents_online.import_curated import filter_evidence
    from tools.agents_online.curation_utils import read_fm
except Exception:
    from curation_utils import xref_by_doi, write_fm, read_fm  # type: ignore
    from import_curated import filter_evidence  # type: ignore


ROOT = pathlib.Path(__file__).resolve().parents[2]


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


DOI_RX = re.compile(r"^10\.\d{4,9}/\S+$", re.I)


def seed_one(doi: str, topic: str) -> Dict[str, Any]:
    # Validate DOI format early to avoid pointless HTTP calls
    if not DOI_RX.match(doi.strip()):
        raise ValueError(f"invalid_doi_format: {doi}")

    cr = xref_by_doi(doi)
    title = cr.get("title")
    if isinstance(title, list):
        title = title[0] if title else None
    date_iso = None
    parts = (
        (cr.get("issued") or {}).get("date-parts")
        or (cr.get("published-print") or {}).get("date-parts")
        or (cr.get("published-online") or {}).get("date-parts")
    )
    if parts and isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0]:
        y = int(parts[0][0]); m = int(parts[0][1]) if len(parts[0])>1 else 1; d = int(parts[0][2]) if len(parts[0])>2 else 1
        date_iso = f"{y:04d}-{m:02d}-{d:02d}"
    evid_id = f"evidence_{slug(topic)}_{slug(doi)[:40]}"
    fm: Dict[str, Any] = {
        "id": evid_id,
        "theme": slug(topic),
        "type_etude": "synthese",
        "message_clinique": "A completer",
        "doi_url": f"https://doi.org/{doi}",
        "publication_date": date_iso or dt.date.today().isoformat(),
        "last_verified": dt.date.today().isoformat(),
        "retraction_status": "ok",
        "evidence_level": {"scale": "OCEBM", "value": "unspecified"},
        "statut": "valide",
    }
    return fm


def write_evidence(fm: Dict[str, Any]) -> pathlib.Path:
    fm = filter_evidence(fm)
    path = ROOT / "evidence" / f"{fm['id']}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    body_title = fm['id'].replace('_',' ').title()
    body = f"# {body_title}\n\n"
    if path.exists():
        old, body_old = read_fm(path)
        old.update(fm)
        write_fm(path, old, body_old)
    else:
        write_fm(path, fm, body)
    return path


def link_strategy(strategy_id: str, evidence_ids: List[str]) -> None:
    sdir = ROOT / "strategies"
    for p in sdir.rglob("*.md"):
        fm, body = read_fm(p)
        if fm.get("id") == strategy_id:
            liens = list(fm.get("liens_evidence") or [])
            changed = False
            for eid in evidence_ids:
                if eid not in liens:
                    liens.append(eid)
                    changed = True
            if changed:
                fm["liens_evidence"] = liens
                write_fm(p, fm, body)
            break


def main():
    ap = argparse.ArgumentParser(description="Seed Evidence by DOI list")
    ap.add_argument("--topic", required=True)
    ap.add_argument("--strategy-id")
    ap.add_argument("dois", nargs="+")
    args = ap.parse_args()

    seeded: List[str] = []
    for doi in args.dois:
        try:
            fm = seed_one(doi, args.topic)
            path = write_evidence(fm)
            seeded.append(fm["id"])
            print(path)
        except Exception as e:
            msg = f"[WARN] skip seed {doi}: {type(e).__name__}: {e}"
            try:
                print(msg)
            except UnicodeEncodeError:
                try:
                    print(msg.encode("cp1252", "replace").decode("cp1252"))
                except Exception:
                    print(msg.encode("ascii", "replace").decode("ascii"))
            continue

    if args.strategy_id:
        link_strategy(args.strategy_id, seeded)


if __name__ == "__main__":
    main()
