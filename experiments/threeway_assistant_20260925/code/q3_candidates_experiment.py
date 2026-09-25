"""Paired fixed-budget screening: uniform / necessary-feasible / critical-guided.
Only replace the north relay; 23 transport tasks & other 3 sites stay fixed.
RF calculations are original two-hop (U-R-G), blockage a loss not LoS veto.
Screening scores NEVER imply continuous or scheduling feasibility.
"""
from __future__ import annotations
import argparse,sys,json,time,copy,math,traceback
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def save(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def run(src,budget=192,seeds=5,solve_seconds=20):
 src=Path(src).resolve();sys.path.insert(0,str(src/'code'))
 from precompute import phases_for,load
 from radio import G,THR,R,BASE,ground,grid,DEM,sample
 from point_fast_v3 import margins,margin
 from dual_pricing_v3 import decode_position
 from coverage_v2 import geometry,prepare_v2
 from joint_v3 import solve_joint
 from export_v2 import export_verified
 old=load(src/'release_final/primary/selected.json');basepoints=np.array([[x[k] for k in 'xyz'] for x in old['sites']]);ds=old['decisions'];j=1
 _,ph=phases_for(ds);points,_,_=sample(ph,step=20);points=np.unique(np.round(points,8),axis=0)
 other=margins(points,G,THR['UG'])
 for k,srcp in enumerate(basepoints):
  if k!=j:other=np.maximum(other,np.minimum(margins(points,srcp,THR['UR']),margin(G,srcp,THR['RG'])))
 target=.5;mask=other<target;hard=points[mask];otherhard=other[mask]
 assert len(hard)>0
 radii={'access':1000*10**((THR['UR']-BASE-target)/20),'backhaul':1000*10**((THR['RG']-BASE-target)/20)}
 x0,y0,z0=basepoints[j];g0=geometry(*basepoints[j]);f0=(z0-g0['ground_m'])/min(R['max_agl_m'],g0['cruise_z']-g0['ground_m'])
 lower=np.array([x0-1000,y0-1000,.05]);upper=np.array([x0+1000,y0+1000,1.0])
 def necessary(pos):return np.linalg.norm(pos-G)<=radii['backhaul'] and np.max(np.linalg.norm(hard-pos,axis=1))<=radii['access']
 def quality(pos):
  back=margin(G,pos,THR['RG']);access=margins(hard,pos,THR['UR']);return float(np.min(np.maximum(otherhard,np.minimum(back,access))))
 oldscore=quality(basepoints[j]);records=[];top=[]
 save(ROOT/'inputs/q3_screen_setup.json',{'transport_decisions':ds,'fixed_base_sites':basepoints.tolist(),'replaced_index':j,'screen_points':len(points),'hard_points':hard.tolist(),'other_hard_margins_db':otherhard.tolist(),'bounds_normalized':[lower.tolist(),upper.tolist()],'target_extra_loss_db':target,'radii_m':radii,'sample_step_s':20,'old_sample_margin_db':oldscore,'scope':'fixed 23 task geometry, north-site replacement; extra loss on original model'})
 # Warm JIT before timing. Same old candidate available to every arm.
 for seed in range(seeds):
  for method in ['uniform','feasible','informed']:
   rng=np.random.default_rng(92550+seed);bestv=np.array([x0,y0,f0]);bestpos=basepoints[j].copy();bestscore=oldscore;hist=[];proposals=0;rf=0;rejects={'decode':0,'necessary':0};t=time.perf_counter()
   while rf<budget and proposals<budget*1000:
    proposals+=1
    if method=='informed' and rng.random()<.80:
     stage=min(3,rf*4//budget);sigma=[350.,180.,90.,40.][stage]
     v=np.array([bestv[0]+rng.normal(0,sigma),bestv[1]+rng.normal(0,sigma),np.clip(bestv[2]+rng.normal(0,.12),.05,1.)]);v=np.clip(v,lower,upper)
    else:v=rng.uniform(lower,upper)
    try:pos=np.array(decode_position(v))
    except (ValueError,IndexError):rejects['decode']+=1;continue
    if method!='uniform' and not necessary(pos):rejects['necessary']+=1;continue
    val=quality(pos);rf+=1
    if val>bestscore+1e-12:bestscore=val;bestv=v.copy();bestpos=pos.copy()
    hist.append({'rf_eval':rf,'xyz':pos.tolist(),'margin_db':val,'best_db':bestscore})
   rec={'seed':92550+seed,'method':method,'rf_evaluations':rf,'raw_proposals':proposals,'rejects':rejects,'budget':budget,'sample_best_extra_db':bestscore,'best_xyz':bestpos.tolist(),'seconds':time.perf_counter()-t,'screen_only':True,'history':hist}
   records.append(rec);save(ROOT/'results/q3_sampling_records.json',records);print('Q3_SCREEN',seed,method,bestscore,rf,proposals,flush=True)
 # Equal validation budget: one top final site per arm; same 30s hard-slack policy
 # and fixed 0.5dB scenario. Each passes inherited full geometry, solver & replay.
 validations=[]
 for method in ['uniform','feasible','informed']:
  rec=max((r for r in records if r['method']==method),key=lambda r:r['sample_best_extra_db']);pos=rec['best_xyz'];out=ROOT/f'results/q3_validations/{method}';result={'method':method,'seed':rec['seed'],'screen_score_db':rec['sample_best_extra_db'],'xyz':pos,'extra_loss_db':target,'fixed_transports':True}
  try:
   geometry(*pos)
   if rec['sample_best_extra_db']<target-1e-7:
    result['status']='sample_disproves_requested_margin';validations.append(result);continue
   pts=basepoints.copy();pts[j]=pos;t=time.perf_counter();data=prepare_v2(ds,pts.tolist(),extra_db=target,out=out/'precomputed.json');result['precompute_s']=time.perf_counter()-t;result['full_uncovered_intervals']=len(data['bad_geographic_intervals'])
   if data['bad_geographic_intervals']:result['status']='full_geometry_rejected'
   else:
    sel,st=solve_joint(data,out/'joint',seconds=solve_seconds,slack_s=30,upper_s=old['makespan_s']+180,max_relay_jobs=4,reference=old)
    result['solver']=st
    if sel is None:result['status']='solver_no_witness_not_infeasibility_proof'
    else:
     summ=export_verified(data,sel,out/'plan',step=1.0);result['status']='complete_verified_witness';result['summary']=summ
  except Exception as e:traceback.print_exc();result['status']='error';result['error']=repr(e)
  validations.append(result);save(ROOT/'results/q3_validations.json',validations);print('Q3_VALIDATE',result,flush=True)
 summary={'methods':{},'seeds':seeds,'rf_budget_per_arm':budget,'target_extra_loss_db':target,'old_fixed_layout_sample_score_db':oldscore,'scope':'same local box and same fixed 3 other relay sites; necessary/geographic screening not original-Q3 global search; not automatically a new official plan','validations':validations,'official_Q3_or_Q4_changed':False,'old_finite_pool_certificate_reused_for_new_candidates':False}
 for method in ['uniform','feasible','informed']:
  rs=[r for r in records if r['method']==method];summary['methods'][method]={'best_sample_db':max(r['sample_best_extra_db'] for r in rs),'median_sample_db':float(np.median([r['sample_best_extra_db'] for r in rs])),'worst_sample_db':min(r['sample_best_extra_db'] for r in rs),'screen_target_hits':sum(r['sample_best_extra_db']>=target-1e-7 for r in rs),'total_raw_proposals':sum(r['raw_proposals'] for r in rs),'total_rf_evaluations':sum(r['rf_evaluations'] for r in rs)}
 save(ROOT/'results/q3_summary.json',summary);print('Q3_DONE',summary,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--budget',type=int,default=192);p.add_argument('--seeds',type=int,default=5);p.add_argument('--seconds',type=float,default=20);a=p.parse_args();run(a.source,a.budget,a.seeds,a.seconds)
