#!/usr/bin/env python3
import argparse
import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import yaml

ROOT = Path(__file__).resolve().parents[2]
GRAPH_PATH = ROOT / "graph" / "export.json"


def split_front_matter(text: str) -> Tuple[Dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, flags=re.S)
    if not m:
        return {}, text
    head, body = m.group(1), m.group(2)
    fm = yaml.safe_load(head) or {}
    return fm, body


def load_md_front_matter(path: Path) -> Tuple[Dict, str]:
    txt = path.read_text(encoding="utf-8", errors="ignore")
    return split_front_matter(txt)


def load_graph():
    data = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    by_id = {n["id"]: n for n in nodes}
    # map strategy -> list of evidence ids
    adj: Dict[str, List[str]] = {}
    for e in edges:
        if e.get("type") == "ETAYE":
            adj.setdefault(e.get("src"), []).append(e.get("dst"))
    return nodes, edges, by_id, adj


def list_strategies(filter_text: Optional[str] = None) -> List[Dict]:
    nodes, _, _, _ = load_graph()
    s = [n for n in nodes if n.get("kind") == "Strategie"]
    if filter_text:
        ft = filter_text.lower()
        s = [n for n in s if ft in n.get("id", "").lower() or ft in Path(n.get("path", "")).name.lower()]
    return sorted(s, key=lambda n: n.get("id", ""))


def resolve_evidence(evid_ids: List[str]) -> List[Tuple[str, Path, Dict]]:
    nodes, _, by_id, _ = load_graph()
    out = []
    for eid in evid_ids:
        node = by_id.get(eid)
        if not node:
            continue
        p = Path(node.get("path"))
        fm, _ = load_md_front_matter(p)
        out.append((eid, p, fm))
    return out


def _normalize(text: str) -> str:
    if not isinstance(text, str):
        return ""
    # strip accents and lowercase for robust matching
    t = unicodedata.normalize("NFKD", text)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t.lower()


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", _normalize(text))


def suggest_strategies(query: str, top_k: int = 5) -> List[Tuple[str, float]]:
    nodes, _, _, _ = load_graph()
    # build corpus for strategies from front-matter and body
    corpus: List[Tuple[str, List[str]]] = []
    for n in nodes:
        if n.get("kind") != "Strategie":
            continue
        p = Path(n.get("path"))
        fm, body = load_md_front_matter(p)
        bag = []
        bag += _tokenize(fm.get("profil", ""))
        sec = fm.get("securite", {}) or {}
        bag += _tokenize(sec.get("score", ""))
        for t in fm.get("test_sentinelle", []) or []:
            bag += _tokenize(t)
        bag += _tokenize(body)
        corpus.append((n["id"], bag))

    qtokens = _tokenize(query)
    if not qtokens:
        return []
    qset = set(qtokens)
    scored: List[Tuple[str, float]] = []
    for sid, tokens in corpus:
        if not tokens:
            scored.append((sid, 0.0))
            continue
        tset = set(tokens)
        inter = len(qset & tset)
        union = len(qset | tset)
        jaccard = inter / union if union else 0.0
        # light boost if exact substring present in profil
        boost = 0.0
        scored.append((sid, jaccard + boost))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def show_strategy(strategy_id: str, export_path: Optional[Path] = None) -> int:
    nodes, _, by_id, adj = load_graph()
    s_node = by_id.get(strategy_id)
    if not s_node or s_node.get("kind") != "Strategie":
        print(f"[ERR] stratégie introuvable: {strategy_id}")
        return 2
    s_path = Path(s_node.get("path"))
    s_fm, s_body = load_md_front_matter(s_path)
    evid_ids = adj.get(strategy_id, [])
    evid = resolve_evidence(evid_ids)

    def fmt_evidence(eid: str, fm: Dict) -> str:
        el = fm.get("evidence_level", {}) or {}
        parts = [
            f"- id: {eid}",
            f"  message_clinique: {fm.get('message_clinique','').strip()}",
            f"  niveau: {el.get('scale','?')} {el.get('value','?')}",
            f"  justification: {el.get('justification','').strip()}",
            f"  source: {fm.get('doi_url') or ('pmid:'+str(fm.get('pmid')) if fm.get('pmid') else '')}",
            f"  publication_date: {fm.get('publication_date','')}",
            f"  retraction_status: {fm.get('retraction_status','')}"
        ]
        return "\n".join(parts)

    # Console output
    print(f"Stratégie: {strategy_id}")
    print(f"Profil: {s_fm.get('profil','')}")
    sec = s_fm.get('securite',{}) or {}
    print(f"Sécurité: score={sec.get('score','')}")
    ts = s_fm.get('test_sentinelle') or []
    if ts:
        print("Tests sentinelles:")
        for t in ts:
            print(f"  - {t}")
    print(f"N evidences: {len(evid)}")
    for eid, _, fm in evid:
        print(fmt_evidence(eid, fm))

    # Export pack
    if export_path:
        lines: List[str] = []
        lines.append(f"# Pack justification — {strategy_id}")
        lines.append("")
        lines.append(f"Profil: {s_fm.get('profil','')}")
        lines.append(f"Sécurité (score): {sec.get('score','')}")
        if ts:
            lines.append("Tests sentinelles:")
            for t in ts:
                lines.append(f"- {t}")
        lines.append("")
        lines.append("## Evidences")
        for eid, _, fm in evid:
            el = fm.get("evidence_level", {}) or {}
            lines.append(f"### {eid}")
            if fm.get("message_clinique"):
                lines.append(fm["message_clinique"].strip())
            lines.append("")
            lines.append(f"- Niveau: {el.get('scale','?')} {el.get('value','?')}")
            if el.get("justification"):
                lines.append(f"- Justification: {el['justification'].strip()}")
            if fm.get("doi_url") or fm.get("pmid"):
                src = fm.get("doi_url") or ("pmid:" + str(fm.get("pmid")))
                lines.append(f"- Source: {src}")
            if fm.get("publication_date"):
                lines.append(f"- Publication: {fm['publication_date']}")
            if fm.get("retraction_status"):
                lines.append(f"- Retraction status: {fm['retraction_status']}")
            lines.append("")
        export_path.parent.mkdir(parents=True, exist_ok=True)
        export_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"[OK] Pack exporte -> {export_path}")

    return 0


def main():
    ap = argparse.ArgumentParser(description="Assistant clinique local — stratégies et justifications")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp_list = sub.add_parser("list", help="Lister les stratégies valides")
    sp_list.add_argument("--filter", "-f", help="Filtre (substring)")

    sp_show = sub.add_parser("show", help="Afficher une stratégie et ses evidences")
    sp_show.add_argument("id", help="ID de la stratégie")
    sp_show.add_argument("--export", "-o", type=Path, help="Exporter un pack justification (.md)")

    sp_suggest = sub.add_parser("suggest", help="Suggérer des stratégies à partir d'une requête clinique")
    sp_suggest.add_argument("--query", "-q", required=True, help="Description clinique (ex: lombalgie, peur du mouvement)")
    sp_suggest.add_argument("--top", "-k", type=int, default=5, help="Nombre de suggestions")

    args = ap.parse_args()

    if args.cmd == "list":
        s = list_strategies(args.filter)
        if not s:
            print("Aucune stratégie trouvée.")
            return 0
        for n in s:
            print(n["id"])  # minimal et exploitable en pipe
        return 0
    elif args.cmd == "show":
        return show_strategy(args.id, args.export)
    elif args.cmd == "suggest":
        res = suggest_strategies(args.query, args.top)
        if not res:
            print("Aucune suggestion.")
            return 0
        for sid, score in res:
            print(f"{sid}\t{score:.3f}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
