from pathlib import Path
import sys,copy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'));sys.path.insert(0,str(ROOT/'code_v4'))
from precompute import load,dump
from pool_master import solve
p=load(ROOT/'experiments_v4/path_pool/pool.json');ref=load(ROOT/'release_final/primary/selected.json');hist=[]
for role in (2,1,0,3):
 sites=p['sites']+[copy.deepcopy(p['sites'][role])]
 profiles=[[{**d,'allowed':d['allowed']+([4] if role in d['allowed'] else [])} for d in row] for row in p['profiles']]
 out=ROOT/f'experiments_v4/single_repeat_{role}';s,st=solve(p['routes'],sites,profiles,out,seconds=30,upper=6341,slack=30,max_relays=5,reference=ref);hist.append({'role':role,'makespan':s['makespan_s'] if s else None,'status':st});dump(ROOT/'experiments_v4/single_repeat_history.json',hist)
