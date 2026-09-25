"""Reprice the unchanged, full V7-Focused covering certificate with accelerated kernels.
No new global bound. Does not invoke LP/tree search; outputs the existing bound audit.
"""
from pathlib import Path
import sys,argparse,subprocess,json,time
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);a=p.parse_args();src=Path(a.source).resolve();sys.path.insert(0,str(src/'code'));import audit_pair
 original=subprocess.run
 def call(args,*aa,**kw):
  name=Path(args[0]).name
  if name in ['cut_pricer','elementary_pricer','memory_pricer']:
   args=[str(ROOT/'code/bin'/f'{name}_accelerated'),*args[1:]]
  return original(args,*aa,**kw)
 subprocess.run=call
 try:r=audit_pair.audit_file(src/'results/final_certificate.json',ROOT/'results/full_accelerated_certificate_audit.json',timeout=90)
 finally:subprocess.run=original
 print(json.dumps({k:v for k,v in r.items() if k!='records'}),flush=True)
