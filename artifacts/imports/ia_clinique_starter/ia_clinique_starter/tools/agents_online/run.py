
import argparse, concurrent.futures as cf, datetime as dt, json, pathlib, re, sys
from typing import Optional, Tuple, Dict, Any, List
import requests, yaml

UA={"User-Agent":"IaCliniqueAgent/1.0 (+local)"}
FM_RX=re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.S)

def read_fm(p): 
    t=p.read_text(encoding="utf-8"); m=FM_RX.match(t); 
    return ((yaml.safe_load(m.group(1)) or {}), m.group(2)) if m else ({}, t)

def write_fm(p,fm,body):
    y=yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).strip()
    p.write_text(f"---\n{y}\n---\n{body}", encoding="utf-8")

def iso_from_crossref(msg):
    parts=(msg.get("issued") or {}).get("date-parts")
    if parts and parts[0]:
        a=parts[0]+[1]*(3-len(parts[0]))
        return f"{a[0]:04d}-{a[1]:02d}-{a[2]:02d}"
    return None

def xref_by_doi(doi):
    r=requests.get(f"https://api.crossref.org/works/{doi}", timeout=15, headers=UA); r.raise_for_status()
    return r.json().get("message", {})

def pmid_from_doi(doi):
    u=f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={doi}%5BDOI%5D&retmode=json"
    r=requests.get(u, timeout=15, headers=UA); r.raise_for_status()
    ids=r.json().get("esearchresult",{}).get("idlist",[])
    return ids[0] if ids else None

def pubmed_summary(pmid):
    u=f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pmid}&retmode=json"
    r=requests.get(u, timeout=15, headers=UA); r.raise_for_status()
    return r.json().get("result",{}).get(pmid,{})

def retraction_flag(summary):
    types=[t.lower() for t in summary.get("pubtype",[])]
    if "retracted publication" in types: return "retracted"
    if "retraction of publication" in types or "expression of concern" in types: return "concern"
    return "ok"

def snapshot_path(md,fm):
    evid_id=fm.get("id") or md.stem
    d=(md.parent/"_audit"); d.mkdir(exist_ok=True)
    return d/f"{evid_id}.json"

def enrich_one(md, write):
    fm, body = read_fm(md)
    out={"file":str(md),"ok":True,"errors":[],"changes":{}}
    if not fm:
        out.update(ok=False, errors=["missing_front_matter"]); return out

    doi=None
    if isinstance(fm.get("doi_url"), str): doi=fm["doi_url"].replace("https://doi.org/","").strip().strip("/")
    elif isinstance(fm.get("doi"), str): doi=fm["doi"].strip().strip("/")

    snap={"checked_at": dt.date.today().isoformat()}
    try:
        if doi:
            cr=xref_by_doi(doi)
            snap["doi_url"]=f"https://doi.org/{doi}"
            snap["title"]=(cr.get("title") or [None])[0]
            snap["journal"]=(cr.get("container-title") or [None])[0]
            snap["authors"]=[" ".join(filter(None, [a.get("given"), a.get("family")])) for a in (cr.get("author") or [])]
            snap["publication_date"]=iso_from_crossref(cr)
            if snap.get("publication_date") and fm.get("publication_date")!=snap["publication_date"]:
                out["changes"]["publication_date"]=snap["publication_date"]
                if write: fm["publication_date"]=snap["publication_date"]

        pmid=fm.get("pmid")
        if not pmid and doi:
            pmid=pmid_from_doi(doi)
            if pmid and write: fm["pmid"]=pmid; out["changes"]["pmid"]=pmid

        retr="unknown"
        if pmid:
            retr=retraction_flag(pubmed_summary(str(pmid)))
        snap["retraction_status"]=retr
        if retr!="unknown" and fm.get("retraction_status")!=retr:
            out["changes"]["retraction_status"]=retr
            if write: fm["retraction_status"]=retr

        today=dt.date.today().isoformat()
        if fm.get("last_verified")!=today:
            out["changes"]["last_verified"]=today
            if write: fm["last_verified"]=today

        sp=snapshot_path(md,fm)
        sp.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")

        if write:
            write_fm(md,fm,body)

    except requests.RequestException as e:
        out["ok"]=False; out["errors"].append(f"net:{type(e).__name__}")
    except Exception as e:
        out["ok"]=False; out["errors"].append(f"err:{type(e).__name__}")
    return out

def discover(paths):
    root=pathlib.Path(".").resolve(); found=[]
    for p in paths:
        P=root/p
        if P.is_file() and P.suffix.lower()==".md": found.append(P)
        elif P.is_dir(): found+=list(P.rglob("*.md"))
    found=[f for f in found if "evidence" in f.parts and f.name.lower().endswith(".md")]
    return sorted(set(found))

def main():
    ap=argparse.ArgumentParser(description="Agents réseau: DOI/PMID/Retraction → snapshots + patch FM")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--max-workers", type=int, default=6)
    ap.add_argument("targets", nargs="*", default=["evidence"])
    a=ap.parse_args()

    mds=discover(a.targets)
    if not mds: print("no evidence .md found", file=sys.stderr); sys.exit(2)

    res=[]
    with cf.ThreadPoolExecutor(max_workers=a.max_workers) as ex:
        for r in ex.map(lambda p: enrich_one(p, a.write), mds):
            res.append(r)
            print(f"[{'OK' if r['ok'] else 'FAIL'}] {r['file']} changes={list(r['changes'].keys())} errors={r['errors']}")

    pathlib.Path("logs").mkdir(exist_ok=True)
    pathlib.Path("logs/agents_run.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__=="__main__":
    main()
