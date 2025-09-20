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


def test_rules_cover_all_tags():
    annotations = load_annotations()
    rules = load_rules()
    tag_set = {entry["tag"] for entry in annotations}
    linked = set()
    for rule in rules:
        linked.update(rule["linked_annotations"])
    assert linked.issuperset({entry["id"] for entry in annotations})
    covered_tags = set()
    for rule in rules:
        covered_tags.update(rule["condition"]["any_tags"])
        covered_tags.update(rule["condition"]["unless_tags"])
    assert covered_tags == tag_set


def test_merge_output_present():
    payload = json.loads((ROOT / "graph" / "knowledge.json").read_text(encoding="utf-8"))
    assert "annotation" in payload and len(payload["annotation"]) == 2925
    assert "decision_rule" in payload and len(payload["decision_rule"]) >= 5
