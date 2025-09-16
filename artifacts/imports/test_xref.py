import sys, pathlib
sys.path.append(str(pathlib.Path('.').resolve()))
from tools.agents_online.curation_utils import xref_by_doi
from pathlib import Path
p = Path('artifacts/imports/dois_to_seed_2025-09-14.txt')
for doi in [l.strip() for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]:
    ok = True
    try:
        msg = xref_by_doi(doi)
        ok = bool(msg.get('DOI'))
    except Exception as e:
        ok = False
    print(doi, '->', 'OK' if ok else 'FAIL')
