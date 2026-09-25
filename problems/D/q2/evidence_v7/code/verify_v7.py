"""Fresh input/upper-bound checks plus full independent repricing of the V7 cover.
Does not resume search, does not mutate published results.
"""
from pathlib import Path
import argparse,json,sys,hashlib,time
from audit_parallel import run as audit
from audit_inputs import run as inputs
from audit_upper_rational import run as upper
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--workers',type=int,default=4);a=p.parse_args()
 out=Path(a.out).resolve()
 if out.exists():raise FileExistsError('Use a new output directory')
 out.mkdir(parents=True);st=time.perf_counter()
 manifest=json.load(open(ROOT/'MANIFEST.sha256.json')) if (ROOT/'MANIFEST.sha256.json').exists() else None
 if manifest:
  for name,sha in manifest['files'].items():
   if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=sha:raise ValueError(('Input/source integrity',name))
 ip=inputs(out/'input_audit.json');up=upper(out/'rational_upper.json')
 sys.path.insert(0,str(ROOT/'upstream/primal/code'))
 from verify_solution import check
 rr=check(ROOT/'results/incumbent_replay');bad=[r for r in rr if not r['pass']]
 if bad:raise ValueError(bad)
 lo=audit(ROOT/'results/final_certificate.json',out/'lower_audit.json',a.workers)
 status=json.load(open(ROOT/'results/status.json'))
 if lo['verified_lower_bound_s']!=status['certified_lower_bound_s']:raise ValueError('Status and lower certificate disagree')
 if up['upper_bound_s']!=status['rational_upper_bound_s']:raise ValueError('Status and upper bound disagree')
 res={'lower_bound_s':lo['verified_lower_bound_s'],'upper_bound_s':up['upper_bound_s'],'complete_pricing_calls':lo['complete_pricing_calls'],'upper_replay_checks':len(rr),'rational_upper_checks':up['rational_checks'],'rational_input_checks':ip['rational_coefficient_comparisons'],'failures':0,'elapsed_s':time.perf_counter()-st,'search_performed':False}
 (out/'summary.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))
if __name__=='__main__':main()
