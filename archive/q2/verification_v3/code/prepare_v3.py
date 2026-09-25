"""Reuse the parent's immutable data snapshot; no new raw-data definitions."""
from pathlib import Path
import base64,zipfile,json,hashlib,subprocess,sys,shutil
ROOT=Path(__file__).resolve().parents[1]
def main():
 data=ROOT/'data';data.mkdir(exist_ok=True);(ROOT/'results').mkdir(exist_ok=True);(ROOT/'logs').mkdir(exist_ok=True)
 if not all((data/(n+'.json')).exists() for n in ['boxes','types','nodes','legs']):
  parent=ROOT.parent;parts=sorted((parent/'data/encoded').glob('*.b64'))
  if not parts:raise RuntimeError('Missing bundled normalized data and parent canonical snapshot')
  packed=base64.b64decode(''.join(p.read_text().strip() for p in parts),validate=True)
  archive=parent/'data/canonical_inputs.zip';archive.write_bytes(packed)
  with zipfile.ZipFile(archive) as z:
   for name in z.namelist():
    target=(parent/'data'/name).resolve()
    if not target.is_relative_to((parent/'data').resolve()):raise RuntimeError('unsafe archive path')
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(name))
  manifest=json.loads((parent/'manifest.json').read_text())
  for fn,want in manifest['fixed_inputs_sha256'].items():
   if hashlib.sha256((parent/fn).read_bytes()).hexdigest()!=want:raise RuntimeError('source hash mismatch: '+fn)
  subprocess.run([sys.executable,str(parent/'src/prepare_data.py')],check=True)
  for n in ['boxes','types','nodes','legs']:shutil.copy2(parent/'data'/f'{n}.json',data/f'{n}.json')
 csvpath=data/'remote_v2_incumbent.csv'
 if not csvpath.exists():shutil.copy2(ROOT.parent/'verification_v2/selected_incumbent.csv',csvpath)
 raw=csvpath.read_bytes();assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()=='0afb0cf4f8108cea601cb5831b64610c895e422e'
 subprocess.run([sys.executable,str(ROOT/'code/verify_incumbent.py')],check=True)
 metrics=json.loads((ROOT/'results/independent_csv/metrics.json').read_text());assert abs(metrics['makespan_s']-5693.231489105106)<1e-6 and metrics['failed']==0 and metrics['late_boxes']==0
 # Minimal seed fields only; these are not trusted physical metrics for pricing.
 seeds=ROOT/'results/remote_incumbent_rebuilt';seeds.mkdir(exist_ok=True)
 for n in ['flights','metrics']:
  if not (seeds/f'{n}.json').exists():shutil.copy2(ROOT/'results/independent_csv'/f'{n}.json',seeds/f'{n}.json')
 print('v3 immutable CSV and all 80 deliveries verified')
if __name__=='__main__':main()
