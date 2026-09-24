"""Closing experiment I/O; immutable upstream input with checked digest."""
from pathlib import Path
import base64, csv, hashlib, io, json, zipfile

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent

def save(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def table(path, rows, fields=None):
    rows=list(rows);path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list,tuple)) else v for k,v in r.items()})

def inputs():
    packed=base64.b64decode(''.join(p.read_text().strip() for p in sorted((REPO/'data/encoded').glob('*.b64'))),validate=True)
    with zipfile.ZipFile(io.BytesIO(packed)) as z:
        data=z.read('instance.json')
    want=load(REPO/'manifest.json')['fixed_inputs_sha256']['data/instance.json']
    assert hashlib.sha256(data).hexdigest()==want
    d=json.loads(data)
    d['boxes']={r[0]:dict(zip(d['box_fields'],r)) for r in d['boxes']}
    d['types']={r['id']:r for r in d['types']}
    d['nodes']={r['id']:r for r in d['nodes']}
    d['geo']={(a,b):(dist,h) for a,b,dist,h in d['legs']}
    d['geo'].update({(b,a):v for (a,b),v in list(d['geo'].items())})
    return d
