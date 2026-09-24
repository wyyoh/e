"""Corrupt copies only; all original result files remain untouched."""
import json,tempfile,shutil
from pathlib import Path
from verify_solution import check,ROOT

def edit(d,file,fn):
 p=d/(file+'.json');x=json.loads(p.read_text());fn(x);p.write_text(json.dumps(x,ensure_ascii=False,indent=2))

def tests(source):
 cases=[
 ('duplicate_box','flights',lambda x:x[0]['box_ids'].__setitem__(0,x[0]['box_ids'][1])),
 ('energy_tamper','flights',lambda x:x[0].__setitem__('energy_kwh',0.)),
 ('early_delivery','deliveries',lambda x:x[0].__setitem__('delivery_s',0.)),
 ('SOC_tamper','flights',lambda x:x[0].__setitem__('return_soc',1.)),
 ('wrong_aircraft_type','flights',lambda x:x[0].__setitem__('aircraft','U08')),
 ('trajectory_teleport','phases',lambda x:x[1].__setitem__('x1',0.)),
 ('trajectory_time_stretch','phases',lambda x:x[1].__setitem__('end_s',x[1]['end_s']+1.)),
 ('wrong_battery_inventory','flights',lambda x:x[0].__setitem__('battery','A-BAT99')),
 ('charge_table_tamper','battery_cycles',lambda x:x[0].__setitem__('full_s',x[0]['return_s'])),
 ]
 results=[]
 for name,file,fn in cases:
  with tempfile.TemporaryDirectory(prefix='q2_negative_') as tmp:
   d=Path(tmp)/'case';shutil.copytree(source,d);edit(d,file,fn)
   try:
    failures=[c for c in check(d) if not c['pass']];caught=bool(failures);msg=failures[:2]
   except (AssertionError,ValueError,KeyError) as e:caught=True;msg=str(e)
   results.append({'case':name,'detected':caught,'example':msg})
 # Reuse the battery while its previous task's charging is still active.
 with tempfile.TemporaryDirectory(prefix='q2_negative_') as tmp:
  d=Path(tmp)/'case';shutil.copytree(source,d)
  fl=json.loads((d/'flights.json').read_text());pair=None
  for a in fl:
   for b in fl:
    if a['flight_id']!=b['flight_id'] and a['type']==b['type'] and a['return_s']<b['start_s']<a['charge_end_s'] and a['battery']!=b['battery']:pair=(a,b);break
   if pair:break
  assert pair
  pair[1]['battery']=pair[0]['battery'];(d/'flights.json').write_text(json.dumps(fl,ensure_ascii=False))
  fs=[c for c in check(d) if not c['pass']];results.append({'case':'unfilled_battery_reuse','detected':bool(fs),'example':fs[:3]})
 assert all(c['detected'] for c in results)
 return results
if __name__=='__main__':
 r=tests(ROOT/'results/main');(ROOT/'results/negative_tests.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print({'tests':len(r),'detected':sum(x['detected'] for x in r)})
