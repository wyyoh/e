from pathlib import Path
import sys,json,copy,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'));sys.path.insert(0,str(ROOT/'code_v4'))
from precompute import load,dump
from pool_master import solve
full=load(ROOT/'experiments_v4/site_screen/screen_pool.json');ref=load(ROOT/'release_final/primary/selected.json');cand=load(ROOT/'experiments_v3/relay_three/expanded_pool.json')['candidates']
key=lambda g:tuple(g[k] for k in 'xyz')
lookup={key(g):j for j,g in enumerate(full['sites'])}
best=ref['makespan_s'];hist=[]
for k,chosen in enumerate(full['selected_site_sets']):
    ids=list(range(4));ids+=sorted(set(lookup[key(cand[j]['geometry'])] for j in chosen['indices'])-set(ids))
    rev={j:k for k,j in enumerate(ids)};sites=[full['sites'][j] for j in ids]
    prs=[[{**d,'allowed':[rev[j] for j in d['allowed'] if j in rev]} for d in group] for group in full['profiles']]
    out=ROOT/f'experiments_v4/combos/set_{k:02d}'
    try:
        s,st=solve(full['routes'],sites,prs,out,seconds=18,upper=6341,slack=30,reference=ref)
        rec={'index':k,'site_indices':ids,'status':st,'screened_makespan_s':s['makespan_s'] if s else None,'continuous_verified':False}
        if s and s['makespan_s']<best-.01:best=s['makespan_s'];dump(ROOT/'experiments_v4/combos/best_screen.json',{'path':str((out/'candidate.json').relative_to(ROOT)),'screened_makespan_s':best,'continuous_verified':False})
    except Exception as e:
        import traceback;traceback.print_exc();rec={'index':k,'error':repr(e)}
    hist.append(rec);dump(ROOT/'experiments_v4/combos/history.json',hist);print('COMBO',k,'BEST_SCREEN',best,flush=True)
