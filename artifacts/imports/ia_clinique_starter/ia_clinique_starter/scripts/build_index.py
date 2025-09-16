
import os, re, json, yaml

ROOT = os.path.dirname(os.path.dirname(__file__)) if __file__ else os.getcwd()
FM_RX = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.S)

def load(path):
    with open(path, encoding="utf-8") as f:
        t = f.read()
    m = FM_RX.match(t)
    if not m:
        return None, t
    fm = yaml.safe_load(m.group(1)) or {}
    body = m.group(2)
    return fm, body

def collect(dirpath):
    items = []
    if not os.path.isdir(dirpath): return items
    for root, _, files in os.walk(dirpath):
        for fn in files:
            if not fn.endswith(".md"): continue
            fm, body = load(os.path.join(root, fn))
            if fm is None: continue
            if fm.get("statut") != "valide": continue
            preview = body.strip().replace("\r","").replace("\n"," ")[:240]
            items.append({
                "path": os.path.relpath(os.path.join(root, fn), ROOT).replace("\\","/"),
                "length": len(body),
                "preview": preview
            })
    return items

index = collect(os.path.join(ROOT, "evidence")) + collect(os.path.join(ROOT, "strategies")) + collect(os.path.join(ROOT, "safety"))
os.makedirs(os.path.join(ROOT, "index"), exist_ok=True)
with open(os.path.join(ROOT, "index", "index.json"), "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, indent=2)
print(f"index/index.json written: entries={len(index)}")
