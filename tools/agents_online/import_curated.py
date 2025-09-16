import json
import pathlib
from typing import Dict, Any, List

import yaml

# Reuse FM helpers
try:
    from tools.agents_online.curation_utils import read_fm, write_fm, snapshot_path
except Exception:
    from curation_utils import read_fm, write_fm, snapshot_path  # type: ignore

ROOT = pathlib.Path(__file__).resolve().parents[2]

ALLOWED_EVIDENCE = {
    "id",
    "theme",
    "type_etude",
    "message_clinique",
    "statut",
    "doi_url",
    "pmid",
    "publication_date",
    "last_verified",
    "retraction_status",
    "evidence_level",
    "pdf_sha256",
    "sources_snapshot",
}

ALLOWED_EVIDENCE_LEVEL = {"scale", "value", "justification"}

ALLOWED_STRATEGIE = {
    "id",
    "profil",
    "securite",
    "test_sentinelle",
    "mcid",
    "protocoles",
    "liens_evidence",
    "statut",
}


def filter_evidence(data: Dict[str, Any]) -> Dict[str, Any]:
    out = {k: v for k, v in data.items() if k in ALLOWED_EVIDENCE}
    evl = out.get("evidence_level")
    if isinstance(evl, dict):
        out["evidence_level"] = {k: v for k, v in evl.items() if k in ALLOWED_EVIDENCE_LEVEL}
    return out


def filter_strategie(data: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in data.items() if k in ALLOWED_STRATEGIE}


def find_md_by_id(kind: str, evid_id: str) -> pathlib.Path | None:
    base = ROOT / ("evidence" if kind == "evidence" else "strategies")
    for p in base.rglob("*.md"):
        fm, _ = read_fm(p)
        if fm.get("id") == evid_id:
            return p
    return None


def import_evidence_yaml(yaml_path: pathlib.Path) -> pathlib.Path:
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    data = filter_evidence(data)
    evid_id = data.get("id")
    if not evid_id:
        raise ValueError(f"Evidence YAML sans id: {yaml_path}")
    md = find_md_by_id("evidence", evid_id)
    if md is None:
        # create new file
        md = ROOT / "evidence" / f"{evid_id}.md"
        md.parent.mkdir(parents=True, exist_ok=True)
        body_title = evid_id.replace("_", " ").title()
        write_fm(md, data, f"# {body_title}\n\n")
    else:
        fm, body = read_fm(md)
        fm.update(data)
        write_fm(md, fm, body)
    return md


def import_strategie_yaml(yaml_path: pathlib.Path) -> pathlib.Path:
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    data = filter_strategie(data)
    sid = data.get("id")
    if not sid:
        raise ValueError(f"Strategie YAML sans id: {yaml_path}")
    md = find_md_by_id("strategie", sid)
    if md is None:
        md = ROOT / "strategies" / f"{sid}.md"
        md.parent.mkdir(parents=True, exist_ok=True)
        body_title = sid.replace("_", " ").title()
        write_fm(md, data, f"# {body_title}\n\n")
    else:
        fm, body = read_fm(md)
        fm.update(data)
        write_fm(md, fm, body)
    return md


def import_snapshot_json(json_path: pathlib.Path) -> pathlib.Path:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    evid_id = data.get("id")
    if not evid_id:
        raise ValueError(f"Snapshot JSON sans id: {json_path}")
    target = ROOT / "evidence" / "_audit" / f"{evid_id}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def main(staging: str) -> None:
    stage = pathlib.Path(staging)
    if not stage.exists():
        raise SystemExit(f"Staging introuvable: {stage}")
    imported_evid: List[str] = []
    imported_strat: List[str] = []
    imported_snaps: List[str] = []

    for y in sorted(stage.glob("*.yaml")):
        name = y.stem.lower()
        if name.startswith("evidence_"):
            md = import_evidence_yaml(y)
            imported_evid.append(str(md))
        elif name.startswith("strategie_"):
            md = import_strategie_yaml(y)
            imported_strat.append(str(md))

    for j in sorted(stage.glob("*.json")):
        if j.name.lower().startswith("evidence_"):
            snap = import_snapshot_json(j)
            imported_snaps.append(str(snap))

    print(json.dumps({
        "evidence_md": imported_evid,
        "strategies_md": imported_strat,
        "snapshots": imported_snaps,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import sys
    staging = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "artifacts" / "imports" / "IA_clinique_outputs_2025-09-09")
    main(staging)

