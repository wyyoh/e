"""Independent Q2 verifier: never trusts solver energy, delivery or phases.
No import of core.py. Uses input records, rebuilds power*time in Wh, charging
piecewise intervals and all expected route-bound phase endpoints.
"""
import json,math,csv,copy
from pathlib import Path
from collections import Counter,defaultdict
ROOT=Path(__file__).resolve().parents[1]
def check(out):
 load=lambda p:json.loads(p.read_text())
 types={x['id']:x for x in load(ROOT/'inputs/types.json')};boxes={x['id']:x for x in load(ROOT/'inputs/boxes.json')};nodes={x['id']:x for x in load(ROOT/'inputs/nodes.json')};geo={(x['from'],x['to']):x for x in load(ROOT/'inputs/legs.json')}
 f=load(out/'flights.json');ds=load(out/'deliveries.json');ls=load(out/'legs.json');ph=load(out/'phases.json');bc=load(out/'battery_cycles.json')
 checks=[]
 def test(name,ok,detail=''):
  checks.append({'check':name,'pass':bool(ok),'detail':str(detail)})
 def eq(name,x,y,tol=1e-7):test(name,math.isfinite(x) and abs(x-y)<=tol,f'{x} vs {y}')
 test('all_original_boxes_exactly_once',Counter(b for x in f for b in x['box_ids'])==Counter(boxes.keys()))
 test('delivery_table_exactly_once',Counter(x['id'] for x in ds)==Counter(boxes.keys()))
 test('flights_unique',len({x['flight_id'] for x in f})==len(f))
 test('leg_count_binding',len(ls)==sum(len(x['route'])-1 for x in f))
 test('phase_count_binding',len(ph)==3*len(ls))
 test('battery_table_binding',Counter(x['flight_id'] for x in bc)==Counter(x['flight_id'] for x in f))
 bcycles={x['flight_id']:x for x in bc}
 dmap={x['id']:x for x in ds};perac=defaultdict(list);perba=defaultdict(list);expected_del={};energy_total=0.;minslack=float('inf');minimumsoc=1.
 for x in f:
  fid=x['flight_id'];t=types.get(x['type']);test(fid+'.type',t is not None)
  if t is None:continue
  test(fid+'.aircraft',x['aircraft'] in t['aircraft']);test(fid+'.battery',x['battery'] in {f'{t["id"]}-BAT{j+1:02d}' for j in range(t['battery_count'])})
  ids=x['box_ids'];test(fid+'.valid_ids',all(i in boxes for i in ids));q=sum(boxes[i]['mass_kg'] for i in ids);vol=sum(round(boxes[i]['volume_m3']*1000) for i in ids)/1000
  eq(fid+'.payload',x['payload_kg'],q);eq(fid+'.volume',x['volume_m3'],vol);test(fid+'.capacity',q<=t['max_payload_kg'] and vol<=t['max_volume_m3']+1e-12)
  route=x['route'];test(fid+'.route_ends',route[0]==route[-1]=='O01');test(fid+'.route_deliveries',set(route[1:-1])=={boxes[i]['site'] for i in ids} and len(route[1:-1])==len(set(route[1:-1])))
  prep=t['prep_s']+len(ids)*t['load_per_box_s'];now=x['start_s']+prep;eq(fid+'.takeoff',now,x['takeoff_s']);eq(fid+'.prep',prep,x['prep_s']);test(fid+'.nonnegative_start',x['start_s']>=-1e-7)
  Ewh=0.;ff=0.;legindex=0
  for a,b in zip(route[:-1],route[1:]):
   legindex+=1;g=geo[a,b]
   # Direct reconstruction, independently of saved aggregate geometry fields.
   H=g['max_dem_m']+50;up=H-nodes[a]['work_z'];dn=H-nodes[b]['work_z']
   distance=math.hypot(nodes[b]['x']-nodes[a]['x'],nodes[b]['y']-nodes[a]['y'])
   eq(fid+f'.leg{legindex}.distance',distance,g['distance_m']);test(fid+f'.leg{legindex}.clearance',up>=0 and dn>=0)
   L=t['empty_range_m']-(t['empty_range_m']-t['full_range_m'])*(q/t['max_payload_kg'])**(3/2)
   powerW=t['battery_kwh']*3600000/(L/t['cruise_mps']);cr=distance/t['cruise_mps'];U=up/t['up_mps'];D=dn/t['down_mps']
   ewh=powerW*cr/3600+((t['empty_mass_kg']+q)*9.81*t['up_mps']/t['up_efficiency'])*U/3600
   candidates=[l for l in ls if l['flight_id']==fid and l['leg_index']==legindex];test(fid+'.leg_unique',len(candidates)==1)
   if candidates:
    l=candidates[0];eq(fid+'.leg.payload',q,l['payload_kg']);eq(fid+'.leg.energy_Wh',ewh,1000*l['energy_kwh'],1e-6);eq(fid+'.leg.range',L,l['equivalent_range_m']);eq(fid+'.leg.start',now,l['start_s']);eq(fid+'.leg.arrival',now+U+cr+D,l['arrival_s'])
   A=nodes[a];B=nodes[b]
   specs=[('爬升',U,[A['x'],A['y'],A['work_z']],[A['x'],A['y'],H]),('巡航',cr,[A['x'],A['y'],H],[B['x'],B['y'],H]),('下降',D,[B['x'],B['y'],H],[B['x'],B['y'],B['work_z']])]
   for stage,dur,p0,p1 in specs:
    xs=[p for p in ph if p['flight_id']==fid and p['leg_index']==legindex and p['stage']==stage];test(fid+'.phase_unique',len(xs)==1)
    if xs:
     p=xs[0];eq(fid+'.phase.start',p['start_s'],now);eq(fid+'.phase.end',p['end_s'],now+dur)
     for key,value in zip(('x0','y0','z0','x1','y1','z1'),p0+p1):eq(fid+'.binding.'+key,p[key],value)
     eq(fid+'.phase.payload',p['payload_kg'],q)
    now+=dur
   Ewh+=ewh;ff+=U+cr+D
   if b!='O01':
    unload=[i for i in ids if boxes[i]['site']==b];now+=t['handover_base_s']+len(unload)*t['handover_per_box_s']
    for i in unload:
     expected_del[i]=now;dm=dmap[i];eq(i+'.delivery_time',dm['delivery_s'],now);test(i+'.flight',dm['flight_id']==fid)
     raw=boxes[i];hard=[]
     for field in ('site','kind','mass_kg','volume_m3','first_batch','first_deadline_s','expected_delivery_s','priority','hard_deadline_s'):test(i+'.source.'+field,dm[field]==raw[field])
     if raw['kind']=='医疗物资':hard.append(raw['expected_delivery_s'])
     if raw['first_batch']=='是':hard.append(raw['first_deadline_s'])
     if hard:test(i+'.hard_deadline',now<=min(hard)+1e-7);minslack=min(minslack,min(hard)-now)
     late=max(0,now-raw['expected_delivery_s']);eq(i+'.tardiness',dm['tardiness_s'],late);eq(i+'.weighted',dm['weighted_tardiness_s'],late*raw['priority'])
    q-=sum(boxes[i]['mass_kg'] for i in unload)
  eq(fid+'.return',x['return_s'],now);eq(fid+'.work',x['work_s'],now-x['start_s']);eq(fid+'.flight_time',x['flight_s'],ff);eq(fid+'.energy',1000*x['energy_kwh'],Ewh,1e-6);test(fid+'.final_empty',q==0)
  soc=1-Ewh/(1000*t['battery_kwh']);eq(fid+'.soc',x['return_soc'],soc);test(fid+'.energy_budget',soc>=t['reserve_pct']/100-1e-9)
  # Integrate charge SOC increments separately in two constant-rate regions.
  needed90=max(0,0.9-soc);needed100=1-max(0.9,soc)
  charge=needed90/(.9/(.65*t['charge_full_s']))+needed100/(.1/(.35*t['charge_full_s']))
  eq(fid+'.charge',x['charge_duration_s'],charge);eq(fid+'.charge_end',x['charge_end_s'],now+charge)
  cyc=bcycles.get(fid)
  if cyc is not None:
   test(fid+'.battery_cycle_id',cyc['battery']==x['battery'] and cyc['aircraft']==x['aircraft'])
   for key,value in [('task_start_s',x['start_s']),('takeoff_s',x['takeoff_s']),('return_s',now),('return_soc',soc),('charge_start_s',now),('charge_duration_s',charge),('full_s',now+charge)]:eq(fid+'.cycle.'+key,cyc[key],value)
  perac[x['aircraft']].append((x['start_s'],now,fid));perba[x['battery']].append((x['start_s'],now+charge,fid))
  energy_total+=Ewh/1000;minimumsoc=min(minimumsoc,soc)
 for category,resources in (('aircraft',perac),('battery',perba)):
  for rid,iv in resources.items():
   iv.sort()
   for l,r in zip(iv[:-1],iv[1:]):test(category+'.'+rid+'.nonoverlap',l[1]<=r[0]+1e-7,(l,r))
 metrics=load(out/'metrics.json');eq('summary.energy',metrics['energy_kwh'],energy_total);eq('summary.makespan',metrics['makespan_s'],max(x['return_s'] for x in f));eq('summary.delivery',metrics['last_delivery_s'],max(expected_del.values()));eq('summary.minsoc',metrics['min_return_soc'],minimumsoc);eq('summary.hard_slack',metrics['min_hard_slack_s'],minslack)
 wt=sum(boxes[i]['priority']*max(0,tm-boxes[i]['expected_delivery_s']) for i,tm in expected_del.items());eq('summary.tardiness',metrics['weighted_tardiness_s'],wt)
 return checks

def run(out):
 cs=check(out);v=out/'validation';v.mkdir(parents=True,exist_ok=True)
 with (v/'checks.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['check','pass','detail']);w.writeheader();w.writerows(cs)
 result={'checks':len(cs),'failed':sum(not x['pass'] for x in cs),'failures':[x for x in cs if not x['pass']]}
 (v/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));return result
if __name__=='__main__':
 import sys
 out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'results/main';res=run(out);print(res);sys.exit(bool(res['failed']))
