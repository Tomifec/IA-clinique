#!/usr/bin/env python3
import sys, os, re, json, yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
out = ROOT/"graph"
out.mkdir(exist_ok=True, parents=True)

nodes = []
edges = []

def load_front_matter(md_path: Path):
    txt = md_path.read_text(encoding="utf-8", errors="ignore")
    m = re.match(r"^---\n(.*?)\n---\n", txt, flags=re.S)
    if not m:
        return {}
    return yaml.safe_load(m.group(1)) or {}

valid_evid = set()
valid_strat = set()

# Evidence nodes (only statut: valide)
evdir = ROOT/"evidence"
for p in evdir.rglob("*.md") if evdir.exists() else []:
    fm = load_front_matter(p)
    if not fm or fm.get("statut") != "valide":
        continue
    evid_id = fm.get("id", p.stem)
    nodes.append({"id": evid_id, "kind":"Evidence", "path": str(p)})
    valid_evid.add(evid_id)

# Strategie nodes (only statut: valide)
sdir = ROOT/"strategies"
for p in sdir.rglob("*.md") if sdir.exists() else []:
    fm = load_front_matter(p)
    if not fm or fm.get("statut") != "valide":
        continue
    sid = fm.get("id", p.stem)
    nodes.append({"id": sid, "kind":"Strategie", "path": str(p)})
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
    nodes.append({"id": fm.get("id", p.stem), "kind":"Risque", "path": str(p)})

with open(out/"export.json","w",encoding="utf-8") as f:
    json.dump({"nodes":nodes,"edges":edges}, f, ensure_ascii=False, indent=2)

print(f"nodes={len(nodes)} edges={len(edges)} -> {out/'export.json'}")
