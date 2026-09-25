"""Assemble an isolated new work tree; never overwrite an existing destination."""
from pathlib import Path
import argparse,zipfile,stat,shutil,json,hashlib
from verify_delivery import verify
ROOT=Path(__file__).resolve().parent

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();dest=Path(a.out).resolve()
 if dest.exists():raise FileExistsError(f'Output must be a new directory: {dest}')
 verify();dest.mkdir(parents=True)
 with zipfile.ZipFile(ROOT/'upstream/Q3-FINAL-V1.zip') as z:
  for info in z.infolist():
   target=(dest/info.filename).resolve()
   if not target.is_relative_to(dest):raise ValueError('Unsafe archive path')
   if stat.S_ISLNK(info.external_attr>>16):raise ValueError('Symlinks are not supported')
  z.extractall(dest)
 q3=dest/'problems/D/q3'
 if not (q3/'code/run_v3.py').is_file():raise ValueError('Upstream archive layout does not match')
 for folder in ['code_v4','tests_v4','experiments_v4']:shutil.copytree(ROOT/'overlay'/folder,q3/folder)
 manifest=json.loads((ROOT/'acceptance/frozen_input_integrity.json').read_text(encoding='utf-8'))
 for item in manifest['files']:
  p=dest/item['path']
  if hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:raise ValueError(('Frozen file changed',item['path']))
 print(f'Assembled isolated workspace: {q3}');print('No optimization was started. Frozen Q3 source bytes are unchanged.')
if __name__=='__main__':main()
