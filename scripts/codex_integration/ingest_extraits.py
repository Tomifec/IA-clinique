#!/usr/bin/env python3
"""
Ingest extraits_json_array.json and Passage 1.txt into the IA-Clinique repository structure.
This script reads a JSON array of evidence records from artifacts/imports/extraits_json_array.json,
generates YAML and Markdown files under 01_evidence/, and updates inventory files under 04_inventory/.
It auto-extends themes.yaml with any new themes encountered.
"""
import json
import re
import sys
import datetime as dt
import unicodedata
import pathlib
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
# Expected input file location relative to repo root
IMP = ROOT / "artifacts" / "imports" / "extraits_json_array.json"
INV = ROOT / "04_inventory"
EV = ROOT / "01_evidence"
THEMES = INV / "themes.yaml"

DOI_RX = re.compile(r"^10\.[0-9]{4,9}/[-._;()/:A-Z0-9]+$", re.I)

def slug(s: str) -> str:
    """Slugify a string to lower case and underscores."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")

def norm_doi(x: str | None) -> str | None:
    if not x:
        return None
    x = x.strip()
    x = x.replace("https://doi.org/", "").replace("http://doi.org/", "")
    return x

def abbr_journal(j: str) -> str:
    """Return a short abbreviation slug for common journal names."""
    m = {
        "The Lancet": "lancet",
        "BMJ": "bmj",
        "NEJM": "nejm",
        "Physical Therapy": "ptj",
        "Cochrane Database of Systematic Reviews": "cochrane",
    }
    return slug(m.get(j, j))

def ensure_themes(themes: set[str]) -> None:
    """Ensure all themes are present in themes.yaml with a proposed status."""
    THEMES.parent.mkdir(parents=True, exist_ok=True)
    data = {"themes": []}
    if THEMES.exists():
        data = yaml.safe_load(THEMES.read_text()) or {"themes": []}
    known = {t.get("slug") for t in data.get("themes", [])}
    for t in sorted(themes):
        if t not in known:
            data.setdefault("themes", []).append({"slug": t, "label": t, "statut": "propose"})
            known.add(t)
    THEMES.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

def build_id(theme: str, journal_abbr: str, year: str, first_author: str) -> str:
    return f"evidence_{theme}_{journal_abbr}_{year}_{slug(first_author)}"

def to_yaml(rec: dict, meta: dict) -> tuple[str, dict]:
    """Create a YAML dictionary from a record and its metadata."""
    doi = norm_doi(rec.get("doi"))
    theme_main = slug(rec.get("theme_principal") or "mouvement")
    # Collect all themes from record (ensure slug)
    extra_themes = set(slug(t) for t in rec.get("themes", []) if t)
    themes = {theme_main, *extra_themes}
    ensure_themes(themes)
    # Build ID using first author or 'na' if missing
    first_author = meta.get("authors", ["na"])[0] if isinstance(meta.get("authors"), list) else meta.get("authors", "na")
    id_ = build_id(theme_main, abbr_journal(meta.get("journal", "na")), str(meta.get("year", "na")), first_author)
    yaml_dict = {
        "id": id_,
        "doi": doi,
        "pmid": rec.get("pmid"),
        "publication_date": rec.get("publication_date"),
        "content_class": rec.get("content_class", "evidence"),
        "theme_principal": theme_main,
        "themes": sorted(list(themes)),
        "study_design": rec.get("study_design"),
        "population": {
            "condition": rec.get("condition"),
            "n": rec.get("n"),
            "setting": rec.get("setting"),
        },
        "intervention": {
            "name": rec.get("intervention"),
            "dose": rec.get("dose"),
        },
        "comparators": rec.get("comparators", []),
        "primary_outcome": rec.get("primary_outcome"),
        "effects": rec.get("effects", []),
        "grade": rec.get("grade", {}),
        "risk_of_bias": rec.get("risk_of_bias", {}),
        "message_clinique": rec.get("message_clinique") or meta.get("title"),
        "recommendation_one_liner": rec.get("recommendation_one_liner"),
        "retraction_status": rec.get("retraction_status", "ok"),
        "last_verified": rec.get("last_verified") or dt.date.today().isoformat(),
        "curator": rec.get("curator", "xx"),
        "needs_update": False,
        "staleness": rec.get("staleness", "warn"),
        "meta": meta,
    }
    return id_, yaml_dict

def main() -> None:
    if not IMP.exists():
        print(f"Input file {IMP} not found", file=sys.stderr)
        sys.exit(1)
    items = json.loads(IMP.read_text(encoding="utf-8"))
    inv_rows = []
    doi_map: dict[str, str] = {}
    EV.mkdir(parents=True, exist_ok=True)
    for rec in items:
        # meta information may be nested under 'meta' key
        meta = rec.get("meta", {})
        # Flatten meta year if it's a date string
        year = None
        if isinstance(rec.get("publication_date"), str) and len(rec.get("publication_date")) >= 4:
            year = rec.get("publication_date")[:4]
        meta.setdefault("year", year)
        id_, yaml_dict = to_yaml(rec, meta)
        # Write YAML file
        yaml_path = EV / f"{id_}.yaml"
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(yaml_dict, f, sort_keys=False, allow_unicode=True)
        # Write minimal MD narrative file
        md_path = EV / f"{id_}.md"
        pico = yaml_dict.get("population", {}).get("condition", ""), yaml_dict.get("intervention", {}).get("name", ""), ", ".join(yaml_dict.get("comparators", []))
        pico_line = f"Population: {pico[0]} | Intervention: {pico[1]} | Comparateurs: {pico[2]}"
        md = (
            f"# Contexte\n{yaml_dict['message_clinique']}\n\n"
            f"# PICO\n{pico_line}\n\n"
            "# Résultats chiffrés\n" + ("- " + yaml_dict['primary_outcome'] if yaml_dict.get('primary_outcome') else "") + "\n\n"
            "# EI / Coût\n\n"
            "# Applicabilité (Quand/Combien)\n\n"
            f"**Recommandation** — {yaml_dict.get('recommendation_one_liner', '')}\n"
        )
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md)
        # Build inventory entry
        inv_rows.append({
            "id": id_,
            "doi": yaml_dict.get("doi"),
            "pmid": yaml_dict.get("pmid"),
            "year": yaml_dict.get("publication_date", "")[:4] if yaml_dict.get("publication_date") else "",
            "study_design": yaml_dict.get("study_design"),
            "condition": yaml_dict.get("population", {}).get("condition"),
            "population_n": yaml_dict.get("population", {}).get("n"),
            "intervention": yaml_dict.get("intervention", {}).get("name"),
            "primary_outcome": yaml_dict.get("primary_outcome"),
            "theme_principal": yaml_dict.get("theme_principal"),
            "themes": ";".join(yaml_dict.get("themes", [])),
            "content_class": yaml_dict.get("content_class", "evidence"),
        })
        doi_key = yaml_dict.get("doi")
        if doi_key:
            doi_map[doi_key] = id_
    # Write inventory CSV and JSON
    INV.mkdir(parents=True, exist_ok=True)
    if inv_rows:
        import csv
        csv_path = INV / "evidence_inventory.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=inv_rows[0].keys())
            writer.writeheader()
            writer.writerows(inv_rows)
        json_path = INV / "evidence_inventory.json"
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(inv_rows, jf, ensure_ascii=False, indent=2)
    doi_map_path = INV / "doi_map.json"
    with open(doi_map_path, "w", encoding="utf-8") as df:
        json.dump(doi_map, df, ensure_ascii=False, indent=2)
    print(f"Created {len(inv_rows)} evidence files and inventory entries.")

if __name__ == "__main__":
    main()
