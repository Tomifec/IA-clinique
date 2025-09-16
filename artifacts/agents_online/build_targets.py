import re, yaml, pathlib
root = pathlib.Path('.')
evdir = root/'evidence'
FM_RX = re.compile(r'^---\n(.*?)\n---\n', re.S)
paths = []
for md in evdir.rglob('*.md'):
    try:
        t = md.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        continue
    m = FM_RX.match(t)
    if not m:
        continue
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except Exception:
        fm = {}
    du = fm.get('doi_url')
    if not isinstance(du, str) or not du.strip():
        paths.append(str(md))
list_path = root/'artifacts'/'agents_online'/'curation_targets_missing_doi.txt'
list_path.write_text('\n'.join(paths)+('\n' if paths else ''), encoding='utf-8')
print(str(list_path))
print('targets='+str(len(paths)))
