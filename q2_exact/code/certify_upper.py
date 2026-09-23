"""Rebuild the incumbent's resource orders using rational times and rigorous
upper enclosures of q^(3/2). No floating tolerance is used for deadlines,
capacity, SOC budget, resource overlap or L*=0. Geometry input decimals are
fixed model coefficients, not assertions of DEM physical measurement accuracy.
"""
from pathlib import Path
from fractions import Fraction as F
from collections import Counter,defaultdict
import math,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
R=lambda x:F(str(x))

def ceil_grid(x,scale):return F(-((-x.numerator*scale)//x.denominator),scale)
def energy_upper(t,l,q):
 r=F(q,t['max_payload_kg']);scale=10**24
 k=math.isqrt(r.numerator*scale*scale//r.denominator)
 hi=F(k,scale)
 if hi*hi<r:hi=F(k+1,scale)
 assert hi*hi>=r and (hi-F(1,scale))**2<=r if r>0 else hi==0
 lower_range=R(t['empty_range_m'])-(R(t['empty_range_m'])-R(t['full_range_m']))*r*hi
 assert lower_range>0
 return R(t['battery_kwh'])*R(l['distance_m'])/lower_range+(R(t['empty_mass_kg'])+q)*F(981,100)*R(l['up_m'])/(R(t['up_efficiency'])*3600000)

def run():
 types={t['id']:t for t in json.loads((ROOT/'inputs/types.json').read_text())};boxes={b['id']:b for b in json.loads((ROOT/'inputs/boxes.json').read_text())};legs={(r['from'],r['to']):r for r in json.loads((ROOT/'inputs/legs.json').read_text())};flights=json.loads((ROOT/'inputs/incumbent_flights.json').read_text())
 assert Counter(b for f in flights for b in f['box_ids'])==Counter(boxes.keys())
 values={};checks=0
 for f in flights:
  t=types[f['type']];ids=f['box_ids'];q=sum(boxes[b]['mass_kg'] for b in ids);vol=sum(R(boxes[b]['volume_m3']) for b in ids)
  assert q<=t['max_payload_kg'] and vol<=R(t['max_volume_m3']);assert f['aircraft'] in t['aircraft'];assert f['battery'] in {f'{t["id"]}-BAT{x+1:02d}' for x in range(t['battery_count'])}
  assert set(f['route'][1:-1])=={boxes[b]['site'] for b in ids} and len(set(f['route'][1:-1]))==len(f['route'][1:-1])
  tm=F(t['prep_s']+len(ids)*t['load_per_box_s']);e=F(0);off={}
  for a,b in zip(f['route'][:-1],f['route'][1:]):
   l=legs[a,b];tm+=R(l['up_m'])/R(t['up_mps'])+R(l['distance_m'])/R(t['cruise_mps'])+R(l['down_m'])/R(t['down_mps']);e+=energy_upper(t,l,q)
   if b!='O01':
    drops=[k for k in ids if boxes[k]['site']==b];tm+=t['handover_base_s']+len(drops)*t['handover_per_box_s']
    for k in drops:off[k]=tm
    q-=sum(boxes[k]['mass_kg'] for k in drops)
  assert q==0;assert e<=R(t['battery_kwh'])*(1-F(t['reserve_pct'],100))
  soc=1-e/R(t['battery_kwh']);charge=t['charge_full_s']*(F(65,100)*max(0,F(9,10)-soc)/F(9,10)+F(35,100)*(1-max(F(9,10),soc))/F(1,10))
  charge=ceil_grid(charge,10**9)
  values[f['flight_id']]={'duration':tm,'energy_upper':e,'charge_upper':charge,'off':off,'flight':f};checks+=7
 # Resource paths determined from published allocation, not from earliest resource heuristics.
 pred=defaultdict(list)
 for kind in ('aircraft','battery'):
  pools=defaultdict(list)
  for f in flights:pools[f[kind]].append(f)
  for pool in pools.values():
   pool.sort(key=lambda f:(f['start_s'],f['flight_id']))
   for a,b in zip(pool[:-1],pool[1:]):pred[b['flight_id']].append((a['flight_id'],kind))
 end={};full={};start={};waiting=set(values);slack=[];rows=[];vis=set()
 while waiting:
  ready=sorted(k for k in waiting if all(a in end for a,_ in pred[k]));assert ready,'resource-order cycle'
  for k in ready:
   x=values[k];s=max([F(0)]+[end[a] if kind=='aircraft' else full[a] for a,kind in pred[k]])
   start[k]=s;end[k]=s+x['duration'];full[k]=end[k]+x['charge_upper']
   for b,o in x['off'].items():
    assert b not in vis;vis.add(b);raw=boxes[b];tm=s+o;assert raw['priority']>0 and tm<=R(raw['expected_delivery_s'])
    if raw['hard_deadline_s'] is not None:assert tm<=R(raw['hard_deadline_s']);slack.append(R(raw['hard_deadline_s'])-tm)
    checks+=2
   rows.append({'id':k,'type':x['flight']['type'],'aircraft':x['flight']['aircraft'],'battery':x['flight']['battery'],'start_fraction':str(s),'return_fraction':str(end[k]),'charge_end_fraction':str(full[k]),'energy_upper_kwh':float(x['energy_upper'])});waiting.remove(k)
 maxend=max(end.values());ub=ceil_grid(maxend,10**6)
 out={'valid':True,'checks':checks,'box_count':len(vis),'sorties':len(flights),'weighted_tardiness_exact':0,'primary_objective_optimal':True,'upper_bound_fraction':str(ub),'upper_bound_s':float(ub),'unrounded_makespan_fraction':str(maxend),'min_hard_slack_s':float(min(slack)),'minimum_soc_lower':float(min(1-x['energy_upper']/R(types[x['flight']['type']]['battery_kwh']) for x in values.values())),'new_solution_search':False,'method':'same resource paths replayed with rational durations; sqrt enclosed upward at 1e-24; charge upper rounded to nanosecond; scalar UB rounded UP to microsecond','global_optimal_proved':False}
 (ROOT/'results/rational_upper_bound.json').write_text(json.dumps(out,indent=2));(ROOT/'results/rational_upper_schedule.json').write_text(json.dumps(rows,indent=2));print(json.dumps(out,indent=2));return out
if __name__=='__main__':run()
