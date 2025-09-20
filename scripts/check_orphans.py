#!/usr/bin/env python3
"""Fail if more than 5% of annotations are not linked to decision rules."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Set

import yaml

ROOT = Path(__file__).resolve().parents[1]
ANNOTATIONS_PATH = ROOT / "items" / "annotations.yaml"
RULES_PATH = ROOT / "items" / "decision_rules.yaml"
THRESHOLD = 0.05


def load_annotations(path: Path) -> Dict[str, str | None]:
    if not path.exists():
        raise FileNotFoundError(f"Missing annotations file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = data.get("annotations") or data.get("annotation") or []
    annotations: Dict[str, str | None] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        identifier = entry.get("id")
        if not identifier:
            continue
        evidence_id = entry.get("evidence_id")
        annotations[str(identifier)] = str(evidence_id) if evidence_id else None
    if not annotations:
        raise ValueError("No annotations found; cannot compute orphan ratio")
    return annotations


def load_rules(path: Path) -> List[Dict[str, object]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing decision rules file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = data.get("decision_rules") or data.get("decision_rule") or []
    return [entry for entry in entries if isinstance(entry, dict)]


def compute_orphans() -> int:
    annotations = load_annotations(ANNOTATIONS_PATH)
    rules = load_rules(RULES_PATH)

    linked: Set[str] = set()
    for rule in rules:
        refs = rule.get("linked_annotations", [])
        if isinstance(refs, list):
            linked.update(str(ref) for ref in refs)
    covered: Set[str] = set()
    for ann_id, evidence_id in annotations.items():
        reference = evidence_id or ann_id
        if reference in linked:
            covered.add(ann_id)
    orphans = set(annotations) - covered

    total = len(annotations)
    ratio = len(orphans) / total
    linked_count = len(covered)
    print(
        "annotations="
        f"{total} linked={linked_count} orphans={len(orphans)} ratio={ratio:.4f}"
    )
    if ratio > THRESHOLD:
        raise SystemExit(f"Orphan ratio {ratio:.2%} exceeds threshold of {THRESHOLD:.0%}")
    return len(orphans)


if __name__ == "__main__":
    compute_orphans()
