"""Read-only originals and unpatched independent physics+radio verifier."""
from pathlib import Path
import sys,json,argparse,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'))
from verify_v2 import verify_v2
ap=argparse.ArgumentParser();ap.add_argument('--plan',required=True);ap.add_argument('--step',type=float,default=1);a=ap.parse_args()
t=time.monotonic();r=verify_v2(a.plan,step=a.step,intervals=True);print(json.dumps({**r,'elapsed_s':time.monotonic()-t},ensure_ascii=False),flush=True)
if r['failed'] or r['point_failures']:sys.exit(1)
