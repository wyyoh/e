"""Expand the compact immutable numeric instance; do not change raw parameters.
The DEM-derived graph is inherited from the previously validated input snapshot.
This command does not repeat DEM extraction; original source hashes are retained.
"""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=ROOT/'data/instance.json';d=json.loads(p.read_text());nodes={n['id']:n for n in d['nodes']}
 boxes=[dict(zip(d['box_fields'],r)) for r in d['boxes']];legs=[]
 for a,b,dist,h in d['legs']:
  for u,v in ((a,b),(b,a)):
   H=h+50;legs.append({'from':u,'to':v,'distance_m':dist,'max_dem_m':h,'cruise_z':H,'from_work_z':nodes[u]['work_z'],'to_work_z':nodes[v]['work_z'],'up_m':H-nodes[u]['work_z'],'down_m':H-nodes[v]['work_z']})
 for name,obj in [('boxes',boxes),('types',d['types']),('nodes',d['nodes']),('legs',legs)]:
  (ROOT/'data'/f'{name}.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2))
 base=json.loads((ROOT/'data/baseline.json').read_text());(ROOT/'data/incumbent_flights.json').write_text(json.dumps(base['flights'],ensure_ascii=False,indent=2))
 (ROOT/'data/incumbent_metrics.json').write_text(json.dumps({'makespan_s':base['claimed_makespan_s']}))
 print(json.dumps({'boxes':len(boxes),'nodes':len(nodes),'directed_legs':len(legs),'instance_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))
if __name__=='__main__':main()
