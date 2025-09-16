#!/usr/bin/env python3
import sys, os, re, json, yaml
from pathlib import Path
from jsonschema import validate, Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {
  "evidence": json.loads((ROOT/"schemas"/"evidence.schema.json").read_text(encoding="utf-8")),
  "strategies": json.loads((ROOT/"schemas"/"strategies.schema.json").read_text(encoding="utf-8")),
  "safety": json.loads((ROOT/"schemas"/"safety.schema.json").read_text(encoding="utf-8")),
}

def load_front_matter(md_path: Path):
    txt = md_path.read_text(encoding="utf-8", errors="ignore")
    m = re.match(r"^---\n(.*?)\n---\n", txt, flags=re.S)
    if not m:
        raise ValueError(f"{md_path}: front-matter manquant")
    data = yaml.safe_load(m.group(1)) or {}
    return data

def validate_dir(name):
    base = ROOT/name
    if not base.exists():
        return 0
    schema = SCHEMAS[name]
    val = Draft202012Validator(schema)
    n_ok = 0
    for p in base.rglob("*.md"):
        data = load_front_matter(p)
        errors = sorted(val.iter_errors(data), key=lambda e: e.path)
        if errors:
            print(f"[FAIL] {p}")
            for e in errors:
                print("  -", e.message)
        else:
            print(f"[OK]   {p}")
            n_ok += 1
    return n_ok

total_ok = 0
rc = 0
for name in ["evidence","strategies","safety"]:
    try:
        total_ok += validate_dir(name)
    except Exception as e:
        print(f"[ERROR] {name}: {e}")
        rc = 1
sys.exit(rc)
