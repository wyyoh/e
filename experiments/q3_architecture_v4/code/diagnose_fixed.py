from pathlib import Path
import sys,time,json,copy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'))
print('IMPORT',flush=True)
from precompute import load,dump
from joint_v3 import solve_joint
print('IMPORTED',flush=True)
data=load(ROOT/'experiments_v3/cargo_joint/energy_polish/precomputed.json')
for name,slack,radio in [('fixed30',30,True),('fixed0',0,True),('no_radio',30,False)]:
 d=copy.deepcopy(data)
 if not radio:d['compact']=[];d['bad_geographic_intervals']=[]
 print('SOLVE',name,flush=True)
 s,st=solve_joint(d,ROOT/'experiments_v4/diagnose'/name,seconds=60,slack_s=slack,upper_s=6341,max_relay_jobs=4)
 print('DONE',name,st,'M=',s.get('makespan_s') if s else None,flush=True)
