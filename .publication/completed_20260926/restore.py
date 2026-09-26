#!/usr/bin/env python3
"""Restore the exact 119 completed source/data files from a checked transport frame.
The old checkpoint is a compression dictionary, never the manuscript to publish.
"""
from pathlib import Path
import argparse,base64,ctypes,ctypes.util,hashlib,io,json,shutil,zipfile

def sha(x): return hashlib.sha256(x).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--checkpoint',required=True);ap.add_argument('--root',default='paper/latex');args=ap.parse_args()
 cp=Path(args.checkpoint).resolve();root=Path(args.root).resolve();here=Path(__file__).resolve().parent
 pieces=[p.read_bytes() for p in sorted(cp.rglob('*')) if p.is_file() and p.suffix in ('.tex','.py','.cls','.bib','.md')]
 archive=base64.b64decode(''.join(p.read_text() for p in sorted((cp/'figure_inputs').glob('part_*.b64'))))
 assert sha(archive)=='ef4e5ec177362b4b8f5367cb5f6c096384d849dc46e700a78879fcf6925962b1'
 with zipfile.ZipFile(io.BytesIO(archive)) as z:
  for name in sorted(z.namelist()):
   if not name.endswith('/'): pieces.append(z.read(name))
 dictionary=b'\n'.join(pieces)
 assert len(dictionary)==899500 and sha(dictionary)=='f0679bfdb127db3d1fff21feb70f08254644784e2efdd416ccb3d0c88343dfcc'
 frame=b''.join(p.read_bytes() for p in sorted(here.glob('*.zstpart')))
 assert len(frame)==101296 and sha(frame)=='8be8a00b79e8f37bf3b5ccadae099783eb01d6a28d580a9e25d973fb9c29ea26',sha(frame)
 lib=ctypes.CDLL(ctypes.util.find_library('zstd') or 'libzstd.so.1')
 lib.ZSTD_createDCtx.restype=ctypes.c_void_p
 lib.ZSTD_decompress_usingDict.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t]
 lib.ZSTD_decompress_usingDict.restype=ctypes.c_size_t
 lib.ZSTD_freeDCtx.argtypes=[ctypes.c_void_p]
 ctx=lib.ZSTD_createDCtx();dest=ctypes.create_string_buffer(807301)
 try: size=lib.ZSTD_decompress_usingDict(ctx,dest,len(dest),frame,len(frame),dictionary,len(dictionary))
 finally: lib.ZSTD_freeDCtx(ctx)
 assert size==807301,size
 raw=dest.raw[:size]
 assert sha(raw)=='b6adbbca6f4ce26723f5eee4719c130b571640589205dab19cfe2050c6524710'
 files=json.loads(raw);assert len(files)==119
 root.mkdir(parents=True,exist_ok=True)
 for name,text in files.items():
  p=(root/name).resolve();assert p.is_relative_to(root) and isinstance(text,str)
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(text.encode('utf-8'))
 # Restore existing, hash-locked figure inputs without recomputing any optimizer.
 shutil.copytree(cp/'figure_inputs',root/'figure_inputs',dirs_exist_ok=True)
 meta={'sha256':sha(archive),'encoding':'concatenate part_*.b64, base64 decode, ZIP-LZMA','size_bytes':len(archive),'parts':4,'files':['terrain_display.csv','paper_data.json','terrain_metadata.json']}
 (root/'figure_inputs/manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
 with zipfile.ZipFile(io.BytesIO(archive)) as z:
  for name in z.namelist():
   if name.endswith('/'): continue
   p=(root/name).resolve();assert p.is_relative_to(root)
   p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
 # Retire only obsolete loader tests; the completed manuscript uses explicit chapters.
 oldtest=root/'tests'
 for p in oldtest.glob('test_*.py'):
  if str(p.relative_to(root)) not in files:
   target=root.parent/'archive/pre_completed_20260926/tests'/p.name
   target.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(p),str(target))
 identity={'source_zip_sha256':'81732467b938701d58c362c27bf450fa141e197f4ab6f2ce68ff638a25c8f5d0','local_review_pdf_sha256':'1961e39deab739dcbb5745a1a4f5d80702d9f419d4e0be2f4bbf260297d67de2','local_review_pages':92,'body_pages':72,'text_payload_sha256':sha(raw),'source_files':{n:sha(t.encode('utf-8')) for n,t in files.items()},'formal_result_lock_blob':'31b72d19ac8d72e173af8f576df78f8538546153','optimizers_rerun':False}
 out=root.parent/'review';out.mkdir(exist_ok=True)
 (out/'completed_source_identity_20260926.json').write_text(json.dumps(identity,ensure_ascii=False,indent=2)+'\n')
 print('Restored exact completed source/data files:',len(files))
 print('Authenticated payload SHA-256:',sha(raw))
if __name__=='__main__':main()
