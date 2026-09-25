"""Post-screening control: audit score scope and replay the already-known .5dB witness.
No additional optimization result is attributed to the sampling strategies.
"""
import argparse,sys,json,time,traceback
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def run(src):
 sys.path.insert(0,str(src/'code'))
 from precompute import phases_for,load
 from radio import G,THR,sample
 from point_fast_v3 import margins,margin
 from coverage_v2 import prepare_v2
 from export_v2 import export_verified
 old=load(src/'release_final/primary/selected.json');rob=load(src/'release_v3/robust_fast/selected.json');_,ph=phases_for(old['decisions']);points,_,_=sample(ph,step=20);points=np.unique(np.round(points,8),axis=0)
 fixed=np.array([[s[k] for k in 'xyz'] for s in old['sites']]);other=margins(points,G,THR['UG'])
 for j,p in enumerate(fixed):
  if j!=1:other=np.maximum(other,np.minimum(margins(points,p,THR['UR']),margin(G,p,THR['RG'])))
 rows=[]
 for r in load(ROOT/'results/q3_sampling_records.json'):
  p=np.array(r['best_xyz']);score=float(np.min(np.maximum(other,np.minimum(margins(points,p,THR['UR']),margin(G,p,THR['RG'])))))
  rows.append({'method':r['method'],'seed':r['seed'],'critical_point_score_db':r['sample_best_extra_db'],'all_sample_points_score_db':score,'target_hit':score>=.5-1e-7})
 save(ROOT/'results/q3_score_scope_audit.json',{'all_sample_points':len(points),'rows':rows,'both_scores_are_screening_only':True})
 pts=[[s[k] for k in 'xyz'] for s in rob['sites']];start=time.monotonic();data=prepare_v2(rob['decisions'],pts,extra_db=.5,out=ROOT/'results/q3_positive_control/precomputed.json')
 assert not data['bad_geographic_intervals']
 met=export_verified(data,rob,ROOT/'results/q3_positive_control/plan',step=1.0)
 result={'source':'main-selected archive release_v3/robust_fast; not a newly found plan','same_transport_decisions_as_main_time':rob['decisions']==old['decisions'],'validation':'PASS','metrics':met,'elapsed_s':time.monotonic()-start}
 save(ROOT/'results/q3_positive_control.json',result);print('POSITIVE_CONTROL_PASS',json.dumps(result,ensure_ascii=False),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);a=p.parse_args();run(Path(a.source).resolve())
