"""Exact-duration Q2 physical evaluator and separate aircraft/battery scheduler.
This module has no communication model, no additional time buffers, and no
integer rounding of physical time. Ordinary due dates only enter objectives.
"""
from __future__ import annotations
import json,math,itertools,heapq
from pathlib import Path
from functools import lru_cache
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
T={x['id']:x for x in json.loads((ROOT/'inputs/types.json').read_text())}
B=json.loads((ROOT/'inputs/boxes.json').read_text());BI={b['id']:i for i,b in enumerate(B)}
N={x['id']:x for x in json.loads((ROOT/'inputs/nodes.json').read_text())}
G={(x['from'],x['to']):x for x in json.loads((ROOT/'inputs/legs.json').read_text())}
TOL=1e-8

def charge_seconds(s,t):
 if not 0<=s<=1+TOL: raise ValueError('SOC outside [0,1]')
 return t['charge_full_s']*(.65*max(0,.9-s)/.9+.35*(1-max(.9,s))/.1)

def leg_values(g,a,b,q):
 t=T[g];v=G[a,b]
 if not 0<=q<=t['max_payload_kg']+TOL:raise ValueError('payload')
 L=t['empty_range_m']-(t['empty_range_m']-t['full_range_m'])*(q/t['max_payload_kg'])**1.5
 up=v['up_m']/t['up_mps'];cr=v['distance_m']/t['cruise_mps'];dn=v['down_m']/t['down_mps']
 hor=t['battery_kwh']*v['distance_m']/L
 climb=(t['empty_mass_kg']+q)*9.81*v['up_m']/(t['up_efficiency']*3600000)
 return up,cr,dn,L,hor,climb

def task(g,ids,route=None):
 ids=tuple(sorted(ids))
 if route is None: route=tuple(sorted({B[b]['site'] for b in ids}))
 return (g,ids,tuple(route))

@lru_cache(maxsize=400000)
def evaluate(k):
 g,ids,route=k
 if not ids or len(set(ids))!=len(ids):return None
 t=T[g];q=sum(B[i]['mass_kg'] for i in ids);litres=sum(round(B[i]['volume_m3']*1000) for i in ids)
 if q>t['max_payload_kg'] or litres>round(t['max_volume_m3']*1000):return None
 if set(route)!={B[i]['site'] for i in ids} or len(set(route))!=len(route):return None
 now=t['prep_s']+len(ids)*t['load_per_box_s'];prep=now
 energy=0.;flight=0.;prev='O01';delivery=[];leglist=[];stops=[]
 for dest in (*route,'O01'):
  up,cr,dn,L,hor,climb=leg_values(g,prev,dest,q)
  dt=up+cr+dn;leglist.append({'from':prev,'to':dest,'payload_kg':q,'start_offset_s':now,'arrival_offset_s':now+dt,'up_s':up,'cruise_s':cr,'down_s':dn,'equivalent_range_m':L,'horizontal_kwh':hor,'climb_kwh':climb,'energy_kwh':hor+climb})
  now+=dt;energy+=hor+climb;flight+=dt
  if dest!='O01':
   drops=[i for i in ids if B[i]['site']==dest];arrival=now
   now+=t['handover_base_s']+len(drops)*t['handover_per_box_s']
   delivery.extend((i,now) for i in drops);stops.append({'site':dest,'ids':drops,'arrival_offset_s':arrival,'delivery_offset_s':now})
   q-=sum(B[i]['mass_kg'] for i in drops)
  prev=dest
 if energy>t['battery_kwh']*(1-t['reserve_pct']/100)+TOL:return None
 assert q==0
 soc=1-energy/t['battery_kwh'];chg=charge_seconds(soc,t)
 latest=min((B[i]['hard_deadline_s']-v for i,v in delivery if B[i]['hard_deadline_s'] is not None),default=float('inf'))
 return {'g':g,'ids':ids,'route':route,'duration':now,'prep':prep,'energy':energy,'soc':soc,'charge':chg,'delivery':tuple(delivery),'latest':latest,'flight':flight,'mass':sum(B[i]['mass_kg'] for i in ids),'volume':litres/1000,'legs':leglist,'stops':stops}

@lru_cache(maxsize=80000)
def variants(g,ids):
 sites=tuple(sorted({B[i]['site'] for i in ids}))
 if len(sites)<=5:
  orders=itertools.permutations(sites)
 else:
  # Heuristic route candidates only; not a physical limit on stops.
  orders=[sites,tuple(reversed(sites))]
 out=[]
 for r in orders:
  k=task(g,ids,r);e=evaluate(k)
  if e is not None:out.append(k)
 return tuple(out)

def schedule(plan,details=False,battery_from='prepare'):
 # plan is dispatch priority order; independent types have separate resource pools.
 ac={g:[(0.,x) for x in t['aircraft']] for g,t in T.items()}
 ba={g:[(0.,f'{g}-BAT{j+1:02d}') for j in range(t['battery_count'])] for g,t in T.items()}
 result=[]; hard_delay=0.;hard_count=0;weighted=0.;soft_count=0;maxlate=0.;ends=[];energies=[];delivery_sum=0.;lastdel=0.;minslack=float('inf');minsoc=1.;work=0.;flight=0.
 for k in plan:
  e=evaluate(k)
  if e is None:return None
  g=k[0];at,aid=heapq.heappop(ac[g]);bt,bid=heapq.heappop(ba[g])
  st=max(at,bt if battery_from=='prepare' else bt-e['prep']);end=st+e['duration'];charge_end=end+e['charge']
  heapq.heappush(ac[g],(end,aid));heapq.heappush(ba[g],(charge_end,bid))
  for i,off in e['delivery']:
   tm=st+off;delivery_sum+=tm;lastdel=max(lastdel,tm);b=B[i]
   if b['hard_deadline_s'] is not None:
    slack=b['hard_deadline_s']-tm;minslack=min(minslack,slack)
    if slack<-1e-7:hard_delay-=slack;hard_count+=1
   late=max(0,tm-b['expected_delivery_s']);weighted+=b['priority']*late
   if late>1e-7:soft_count+=1
   maxlate=max(maxlate,late)
  ends.append(end);energies.append(e['energy']);minsoc=min(minsoc,e['soc']);work+=e['duration'];flight+=e['flight']
  if details:result.append({'task':k,'aircraft':aid,'battery':bid,'start_s':st,'takeoff_s':st+e['prep'],'return_s':end,'charge_start_s':end,'charge_end_s':charge_end})
 metrics={'hard_late_boxes':hard_count,'hard_lateness_s':hard_delay,'weighted_tardiness_s':weighted,'late_boxes':soft_count,'max_tardiness_s':maxlate,'makespan_s':max(ends,default=0),'energy_kwh':sum(energies),'sorties':len(plan),'last_delivery_s':lastdel,'sum_delivery_s':delivery_sum,'min_hard_slack_s':minslack,'min_return_soc':minsoc,'work_s':work,'pure_flight_s':flight,'type_counts':dict(Counter(k[0] for k in plan)),'multi_stop_sorties':sum(len(k[2])>1 for k in plan)}
 return (metrics,result) if details else metrics

def quality(m,mode='time'):
 # Only the search surrogate. Final accepted solution selection is lexicographic.
 if mode=='time':ew,nw=.12,.12
 elif mode=='balanced':ew,nw=30.,10.
 else:ew,nw=150.,10.
 return 1e7*m['hard_late_boxes']+10000*m['hard_lateness_s']+100*m['weighted_tardiness_s']+m['makespan_s']+ew*m['energy_kwh']+nw*m['sorties']+.0005*m['sum_delivery_s']

def as_decisions(plan):
 return [{'type':g,'boxes':[B[i]['id'] for i in ids],'route':list(r)} for g,ids,r in plan]

def from_decisions(rows):return [task(x['type'],[BI[i] for i in x['boxes']],x['route']) for x in rows]
