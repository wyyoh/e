"""Coordinate candidate search preserving coverage of current trajectories.
Keep only point-feasible replacements, not a continuous-feasibility assertion.
"""
from pathlib import Path
import sys,copy,numpy as np,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'));sys.path.insert(0,str(ROOT/'code_v4'))
from precompute import load,dump
from pool_master import solve
ref=load(ROOT/'release_final/primary/selected.json');pack=load(ROOT/'experiments_v4/site_screen/screen_pool.json');routes=pack['routes']
r=ROOT/'experiments_v4/dense_site_search';info=load(r/'points.json');data=np.load(r/'point_matrix.npz');C=data['coverage'];cand=load(ROOT/'experiments_v3/relay_three/expanded_pool.json')['candidates'];sites=[c['geometry'] for c in cand]
lookup={tuple(g[k] for k in 'xyz'):i for i,g in enumerate(sites)};old=[lookup[tuple(g[k] for k in 'xyz')] for g in ref['sites']]
rev=np.array(info['reverse']);blk=info['black_indices'];bm={k:j for j,k in enumerate(blk)};meta=info['point_meta'];prices=np.array([g['out_s']+g['back_s'] for g in sites]);hist=[];best=ref['makespan_s'];rng=np.random.default_rng(876)
out=ROOT/'experiments_v4/coordinate_sites';out.mkdir(parents=True,exist_ok=True)
for role in [2,1,3,0]:
 others=[j for k,j in enumerate(old) if k!=role];needed=~C[others].any(axis=0);eligible=np.flatnonzero(C[:,needed].all(axis=1));eligible=[int(j) for j in eligible if j not in old]
 good=sorted(eligible,key=lambda j:prices[j])[:8]+sorted(eligible,key=lambda j:-int(C[j].sum()))[:8]
 good+=sorted(eligible,key=lambda j:np.linalg.norm(data['positions'][j]-data['positions'][old[role]]))[:8]
 seen=set();good=[j for j in good if not(j in seen or seen.add(j))]
 print('ROLE',role,'eligible',len(eligible),'tested',len(good),flush=True)
 for cnt,j in enumerate(good):
  js=old.copy();js[role]=j;gs=[sites[j] for j in js];profiles=[[] for _ in routes]
  for idx,(i,t) in enumerate(meta):
   b=bm.get(int(rev[idx]));
   if b is None:continue
   allow=np.flatnonzero(C[js,b]).tolist();profiles[i].append({'a':float(t),'b':float(t),'allowed':allow,'kind':'screen_point'})
  for i,rows in enumerate(profiles):
   tmp=[]
   for d in sorted(rows,key=lambda a:a['a']):
    if tmp and d['allowed']==tmp[-1]['allowed'] and d['a']-tmp[-1]['b']<=20+1e-5:tmp[-1]['b']=d['b']
    else:tmp.append(d.copy())
   profiles[i]=tmp
  case=out/f'role{role}_site{j}';newref=copy.deepcopy(ref);newref['sites']=gs
  try:
   sol,st=solve(routes,gs,profiles,case,seconds=7,upper=6341,slack=30,reference=newref)
   row={'role':role,'site_id':j,'site_xyz':cand[j]['xyz'],'status':st,'screen_makespan':sol['makespan_s'] if sol else None,'continuous_verified':False}
   if sol and sol['makespan_s']<best-.01:best=sol['makespan_s'];dump(out/'best_screen.json',{'candidate_path':str((case/'candidate.json').relative_to(ROOT)),'makespan_s':best,'continuous_verified':False})
  except Exception as e:
   import traceback;traceback.print_exc();row={'role':role,'site_id':j,'error':repr(e)}
  hist.append(row);dump(out/'history.json',hist);print('COORD_RESULT',role,j,'BEST',best,flush=True)
