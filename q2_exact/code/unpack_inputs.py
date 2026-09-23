"""Expand the versioned, compact numeric snapshot without network access.
This is a normalized input snapshot; DEM extraction is upstream, not rerun here.
"""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def run():
 src=ROOT/'snapshot.json';x=json.loads(src.read_text());out=ROOT/'inputs';out.mkdir(parents=True,exist_ok=True)
 tables={k:[dict(zip(x[k+'_fields'],r)) for r in x[k]] for k in ('types','boxes','nodes')}
 ns=tables['nodes'];bs=tables['boxes'];legs=[]
 for i,j,d,z in x['legs']:
  for a,b in ((i,j),(j,i)):
   H=z+50;legs.append({'from':ns[a]['id'],'to':ns[b]['id'],'distance_m':d,'max_dem_m':z,'up_m':H-ns[a]['work_z'],'down_m':H-ns[b]['work_z']})
 flights=[]
 for row in x['flights']:
  f=dict(zip(x['flights_fields'],row));f['route']=[ns[i]['id'] for i in f.pop('route_node_indices')];f['box_ids']=[bs[i]['id'] for i in f.pop('box_indices')];flights.append(f)
 tables.update(legs=legs,incumbent_flights=flights,incumbent_metrics=x['metrics'])
 for k,data in tables.items():(out/(k+'.json')).write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
 meta={'snapshot_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'upstream_archive_sha256':x['upstream_archive_sha256'],'scope':'normalized raw fields, verified geometry and incumbent resource orders; no internet fetch or new DEM extraction','tables':{k:len(v) if isinstance(v,list) else None for k,v in tables.items()}}
 (out/'snapshot_manifest.json').write_text(json.dumps(meta,indent=2));return meta
if __name__=='__main__':print(run())
