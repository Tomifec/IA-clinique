#!/usr/bin/env python3
"""Convert decision_rules.json into structured YAML referencing annotations."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set

import yaml


def load_annotations(path: Path) -> Dict[str, Dict[str, object]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = data.get("annotations") or data.get("annotation") or []
    annotations: Dict[str, Dict[str, object]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        identifier = entry.get("id")
        if not identifier:
            continue
        annotations[str(identifier)] = entry
    return annotations


def map_tag_to_annotations(annotations: Dict[str, Dict[str, object]]) -> Dict[str, Set[str]]:
    mapping: Dict[str, Set[str]] = defaultdict(set)
    for identifier, entry in annotations.items():
        tag = entry.get("tag")
        if isinstance(tag, str) and tag:
            mapping[tag].add(identifier)
    return mapping


def build_rule_payload(
    key: str,
    data: Dict[str, object],
    tag_map: Dict[str, Set[str]],
    fallback_rule: Dict[str, object] | None,
) -> Dict[str, object]:
    evidence_items = data.get("evidence") or []
    evidence_themes = {
        item.get("theme")
        for item in evidence_items
        if isinstance(item, dict) and isinstance(item.get("theme"), str)
    }

    any_tags = list(dict.fromkeys((data.get("if_any") or []) + list(evidence_themes)))
    unless_tags = list(dict.fromkeys(data.get("and_not") or data.get("unless") or []))

    if not any_tags and fallback_rule is not None:
        prev_cond = fallback_rule.get("condition", {})
        if isinstance(prev_cond, dict):
            inherited = prev_cond.get("any_tags", [])
            if isinstance(inherited, list):
                any_tags = list(inherited)

    linked: Set[str] = set()
    for tag in any_tags + unless_tags:
        linked.update(tag_map.get(tag, set()))

    return {
        "id": f"triage_{key}",
        "type": "decision_rule",
        "category": key,
        "condition": {
            "any_tags": sorted(set(any_tags)),
            "all_tags": [],
            "unless_tags": sorted(set(unless_tags)),
        },
        "action": data.get("action", ""),
        "linked_annotations": sorted(linked),
    }


def ensure_tag_coverage(rules: List[Dict[str, object]], tag_map: Dict[str, Set[str]]) -> None:
    covered: Set[str] = set()
    for rule in rules:
        condition = rule.get("condition", {})
        if isinstance(condition, dict):
            covered.update(condition.get("any_tags", []))
            covered.update(condition.get("unless_tags", []))
    missing = set(tag_map) - covered
    if not missing:
        return
    anchor = rules[0]
    cond = anchor.setdefault("condition", {})
    if isinstance(cond, dict):
        any_tags = cond.setdefault("any_tags", [])
        if isinstance(any_tags, list):
            for tag in sorted(missing):
                if tag not in any_tags:
                    any_tags.append(tag)
    linked = anchor.setdefault("linked_annotations", [])
    if isinstance(linked, list):
        for tag in missing:
            linked.extend(sorted(tag_map.get(tag, [])))
        anchor["linked_annotations"] = sorted(set(linked))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_path", type=Path, help="Path to decision_rules.json")
    parser.add_argument("annotations", type=Path, help="Path to annotations.yaml")
    parser.add_argument("--output", type=Path, default=None, help="Destination YAML file")
    args = parser.parse_args()

    annotations = load_annotations(args.annotations)
    tag_map = map_tag_to_annotations(annotations)

    data = json.loads(args.json_path.read_text(encoding="utf-8"))

    rules: List[Dict[str, object]] = []
    fallback_rule: Dict[str, object] | None = None
    for key, value in data.items():
        if not isinstance(value, dict):
            continue
        rule_payload = build_rule_payload(key, value, tag_map, fallback_rule)
        rules.append(rule_payload)
        fallback_rule = rule_payload

    ensure_tag_coverage(rules, tag_map)

    payload = {"decision_rules": rules}
    text = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
