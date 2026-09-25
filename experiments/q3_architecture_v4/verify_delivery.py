"""Check the complete delivered file set without starting optimization."""
from pathlib import Path
import json,hashlib,zipfile
ROOT=Path(__file__).resolve().parent

def verify():
 manifest=json.loads((ROOT/'MANIFEST.sha256.json').read_text(encoding='utf-8'));failures=[]
 for name,expected in manifest['files'].items():
  path=ROOT/name
  if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:failures.append(name)
 if failures:raise ValueError({'file_integrity_failed':failures})
 archive=ROOT/'upstream/Q3-FINAL-V1.zip'
 if hashlib.sha256(archive.read_bytes()).hexdigest()!='97f5ea8018a557d604bee87d6886675ecf7648f035e8df0f47f20ff6e7fbc56b':raise ValueError('Wrong upstream archive')
 with zipfile.ZipFile(archive) as z:
  bad=z.testzip()
  if bad:raise ValueError(('Upstream CRC',bad))
 result={'files_checked':len(manifest['files']),'failures':0,'upstream_crc':'PASS','optimization_performed':False};print(json.dumps(result,ensure_ascii=False,indent=2));return result
if __name__=='__main__':verify()
