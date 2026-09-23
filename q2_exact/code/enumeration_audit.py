"""Exact count of capacity-only batch multisets; audit unsafe metric shortcuts.
Counts are NOT energy-feasible route counts and no finite depth is called complete.
"""
from pathlib import Path
from collections import Counter
import json,math,time,itertools
ROOT=Path(__file__).resolve().parents[1]

def run():
 B=json.loads((ROOT/'inputs/boxes.json').read_text());T=json.loads((ROOT/'inputs/types.json').read_text());G={(r['from'],r['to']):r for r in json.loads((ROOT/'inputs/legs.json').read_text())};N=['O01']+sorted(set(b['site'] for b in B))
 # Only collapse identical attributes. All positive tardiness weights retained.
 eq=Counter((b['site'],b['mass_kg'],round(b['volume_m3']*1000),b['hard_deadline_s'],b['expected_delivery_s'],b['priority'],b['first_batch']) for b in B)
 capcounts={};counts_time={}
 for t in T:
  start=time.perf_counter();Q=t['max_payload_kg'];V=round(1000*t['max_volume_m3']);dp={(0,0):1}
  for key,num in eq.items():
   w,v=key[1:3];nxt=Counter()
   for (q,vol),cnt in dp.items():
    for c in range(min(num,(Q-q)//w,(V-vol)//v)+1):nxt[q+c*w,vol+c*v]+=cnt
   dp=nxt
  capcounts[t['id']]=sum(dp.values())-1;counts_time[t['id']]=time.perf_counter()-start
 def tau(t,i,j):
  a=G[i,j];return a['up_m']/t['up_mps']+a['distance_m']/t['cruise_mps']+a['down_m']/t['down_mps']
 violations=[]
 for t in T:
  for i,j,k in itertools.permutations(N,3):
   if j=='O01':continue
   direct=tau(t,i,k);via=tau(t,i,j)+tau(t,j,k)
   if direct>via+1e-7:violations.append({'type':t['id'],'from':i,'via':j,'to':k,'direct_flight_s':direct,'via_flight_s':via,'saving_s':direct-via,'saving_after_base_service_s':direct-via-t['handover_base_s']})
 violations.sort(key=lambda x:x['saving_s'],reverse=True)
 out={'equivalence_classes':len(eq),'capacity_only_multisets':capcounts,'count_seconds':counts_time,'metric_violations':len(violations),'largest_violations':violations[:12],'scope':'capacity only, before energy/time/order checks; equivalent copies counted once','elementarity_not_proved':True}
 (ROOT/'results/enumeration_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__':run()
