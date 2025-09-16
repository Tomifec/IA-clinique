import argparse
import concurrent.futures as cf
import json
import pathlib
import sys
from typing import List, Dict, Any


# Import helpers whether run from repo root or directly from this folder
try:  # when run from repo root
    from tools.agents_online.curation_utils import discover, enrich_one, enrich_via_search
except Exception:  # when run as `python curate.py`
    from curation_utils import discover, enrich_one, enrich_via_search  # type: ignore


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Multi-agents réseau: DOI/PMID/Retraction → snapshots + patch FM"
    )
    ap.add_argument("--write", action="store_true", help="écrit dans le front-matter")
    ap.add_argument("--search", action="store_true", help="tente de trouver DOI/PMID via Crossref/PubMed si absent")
    ap.add_argument("--max-workers", type=int, default=6)
    ap.add_argument("targets", nargs="*", default=["evidence"], help="fichiers/dossiers/globs")
    args = ap.parse_args(argv)

    mds = discover(args.targets)
    if not mds:
        print("no evidence .md found", file=sys.stderr)
        return 2

    results: List[Dict[str, Any]] = []
    # Stream results as they complete, preserving simple status output per file
    fn = enrich_via_search if args.search else enrich_one
    with cf.ThreadPoolExecutor(max_workers=args.max_workers) as ex:
        for r in ex.map(lambda p: fn(p, args.write), mds):
            results.append(r)
            status = "OK" if r.get("ok") else "FAIL"
            changes = list((r.get("changes") or {}).keys())
            errors = r.get("errors") or []
            print(f"{status} {r.get('file')} changes={changes} errors={errors}")

    # Summary
    total = len(results)
    ok = sum(1 for r in results if r.get("ok"))
    wrote = sum(1 for r in results if r.get("wrote"))
    print(f"processed={total} ok={ok} wrote={wrote}")

    # Persist logs in both logs/ and artifacts/
    pathlib.Path("logs").mkdir(exist_ok=True)
    logs_path = pathlib.Path("logs/agents_run.json")
    logs_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    out_path = pathlib.Path("artifacts/agents_online/curation_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"logs -> {logs_path}; artifacts -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
