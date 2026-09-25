"""Permit handoffs inside constant-geometry intervals via certified subintervals.
Splitting an already certified interval does not replace it by sampled coverage.
"""
from pathlib import Path
import sys,copy,math,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'));sys.path.insert(0,str(ROOT/'code_v4'))
from precompute import load,dump,digest
from pool_master import solve

def refine(data,dt):
 d=copy.deepcopy(data);rows=[];compact=[]
 for row in data['rows']:
  allow=[j for j,b in enumerate(row['available'][1:]) if b];n=math.ceil((row['b']-row['a'])/dt) if not row['available'][0] and len(allow)>1 else 1
  for k in range(n):
   new={**row,'a':row['a']+(row['b']-row['a'])*k/n,'b':row['a']+(row['b']-row['a'])*(k+1)/n};rid=len(rows);rows.append(new)
   if not new['available'][0]:
    c={'i':row['i'],'a':new['a'],'b':new['b'],'allowed':allow,'row_ids':[rid],'kind':'interval'}
    if compact and len(allow)==1 and compact[-1]['i']==c['i'] and compact[-1]['allowed']==allow and abs(compact[-1]['b']-c['a'])<1e-8:compact[-1]['b']=c['b'];compact[-1]['row_ids']+=[rid]
    else:compact.append(c)
 d['rows']=rows;d['compact']=compact+[copy.deepcopy(x) for x in data['compact'] if x['kind']=='endpoint'];d['time_refinement']={'max_multi_provider_piece_s':dt,'source_cache_key':data['cache_key'],'claim':'constant-geometry subsets only'};d['cache_key']=digest({'base':data['cache_key'],'split':dt});return d

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--dt',type=float,default=30);ap.add_argument('--seconds',type=float,default=100);a=ap.parse_args();data=refine(load(ROOT/'experiments_v3/cargo_joint/energy_polish/precomputed.json'),a.dt);ref=load(ROOT/'release_final/primary/selected.json');out=ROOT/f'experiments_v4/split_atoms_{int(a.dt)}';dump(out/'precomputed.json',data)
 profiles=[[{k:d[k] for k in ('a','b','allowed','kind')} for d in data['compact'] if d['i']==i] for i in range(len(data['decisions']))];sel,st=solve(data['decisions'],data['sites'],profiles,out/'master',seconds=a.seconds,slack=30,reference=ref,fixed_routes=True)
 if sel:
  sel['coverage_cache_key']=data['cache_key'];sel['cover_assignment']={}
  for h,d in enumerate(data['compact']):
   st=sel['starts'][d['i']];j=next(j for j in d['allowed'] if j in sel['active_jobs'] and sel['relay_start'][j]<=st+d['a']+1e-6 and sel['relay_end'][j]>=st+d['b']-1e-6);sel['cover_assignment'][str(h)]=j
  dump(out/'selected.json',sel)
  if sel['makespan_s']<ref['makespan_s']-.1:
   from fast_geometry import enable;enable();from export_v2 import export_verified;export_verified(data,sel,out/'plan',step=1,verify=False);print('PENDING_UNPATCHED_INDEPENDENT_AUDIT',sel['makespan_s'],flush=True)
if __name__=='__main__':main()
