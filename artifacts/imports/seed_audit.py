import json, re, pathlib
ROOT = pathlib.Path('.')
DATE = '2025-09-13'

# compute evidence id from DOI and topic (same as seed_by_doi.slug logic)
def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")

def expected_id(doi: str) -> str:
    topic = 'import_refs_' + DATE.replace('-', '_')
    return f"evidence_{slug(topic)}_{slug(doi)[:40]}"

inp = ROOT / f'artifacts/imports/dois_to_seed_{DATE}.txt'
if not inp.exists():
    print(f'no dois_to_seed file: {inp}')
    raise SystemExit(0)

dois = [l.strip() for l in inp.read_text(encoding='utf-8').splitlines() if l.strip()]
created = []
failed = []
for d in dois:
    eid = expected_id(d)
    md = ROOT / 'evidence' / f'{eid}.md'
    if md.exists():
        created.append({'doi': d, 'evidence_id': eid, 'path': str(md)})
    else:
        failed.append({'doi': d, 'expected_id': eid})

report = {
    'date': DATE,
    'topic': 'import_refs_' + DATE.replace('-', '_'),
    'total': len(dois),
    'created_count': len(created),
    'failed_count': len(failed),
    'created': created,
    'failed': failed,
}
(out := ROOT / f'artifacts/imports/seed_report_{DATE}.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(out)

# Heuristic corrections for failed DOIs
corrected = []
for f in failed:
    d = f['doi']
    d2 = d
    d2 = d2.rstrip('-.')  # drop trailing dashes/dots
    if d2.endswith('Eur'):
        d2 = d2[:-3]
    # drop common junk suffixes after a space (should not occur here)
    d2 = d2.split()[0]
    # Accept only if materially changed and has at least one slash and total length > 8
    if d2 != d and '/' in d2 and len(d2) >= 10:
        corrected.append(d2)

if corrected:
    out_corr = ROOT / f'artifacts/imports/dois_to_seed_corrected_{DATE}.txt'
    out_corr.write_text('\n'.join(sorted(set(corrected))) + '\n', encoding='utf-8')
    print(out_corr)
else:
    print('NO_CORRECTIONS')
