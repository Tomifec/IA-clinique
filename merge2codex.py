"""Convert knowledge_items_clean.yaml into Codex evidence JSON and inventory."""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import yaml

RE_PUBMED = re.compile(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)/?")
RE_NON_ALNUM = re.compile(r"[^0-9a-zA-Z]+")


@dataclass
class EvidenceRecord:
    """Representation of an evidence item ready to be serialised."""

    id: str
    theme: str
    type_etude: str
    message_clinique: str
    statut: str
    doi_url: str | None = None
    pmid: str | None = None
    publication_date: str | None = None
    last_verified: str | None = None
    retraction_status: str | None = None
    evidence_level: dict[str, str] | None = None
    sources_snapshot: str | None = None

    def to_json(self) -> dict[str, object]:
        data: dict[str, object] = {
            "id": self.id,
            "theme": self.theme,
            "type_etude": self.type_etude,
            "message_clinique": self.message_clinique,
            "statut": self.statut,
        }
        if self.doi_url:
            data["doi_url"] = self.doi_url
        if self.pmid:
            data["pmid"] = self.pmid
        if self.publication_date:
            data["publication_date"] = self.publication_date
        if self.last_verified:
            data["last_verified"] = self.last_verified
        if self.retraction_status:
            data["retraction_status"] = self.retraction_status
        if self.evidence_level:
            data["evidence_level"] = self.evidence_level
        if self.sources_snapshot:
            data["sources_snapshot"] = self.sources_snapshot
        return data


def load_items(path: Path) -> list[dict]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    items = raw.get("items") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        raise ValueError(f"Unexpected structure in {path}")
    return items


def slugify(value: str) -> str:
    slug = RE_NON_ALNUM.sub("_", value).strip("_")
    return slug.lower() or "evidence"


def ensure_unique(base: str, registry: defaultdict[str, int]) -> str:
    counter = registry[base]
    registry[base] += 1
    if counter == 0:
        return base
    return f"{base}_{counter}"


def extract_theme(item: dict) -> str:
    for key in ("theme_principal", "theme", "themePrincipal"):
        theme = item.get(key)
        if isinstance(theme, str) and theme.strip():
            return slugify(theme)
    canonical = item.get("canonical") or []
    if isinstance(canonical, list):
        for entry in canonical:
            if isinstance(entry, str) and entry.strip():
                return slugify(entry)
    return "non_classe"


def extract_message(item: dict) -> str:
    for key in ("summary_fr", "summary", "resume", "message"):
        text = item.get(key)
        if isinstance(text, str) and text.strip():
            return text.strip()
    claims = item.get("claims") or []
    if isinstance(claims, list) and claims:
        primary = claims[0]
        if isinstance(primary, dict):
            text = primary.get("text") or primary.get("message")
            if isinstance(text, str) and text.strip():
                return text.strip()
    title = item.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    return "Résumé indisponible."


def extract_pmid(item: dict) -> str | None:
    for source in item.get("sources") or []:
        if not isinstance(source, dict):
            continue
        url = source.get("url")
        if not isinstance(url, str):
            continue
        match = RE_PUBMED.search(url)
        if match:
            return match.group(1)
    return None


def to_date(value: str | None) -> str | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


def publication_date(item: dict) -> str | None:
    year = item.get("year")
    if isinstance(year, int):
        return f"{year:04d}-01-01"
    if isinstance(year, str) and year.strip():
        cleaned = year.strip()
        if cleaned.isdigit():
            return f"{int(cleaned):04d}-01-01"
    return None


def build_evidence(item: dict, filenames: defaultdict[str, int]) -> tuple[EvidenceRecord, Path]:
    identifier = str(item.get("id") or "") or ""
    if not identifier:
        raise ValueError("Each item must provide an id")
    theme = extract_theme(item)
    message = extract_message(item)
    doi = item.get("doi")
    doi_url = f"https://doi.org/{doi}" if isinstance(doi, str) and doi.strip() else None
    pmid = extract_pmid(item)
    pub_date = publication_date(item)
    last_verified = to_date(item.get("updated_at") or item.get("created_at"))
    can_be_valide = (
        item.get("access_ok")
        and (doi_url or pmid)
        and pub_date is not None
        and last_verified is not None
    )
    statut = "valide" if can_be_valide else "brouillon"
    evidence_level = None
    retraction_status = None
    if statut == "valide":
        evidence_level = {
            "scale": "unknown",
            "value": "unknown",
            "justification": message,
        }
        retraction_status = "ok"
    sources_snapshot = None
    if item.get("sources"):
        sources_snapshot = json.dumps(item["sources"], ensure_ascii=False)
    record = EvidenceRecord(
        id=identifier,
        theme=theme,
        type_etude="inconnu",
        message_clinique=message,
        statut=statut,
        doi_url=doi_url,
        pmid=pmid,
        publication_date=pub_date if statut == "valide" else None,
        last_verified=last_verified if statut == "valide" else None,
        retraction_status=retraction_status,
        evidence_level=evidence_level,
        sources_snapshot=sources_snapshot,
    )
    filename = ensure_unique(slugify(identifier), filenames) + ".json"
    return record, Path("evidence") / filename


def write_inventory(records: Iterable[tuple[EvidenceRecord, Path]], destination: Path) -> None:
    rows = []
    for record, path in records:
        row = {
            "id": record.id,
            "theme": record.theme,
            "type_etude": record.type_etude,
            "doi_url": record.doi_url or "",
            "pmid": record.pmid or "",
            "publication_date": record.publication_date or "",
            "retraction_status": record.retraction_status or "",
            "path": str(path).replace("\\", "/"),
        }
        rows.append(row)
    rows.sort(key=lambda r: r["id"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            [
                "id",
                "theme",
                "type_etude",
                "doi_url",
                "pmid",
                "publication_date",
                "retraction_status",
                "path",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def main(args: list[str]) -> None:
    if len(args) != 1:
        print("Usage: python merge2codex.py knowledge_items_clean.yaml", file=sys.stderr)
        sys.exit(1)
    source = Path(args[0])
    items = load_items(source)
    evidence_dir = Path("evidence")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    filenames: defaultdict[str, int] = defaultdict(int)
    records: list[tuple[EvidenceRecord, Path]] = []
    for item in items:
        record, path = build_evidence(item, filenames)
        path.write_text(json.dumps(record.to_json(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        records.append((record, path))
    write_inventory(records, Path("artifacts") / "evidence_inventory.csv")


if __name__ == "__main__":
    main(sys.argv[1:])
