"""Exact continuous-time scheduling of a FIXED selected multiset of sorties.
Aircraft and batteries are independently assignable; resource intervals are
non-overlapping. No time rounding. Identical physical boxes are matched by due
date to delivery slots; all original IDs are then reconstructed. Status=optimal
only certifies this fixed selected multiset, never all route decisions.
"""
from pathlib import Path
from collections import Counter,defaultdict
import json,math,time,itertools
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import coo_matrix
from workload_cg import setup
ROOT=Path(__file__).resolve().parents[1]

def main(seconds=120,cap=None):
    jobs=json.loads((ROOT/'results/selected_jobs.json').read_text());n=len(jobs)
    if not n:raise RuntimeError('master did not produce a candidate')
    B,types,classes,demand,*_=setup();UB=json.loads((ROOT/'data/incumbent_metrics.json').read_text())['makespan_s'] if cap is None else cap
    # s_i in continuous seconds; T, assignments, pair precedence and deadline indicators.
    lower=[0.]*n+[0.];upper=[max(0.,UB-c['duration_s']) for c in jobs]+[UB];integral=[0]*(n+1);T=n
    def var(ub=1,integer=True):
      i=len(lower);lower.append(0.);upper.append(ub);integral.append(int(integer));return i
    ac={};ba={};rr=[];cc=[];vv=[];lo=[];hi=[]
    def row(terms,l=-np.inf,u=np.inf):
      i=len(lo)
      for j,v in terms:
       if v:rr.append(i);cc.append(j);vv.append(v)
      lo.append(l);hi.append(u)
    for i,c in enumerate(jobs):
      t=types[c['type']];ac[i]=[var() for _ in t['aircraft']];ba[i]=[var() for _ in range(t['battery_count'])]
      row([(v,1) for v in ac[i]],1,1);row([(v,1) for v in ba[i]],1,1);row([(i,1),(T,-1)],u=-c['duration_s'])
    for g,t in enumerate(types):
      ids=[i for i,c in enumerate(jobs) if c['type']==g]
      # Canonical first-used labels remove only resource-label symmetries.
      for k,i in enumerate(ids):
       for ass in (ac,ba):
        for u in range(1,len(ass[i])):
         row([(ass[i][u],1)]+[(ass[j][u-1],-1) for j in ids[:k]],u=0)
      for a,i in enumerate(ids):
       for j in ids[a+1:]:
        order=var()
        for ass,extra in ((ac,False),(ba,True)):
         pi=jobs[i]['duration_s']+(jobs[i]['charge_s'] if extra else 0)
         pj=jobs[j]['duration_s']+(jobs[j]['charge_s'] if extra else 0)
         M=UB+max(jobs[i]['charge_s'],jobs[j]['charge_s']) if extra else UB
         for u in range(len(ass[i])):
          # order=1 -> i before j, conditional on same resource u.
          row([(i,1),(j,-1),(order,M),(ass[i][u],M),(ass[j][u],M)],u=3*M-pi)
          row([(j,1),(i,-1),(order,-M),(ass[i][u],M),(ass[j][u],M)],u=2*M-pj)
    # Stage-one optimum is zero tardiness. Preserve original hard deadline too.
    raw_by_class=defaultdict(list)
    for b in B:
      k=classes.index((b['site'],b['kind'],int(b['mass_kg']),round(b['volume_m3']*1000)))
      due=min(b['expected_delivery_s'], b['hard_deadline_s'] if b['hard_deadline_s'] is not None else math.inf)
      raw_by_class[k].append((due,b['id']))
    for k,raw in raw_by_class.items():
      raw.sort()
      for d in sorted(set(x[0] for x in raw)):
       need=sum(x[0]<=d for x in raw);terms=[]
       for i,c in enumerate(jobs):
        count=c['counts'][k]
        if not count:continue
        off=c['delivery_offsets'][str(k)]
        if off>d+1e-9:continue
        if UB-c['duration_s']+off<=d+1e-9:terms.append((i,0));need-=count
        else:
         z=var();row([(i,1),(z,UB)],u=d-off+UB);terms.append((z,count))
       if need>0:row(terms,l=need)
    A=coo_matrix((vv,(rr,cc)),shape=(len(lo),len(lower))).tocsc();cost=np.zeros(len(lower));cost[T]=1
    start=time.monotonic();r=milp(cost,integrality=np.array(integral),bounds=Bounds(lower,upper),constraints=LinearConstraint(A,lo,hi),options={'time_limit':seconds,'mip_rel_gap':0.,'disp':True})
    result={'scope':'fixed-selected-sorties exact scheduling only','sorties':n,'variables':len(lower),'constraints':len(lo),'status':int(r.status),'message':r.message,'cap_s':UB,'objective_s':None if r.fun is None else float(r.fun),'solver_fixed_task_dual_bound_s':None if r.mip_dual_bound is None else float(r.mip_dual_bound),'solver_gap':None if r.mip_gap is None else float(r.mip_gap),'elapsed_s':time.monotonic()-start}
    if r.x is not None:
      output=[]
      for i,c in enumerate(jobs):
       t=types[c['type']];u=int(np.argmax(r.x[ac[i]]));b=int(np.argmax(r.x[ba[i]]))
       output.append(dict(c,flight_id=f'Q2-EXACT-{i+1:02d}',start_s=float(r.x[i]),return_s=float(r.x[i]+c['duration_s']),aircraft=t['aircraft'][u],battery=f'{t["id"]}-BAT{b+1:02d}',box_ids=[]))
      for k,raw in raw_by_class.items():
       slots=[]
       for i,c in enumerate(output):
        if c['counts'][k]:slots.extend((c['start_s']+c['delivery_offsets'][str(k)],i) for _ in range(c['counts'][k]))
       slots.sort();raw.sort()
       if len(raw)!=len(slots):raise AssertionError('coverage mismatch')
       for (due,bid),(tm,i) in zip(raw,slots):
        if tm>due+1e-6:raise AssertionError('deadline assignment failed')
        output[i]['box_ids'].append(bid)
      (ROOT/'results/scheduled_candidate.json').write_text(json.dumps(output,ensure_ascii=False,indent=2))
    (ROOT/'results/schedule_check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print('FINAL',json.dumps(result,indent=2),flush=True)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--seconds',type=float,default=120);p.add_argument('--cap',type=float);a=p.parse_args();main(a.seconds,a.cap)
