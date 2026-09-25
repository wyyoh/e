"""Diagnostic only after point screening: free transport resource order and H=7200s.
These extra runs are not included in the original fixed-budget sampling comparison.
Two distinct geometric candidates; feasible arm duplicates uniform exactly.
"""
import argparse,sys,json,traceback,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);a=p.parse_args();sys.path.insert(0,str(Path(a.source).resolve()/'code'))
 from joint_v3 import solve_joint
 from export_v2 import export_verified
 records=[]
 for arm in ['uniform','informed']:
  data=json.loads((ROOT/f'results/q3_validations/{arm}/precomputed.json').read_text());out=ROOT/f'results/q3_free_order/{arm}';rec={'arm':arm,'cap_s':7200,'extra_loss_db':.5,'transport_structure':'unchanged main Q3 time decisions','resource_order':'free','time_limit_s':30,'followup_not_in_sampling_statistics':True}
  try:
   sel,st=solve_joint(data,out/'joint',seconds=30,slack_s=30,upper_s=7200,max_relay_jobs=4,reference=None);rec['solver']=st
   if sel is None:rec['status']='no_witness'
   else:
    rec['metrics']=export_verified(data,sel,out/'plan',step=1.0);rec['status']='full_verified_witness'
  except Exception as e:traceback.print_exc();rec['status']='error';rec['error']=repr(e)
  records.append(rec);save(ROOT/'results/q3_schedule_followup.json',records);print('FOLLOWUP',rec,flush=True)
