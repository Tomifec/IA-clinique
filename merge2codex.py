
"""Merge Kit/All/Merged YAML into Codex schema."""
import yaml, uuid, csv, sys, json
from pathlib import Path

def load_items(paths):
    items=[]
    for p in paths:
        data = yaml.safe_load(Path(p).read_text(encoding='utf-8'))
        if isinstance(data, dict) and 'items' in data:
            data = data['items']
        if isinstance(data, list):
            items.extend(data)
        else:
            items.append(data)
    return items

def normalise(it):
    nid = str(it.get('id') or uuid.uuid4())
    return {'id': nid,
            'title': it.get('title','').strip(),
            'doi': it.get('doi') or it.get('doi_url') or '',
            **{k:v for k,v in it.items() if k not in ['id','title','doi','doi_url']}}
if __name__=='__main__':
    yamls = sys.argv[1:-1]
    out_yaml = Path(sys.argv[-1])
    items = [normalise(x) for x in load_items(yamls)]
    yaml.safe_dump({'items':items}, out_yaml.open('w',encoding='utf-8'), sort_keys=False, allow_unicode=True)
    with open(out_yaml.with_suffix('.csv'),'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,['id','title','doi'])
        w.writeheader()
        for it in items:
            w.writerow({'id':it['id'],'title':it['title'],'doi':it['doi']})
