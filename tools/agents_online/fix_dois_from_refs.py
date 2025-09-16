import re
import pathlib
from typing import Dict, List, Optional, Tuple

try:
    from tools.agents_online.curation_utils import xref_by_doi
    from tools.agents_online.curation_utils import search_crossref_biblio, choose_best_crossref  # type: ignore
except Exception:
    from curation_utils import xref_by_doi, search_crossref_biblio, choose_best_crossref  # type: ignore


ROOT = pathlib.Path(__file__).resolve().parents[2]


DOI_URL_RX = re.compile(r"https?://doi\.org/(10\.\S+)", re.I)
# Match bullet lines like:
# - ?? **10.1016/...** - Title...
# - ok **10.7326/...** - Title...
LINE_RX = re.compile(r"^\s*-\s+.*\*\*(10\.[^*]+)\*\*\s*-\s*(.*)$", re.I)


def parse_refs_md(path: pathlib.Path) -> Dict[str, str]:
    """Return mapping: doi -> title (if available)"""
    out: Dict[str, str] = {}
    if not path.exists():
        return out
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    pending_doi: Optional[str] = None
    pending_title: Optional[str] = None
    for ln in lines:
        m = LINE_RX.match(ln)
        if m:
            # example line: - ?? **10.1016/...** - Title...
            candidate_doi = (m.group(1) or '').strip()
            title = (m.group(2) or '').strip()
            pending_doi = candidate_doi
            pending_title = title if title and 'Titre non disponible' not in title else None
            continue
        m2 = DOI_URL_RX.search(ln)
        if m2:
            doi2 = m2.group(1).strip()
            doi = (pending_doi or doi2).strip()
            if doi and pending_title:
                out[doi] = pending_title
            # reset
            pending_doi = None
            pending_title = None
    return out


def crossref_resolves(doi: str) -> bool:
    try:
        msg = xref_by_doi(doi)
        return bool(msg and isinstance(msg, dict) and msg.get('DOI'))
    except Exception:
        return False


def fix_dois(dois: List[str], refs_map: Dict[str, str]) -> List[Tuple[str, str]]:
    """Return list of (old_doi, corrected_doi)"""
    fixes: List[Tuple[str, str]] = []
    for d in dois:
        # quick accept if resolves
        if crossref_resolves(d):
            continue
        # exact title by same key
        title = refs_map.get(d)
        if not title:
            # Fallback: infer title tokens from DOI line context (e.g., RESTORE item present)
            # Try to find any entry in refs_map where DOI shares a visible stub and has a title
            stub = d.split('(')[0] if '(' in d else d.rsplit('-', 1)[0]
            for k, t in refs_map.items():
                if t and stub and k.lower().startswith(stub.lower()[:12]):
                    title = t
                    break
        if not title:
            continue
        # Crossref search by title
        try:
            items = search_crossref_biblio(title, rows=5)
        except Exception:
            items = []
        best = None
        if items:
            best = choose_best_crossref(items, title)
        if best and best.get('DOI'):
            corr = str(best['DOI'])
            if crossref_resolves(corr):
                fixes.append((d, corr))
    return fixes


def main() -> int:
    refs_file = pathlib.Path(r"C:\Users\Thomas ROBINEAU\Downloads\references_consolide_dedup_funky (1).md")
    refs_map = parse_refs_md(refs_file)

    date = '2025-09-14'
    todo_path = ROOT / f'artifacts/imports/dois_to_seed_{date}.txt'
    if not todo_path.exists():
        print(f'no_file {todo_path}')
        return 0
    todos = [l.strip() for l in todo_path.read_text(encoding='utf-8').splitlines() if l.strip()]
    fixes = fix_dois(todos, refs_map)
    if not fixes:
        print('no_fixes')
        return 0
    fixed_set = set(doi for _, doi in fixes)
    out_fixed = ROOT / f'artifacts/imports/dois_to_seed_{date}_fixed.txt'
    out_fixed.write_text("\n".join(sorted(fixed_set)) + "\n", encoding='utf-8')
    # also log mapping
    map_path = ROOT / f'artifacts/imports/dois_fixed_mapping_{date}.csv'
    map_lines = ["old,corrected"] + [f'"{o}","{n}"' for o, n in fixes]
    map_path.write_text("\n".join(map_lines) + "\n", encoding='utf-8')
    print(str(out_fixed))
    print(str(map_path))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
