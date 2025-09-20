import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_annotations():
    data = yaml.safe_load((ROOT / "items" / "annotations.yaml").read_text(encoding="utf-8"))
    return data["annotations"]


def load_rules():
    data = yaml.safe_load((ROOT / "items" / "decision_rules.yaml").read_text(encoding="utf-8"))
    return data["decision_rules"]


def test_annotation_volume():
    annotations = load_annotations()
    assert len(annotations) == 2925
    for entry in annotations:
        assert entry["id"]
        assert entry["type"] == "clinical_snippet"
        assert entry["tag"]
        assert entry["snippet"]
        assert entry["source_file"]
    assert any(a.get("evidence_id") for a in annotations), "evidence_id manquant"


def test_rules_cover_all_tags():
    annotations = load_annotations()
    rules = load_rules()
    tag_set = {entry["tag"] for entry in annotations}
    linked = set()
    for rule in rules:
        linked.update(rule["linked_annotations"])
    for entry in annotations:
        ref = entry.get("evidence_id") or entry["id"]
        assert ref in linked
    covered_tags = set()
    for rule in rules:
        covered_tags.update(rule["condition"]["any_tags"])
        covered_tags.update(rule["condition"]["unless_tags"])
    assert covered_tags == tag_set


def test_merge_output_present():
    payload = json.loads((ROOT / "graph" / "knowledge.json").read_text(encoding="utf-8"))
    assert "annotation" in payload and len(payload["annotation"]) == 2925
    assert "decision_rule" in payload and len(payload["decision_rule"]) >= 5


def test_graph_contains_renvoi_edge():
    graph = json.loads((ROOT / "graph" / "export.json").read_text(encoding="utf-8"))
    edges = graph.get("edges") or []
    assert any(edge.get("type") == "RENVOI" for edge in edges), "RENVOI edge manquante"
