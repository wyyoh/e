"""Targeted new route modes: reverse/permute ordered stops, preserving real boxes.
No geometry/energy alteration. Master chooses exact box cover and resources.
"""
from pathlib import Path
import sys,argparse,itertools
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'));sys.path.insert(0,str(ROOT/'code_v4'))
from precompute import load,dump
from transport import variants,evaluate,BI,B,T
from pool_master import routekey,solve
from run_pool import inherited_pool
from screen_sites import sampled_profiles

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--name',default='order_modes');ap.add_argument('--seconds',type=float,default=120);ap.add_argument('--types',action='store_true');ap.add_argument('--full',action='store_true');a=ap.parse_args();ref,known,files=inherited_pool();routes=list(ref['decisions']);seen={routekey(d) for d in routes}
 for role in ['compact22','energy22','baseline']:
  for d in load(ROOT/f'release_v3/{role}/selected.json')['decisions']:
   if routekey(d) not in seen:seen.add(routekey(d));routes.append(d)
 for d,_,_ in known.values():
  if routekey(d) not in seen:seen.add(routekey(d));routes.append(d)
 oldroutes=routes[:];new=[]
 for d in oldroutes:
  ids=tuple(sorted(BI[b] for b in d['boxes']))
  for typ in (list(T) if a.types else [d['type']]):
   for k in variants(typ,ids):
    e=evaluate(k)
    if e['latest'] < 30:continue
    dd={'type':typ,'boxes':[B[b]['id'] for b in ids],'route':list(k[2])}
    if routekey(dd) not in seen:seen.add(routekey(dd));routes.append(dd);new.append(dd)
 out=ROOT/'experiments_v4'/a.name;out.mkdir(parents=True,exist_ok=False);dump(out/'new_route_modes.json',new);print('NEW_MODES',len(routes),len(new),[(d['type'],d['route']) for d in new],flush=True)
 if a.full:
  from fast_geometry import enable;enable();from coverage_v2 import prepare_v2;data=prepare_v2(routes,ref['sites'],out=out/'full_geometry.json');profiles=[[{'a':d['a'],'b':d['b'],'allowed':d['allowed'],'kind':d['kind']} for d in data['compact'] if d['i']==i] for i in range(len(routes))];meta={'whole_time_geometry':True}
 else:profiles,meta=sampled_profiles(routes,ref['sites'],20)
 dump(out/'pool.json',{'routes':routes,'sites':ref['sites'],'profiles':profiles,'metadata':meta});solve(routes,ref['sites'],profiles,out/'master',seconds=a.seconds,slack=30,reference=ref)
if __name__=='__main__':main()
