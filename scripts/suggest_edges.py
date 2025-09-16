#!/usr/bin/env python3
"""
Suggest strategy→evidence edges based on simple keyword overlap.

Outputs a text file compatible with scripts/apply_edges.py:
  strategie_id --ETAYE--> evidence_id

Heuristics:
- Evidence candidates: statut: valide and not already linked from any strategy
- Tokens from evidence id and snapshot Crossref title (if available)
- Tokens from strategy id and H1 title (if present)
- Overlap score = |tokens_evidence ∩ tokens_strategy|
- Emit suggestions with score >= threshold (default 2)

Usage:
  python scripts/suggest_edges.py [--out artifacts/reports/edges_suggestions.txt] [--min-score 2]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import yaml


ROOT = Path(__file__).resolve().parents[1]


FM_RX = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.S)


STOP = {
    "evidence",
    "import",
    "refs",
    "ref",
    "valide",
    "brouillon",
    "strategie",
    "safety",
    "tms",
    "md",
}


SYN: Dict[str, Set[str]] = {
    # strategy id keyword -> synonyms included in evidence tokens
    "education": {"education", "educative", "pne", "pain_neuroscience_education", "conseils", "stay", "active"},
    "exercice": {"exercise", "exercises", "exercice", "exercices", "therapeutique"},
    "smt": {"manipulation", "spinal", "manual", "thrust", "hvla", "smt", "mobilisation"},
    "mdt": {"mckenzie", "directionnelle", "preference", "mdt"},
    "mwm": {"mobilisation", "with", "movement", "mwm"},
    "traction": {"traction", "decompression"},
    "cognitive_functional_therapy": {"cft", "cognitive", "functional", "therapy"},
    "facteurs": {"prognostic", "pronostic", "predictors", "risk", "facteurs"},
}


def _read_fm(p: Path) -> Tuple[Dict, str]:
    t = p.read_text(encoding="utf-8", errors="ignore")
    m = FM_RX.match(t)
    if not m:
        return {}, t
    head, body = m.group(1), m.group(2)
    try:
        fm = yaml.safe_load(head) or {}
    except Exception:
        fm = {}
    return fm, body


def _snapshot_title(md: Path, fm: Dict) -> Optional[str]:
    rel = fm.get("sources_snapshot")
    if not rel:
        return None
    try:
        snap = (md.parent / rel).resolve()
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


def _tokens_from_text(s: str) -> Set[str]:
    toks = set(t.lower() for t in re.split(r"[^a-zA-Z0-9]+", s) if t)
    return {t for t in toks if t not in STOP and not t.isdigit()}


def evidence_candidates() -> List[Tuple[str, Path, Set[str]]]:
    evdir = ROOT / "evidence"
    sdir = ROOT / "strategies"
    linked: Set[str] = set()
    if sdir.exists():
        for p in sdir.rglob("*.md"):
            fm, _ = _read_fm(p)
            for e in fm.get("liens_evidence") or []:
                linked.add(str(e))

    out: List[Tuple[str, Path, Set[str]]] = []
    for p in evdir.rglob("*.md") if evdir.exists() else []:
        fm, _ = _read_fm(p)
        if fm.get("statut") != "valide":
            continue
        evid = str(fm.get("id") or p.stem)
        if evid in linked:
            continue
        tok: Set[str] = set()
        tok |= _tokens_from_text(evid)
        title = _snapshot_title(p, fm)
        if title:
            tok |= _tokens_from_text(title)
        out.append((evid, p, tok))
    return out


def strategy_profiles() -> List[Tuple[str, Path, Set[str]]]:
    sdir = ROOT / "strategies"
    out: List[Tuple[str, Path, Set[str]]] = []
    for p in sdir.rglob("*.md") if sdir.exists() else []:
        fm, body = _read_fm(p)
        sid = str(fm.get("id") or p.stem)
        tok = _tokens_from_text(sid)
        # H1 line if present
        for line in body.splitlines():
            if line.startswith("# "):
                tok |= _tokens_from_text(line[2:])
                break
        # add synonyms based on detected keywords
        syn: Set[str] = set()
        for k, vals in SYN.items():
            if k in tok:
                syn |= vals
        tok |= syn
        out.append((sid, p, tok))
    return out


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Suggest strategy->evidence edges")
    ap.add_argument("--out", default=str(ROOT / "artifacts" / "reports" / "edges_suggestions.txt"))
    ap.add_argument("--min-score", type=int, default=2)
    args = ap.parse_args(argv)

    suggestions: List[Tuple[str, str, int]] = []
    strategies = strategy_profiles()
    evids = evidence_candidates()
    for evid, _, etok in evids:
        best_sid: Optional[str] = None
        best_score = 0
        for sid, _, stok in strategies:
            score = len(etok & stok)
            if score > best_score:
                best_sid = sid
                best_score = score
        if best_sid and best_score >= args.min_score:
            suggestions.append((best_sid, evid, best_score))

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{sid} --ETAYE--> {eid}  # score={score}" for sid, eid, score in sorted(suggestions)]
    outp.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    # also write a clean file compatible with apply_edges.py (no comments)
    clean_path = outp.with_suffix(".clean.txt")
    clean_lines = [f"{sid} --ETAYE--> {eid}" for sid, eid, _ in sorted(suggestions)]
    clean_path.write_text("\n".join(clean_lines) + ("\n" if clean_lines else ""), encoding="utf-8")
    print(f"suggestions={len(suggestions)} -> {outp}; clean -> {clean_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
