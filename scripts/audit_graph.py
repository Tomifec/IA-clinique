#!/usr/bin/env python3
import json
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[1]
graph_path = ROOT / 'graph' / 'export.json'
reports = ROOT / 'artifacts' / 'reports'
reports.mkdir(parents=True, exist_ok=True)


def load_graph() -> Dict:
    if not graph_path.exists():
        return {"nodes": [], "edges": []}
    return json.loads(graph_path.read_text(encoding='utf-8'))


def main() -> int:
    g = load_graph()
    nodes: List[Dict] = g.get('nodes', [])
    edges: List[Dict] = g.get('edges', [])

    by_kind: Dict[str, int] = {}
    for n in nodes:
        by_kind[n.get('kind', 'Unknown')] = by_kind.get(n.get('kind', 'Unknown'), 0) + 1

    # Strategy coverage: number of outgoing edges per strategy id
    out_counts: Dict[str, int] = {}
    for e in edges:
        src = e.get('src')
        if not src:
            continue
        out_counts[src] = out_counts.get(src, 0) + 1

    # Summaries
    summary = {
        'node_counts': by_kind,
        'edges_count': len(edges),
        'strategies_linked': len(out_counts),
        'avg_links_per_strategy': (sum(out_counts.values()) / len(out_counts)) if out_counts else 0.0,
        'max_links_strategy': max(out_counts.items(), key=lambda x: x[1]) if out_counts else None,
    }

    # Write JSON summary
    (reports / 'graph_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

    # Write CSV coverage per strategy
    csv_lines = ['strategy_id,links'] + [f'{sid},{cnt}' for sid, cnt in sorted(out_counts.items(), key=lambda x: (-x[1], x[0]))]
    (reports / 'strategy_coverage.csv').write_text('\n'.join(csv_lines) + '\n', encoding='utf-8')

    # Evidence count by basename prefix (theme heuristic)
    # Parse evidence id from node id, count grouped by first token after 'evidence_'
    from collections import defaultdict
    theme_counts = defaultdict(int)
    for n in nodes:
        if n.get('kind') != 'Evidence':
            continue
        evid = str(n.get('id') or '')
        if not evid.startswith('evidence_'):
            continue
        rest = evid[len('evidence_'):]
        theme = rest.split('_', 1)[0] if '_' in rest else rest
        theme_counts[theme] += 1
    lines = ['theme,count'] + [f'{k},{v}' for k, v in sorted(theme_counts.items(), key=lambda x: (-x[1], x[0]))]
    (reports / 'evidence_by_theme.csv').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    print(f"summary -> {reports/'graph_summary.json'}; coverage -> {reports/'strategy_coverage.csv'}; themes -> {reports/'evidence_by_theme.csv'}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

