import argparse
import concurrent.futures as cf
import datetime as dt
import json
import pathlib
import re
import sys
from typing import Optional, Tuple, Dict, Any, List

import requests
import yaml


UA: Dict[str, str] = {"User-Agent": "IaCliniqueAgent/1.0 (+local)"}

# Try to import curation helpers; if unavailable, HTTP mode still works
try:
    from tools.agents_online.curation_utils import discover, enrich_one  # type: ignore
except Exception:  # running from within folder or without package context
    try:
        from curation_utils import discover, enrich_one  # type: ignore
    except Exception:
        discover = None  # type: ignore
        enrich_one = None  # type: ignore


def load_config(path: pathlib.Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict) or "jobs" not in data or not isinstance(data["jobs"], list):
        raise ValueError("Config must be a mapping with a 'jobs' list")
    return data


def make_session(extra_headers: Optional[Dict[str, str]] = None) -> requests.Session:
    s = requests.Session()
    headers = {**UA}
    if extra_headers:
        headers.update(extra_headers)
    s.headers.update(headers)
    return s


def _one_request(
    sess: requests.Session,
    job: Dict[str, Any],
    timeout: float,
    retries: int,
) -> Dict[str, Any]:
    url = job.get("url")
    method = str(job.get("method", "GET")).upper()
    params = job.get("params") or None
    data = job.get("data") or None
    json_body = job.get("json") or None
    name = job.get("name") or url
    headers = job.get("headers") or {}

    result: Dict[str, Any] = {
        "name": name,
        "url": url,
        "method": method,
        "ok": False,
        "status_code": None,
        "error": None,
        "headers": None,
        "text_sample": None,
        "fetched_at": dt.datetime.utcnow().isoformat() + "Z",
    }

    if not url:
        result["error"] = "missing url"
        return result

    # Per-request headers override session headers
    if headers:
        sess.headers.update(headers)

    attempt = 0
    while True:
        try:
            resp = sess.request(
                method,
                url,
                params=params,
                data=data,
                json=json_body,
                timeout=timeout,
            )
            result["status_code"] = resp.status_code
            result["headers"] = dict(resp.headers)
            result["ok"] = resp.ok
            # Keep output compact; store a small sample only
            text = resp.text or ""
            result["text_sample"] = text[:2048]
            return result
        except Exception as e:
            attempt += 1
            result["error"] = f"{type(e).__name__}: {e}"
            if attempt > retries:
                return result


def run_jobs(
    jobs: List[Dict[str, Any]],
    max_workers: int,
    timeout: float,
    retries: int,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    with make_session() as sess:
        with cf.ThreadPoolExecutor(max_workers=max_workers) as ex:
            futs = [
                ex.submit(_one_request, sess, job, timeout, retries)
                for job in jobs
            ]
            for fut in cf.as_completed(futs):
                results.append(fut.result())
    return results


def _run_curate(targets: List[str], write: bool, max_workers: int) -> int:
    if discover is None or enrich_one is None:
        print("curation utilities not available", file=sys.stderr)
        return 2
    files = discover(targets or ["evidence"])  # type: ignore
    if not files:
        print("no evidence .md found", file=sys.stderr)
        return 2

    results: List[Dict[str, Any]] = []
    with cf.ThreadPoolExecutor(max_workers=max_workers) as ex:
        for r in ex.map(lambda p: enrich_one(p, write), files):  # type: ignore
            results.append(r)
            status = "OK" if r.get("ok") else "FAIL"
            changes = list((r.get("changes") or {}).keys())
            errors = r.get("errors") or []
            print(f"{status} {r.get('file')} changes={changes} errors={errors}")

    # Persist logs
    pathlib.Path("logs").mkdir(exist_ok=True)
    logs_path = pathlib.Path("logs/agents_run.json")
    logs_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    out_path = pathlib.Path("artifacts/agents_online/curation_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"logs -> {logs_path}; artifacts -> {out_path}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="agents_online: HTTP jobs runner and curation helper")
    # HTTP jobs mode args
    p.add_argument("--config", default="tools/agents_online/jobs.yml", help="YAML config with a 'jobs' list")
    p.add_argument("--out", default="artifacts/agents_online/results.json", help="Output JSON path for HTTP mode")
    p.add_argument("--timeout", type=float, default=20.0)
    p.add_argument("--retries", type=int, default=1)
    # Shared
    p.add_argument("--max-workers", type=int, default=6)
    # Curation mode trigger: any positional targets → curate evidence files
    p.add_argument("targets", nargs="*", help="If provided, run curation on these files/dirs/globs (default evidence)")
    p.add_argument("--write", action="store_true", help="When in curation mode, patch front-matter")

    args = p.parse_args(argv)

    # If user passed targets (e.g., 'evidence'), run curation mode
    if args.targets:
        return _run_curate(args.targets, args.write, args.max_workers)

    # Otherwise, HTTP jobs mode
    cfg_path = pathlib.Path(args.config)
    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    config = load_config(cfg_path)
    jobs = config.get("jobs", [])
    results = run_jobs(jobs, args.max_workers, args.timeout, args.retries)

    payload = {
        "generated_at": dt.datetime.utcnow().isoformat() + "Z",
        "config": str(cfg_path),
        "results": results,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
