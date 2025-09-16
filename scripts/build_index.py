#!/usr/bin/env python3
import sys, os, re, json, yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
out = ROOT/"index"
out.mkdir(exist_ok=True, parents=True)

def split_front_matter(txt: str):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", txt, flags=re.S)
    if m:
        return m.group(1), m.group(2)
    return "", txt

items = []
for base in ["evidence","strategies","safety"]:
    d = ROOT/base
    for p in d.rglob("*.md") if d.exists() else []:
        txt = p.read_text(encoding="utf-8", errors="ignore")
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", txt, flags=re.S)
        if not m:
            continue
        head, body = m.group(1), m.group(2)
        fm = yaml.safe_load(head) or {}
        if fm.get("statut") != "valide":
            continue
        items.append({
            "path": str(p.relative_to(ROOT)),
            "length": len(body),
            "preview": body.strip().splitlines()[:3]
        })

with open(out/"index.json","w",encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)
print(f"indexed={len(items)} -> {out/'index.json'}")
