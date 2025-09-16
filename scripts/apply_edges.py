#!/usr/bin/env python3
import re
import sys
from pathlib import Path
from typing import Dict, Any, Tuple, List

import yaml


ROOT = Path(__file__).resolve().parents[1]


def read_fm(p: Path) -> Tuple[Dict[str, Any], str]:
    txt = p.read_text(encoding="utf-8", errors="ignore")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", txt, flags=re.S)
    if not m:
        return {}, txt
    head, body = m.group(1), m.group(2)
    fm = yaml.safe_load(head) or {}
    return fm, body


def write_fm(p: Path, fm: Dict[str, Any], body: str) -> None:
    y = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).strip()
    p.write_text(f"---\n{y}\n---\n{body.lstrip()}", encoding="utf-8")


def load_edges(path: Path) -> List[Tuple[str, str, str]]:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    out: List[Tuple[str, str, str]] = []
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        m = re.match(r"^(\S+)\s+--([A-Z]+)-->\s+(\S+)$", s)
        if not m:
            continue
        src, typ, dst = m.group(1), m.group(2), m.group(3)
        out.append((src, typ, dst))
    return out


def build_strategy_index() -> Dict[str, Path]:
    idx: Dict[str, Path] = {}
    sdir = ROOT / "strategies"
    for p in sdir.rglob("*.md") if sdir.exists() else []:
        try:
            fm, _ = read_fm(p)
        except Exception as e:
            print(f"[WARN] skip parsing {p}: {type(e).__name__}: {e}")
            continue
        sid = fm.get("id")
        if sid:
            idx[str(sid)] = p
    return idx


def apply_edges(edges_file: Path) -> int:
    edges = load_edges(edges_file)
    if not edges:
        print(f"No edges found in {edges_file}")
        return 0
    idx = build_strategy_index()
    changed = 0
    for src, typ, dst in edges:
        if typ != "ETAYE":
            continue
        p = idx.get(src)
        if not p:
            print(f"[WARN] strategy id not found: {src}")
            continue
        try:
            fm, body = read_fm(p)
        except Exception as e:
            print(f"[WARN] skip patch {p}: {type(e).__name__}: {e}")
            continue
        liens = fm.get("liens_evidence")
        if liens is None:
            liens = []
        if dst not in liens:
            liens = list(liens) + [dst]
            fm["liens_evidence"] = liens
            write_fm(p, fm, body)
            changed += 1
            print(f"[PATCH] {p}: added {dst} to liens_evidence")
    print(f"Applied: {changed} updates")
    return changed


def main(argv: List[str]) -> int:
    edges_path = Path(argv[1]) if len(argv) > 1 else ROOT / "artifacts" / "imports" / "IA_clinique_outputs_2025-09-09" / "graph_edges.txt"
    if not edges_path.exists():
        print(f"Edges file not found: {edges_path}")
        return 2
    apply_edges(edges_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
