"""Reproduce experiments in a NEW directory, with exact main-pinned archives.
No network; never writes to main, formal snapshots or other experimental branches.
"""
from pathlib import Path
import argparse,zipfile,hashlib,json,subprocess,os,sys,time
HERE=Path(__file__).resolve().parents[1]
EXPECTED={'q2':'0804f989699dc506b3111dacc7408d9acdeb6e1115e7f32ec36934116de6ce58','q3':'97f5ea8018a557d604bee87d6886675ecf7648f035e8df0f47f20ff6e7fbc56b'}
def unpack(path,dest,expected):
 path=Path(path)
 if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError(f'Pinned archive differs: {path}')
 dest.mkdir(parents=True,exist_ok=False)
 with zipfile.ZipFile(path) as z:
  for i in z.infolist():
   p=Path(i.filename)
   if p.is_absolute() or '..' in p.parts or ((i.external_attr>>16)&0o170000)==0o120000:raise ValueError('unsafe zip member')
  z.extractall(dest)
 return dest
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--q2-archive',required=True);p.add_argument('--q3-archive',required=True);p.add_argument('--out',required=True);p.add_argument('--skip-full-audit',action='store_true');p.add_argument('--skip-followup',action='store_true');a=p.parse_args()
 out=Path(a.out).resolve()
 if out.exists():raise FileExistsError('Use a new output directory; old evidence is never overwritten')
 out.mkdir(parents=True)
 import shutil
 shutil.copytree(HERE/'code',out/'code',ignore=shutil.ignore_patterns('bin','__pycache__'))
 for d in ['inputs','results','logs']: (out/d).mkdir()
 for origin in [HERE/'inputs/baseline_lock.json',HERE/'BASELINE.json']:
  if origin.exists():
   shutil.copyfile(origin,out/'inputs/baseline_lock.json');break
 v=unpack(a.q2_archive,out/'upstream_q2',EXPECTED['q2'])/'q2_evidence_v7';q=unpack(a.q3_archive,out/'upstream_q3',EXPECTED['q3'])/'problems/D/q3'
 commands=[['build_pricers.py',str(v/'code'),str(out/'code/bin')],['pricing_experiment.py','--source',str(v),'--nodes','8','--repeats','3'],['resource_chain_experiment.py','--source',str(v),'--seconds','25'],['q3_candidates_experiment.py','--source',str(q),'--budget','192','--seeds','5','--seconds','20']]
 if not a.skip_full_audit:commands.append(['audit_accelerated.py','--source',str(v)])
 if not a.skip_followup:
  commands.append(['q3_schedule_followup.py','--source',str(q)])
  commands.append(['q3_control.py','--source',str(q)])
 env=os.environ.copy();env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1');runs=[]
 for command in commands:
  t=time.time();log=out/'logs'/f'{command[0]}.log'
  with log.open('w') as f:r=subprocess.run([sys.executable,'-u',str(out/'code'/command[0]),*command[1:]],stdout=f,stderr=subprocess.STDOUT,env=env)
  runs.append({'command':command,'returncode':r.returncode,'seconds':time.time()-t,'log':str(log.relative_to(out))});(out/'runs.json').write_text(json.dumps(runs,indent=2))
  if r.returncode:raise RuntimeError(f'{command[0]} failed; see {log}')
 print('Finished',out)
