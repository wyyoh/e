"""Structured whole-batch candidate construction, not local one-box swaps.
Enumerate single-service count modes retaining deadline-equivalent cargo classes;
add inherited feasible multi-service patterns. Resource workload is a screening
relaxation only. Each complete plan is then independently scheduled jointly with
relays; point feasibility must still pass full interval verification later.
"""
from pathlib import Path
import sys,json,itertools,numpy as np,math,time
from collections import defaultdict
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import csr_matrix,vstack
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'));sys.path.insert(0,str(ROOT/'code_v4'))
from precompute import load,dump,digest
from transport import B,BI,T,task,evaluate,variants
from pool_master import solve,routekey
from screen_sites import sampled_profiles

def main():
 out=ROOT/'experiments_v4/whole_batch';out.mkdir(parents=True,exist_ok=True);ref=load(ROOT/'release_final/primary/selected.json');groups=defaultdict(list)
 for i,b in enumerate(B):groups[(b['site'],b['mass_kg'],b['volume_m3'],b['expected_delivery_s'],b['hard_deadline_s'],b['priority'])].append(i)
 ck=list(groups);cl=[groups[k] for k in ck];which={b:k for k,row in enumerate(cl) for b in row};dem=np.array([len(row) for row in cl]);nc=len(cl);modes=[];seen=set()
 def add(g,ids,order):
  counts=np.bincount([which[b] for b in ids],minlength=nc);key=(g,tuple(counts),tuple(order))
  if key in seen:return
  ids2=tuple(sorted(b for k,c in enumerate(counts) for b in cl[k][:c]));e=evaluate(task(g,ids2,order))
  if e is None:return
  latest=min([B[b]['expected_delivery_s']-off for b,off in e['delivery']]+[B[b]['hard_deadline_s']-off-30 for b,off in e['delivery'] if B[b]['hard_deadline_s'] is not None])
  if latest<0:return
  seen.add(key);modes.append({'type':g,'boxes':[B[b]['id'] for b in ids2],'route':list(order),'counts':counts.tolist(),'energy':e['energy'],'duration':e['duration'],'charge':e['charge']})
 for site in sorted({b['site'] for b in B}):
  ii=[j for j,k in enumerate(ck) if k[0]==site]
  for counts in itertools.product(*(range(len(cl[j])+1) for j in ii)):
   if not any(counts):continue
   ids=tuple(b for j,c in zip(ii,counts) for b in cl[j][:c])
   for g in T:add(g,ids,(site,))
 for source in ['experiments_v4/cross_type_modes/pool.json','experiments_v4/targeted_modes/pool.json','experiments_v4/type_order_modes/pool.json']:
  for d in load(ROOT/source)['routes']:add(d['type'],tuple(BI[b] for b in d['boxes']),d['route'])
 profiles,screen=sampled_profiles(modes,ref['sites'],20);valid=[i for i,row in enumerate(profiles) if all(d['allowed'] for d in row)];modes=[modes[i] for i in valid];profiles=[profiles[i] for i in valid];nm=len(modes);print('WHOLE_MODES',nm,'classes',nc,flush=True);dump(out/'modes.json',{'modes':modes,'profiles':profiles,'classes':cl,'screen':screen})
 C=np.array([m['counts'] for m in modes]).T;rows=[csr_matrix(C)];lo=list(dem);hi=list(dem)
 for g,t in T.items():w=np.array([m['duration'] if m['type']==g else 0 for m in modes]);rows.append(csr_matrix(w[None,:]));lo.append(0);hi.append(len(t['aircraft'])*6250)
 rows.append(csr_matrix(np.ones((1,nm))));lo.append(18);hi.append(25);A=vstack(rows).tocsc();lo=np.array(lo);hi=np.array(hi);ub=np.array([min(dem[k]//c for k,c in enumerate(m['counts']) if c) for m in modes]);rng=np.random.default_rng(146);hist=[];best=ref['makespan_s']
 for k in range(16):
  weights={g:rng.uniform(.7,1.4) for g in T};cost=np.array([m['energy']+rng.uniform(.0001,.001)*weights[m['type']]*m['duration']+.2 for m in modes]);cost*=rng.uniform(.98,1.02,nm);rr=milp(cost,integrality=np.ones(nm),bounds=Bounds(0,ub),constraints=LinearConstraint(A,lo,hi),options={'time_limit':3,'mip_rel_gap':.001})
  if rr.x is None:hist.append({'k':k,'mode_status':int(rr.status),'plan':None});continue
  mult=np.rint(rr.x).astype(int);assert np.array_equal(C@mult,dem);selected=[i for i,n in enumerate(mult) for _ in range(n)];avail=[row.copy() for row in cl];dec=[];prs=[]
  for i in selected:
   m=modes[i];ids=[]
   for c,n in enumerate(m['counts']):ids+=avail[c][:n];avail[c]=avail[c][n:]
   dec.append({'type':m['type'],'boxes':[B[b]['id'] for b in ids],'route':m['route']});prs.append(profiles[i])
  assert not any(avail);chosen=np.flatnonzero(mult);row=np.zeros(nm);row[chosen]=1;A=vstack([A,csr_matrix(row[None,:])]).tocsc();lo=np.r_[lo,-np.inf];hi=np.r_[hi,sum(mult)-1];case=out/f'candidate_{k:02d}';dump(case/'model_input.json',{'decisions':dec,'sites':ref['sites'],'profiles':prs,'mode_indices':selected,'mode_status':int(rr.status),'continuous_verified':False})
  try:
   sol,st=solve(dec,ref['sites'],prs,case/'master',seconds=14,upper=6341,slack=30,fixed_routes=True);rec={'k':k,'sorties':len(dec),'energy':sum(modes[i]['energy'] for i in selected),'status':st,'screen_makespan':sol['makespan_s'] if sol else None,'continuous_verified':False}
   if sol and sol['makespan_s']<best-.01:best=sol['makespan_s'];dump(out/'best_screen.json',{'candidate_path':str((case/'master/candidate.json').relative_to(ROOT)),'makespan_s':best,'continuous_verified':False})
  except Exception as e:
   import traceback;traceback.print_exc();rec={'k':k,'error':repr(e)}
  hist.append(rec);dump(out/'history.json',hist);print('WHOLE_CANDIDATE',k,'BEST_SCREEN',best,flush=True)
if __name__=='__main__':main()
