#!/usr/bin/env python3
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
out = ROOT/"graph"
out.mkdir(exist_ok=True, parents=True)

nodes = []
edges = []
node_ids = set()

def load_front_matter(md_path: Path):
    txt = md_path.read_text(encoding="utf-8", errors="ignore")
    m = re.match(r"^---\n(.*?)\n---\n", txt, flags=re.S)
    if not m:
        return {}
    return yaml.safe_load(m.group(1)) or {}

valid_evid = set()
valid_strat = set()

def iter_evidence_payloads(evdir: Path):
    for path in evdir.rglob("*.md"):
        data = load_front_matter(path)
        if data:
            yield path, data
    for path in evdir.rglob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            yield path, data


# Evidence nodes (only statut: valide)
evdir = ROOT/"evidence"
if evdir.exists():
    for path, payload in iter_evidence_payloads(evdir):
        if payload.get("statut") != "valide":
            continue
        evid_id = str(payload.get("id") or path.stem)
        if not evid_id or evid_id in node_ids:
            continue
        nodes.append({"id": evid_id, "kind": "Evidence", "path": str(path)})
        node_ids.add(evid_id)
        valid_evid.add(evid_id)

# Strategie nodes (only statut: valide)
sdir = ROOT/"strategies"
for p in sdir.rglob("*.md") if sdir.exists() else []:
    fm = load_front_matter(p)
    if not fm or fm.get("statut") != "valide":
        continue
    sid = fm.get("id", p.stem)
    if sid in node_ids:
        continue
    nodes.append({"id": sid, "kind": "Strategie", "path": str(p)})
    node_ids.add(sid)
    valid_strat.add(sid)
    # Edges only if destination evidence is valid
    for evid in fm.get("liens_evidence", []):
        if evid in valid_evid:
            edges.append({"src": sid, "dst": evid, "type":"ETAYE"})

# Safety nodes (only statut: valide)
safedir = ROOT/"safety"
for p in safedir.rglob("*.md") if safedir.exists() else []:
    fm = load_front_matter(p)
    if not fm or fm.get("statut") != "valide":
        continue
    rid = fm.get("id", p.stem)
    if rid not in node_ids:
        nodes.append({"id": rid, "kind": "Risque", "path": str(p)})
        node_ids.add(rid)

# Additional knowledge types (annotations & rules)
knowledge_path = ROOT / "graph" / "knowledge.json"
if knowledge_path.exists():
    try:
        knowledge = json.loads(knowledge_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[WARN] Unable to parse {knowledge_path}: {exc}")
        knowledge = {}
    annotations = knowledge.get("annotation") or []
    if isinstance(annotations, list):
        for ann in annotations:
            if not isinstance(ann, dict):
                continue
            ann_id = ann.get("id")
            if not ann_id or ann_id in node_ids:
                continue
            nodes.append({
                "id": ann_id,
                "kind": "Annotation",
                "tag": ann.get("tag"),
                "source": ann.get("source_file"),
            })
            node_ids.add(ann_id)
            evid = ann.get("evidence_id")
            if evid and evid in valid_evid:
                edges.append({"src": ann_id, "dst": evid, "type": "RENVOI"})
    rules = knowledge.get("decision_rule") or []
    if isinstance(rules, list):
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            rule_id = rule.get("id")
            if not rule_id or rule_id in node_ids:
                continue
            nodes.append({
                "id": rule_id,
                "kind": "DecisionRule",
                "category": rule.get("category"),
            })
            node_ids.add(rule_id)
            for ann_id in rule.get("linked_annotations", []) or []:
                if ann_id in node_ids:
                    edges.append({"src": rule_id, "dst": ann_id, "type": "UTILISE"})

with open(out/"export.json","w",encoding="utf-8") as f:
    json.dump({"nodes":nodes,"edges":edges}, f, ensure_ascii=False, indent=2)

print(f"nodes={len(nodes)} edges={len(edges)} -> {out/'export.json'}")
