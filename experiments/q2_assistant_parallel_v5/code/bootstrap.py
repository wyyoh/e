"""Immutable compact numeric input. Writes only inside this experiment directory."""
from pathlib import Path
import gzip, json, hashlib, base64, io, zipfile
ROOT=Path(__file__).resolve().parents[1]
RAW_SHA='24da33d683b1db252f286fc8c99058d781bc95f968bae38855a5507c9209ce4a'
GZIP_SHA='8ec2c345ae153cd3d69c65d6273e9645feabbd4b61a79cd114c319e0ebdc12eb'
def main():
 archive=ROOT/'inputs/model.json.gz'
 if archive.exists():
  raw=archive.read_bytes()
  if hashlib.sha256(raw).hexdigest()!=GZIP_SHA:raise ValueError('compressed input identity changed')
  decoded=gzip.decompress(raw)
  if hashlib.sha256(decoded).hexdigest()!=RAW_SHA:raise ValueError('numeric model identity changed')
 else:
  # Git deployment reuses the immutable data already on the base branch IN MEMORY.
  # Nothing is written to any ancestor/Codex directory.
  parent=next((p for p in ROOT.parents if (p/'data/encoded/00.b64').exists()),None)
  if parent is None:raise FileNotFoundError('model.json.gz or base repository data/encoded required')
  packed=base64.b64decode(''.join(p.read_text().strip() for p in sorted((parent/'data/encoded').glob('*.b64'))),validate=True)
  with zipfile.ZipFile(io.BytesIO(packed)) as z:original=z.read('instance.json')
  if hashlib.sha256(original).hexdigest()!='ce9ed762a3e5a1b9bffb3614e82aa149002de2ec5ebe45ab88e2c0509a7628c6':raise ValueError('base input identity changed')
  src=json.loads(original)
  decoded=json.dumps({'box_fields':src['box_fields'],'boxes':src['boxes'],'types':src['types'],'nodes':src['nodes'],'geometry':src['legs']}).encode()
 d=json.loads(decoded);nodes={n['id']:n for n in d['nodes']};legs=[]
 for a,b,dist,h in d['geometry']:
  for u,v in ((a,b),(b,a)):
   H=h+50;legs.append(dict(zip(('from','to','distance_m','max_dem_m','cruise_z','from_work_z','to_work_z','up_m','down_m'),(u,v,dist,h,H,nodes[u]['work_z'],nodes[v]['work_z'],H-nodes[u]['work_z'],H-nodes[v]['work_z']))))
 values={'boxes':[dict(zip(d['box_fields'],r)) for r in d['boxes']],'types':d['types'],'nodes':d['nodes'],'legs':legs}
 for folder in [ROOT/'inputs',ROOT/'proof/data']:
  folder.mkdir(parents=True,exist_ok=True)
  for name,rows in values.items():
   path=folder/(name+'.json')
   if path.exists():
    old=json.loads(path.read_text());key=(lambda r:(r['from'],r['to'])) if name=='legs' else (lambda r:r['id'])
    old={key(r):r for r in old}
    if len(old)!=len(rows):raise ValueError('existing data row count differs: '+str(path))
    for r in rows:
     if any(old[key(r)].get(k)!=v for k,v in r.items()):raise ValueError('existing data differs: '+str(path))
   else:path.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
 for folder in [ROOT/'results',ROOT/'logs',ROOT/'proof/results']:folder.mkdir(parents=True,exist_ok=True)
 return {'boxes':len(values['boxes']),'nodes':len(nodes),'directed_legs':len(legs),'numeric_input_origin':'pinned V4 compact snapshot or identical pinned repository instance','dem_reextracted':False}
if __name__=='__main__':print(json.dumps(main()))
