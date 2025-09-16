import os
import re
import json
import time
import pathlib
import datetime as dt
from typing import Tuple, Dict, Any, Optional, List

import requests
import yaml
from urllib.parse import quote


UA: Dict[str, str] = {"User-Agent": "IaCliniqueAgent/1.0 (+local)"}

# --- Front-matter helpers ---

FM_RX = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.S)


def read_fm(p: pathlib.Path) -> Tuple[Dict[str, Any], str]:
    t = p.read_text(encoding="utf-8")
    m = FM_RX.match(t)
    if m:
        head = m.group(1)
        body = m.group(2)
        fm = yaml.safe_load(head) or {}
        return fm, body
    return {}, t


def write_fm(p: pathlib.Path, fm: Dict[str, Any], body: str) -> None:
    y = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).strip()
    p.write_text(f"---\n{y}\n---\n{body.lstrip()}", encoding="utf-8")


# --- Metadata helpers ---

def iso_from_crossref(msg: Dict[str, Any]) -> Optional[str]:
    parts = (
        (msg.get("issued") or {}).get("date-parts")
        or (msg.get("published-print") or {}).get("date-parts")
        or (msg.get("published-online") or {}).get("date-parts")
    )
    if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0]:
        dp = parts[0]
        y = int(dp[0])
        m = int(dp[1]) if len(dp) > 1 else 1
        d = int(dp[2]) if len(dp) > 2 else 1
        return f"{y:04d}-{m:02d}-{d:02d}"
    return None


def xref_by_doi(doi: str) -> Dict[str, Any]:
    u = f"https://api.crossref.org/works/{quote(doi)}"
    r = _get_with_backoff(u, params=None, timeout=15, headers=UA)
    return r.json().get("message", {})


def pmid_from_doi(doi: str) -> Optional[str]:
    term = quote(doi) + "%5BDOI%5D"
    params = {"db": "pubmed", "term": term, "retmode": "json"}
    email = os.getenv("NCBI_EMAIL")
    if email:
        params.update({"email": email, "tool": "IaCliniqueLocal"})
    u = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    r = _get_with_backoff(u, params=params, timeout=20, headers=UA)
    ids = (r.json().get("esearchresult", {}) or {}).get("idlist", [])
    return ids[0] if ids else None


def pubmed_summary(pmid: str) -> Dict[str, Any]:
    params = {"db": "pubmed", "id": str(pmid), "retmode": "json"}
    email = os.getenv("NCBI_EMAIL")
    if email:
        params.update({"email": email, "tool": "IaCliniqueLocal"})
    u = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    r = _get_with_backoff(u, params=params, timeout=20, headers=UA)
    return (r.json().get("result", {}) or {}).get(str(pmid), {})


def retraction_flag(summary: Dict[str, Any]) -> str:
    pts = [str(t).lower() for t in summary.get("pubtype", [])]
    if any("retracted publication" in t for t in pts):
        return "retracted"
    if any("retraction of publication" in t or "expression of concern" in t for t in pts):
        return "concern"
    return "ok"


# --- Enrichment helpers ---

def snapshot_path(md: pathlib.Path, fm: Dict[str, Any]) -> pathlib.Path:
    evid_id = (fm.get("id") or md.stem)
    # keep snapshots under evidence/_audit
    d = md.parent / "_audit"
    d.mkdir(parents=True, exist_ok=True)
    safe_id = re.sub(r"[^a-zA-Z0-9_.-]", "_", str(evid_id))
    return d / f"{safe_id}.json"


def enrich_one(md: pathlib.Path, write: bool = False) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "file": str(md),
        "ok": True,
        "errors": [],
        "changes": {},
        "wrote": False,
        "snapshot": None,
    }

    if not md.exists():
        out["ok"] = False
        out["errors"].append("file not found")
        return out

    fm, body = read_fm(md)
    if not fm:
        out.update(ok=False)
        out["errors"].append("missing_front_matter")
        return out

    before = dict(fm)
    changes: Dict[str, Any] = {}
    sources: Dict[str, Any] = {}

    # DOI normalization and extraction (supports 'doi_url' or 'doi'); only persist 'doi_url' per schema
    def normalize_doi(val: Optional[str]) -> Optional[str]:
        if not val:
            return None
        v = str(val).strip()
        v = re.sub(r"^(https?://(dx\.)?doi\.org/)", "", v, flags=re.I)
        v = v.strip().strip("/")
        return v or None

    doi: Optional[str] = None
    if isinstance(fm.get("doi_url"), str) and fm.get("doi_url").strip():
        doi = normalize_doi(fm["doi_url"])  # may strip prefix
    elif isinstance(fm.get("doi"), str) and fm.get("doi").strip():
        doi = normalize_doi(fm["doi"])
        # if we only had 'doi', convert to schema-compliant 'doi_url'
        if doi and not fm.get("doi_url"):
            fm["doi_url"] = f"https://doi.org/{doi}"
            changes["doi_url"] = fm["doi_url"]
            # drop non-schema key if present
            if "doi" in fm:
                del fm["doi"]

    pmid = None
    if fm.get("pmid") not in (None, ""):
        pmid = str(fm.get("pmid")).strip()

    # Crossref enrichment
    if doi:
        try:
            cr = xref_by_doi(doi)
            sources["crossref"] = cr
            iso = iso_from_crossref(cr)
            if iso and fm.get("publication_date") != iso:
                fm["publication_date"] = iso
                changes["publication_date"] = iso
        except Exception as e:
            out["errors"].append(f"crossref: {type(e).__name__}: {e}")

    # PMID enrichment
    if doi and not pmid:
        try:
            pmid_found = pmid_from_doi(doi)
            if pmid_found:
                fm["pmid"] = pmid_found
                changes["pmid"] = pmid_found
                pmid = pmid_found
        except Exception as e:
            out["errors"].append(f"pmid_lookup: {type(e).__name__}: {e}")

    # PubMed summary and retraction flag
    if pmid:
        try:
            summ = pubmed_summary(pmid)
            sources["pubmed_summary"] = summ
            status = retraction_flag(summ)
            if fm.get("retraction_status") != status:
                fm["retraction_status"] = status
                changes["retraction_status"] = status
        except Exception as e:
            out["errors"].append(f"pubmed_summary: {type(e).__name__}: {e}")

    # Last verified timestamp
    today = dt.date.today().isoformat()
    if fm.get("last_verified") != today:
        fm["last_verified"] = today
        changes["last_verified"] = today

    # Snapshot writing if we fetched anything
    if sources:
        snap_path = snapshot_path(md, fm)
        snap_payload = {
            "file": str(md),
            "id": fm.get("id") or md.stem,
            "doi": doi,
            "pmid": pmid,
            "checked_at": dt.date.today().isoformat(),
            "fetched_at": dt.datetime.utcnow().isoformat() + "Z",
            "sources": sources,
        }
        snap_path.write_text(json.dumps(snap_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        out["snapshot"] = str(snap_path)
        # Store reference to snapshot in FM if not present
        if not fm.get("sources_snapshot"):
            rel = str(snap_path.relative_to(md.parent)) if snap_path.is_relative_to(md.parent) else str(snap_path)
            fm["sources_snapshot"] = rel
            changes["sources_snapshot"] = rel

    out["changes"] = {k: {"from": before.get(k), "to": v} for k, v in changes.items()}

    if write and changes:
        write_fm(md, fm, body)
        out["wrote"] = True

    # ok if no fatal errors; also mark not ok on network errors
    if any(err for err in out["errors"] if "file not found" in err or "missing_front_matter" in err):
        out["ok"] = False
    elif any(err.startswith("crossref:") or err.startswith("pmid_lookup:") or err.startswith("pubmed_summary:") for err in out["errors"]):
        out["ok"] = False
    return out


def discover(paths: List[str]) -> List[pathlib.Path]:
    """Discover Markdown files from given paths/globs.
    - If a path is a directory: include all *.md recursively.
    - If a path is a file ending with .md: include it.
    - Otherwise treat as a glob and expand; for directories, recurse to *.md.
    Returns a sorted list of unique Paths.
    """
    root = pathlib.Path(".").resolve()
    found: List[pathlib.Path] = []
    specs = paths or ["evidence"]
    for spec in specs:
        p = pathlib.Path(spec)
        if p.exists():
            if p.is_dir():
                found.extend(sorted(p.rglob("*.md")))
            elif p.is_file() and p.suffix.lower() == ".md":
                found.append(p)
        else:
            for g in root.glob(spec):
                if g.is_dir():
                    found.extend(sorted(g.rglob("*.md")))
                elif g.is_file() and g.suffix.lower() == ".md":
                    found.append(g)
    # dedupe
    uniq = []
    seen = set()
    for f in sorted(found, key=lambda x: str(x)):
        s = str(f)
        if s not in seen:
            seen.add(s)
            uniq.append(f)
    return uniq


def enrich_many(paths: List[str], write: bool = False) -> List[Dict[str, Any]]:
    files = discover(paths)
    return [enrich_one(f, write=write) for f in files]


def _get_with_backoff(url: str, params: Optional[Dict[str, Any]] = None, timeout: int = 20, headers: Optional[Dict[str, str]] = None, retries: int = 5, backoff: float = 1.5) -> requests.Response:
    """HTTP GET with simple exponential backoff for 429/5xx."""
    attempt = 0
    last_exc: Optional[Exception] = None
    while attempt < retries:
        try:
            resp = requests.get(url, params=params, timeout=timeout, headers=headers)
            if resp.status_code in (429, 500, 502, 503, 504):
                # Retryable
                delay = backoff ** attempt
                time.sleep(delay)
                attempt += 1
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            last_exc = e
            # If 429/5xx, sleep and retry; else raise
            status = getattr(e.response, "status_code", None) if hasattr(e, "response") else None
            if status in (429, 500, 502, 503, 504):
                delay = backoff ** attempt
                time.sleep(delay)
                attempt += 1
                continue
            raise
    if last_exc:
        raise last_exc
    # Fallback raise if somehow no exception captured
    raise RuntimeError("HTTP backoff failed without exception")


# --- Discovery + search-assisted enrichment ---

def h1_title(md: pathlib.Path) -> Optional[str]:
    try:
        txt = md.read_text(encoding="utf-8")
    except Exception:
        return None
    for line in txt.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def search_crossref_biblio(query: str, rows: int = 5) -> List[Dict[str, Any]]:
    if not query:
        return []
    params = {
        "query.bibliographic": query,
        "rows": str(rows),
        "select": "DOI,title,author,container-title,issued,type,URL",
        "sort": "published",
        "order": "desc",
    }
    r = _get_with_backoff("https://api.crossref.org/works", params=params, timeout=25, headers=UA)
    return (r.json().get("message", {}) or {}).get("items", [])


def choose_best_crossref(items: List[Dict[str, Any]], query: str) -> Optional[Dict[str, Any]]:
    if not items:
        return None
    q = query.lower()
    tokens = [t for t in re.split(r"\W+", q) if t]
    def score(it: Dict[str, Any]) -> int:
        t = " ".join(it.get("title") or []) if isinstance(it.get("title"), list) else str(it.get("title") or "")
        c = " ".join(it.get("container-title") or []) if isinstance(it.get("container-title"), list) else str(it.get("container-title") or "")
        s = (t + " " + c).lower()
        return sum(1 for tok in tokens if tok and tok in s)
    items_sorted = sorted(items, key=score, reverse=True)
    return items_sorted[0] if items_sorted else None


def enrich_via_search(md: pathlib.Path, write: bool = False) -> Dict[str, Any]:
    out = {"file": str(md), "ok": True, "errors": [], "changes": {}, "wrote": False, "snapshot": None}
    if not md.exists():
        out.update(ok=False)
        out["errors"].append("file not found")
        return out
    fm, body = read_fm(md)
    if not fm:
        out.update(ok=False)
        out["errors"].append("missing_front_matter")
        return out
    before = dict(fm)
    changes: Dict[str, Any] = {}

    doi = None
    if isinstance(fm.get("doi_url"), str) and fm["doi_url"].strip():
        doi = re.sub(r"^(https?://(dx\.)?doi\.org/)", "", fm["doi_url"].strip(), flags=re.I).strip("/")
    if not doi:
        title = h1_title(md) or fm.get("theme") or fm.get("id") or md.stem
        # add domain hint to improve match quality
        hint = " low back pain"
        results = []
        try:
            results = search_crossref_biblio(title + hint)
        except Exception as e:
            out["errors"].append(f"search:{type(e).__name__}:{e}")
        if results:
            best = choose_best_crossref(results, title)
            if best and best.get("DOI"):
                doi = best["DOI"]
                fm["doi_url"] = f"https://doi.org/{doi}"
                changes["doi_url"] = fm["doi_url"]
    # Enrich from DOI as in enrich_one
    sources: Dict[str, Any] = {}
    if doi:
        try:
            cr = xref_by_doi(doi)
            sources["crossref"] = cr
            iso = iso_from_crossref(cr)
            if iso and fm.get("publication_date") != iso:
                fm["publication_date"] = iso
                changes["publication_date"] = iso
        except Exception as e:
            out["errors"].append(f"crossref:{type(e).__name__}:{e}")
        try:
            pmid = fm.get("pmid")
            if not pmid:
                pmid = pmid_from_doi(doi)
                if pmid:
                    fm["pmid"] = pmid
                    changes["pmid"] = pmid
            if pmid:
                summ = pubmed_summary(str(pmid))
                status = retraction_flag(summ)
                if fm.get("retraction_status") != status:
                    fm["retraction_status"] = status
                    changes["retraction_status"] = status
        except Exception as e:
            out["errors"].append(f"pubmed:{type(e).__name__}:{e}")

    # Ensure required fields if promoting
    today = dt.date.today().isoformat()
    if fm.get("last_verified") != today:
        fm["last_verified"] = today
        changes["last_verified"] = today
    if "evidence_level" not in fm:
        fm["evidence_level"] = {"scale": "OCEBM", "value": "unspecified"}
        changes["evidence_level"] = fm["evidence_level"]
    # ensure retraction_status exists, default ok
    if "retraction_status" not in fm:
        fm["retraction_status"] = "ok"
        changes["retraction_status"] = "ok"

    # write snapshot if we fetched something
    if sources:
        snap_path = snapshot_path(md, fm)
        snap_payload = {
            "file": str(md),
            "id": fm.get("id") or md.stem,
            "doi": doi,
            "pmid": fm.get("pmid"),
            "checked_at": today,
            "fetched_at": dt.datetime.utcnow().isoformat() + "Z",
            "sources": sources,
        }
        snap_path.write_text(json.dumps(snap_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        out["snapshot"] = str(snap_path)
        if not fm.get("sources_snapshot"):
            try:
                rel = str(snap_path.relative_to(md.parent))
            except Exception:
                rel = str(snap_path)
            fm["sources_snapshot"] = rel
            changes["sources_snapshot"] = rel

    # Promote if DOI/PMID exist and publication_date present
    if (fm.get("doi_url") or fm.get("pmid")) and fm.get("publication_date"):
        if fm.get("statut") != "valide":
            fm["statut"] = "valide"
            changes["statut"] = "valide"

    out["changes"] = {k: {"from": before.get(k), "to": v} for k, v in changes.items()}
    if write and changes:
        write_fm(md, fm, body)
        out["wrote"] = True
    return out
