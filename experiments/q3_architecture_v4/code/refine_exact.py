"""Recompute full ray-fan geometry for a screened candidate, re-solve, then export.
A point-screen objective is NEVER published as feasible. Original unpatched
verify_v2 must be run afterward to accept a final plan.
"""
from pathlib import Path
import sys,time,json,argparse,copy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'));sys.path.insert(0,str(ROOT/'code_v4'))
from precompute import load,dump
from pool_master import solve

def run(path,out,seconds=90,upper=6341,slack=30):
    from fast_geometry import enable
    enable();from coverage_v2 import prepare_v2;from export_v2 import export_verified;from verify_v2 import check_physical;from partition_v2 import analyze
    old=load(path);out=Path(out);out.mkdir(parents=True,exist_ok=False);sites=[old['sites'][j] for j in old['active_jobs']]
    print('FULL_GEOMETRY_START',len(old['decisions']),len(sites),flush=True);t=time.monotonic();data=prepare_v2(old['decisions'],sites,extra_db=0.,out=out/'precomputed.json')
    print('FULL_GEOMETRY_READY',len(data['compact']),len(data['bad_geographic_intervals']),time.monotonic()-t,flush=True)
    if data['bad_geographic_intervals']:
        dump(out/'rejection.json',{'reason':'continuous_geographic_gap','count':len(data['bad_geographic_intervals']),'publish_as_feasible':False});return
    profiles=[[{'a':d['a'],'b':d['b'],'allowed':d['allowed'],'kind':d['kind']} for d in data['compact'] if d['i']==i] for i in range(len(old['decisions']))]
    sel,status=solve(old['decisions'],data['sites'],profiles,out/'master',seconds=seconds,upper=upper,slack=slack,reference=old,fixed_routes=True)
    if sel is None:return
    sel['coverage_cache_key']=data['cache_key'];sel['cover_assignment']={}
    for h,d in enumerate(data['compact']):
        i=d['i'];a=sel['starts'][i]+d['a'];b=sel['starts'][i]+d['b'];j=next((j for j in d['allowed'] if j in sel['active_jobs'] and sel['relay_start'][j]<=a+1e-6 and sel['relay_end'][j]>=b-1e-6),None)
        if j is None:raise ValueError(('lost exact coverage',h,d))
        sel['cover_assignment'][str(h)]=j
    dump(out/'selected.json',sel);print('EXPORT_START',sel['makespan_s'],flush=True);summary=export_verified(data,sel,out/'plan',step=1.,verify=False);checks=check_physical(out/'plan');bad=[r for r in checks if not r['pass']];dump(out/'physical_audit.json',{'checks':len(checks),'failures':bad})
    if bad:raise ValueError(('physical_audit_fail',bad[:5]))
    part=analyze(out/'plan',out/'q4_precheck');print('EXPORTED_PENDING_ORIGINAL_INTERVAL_VERIFY',summary['joint_makespan_s'],summary['total_energy_kwh'],part['component_count'],flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--candidate',required=True);ap.add_argument('--out',required=True);ap.add_argument('--seconds',type=float,default=90);ap.add_argument('--upper',type=float,default=6341);ap.add_argument('--slack',type=float,default=30);a=ap.parse_args();run(a.candidate,a.out,a.seconds,a.upper,a.slack)
