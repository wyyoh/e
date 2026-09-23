"""Rebuild bounds; optionally repeat limited primal master/scheduling search.
Never upgrades an incomplete model's status to a global optimality claim.
"""
from pathlib import Path
import argparse,subprocess,sys,json,hashlib,zipfile,base64
ROOT=Path(__file__).resolve().parents[1]
def run(args,log=None):
    if log:
        with (ROOT/'logs'/log).open('w') as f:subprocess.run(args,check=True,stdout=f,stderr=subprocess.STDOUT)
    else:subprocess.run(args,check=True)
def main():
    p=argparse.ArgumentParser();p.add_argument('--search',action='store_true');p.add_argument('--check-only',action='store_true');a=p.parse_args()
    for d in ('logs','results'): (ROOT/d).mkdir(exist_ok=True)
    # Text-transported ZIP snapshot: decode before checking original JSON hashes.
    packed=ROOT/'data/canonical_inputs.zip'
    if not packed.exists():
        parts=sorted((ROOT/'data/encoded').glob('*.b64'))
        if not parts:raise RuntimeError('missing canonical input snapshot')
        packed.write_bytes(base64.b64decode(''.join(p.read_text().strip() for p in parts),validate=True))
    # Lossless, small fixed-data snapshots; source code stays as normal Git files.
    for archive,destination in [('data/canonical_inputs.zip','data'),('evidence_snapshot.zip','.')]:
        zpath=ROOT/archive
        if zpath.exists():
            with zipfile.ZipFile(zpath) as z:
                for member in z.infolist():
                    target=(ROOT/destination/member.filename).resolve()
                    if not target.is_relative_to(ROOT.resolve()):raise RuntimeError('unsafe archive member')
                    if not target.exists():
                        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(member))
    manifest=json.loads((ROOT/'manifest.json').read_text())
    for fn,want in manifest['fixed_inputs_sha256'].items():
        if hashlib.sha256((ROOT/fn).read_bytes()).hexdigest()!=want:raise RuntimeError('input changed: '+fn)
    run([sys.executable,str(ROOT/'src/prepare_data.py')])
    for name in ('energy_pricer','pattern_pricer'):
        run(['g++','-O3','-std=c++17',str(ROOT/'src'/f'{name}.cpp'),'-o',str(ROOT/'src'/name)])
    run([sys.executable,str(ROOT/'src/verify_upper_bound.py')],'baseline_independent.log')
    if not a.check_only:
        for script,extra in [('enumeration_audit.py',[]),('workload_cg.py',[]),('energy_cg.py',['--quantum','.01']),('energy_cg.py',['--quantum','.001']),('pattern_cg.py',['--quantum','.001']),('pattern_cg.py',['--quantum','.000001'])]:
            run([sys.executable,str(ROOT/'src'/script)]+extra,script.replace('.py','')+('_'.join(extra)).replace('/','_')+'.log')
    run([sys.executable,str(ROOT/'tests/test_pricer.py')],'pricer_tests.log')
    run([sys.executable,str(ROOT/'tests/test_upper_bound.py')],'upper_bound_negative_tests.log')
    run([sys.executable,str(ROOT/'src/verify_certificate.py')],'certificate_verification.log')
    if a.search:
        run([sys.executable,str(ROOT/'src/restricted_master.py'),'--seconds','90'],'restricted_master.log')
        run([sys.executable,str(ROOT/'src/schedule_check.py'),'--seconds','120'],'schedule_check.log')
    b=json.loads((ROOT/'results/baseline_independent.json').read_text());c=json.loads((ROOT/'results/certificate_verification.json').read_text())
    if b['failed'] or c['failed']:raise RuntimeError('bound check failed')
    ub=b['metrics']['makespan_s'];lb=c['lower_bound_s'];gap=(ub-lb)/ub
    result={'version':'Q2-GLOBAL-VERIFY-V1','all_80_boxes_included':True,'weighted_tardiness_optimum':0,'verified_upper_bound_s':ub,'verified_lower_bound_s':lb,'normalized_gap_over_ub':gap,'global_optimality_proved':False,'scope':'complete pricing for a relaxation; no full-original Branch-Price-and-Check certificate','tolerance_s':1e-6}
    if lb>ub+1e-6:raise RuntimeError('invalid bound ordering')
    result['global_optimality_proved']=abs(ub-lb)<=1e-6
    (ROOT/'results/proof_status.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
