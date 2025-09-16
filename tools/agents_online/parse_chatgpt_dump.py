import argparse
import datetime as dt
import json
import pathlib
import re
from typing import Any, Dict, List, Tuple

import yaml

# Reuse helpers
try:
    from tools.agents_online.curation_utils import write_fm
    from tools.agents_online.import_curated import filter_evidence, filter_strategie
except Exception:
    from curation_utils import write_fm  # type: ignore
    from import_curated import filter_evidence, filter_strategie  # type: ignore


ROOT = pathlib.Path(__file__).resolve().parents[2]

YAML_BLOCK_RX = re.compile(r"^---\n(.*?)\n---\n?", re.S | re.M)
CODE_FENCE_RX = re.compile(r"```(json|yml|yaml)?\n([\s\S]*?)\n```", re.M)


def classify_yaml(data: Dict[str, Any]) -> str:
    if not isinstance(data, dict):
        return "unknown"
    if {"id", "theme", "type_etude", "message_clinique"}.issubset(data.keys()):
        return "evidence"
    if {"id", "profil", "securite", "test_sentinelle", "liens_evidence"}.intersection(
        data.keys()
    ):
        return "strategie"
    return "unknown"


def extract_yaml_blocks(text: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for m in YAML_BLOCK_RX.finditer(text):
        try:
            data = yaml.safe_load(m.group(1)) or {}
            if isinstance(data, dict):
                items.append(data)
        except Exception:
            continue
    # Also scan code fences for YAML
    for m in CODE_FENCE_RX.finditer(text):
        lang = (m.group(1) or "").lower()
        body = m.group(2)
        if lang in ("yaml", "yml") or (body.strip().startswith("---") and body.strip().endswith("---")):
            try:
                content = body
                if content.strip().startswith("---"):
                    content = content.strip()[3:].strip()
                    if content.endswith("---"):
                        content = content[: -3].strip()
                data = yaml.safe_load(content) or {}
                if isinstance(data, dict):
                    items.append(data)
            except Exception:
                pass
    return items


def extract_json_blocks(text: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for m in CODE_FENCE_RX.finditer(text):
        lang = (m.group(1) or "").lower()
        body = m.group(2).strip()
        if body.startswith("{") and body.endswith("}"):
            try:
                data = json.loads(body)
                if isinstance(data, dict):
                    out.append(data)
            except Exception:
                continue
    return out


def extract_edges(text: str) -> List[Tuple[str, str]]:
    edges: List[Tuple[str, str]] = []
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r"^(?:Strategie[_\w-]+|strategie[_\w-]+)\s+--ETAYE-->\s+(?:Evidence[_\w-]+|evidence[_\w-]+)$", s)
        if m:
            parts = re.split(r"\s+--ETAYE-->\s+", s)
            if len(parts) == 2:
                # normalize to lowercase ids
                edges.append((parts[0].strip().lower(), parts[1].strip().lower()))
    return edges


def write_evidence(data: Dict[str, Any]) -> pathlib.Path:
    data = filter_evidence(data)
    evid_id = data.get("id")
    if not evid_id:
        raise ValueError("Evidence YAML sans id")
    md = ROOT / "evidence" / f"{evid_id}.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    title = evid_id.replace("_", " ").title()
    body = f"# {title}\n\n"
    write_fm(md, data, body if not md.exists() else body + md.read_text(encoding="utf-8") )
    return md


def write_strategie(data: Dict[str, Any]) -> pathlib.Path:
    data = filter_strategie(data)
    sid = data.get("id")
    if not sid:
        raise ValueError("Strategie YAML sans id")
    md = ROOT / "strategies" / f"{sid}.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    title = sid.replace("_", " ").title()
    body = f"# {title}\n\n"
    write_fm(md, data, body if not md.exists() else body + md.read_text(encoding="utf-8") )
    return md


def write_snapshot(data: Dict[str, Any]) -> pathlib.Path:
    evid_id = data.get("id")
    if not evid_id:
        raise ValueError("Snapshot JSON sans id")
    p = ROOT / "evidence" / "_audit" / f"{evid_id}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def main():
    ap = argparse.ArgumentParser(description="Parse ChatGPT web dump and import Evidence/Strategie/JSON edges")
    ap.add_argument("dump", help="Path to ChatGPT markdown/plain dump")
    ap.add_argument("--apply-edges", action="store_true", help="Extract and apply edges if present")
    args = ap.parse_args()

    dump_path = pathlib.Path(args.dump)
    text = dump_path.read_text(encoding="utf-8", errors="ignore")

    yamls = extract_yaml_blocks(text)
    jsons = extract_json_blocks(text)
    edges = extract_edges(text) if args.apply_edges else []

    evid_written: List[str] = []
    strat_written: List[str] = []
    snap_written: List[str] = []

    for y in yamls:
        kind = classify_yaml(y)
        try:
            if kind == "evidence":
                p = write_evidence(y)
                evid_written.append(str(p))
            elif kind == "strategie":
                p = write_strategie(y)
                strat_written.append(str(p))
        except Exception as e:
            print(f"[WARN] YAML skip: {type(e).__name__}: {e}")

    for j in jsons:
        try:
            p = write_snapshot(j)
            snap_written.append(str(p))
        except Exception as e:
            print(f"[WARN] JSON skip: {type(e).__name__}: {e}")

    edges_file: pathlib.Path | None = None
    if edges:
        stage = ROOT / "artifacts" / "imports" / ("chatgpt_dump_" + dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"))
        stage.mkdir(parents=True, exist_ok=True)
        edges_file = stage / "graph_edges.txt"
        with edges_file.open("w", encoding="utf-8") as f:
            for src, dst in edges:
                f.write(f"{src} --ETAYE--> {dst}\n")

    result = {
        "evidence_md": evid_written,
        "strategies_md": strat_written,
        "snapshots": snap_written,
        "edges_file": str(edges_file) if edges_file else None,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

