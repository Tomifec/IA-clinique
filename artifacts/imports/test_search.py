import sys, pathlib, json
sys.path.append(str(pathlib.Path('.').resolve()))
from tools.agents_online.curation_utils import search_crossref_biblio, choose_best_crossref
queries = [
  'Cognitive functional therapy with or without movement sensor biofeedback versus usual care for chronic disabling low back pain (RESTORE).',
  'Noninvasive Treatments for Acute, Subacute, and Chronic Low Back Pain: ACP Clinical Practice Guideline.'
]
for q in queries:
    items = search_crossref_biblio(q, rows=3)
    print('Q:', q[:60])
    print('N:', len(items))
    if items:
        best = choose_best_crossref(items, q)
        print('BEST DOI:', (best or {}).get('DOI'))
