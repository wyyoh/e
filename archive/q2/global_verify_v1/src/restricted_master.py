"""Primal candidate search with an incomplete route pool; NEVER a global bound.
Solve exact coverage and per-aircraft workload allocation for this pool.
Continuous-time scheduling must be checked separately before an upper bound.
"""
from pathlib import Path
from collections import Counter,defaultdict
import json,math,itertools,time
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import coo_matrix
from workload_cg import setup
ROOT=Path(__file__).resolve().parents[1]

def evaluate(g,seq,B,types,classes,raws,geo,nd):
    t=types[g];counts=Counter(seq);demand=Counter((b['site'],b['kind'],int(b['mass_kg']),round(b['volume_m3']*1000)) for b in B)
    if any(n>demand[classes[j]] for j,n in counts.items()):return None
    route=[k for k,_ in itertools.groupby(seq,key=lambda j:classes[j][0])]
    if len(set(route))!=len(route):return None # PRIMAL pool restriction, not global-LB pricing
    mass=sum(classes[j][2]*n for j,n in counts.items());vol=sum(classes[j][3]*n for j,n in counts.items());nbox=len(seq)
    if mass>t['max_payload_kg'] or vol>round(t['max_volume_m3']*1000):return None
    p=t['prep_s']+nbox*t['load_per_box_s'];q=mass;e=0.;prev='O01';offs={}
    for dest in route+['O01']:
      l=geo[prev,dest];d=l['distance_m'];L=t['empty_range_m']-(t['empty_range_m']-t['full_range_m'])*(q/t['max_payload_kg'])**1.5
      e+=t['battery_kwh']*d/L+(t['empty_mass_kg']+q)*9.81*l['up_m']/(t['up_efficiency']*3600000)
      p+=float(raws[g][nd[prev],nd[dest]])
      if dest!='O01':
       drop=[j for j in seq if classes[j][0]==dest];p+=t['handover_base_s']+len(drop)*t['handover_per_box_s']
       for j in drop:offs[str(j)]=p
       q-=sum(classes[j][2] for j in drop)
      prev=dest
    if e>t['battery_kwh']*(1-t['reserve_pct']/100)+1e-9:return None
    soc=1-e/t['battery_kwh'];chg=t['charge_full_s']*(.65*max(0,.9-soc)/.9+.35*(1-max(.9,soc))/.1)
    return {'type':g,'counts':[counts[j] for j in range(len(classes))],'route':route,'duration_s':p,'energy_kwh':e,'charge_s':chg,'delivery_offsets':offs,'mass_kg':mass,'volume_l':vol}

def makepool():
    B,types,classes,demand,sites,weights,volumes,travel,raws=setup();names=['O01']+sorted({b['site'] for b in B});nd={n:i for i,n in enumerate(names)}
    geo={(l['from'],l['to']):l for l in json.loads((ROOT/'data/legs.json').read_text())};pool=[];seen=set()
    def add(g,seq):
      c=evaluate(g,seq,B,types,classes,raws,geo,nd)
      if not c:return
      key=(g,tuple(c['counts']),tuple(c['route']))
      if key not in seen:seen.add(key);pool.append(c)
    for fn in (ROOT/'results').glob('energy_columns*.json'):
      for c in json.loads(fn.read_text()):add(c['type'],c['sequence'])
    for c in json.loads((ROOT/'results/workload_columns.json').read_text()):add('ABC'.index(c['type']),c['sequence'])
    bm={b['id']:b for b in B}
    for f in json.loads((ROOT/'data/incumbent_flights.json').read_text()):
      seq=[]
      for site in f['route'][1:-1]:
       for bid in f['box_ids']:
        b=bm[bid]
        if b['site']==site:seq.append(classes.index((site,b['kind'],b['mass_kg'],round(b['volume_m3']*1000))))
      add('ABC'.index(f['type']),seq)
    # All single-site bounded patterns: provide exact single-site alternatives.
    for g,t in enumerate(types):
      for site in names[1:]:
       js=[j for j,c in enumerate(classes) if c[0]==site]
       for ns in itertools.product(*(range(int(demand[j])+1) for j in js)):
        seq=[j for j,n in zip(js,ns) for _ in range(n)]
        if seq:add(g,seq)
    (ROOT/'results/primal_pool.json').write_text(json.dumps(pool,separators=(',',':')))
    return pool,types,demand

def main(seconds=60):
    pool,types,demand=makepool();R=len(pool);nc=len(demand);ub=json.loads((ROOT/'data/incumbent_metrics.json').read_text())['makespan_s']
    cols=[];jobsbyr=defaultdict(list)
    for r,c in enumerate(pool):
      for u in range(len(types[c['type']]['aircraft'])):jobsbyr[r].append(len(cols));cols.append((r,u))
    J=len(cols);F=J+R;N=F+1
    rr=[];cc=[];vv=[];lo=[];hi=[]
    def row(items,l,u):
      i=len(lo)
      for j,v in items:
       if v:rr.append(i);cc.append(j);vv.append(v)
      lo.append(l);hi.append(u)
    for j in range(nc):row([(k,pool[r]['counts'][j]) for k,(r,u) in enumerate(cols)],demand[j],demand[j])
    for g,t in enumerate(types):
      for u in range(len(t['aircraft'])):
       row([(k,pool[r]['duration_s']) for k,(r,uu) in enumerate(cols) if pool[r]['type']==g and u==uu]+[(F,-1)],-np.inf,0)
      # Battery workload minus at most B final recharge tails (necessary only).
      row([(k,pool[r]['duration_s']+pool[r]['charge_s']) for k,(r,u) in enumerate(cols) if pool[r]['type']==g]+[(J+r,-pool[r]['charge_s']) for r in range(R) if pool[r]['type']==g]+[(F,-t['battery_count'])],-np.inf,0)
      row([(J+r,1) for r in range(R) if pool[r]['type']==g],0,t['battery_count'])
    for r in range(R):row([(J+r,1)]+[(k,-1) for k in jobsbyr[r]],-np.inf,0)
    lim=[]
    for c in pool:lim.append(min(int(demand[j])//n for j,n in enumerate(c['counts']) if n))
    upper=np.array([lim[r] for r,u in cols]+lim+[ub]);integ=np.ones(N);integ[F]=0;cost=np.zeros(N);cost[F]=1
    A=coo_matrix((vv,(rr,cc)),shape=(len(lo),N)).tocsc();start=time.monotonic()
    res=milp(cost,integrality=integ,bounds=Bounds(np.zeros(N),upper),constraints=LinearConstraint(A,lo,hi),options={'time_limit':seconds,'mip_rel_gap':0.0,'disp':True})
    out={'scope':'INCOMPLETE pool + workload relaxation; neither feasible schedule nor global lower bound','pool_columns':R,'variables':N,'constraints':len(lo),'status':int(res.status),'message':res.message,'elapsed_s':time.monotonic()-start,'objective_s':None if res.fun is None else float(res.fun),'solver_pool_dual_bound_s':None if res.mip_dual_bound is None else float(res.mip_dual_bound),'solver_pool_gap':None if res.mip_gap is None else float(res.mip_gap)}
    selected=[]
    if res.x is not None:
      for k,(r,u) in enumerate(cols):
       for _ in range(round(res.x[k])):selected.append(dict(pool[r],pool_id=r,suggested_aircraft=u))
    out['selected_jobs']=len(selected)
    (ROOT/'results/restricted_master.json').write_text(json.dumps(out,indent=2));(ROOT/'results/selected_jobs.json').write_text(json.dumps(selected,indent=2))
    print('FINAL',json.dumps(out,indent=2),flush=True)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--seconds',type=float,default=60);a=p.parse_args();main(a.seconds)
