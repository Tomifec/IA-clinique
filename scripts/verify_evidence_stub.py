#!/usr/bin/env python3
import sys, os, re, yaml, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load_front_matter(md_path: Path):
    txt = md_path.read_text(encoding="utf-8", errors="ignore")
    m = re.match(r"^---\n(.*?)\n---\n", txt, flags=re.S)
    if not m:
        raise ValueError(f"{md_path}: front-matter manquant")
    return yaml.safe_load(m.group(1)) or {}

def sha256_file(p: Path):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

rc = 0
evdir = ROOT/"evidence"
for md in evdir.rglob("*.md") if evdir.exists() else []:
    fm = load_front_matter(md)
    if fm.get("statut") != "valide":
        continue
    for k in ["publication_date","last_verified","retraction_status","evidence_level","sources_snapshot"]:
        if k not in fm:
            print(f"[GATE-FAIL] {md}: champ manquant `{k}`")
            rc = 2
    pdf = fm.get("pdf_sha256")
    if pdf:
        # optional: verify file exists and matches hash if present locally
        rel = fm.get("sources_snapshot","")
        pdf_dir = ROOT/"evidence"/"_pdf"
        cand = pdf_dir / (md.stem + ".pdf")
        if cand.exists():
            digest = sha256_file(cand)
            if digest != pdf:
                print(f"[GATE-FAIL] {md}: pdf_sha256 mismatch")
                rc = 2
print("[GATE] terminé")
sys.exit(rc)
