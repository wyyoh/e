"""Bounded exact selection neighborhoods from generated pair patterns.
Untouched transport tasks stay in the pool, while all resource times stay free.
Output remains point-screen-only pending full original verification.
"""
from pathlib import Path
import sys,copy,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'));sys.path.insert(0,str(ROOT/'code_v4'))
from precompute import load,dump
from pool_master import routekey,solve
full=load(ROOT/'experiments_v4/cross_type_modes/pool.json');ref=load(ROOT/'release_final/primary/selected.json');hist=[];best=ref['makespan_s'];lookup={routekey(d):i for i,d in enumerate(full['routes'])}
for rr in full['generator']:
 i,j=rr['pair'];union=set(ref['decisions'][i]['boxes']+ref['decisions'][j]['boxes']);ids=[lookup[routekey(d)] for d in ref['decisions']]
 ids+=sorted({k for k,d in enumerate(full['routes']) if set(d['boxes'])<=union}-set(ids))
 routes=[full['routes'][k] for k in ids];profiles=[full['profiles'][k] for k in ids]
 out=ROOT/f'experiments_v4/cross_pairs/{i:02d}_{j:02d}'
 s,st=solve(routes,full['sites'],profiles,out,seconds=16,slack=30,reference=ref)
 rec={'pair':[i,j],'pool_size':len(routes),'solver':st,'screened_makespan_s':s['makespan_s'] if s else None,'continuous_verified':False}
 if s and s['makespan_s']<best-.01:
  best=s['makespan_s'];dump(ROOT/'experiments_v4/cross_pairs/best_screen.json',{'path':str((out/'candidate.json').relative_to(ROOT)),'screened_makespan_s':best,'continuous_verified':False})
 hist.append(rec);dump(ROOT/'experiments_v4/cross_pairs/history.json',hist);print('PAIR_DONE',i,j,'SCREEN_BEST',best,flush=True)
