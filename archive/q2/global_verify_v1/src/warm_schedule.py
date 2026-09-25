"""Feasible-start constructor for the exact scheduler; NOT an exact algorithm.
Used only to seek and independently validate primal bounds for the integer
master's newly selected columns. Does not produce any lower-bound certificate.
"""
from pathlib import Path
from collections import defaultdict
import json,heapq,math,random,time
from workload_cg import setup
ROOT=Path(__file__).resolve().parents[1]
def main():
 jobs=json.loads((ROOT/'results/selected_jobs.json').read_text());B,types,classes,demand,*_=setup();raw=defaultdict(list)
 for b in B:
  k=classes.index((b['site'],b['kind'],b['mass_kg'],round(b['volume_m3']*1000)))
  due=min(b['expected_delivery_s'],b['hard_deadline_s'] or math.inf);raw[k].append((due,b['id']))
 for x in raw.values():x.sort()
 def decode(order,detail=False):
  aa=[[(0.,i) for i in range(len(g['aircraft']))] for g in types];bb=[[(0.,i) for i in range(g['battery_count'])] for g in types];deltas=defaultdict(list);plan=[];endall=0.
  for i in order:
   c=jobs[i];g=c['type'];ar,ai=heapq.heappop(aa[g]);br,bi=heapq.heappop(bb[g]);st=max(ar,br);end=st+c['duration_s'];heapq.heappush(aa[g],(end,ai));heapq.heappush(bb[g],(end+c['charge_s'],bi));endall=max(endall,end)
   for k,n in enumerate(c['counts']):
    if n:deltas[k].extend((st+c['delivery_offsets'][str(k)],i) for _ in range(n))
   if detail:plan.append(dict(c,flight_id=f'Q2-PROOF-{i+1:02d}',start_s=st,return_s=end,aircraft=types[g]['aircraft'][ai],battery=f'{types[g]["id"]}-BAT{bi+1:02d}',box_ids=[]))
  late=0.;mapping=defaultdict(list)
  for k,slots in deltas.items():
   slots.sort()
   for (tm,i),(due,bid) in zip(slots,raw[k]):late+=max(0,tm-due);mapping[i].append(bid)
  if detail:
   for p in plan:p['box_ids']=mapping[int(p['flight_id'].split('-')[-1])-1]
   return late,endall,plan
  return late*10000+endall,late,endall
 start=time.monotonic();best=None
 for seed in [420,421,422]:
  rng=random.Random(seed);order=list(range(len(jobs)));rng.shuffle(order);cur=decode(order);temperature=300.
  for k in range(15000):
   p=order.copy();a,b=rng.sample(range(len(p)),2)
   if rng.random()<.5:p[a],p[b]=p[b],p[a]
   else:p.insert(b,p.pop(a))
   val=decode(p)
   if best is None or (val[1],val[2])<(best[0][1],best[0][2]):best=(val,p)
   temperature=300*(1-k/15000)+1
   if val[0]<cur[0] or rng.random()<math.exp(max(-700,(cur[0]-val[0])/temperature)):order,cur=p,val
 late,span,plan=decode(best[1],True);result={'scope':'heuristic warm start only','zero_lateness':late<=1e-6,'lateness_sum_s':late,'makespan_s':span,'elapsed_s':time.monotonic()-start}
 (ROOT/'results/warm_schedule.json').write_text(json.dumps(result,indent=2))
 if late<=1e-6:(ROOT/'results/warm_candidate.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
 print(result)
if __name__=='__main__':main()
