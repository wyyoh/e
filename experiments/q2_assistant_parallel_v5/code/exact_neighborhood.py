"""Exact capacity/route recombination INSIDE a selected neighborhood.
MILP assigns chosen trips to aircraft workload bins, then full battery schedules
are evaluated. The pool dual is NOT a global bound; only validated schedules
may improve the incumbent. Original physics is imported unchanged from core.
"""
from core import *
from alns import finite_key,feasible,canonicalize
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import coo_matrix
import random,time,argparse
ROOT=Path(__file__).resolve().parents[1]

def optimize_order(plan,rng,trials=5000):
 out=[]
 for g in T:
  ps=[p for p in plan if p[0]==g];n=len(ps)
  def key(order):
   m=schedule(order);return (m['hard_late_boxes'],m['hard_lateness_s'],m['weighted_tardiness_s'],m['makespan_s'],m['sum_delivery_s'])
  best=list(ps);kb=key(best)
  starts=[list(ps),sorted(ps,key=lambda k:evaluate(k)['latest']),sorted(ps,key=lambda k:min(B[i]['expected_delivery_s']-v for i,v in evaluate(k)['delivery']))]
  for p in starts:
   k=key(p)
   if k<kb:best,kb=p,k
  if n<=7:
   for perm in itertools.permutations(ps):
    k=key(perm)
    if k<kb:best,kb=list(perm),k
  else:
   cur=list(best);kc=kb
   for it in range(trials):
    pp=list(cur)
    a,b=rng.sample(range(n),2)
    if rng.random()<.6:pp[a],pp[b]=pp[b],pp[a]
    else:pp.insert(b,pp.pop(a))
    k=key(pp)
    if k<kc or rng.random()<.004:cur,kc=pp,k
    if k<kb:best,kb=pp,k
    if it%500==499:cur,kc=list(best),kb
  out.extend(best)
 return out

def run(case,plan,remove,seconds=30,seed=1):
 rng=random.Random(seed);st=time.monotonic();removed=[plan[i] for i in remove];ids=sorted(i for k in removed for i in k[1]);keep=[k for i,k in enumerate(plan) if i not in remove]
 if len(ids)>15:raise ValueError('neighborhood too large')
 cols=[];seen=set()
 def add(k):
  if k in seen:return
  e=evaluate(k)
  if e is not None and e['latest']>=-1e-7 and all(v<=B[i]['expected_delivery_s']+1e-7 for i,v in e['delivery']):
   seen.add(k);cols.append(k)
 for k in keep+removed:add(k)
 # Every actual box subset, every site permutation, every type in this neighborhood.
 for mask in range(1,1<<len(ids)):
  bs=tuple(ids[j] for j in range(len(ids)) if mask>>j&1);w=sum(B[i]['mass_kg'] for i in bs);vol=sum(round(B[i]['volume_m3']*1000) for i in bs)
  if w>80 or vol>250:continue
  sites=sorted({B[i]['site'] for i in bs})
  for g,t in T.items():
   if w>t['max_payload_kg'] or vol>round(t['max_volume_m3']*1000):continue
   for route in itertools.permutations(sites):add(task(g,bs,route))
 ac=[(g,a) for g,t in T.items() for a in t['aircraft']];aj={a:k for k,(g,a) in enumerate(ac)}
 variables=[(k,a) for k,col in enumerate(cols) for g,a in ac if g==col[0]]
 nn=len(variables);rows=[];cc=[];val=[]
 # Coverage of 80 individual boxes prevents altering or duplicating original IDs.
 for j,(k,a) in enumerate(variables):
  for b in cols[k][1]:rows.append(b);cc.append(j);val.append(1.)
  rows.append(80+aj[a]);cc.append(j);val.append(evaluate(cols[k])['duration'])
 for a in range(8):rows.append(80+a);cc.append(nn);val.append(-1.)
 # Symmetry breaking: nonincreasing workloads on interchangeable same-type aircraft.
 si=88
 for g,t in T.items():
  for aa,bb in zip(t['aircraft'],t['aircraft'][1:]):
   for j,(k,a) in enumerate(variables):
    if a==aa or a==bb:rows.append(si);cc.append(j);val.append(evaluate(cols[k])['duration']*(-1 if a==aa else 1))
   si+=1
 mat=coo_matrix((val,(rows,cc)),shape=(si,nn+1)).tocsc()
 lower=np.r_[np.ones(80),np.full(si-80,-np.inf)];upper=np.r_[np.ones(80),np.zeros(si-80)]
 objective=np.r_[[.0005*evaluate(cols[k])['energy']+rng.random()*.0001 for k,a in variables],1.]
 ub=schedule(plan)['makespan_s']
 result=milp(objective,integrality=np.r_[np.ones(nn),0],bounds=Bounds(np.zeros(nn+1),np.r_[np.ones(nn),ub]),constraints=LinearConstraint(mat,lower,upper),options={'time_limit':seconds,'mip_rel_gap':1e-5})
 rec={'case':case,'removed_indexes':remove,'removed_boxes':[B[i]['id'] for i in ids],'candidate_trips':len(cols),'variables':nn+1,'status':int(result.status),'message':result.message,'seconds':time.monotonic()-st,'pool_bound_not_global':None if result.mip_dual_bound is None else float(result.mip_dual_bound),'candidate_global_optimality':False}
 if result.x is not None:
  chosen=[cols[k] for (k,a),x in zip(variables,result.x) if x>.5]
  assert Counter(i for p in chosen for i in p[1])==Counter(range(len(B)))
  chosen.sort(key=lambda k:evaluate(k)['latest'])
  sched=optimize_order(chosen,rng,7000);m=schedule(sched)
  rec['decoded_metrics']=m;rec['selected_decisions']=as_decisions(sched);rec['workload_surrogate_s']=float(result.x[-1])
 return rec

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--seconds',type=float,default=25);a=ap.parse_args()
 starts=[json.loads((ROOT/'inputs/start_v4.json').read_text())]+[json.loads(p.read_text()) for p in (ROOT/'results').glob('seed*/best.json')]
 plans=[from_decisions(x['decisions']) for x in starts];plan=min(plans,key=lambda p:finite_key(schedule(p)))
 # Geographic/task role exchanges larger than the earlier 1-2-trip ruin operators.
 blocks=[('S004','S006'),('S004','S005'),('S004','S008'),('S006','S008'),('S005','S008'),('S001','S006')]
 best=plan;bestm=schedule(best);records=[]
 for case,sites in enumerate(blocks):
  indices=[i for i,p in enumerate(best) if any(s in p[2] for s in sites)]
  if sum(len(best[i][1]) for i in indices)>15:
   records.append({'case':case,'sites':sites,'status':'skipped_over_15_boxes'});continue
  rec=run(case,best,indices,a.seconds,92470+case);rec['sites']=sites
  m=rec.get('decoded_metrics')
  if m and feasible(m) and finite_key(m)<finite_key(bestm):
   best=from_decisions(rec['selected_decisions']);bestm=m;print('IMPROVED',json.dumps(m),flush=True)
  records.append(rec)
  (ROOT/'results/neighborhood_records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
  (ROOT/'results/neighborhood_best.json').write_text(json.dumps({'metrics':bestm,'decisions':as_decisions(best)},ensure_ascii=False,indent=2))
  print('CASE',case,'candidates',rec.get('candidate_trips'),'status',rec['status'],'bound',rec.get('pool_bound_not_global'),'decoded',None if not m else [m['hard_late_boxes'],m['late_boxes'],m['makespan_s']],flush=True)
  evaluate.cache_clear();variants.cache_clear()
if __name__=='__main__':main()
