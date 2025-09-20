import json
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
TRIAGE_DOCS = ROOT / "docs" / "triage_pack_2025-09-13" / "core"


@pytest.fixture(scope="module")
def triage_context(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("triage_pipeline")
    csv_path = tmp_dir / "snippets.csv"
    annotations_path = tmp_dir / "annotations.yaml"
    rules_path = tmp_dir / "decision_rules.yaml"
    knowledge_path = ROOT / "graph" / "knowledge.json"
    export_path = ROOT / "graph" / "export.json"

    knowledge_path.parent.mkdir(parents=True, exist_ok=True)
    if knowledge_path.exists():
        knowledge_path.unlink()
    if export_path.exists():
        export_path.unlink()

    with csv_path.open("w", encoding="utf-8") as handle:
        subprocess.run(
            [
                "python",
                "tools/extract_snippets.py",
                str(TRIAGE_DOCS / "knowledge_crossref.json"),
            ],
            check=True,
            cwd=ROOT,
            stdout=handle,
        )

    subprocess.run(
        [
            "python",
            "tools/map2annotations.py",
            str(csv_path),
            str(ROOT / "knowledge_items_clean.yaml"),
            "--output",
            str(annotations_path),
        ],
        check=True,
        cwd=ROOT,
    )

    subprocess.run(
        [
            "python",
            "tools/json2yaml_rules.py",
            str(TRIAGE_DOCS / "decision_rules.json"),
            str(annotations_path),
            "--output",
            str(rules_path),
        ],
        check=True,
        cwd=ROOT,
    )

    subprocess.run(
        [
            "python",
            "scripts/merge2codex.py",
            "--allow",
            "annotation",
            "--allow",
            "decision_rule",
            str(annotations_path),
            str(rules_path),
            "--output",
            str(knowledge_path),
        ],
        check=True,
        cwd=ROOT,
    )

    subprocess.run(
        ["python", "scripts/etl_graph.py"],
        check=True,
        cwd=ROOT,
    )

    payload = json.loads(knowledge_path.read_text(encoding="utf-8"))
    graph = json.loads(export_path.read_text(encoding="utf-8"))
    annotations = payload.get("annotation") or []
    rules = payload.get("decision_rule") or []

    return {
        "annotations": annotations,
        "rules": rules,
        "knowledge": payload,
        "graph": graph,
    }


def test_annotation_volume(triage_context):
    annotations = triage_context["annotations"]
    assert len(annotations) == 2925
    for entry in annotations:
        assert entry["id"]
        assert entry["type"] == "clinical_snippet"
        assert entry["tag"]
        assert entry["snippet"]
        assert entry["source_file"]
    assert any(a.get("evidence_id") for a in annotations), "evidence_id manquant"


def test_rules_cover_all_tags(triage_context):
    annotations = triage_context["annotations"]
    rules = triage_context["rules"]
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


def test_merge_output_present(triage_context):
    payload = triage_context["knowledge"]
    assert "annotation" in payload and len(payload["annotation"]) == 2925
    assert "decision_rule" in payload and len(payload["decision_rule"]) >= 5


def test_graph_contains_renvoi_edge(triage_context):
    graph = triage_context["graph"]
    edges = graph.get("edges") or []
    assert any(edge.get("type") == "RENVOI" for edge in edges), "RENVOI edge manquante"
