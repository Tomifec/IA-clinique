
import os, re, json, yaml

ROOT = os.path.dirname(os.path.dirname(__file__)) if __file__ else os.getcwd()
FM_RX = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)

def load_fm(path):
    with open(path, encoding="utf-8") as f:
        t = f.read()
    m = FM_RX.match(t)
    if not m: return None
    return yaml.safe_load(m.group(1)) or {}

nodes = []
edges = []

# Evidence nodes
evi_dir = os.path.join(ROOT, "evidence")
if os.path.isdir(evi_dir):
    for root, _, files in os.walk(evi_dir):
        for fn in files:
            if not fn.endswith(".md"): continue
            fm = load_fm(os.path.join(root, fn))
            if not fm: continue
            if fm.get("statut") == "valide":
                nodes.append({"id": fm["id"], "type": "Evidence"})

# Strategy nodes and ETAYE edges
str_dir = os.path.join(ROOT, "strategies")
if os.path.isdir(str_dir):
    for root, _, files in os.walk(str_dir):
        for fn in files:
            if not fn.endswith(".md"): continue
            fm = load_fm(os.path.join(root, fn))
            if not fm: continue
            if fm.get("statut") == "valide":
                sid = fm["id"]
                nodes.append({"id": sid, "type": "Strategie"})
                for evid in fm.get("liens_evidence", []):
                    edges.append({"from": sid, "to": evid, "type": "ETAYE"})

# Safety nodes (optional)
saf_dir = os.path.join(ROOT, "safety")
if os.path.isdir(saf_dir):
    for root, _, files in os.walk(saf_dir):
        for fn in files:
            if not fn.endswith(".md"): continue
            fm = load_fm(os.path.join(root, fn))
            if not fm: continue
            if fm.get("statut") == "valide":
                nodes.append({"id": fm["id"], "type": "Safety"})

# de-duplicate nodes
seen = set(); uniq_nodes = []
for n in nodes:
    key = (n["id"], n["type"])
    if key in seen: continue
    seen.add(key); uniq_nodes.append(n)

out = {"nodes": uniq_nodes, "edges": edges}

os.makedirs(os.path.join(ROOT, "graph"), exist_ok=True)
with open(os.path.join(ROOT, "graph", "export.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print(f"graph/export.json written: nodes={len(uniq_nodes)} edges={len(edges)}")
