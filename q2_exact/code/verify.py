"""Rebuild incumbent and verify the published bound; no optimizer needed."""
from pathlib import Path
import subprocess,sys,json
ROOT=Path(__file__).resolve().parents[1]
def main():
 (ROOT/'results').mkdir(exist_ok=True)
 for args in [('unpack_inputs.py',),('certify_upper.py',),('enumeration_audit.py',),('certify_bound.py','--cuts','--verify-only')]:
  subprocess.run([sys.executable,str(ROOT/'code'/args[0]),*args[1:]],check=True)
 lo=json.loads((ROOT/'results/rational_certificate_cuts_verification.json').read_text())
 up=json.loads((ROOT/'results/rational_upper_bound.json').read_text())
 print('Certified interval:',lo['lower_bound_s'],'<= T* <=',up['upper_bound_s'])
 print('Global optimality is NOT proved.')
if __name__=='__main__':main()
