"""Search inherited sites using the actual current path's screen points.
Point coverage is only a candidate generator, not continuous-time certification.
"""
from pathlib import Path
import sys,time,json,numpy as np,math
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'));sys.path.insert(0,str(ROOT/'code_v4'))
from precompute import load,dump,phases_for
from radio import R,G,THR,BASE,LOSS
from run_pool import inherited_pool
from pool_master import solve,routekey
from numba import njit
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import csr_matrix,vstack
import point_fast_v3 as pf
@njit(cache=True)
def available(points,src,threshold,xl,xh,yl,yh,zz,ids,off,ny,nx,ox,oy,width):
 out=np.zeros(len(points),dtype=np.bool_)
 for k in range(len(points)):
  d=max(1e-8,math.sqrt(((points[k]-src)**2).sum()));clear=threshold-BASE-20*math.log10(d/1000)
  if clear<-1e-10:continue
  if clear>=LOSS-1e-10:out[k]=True;continue
  out[k]=not pf.blocked_kernel(src,points[k],xl,xh,yl,yh,zz,ids,off,ny,nx,ox,oy,width)
 return out

def main():
 out=ROOT/'experiments_v4/dense_site_search';out.mkdir(parents=True,exist_ok=True)
 pack=load(ROOT/'experiments_v4/site_screen/screen_pool.json');routes=pack['routes'];ref=load(ROOT/'release_final/primary/selected.json')
 cand=load(ROOT/'experiments_v3/relay_three/expanded_pool.json')['candidates'];sites=[c['geometry'] for c in cand]
 ev,ph=phases_for(routes);points=[];meta=[]
 for p in ph:
  a=np.array([p[k+'0'] for k in 'xyz']);b=np.array([p[k+'1'] for k in 'xyz']);dt=p['end_s']-p['start_s']
  tt=np.linspace(0,1,max(2,int(np.ceil(dt/20))+1)) if np.linalg.norm(b-a)>1e-9 else np.array([0.,1.])
  for t in tt:points.append(a+(b-a)*t);meta.append((p['i'],p['start_s']+dt*t))
 uniq,rev=np.unique(np.array(points),axis=0,return_inverse=True);direct=pf.margins(uniq,G,THR['UG'])>=-1e-10
 blk=np.flatnonzero(~direct);black=uniq[blk];bkindex={int(k):j for j,k in enumerate(blk)}
 dump(out/'points.json',{'unique_points':uniq.tolist(),'black_indices':blk.tolist(),'point_meta':meta,'reverse':rev.tolist(),'screen_step_s':20,'continuous_proof':False})
 t0=time.monotonic();C=np.zeros((len(sites),len(black)),dtype=bool)
 for j,g in enumerate(sites):
  s=np.array([g[k] for k in 'xyz']);back=pf.margins(s[None,:],G,THR['RG'])[0]>=-1e-10
  if back:C[j]=available(black,s,THR['UR'],pf.XL,pf.XH,pf.YL,pf.YH,pf.ZZ,pf.IDS,pf.OFF,pf.NY,pf.NX,pf.OX,pf.OY,pf.WIDTH)
  if j%500==0:print('SITE_MATRIX',j,'/',len(sites),'black',len(black),'sec',time.monotonic()-t0,flush=True)
 np.savez_compressed(out/'point_matrix.npz',coverage=C,points=black,positions=np.array([[g[k] for k in 'xyz'] for g in sites]))
 print('MATRIX_DONE',time.monotonic()-t0,'uncovered',int((~C.any(axis=0)).sum()),flush=True)
 seen={tuple(g[k] for k in 'xyz'):j for j,g in enumerate(sites)}
 for g in ref['sites']:
  if tuple(g[k] for k in 'xyz') not in seen:
   s=np.array([g[k] for k in 'xyz']);row=available(black,s,THR['UR'],pf.XL,pf.XH,pf.YL,pf.YH,pf.ZZ,pf.IDS,pf.OFF,pf.NY,pf.NX,pf.OX,pf.OY,pf.WIDTH);C=np.vstack([C,row]);seen[tuple(g[k] for k in 'xyz')]=len(sites);sites.append(g)
 prices=np.array([g['out_s']+g['back_s'] for g in sites]);reps={}
 for j,row in enumerate(C):
  if not row.any():continue
  key=np.packbits(row).tobytes()
  if key not in reps or prices[j]<prices[reps[key]]:reps[key]=j
 ids=list(reps.values());mat=vstack([csr_matrix(C[ids].T.astype(float)),np.ones((1,len(ids)))]).tocsc();lo=np.r_[np.ones(len(black)),4];hi=np.r_[np.full(len(black),np.inf),4]
 rng=np.random.default_rng(6201);hist=[];sets=[];best=6340.439338658365
 for k in range(24):
  costs=prices[ids]*(rng.uniform(.7,1.3,len(ids)) if k else 1)
  if k>3:costs+=rng.uniform(-150,150,len(black))@C[ids].T
  rr=milp(costs,integrality=np.ones(len(ids)),bounds=Bounds(0,1),constraints=LinearConstraint(mat,lo,hi),options={'time_limit':4,'mip_rel_gap':.01})
  if rr.x is None:print('SETCOVER_FAILED',k,rr.message,flush=True);break
  selected=[ids[j] for j,x in enumerate(rr.x) if x>.5];sets.append(selected)
  row=np.zeros(len(ids));row[np.flatnonzero(rr.x>.5)]=1;mat=vstack([mat,csr_matrix(row[None,:])]).tocsc();lo=np.r_[lo,-np.inf];hi=np.r_[hi,3]
  profiles=[[] for _ in routes]
  for idx,(i,t) in enumerate(meta):
   if direct[rev[idx]]:continue
   b=bkindex[int(rev[idx])];allow=np.flatnonzero(C[selected,b]).tolist();profiles[i].append({'a':float(t),'b':float(t),'allowed':allow,'kind':'screen_point'})
  for i,rows in enumerate(profiles):
   tmp=[]
   for d in sorted(rows,key=lambda a:a['a']):
    if tmp and d['allowed']==tmp[-1]['allowed'] and d['a']-tmp[-1]['b']<=20+1e-5:tmp[-1]['b']=d['b']
    else:tmp.append(d.copy())
   profiles[i]=tmp
  case=out/f'layout_{k:02d}';dump(case/'model_input.json',{'routes':routes,'sites':[sites[j] for j in selected],'profiles':profiles,'candidate_indices':selected,'continuous_certified':False})
  try:
   sol,st=solve(routes,[sites[j] for j in selected],profiles,case/'master',seconds=18,upper=6341,slack=30)
   row={'set':k,'sites':selected,'status':st,'screen_makespan':sol['makespan_s'] if sol else None,'full_continuous_verified':False}
   if sol and sol['makespan_s']<best:best=sol['makespan_s'];dump(out/'best_screen.json',{'candidate_path':str((case/'master/candidate.json').relative_to(ROOT)),'makespan_s':best,'continuous_verified':False})
  except Exception as e:
   import traceback;traceback.print_exc();row={'set':k,'sites':selected,'error':repr(e)}
  hist.append(row);dump(out/'history.json',hist);print('DENSE_LAYOUT',k,'BEST_SCREEN',best,flush=True)
 dump(out/'search_summary.json',{'sites':len(sites),'coverage_classes':len(ids),'black_points':len(black),'sets':len(hist),'elapsed_s':time.monotonic()-t0,'continuous_verified':False})
if __name__=='__main__':main()
