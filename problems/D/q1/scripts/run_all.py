"""One command rebuild. Regression numbers are read only after all computation."""
import argparse
import importlib.metadata
import platform
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from model.io import ROOT,write_json
from scripts.prepare import prepare
from scripts.payload import payloads
from scripts.optimize import optimize
from scripts.analyze import analyze
from scripts.crosscheck import crosscheck
from scripts.validate import validate
from scripts.figures import figures


def run(out,figure_dir,full_box=False):
    out=Path(out);start=time.perf_counter()
    print('1/7 Raw attachments and complete projected DEM traversal',flush=True)
    nodes,types,boxes,dem,geo=prepare(out)
    print('2/7 Continuous safe-payload roots',flush=True)
    payloads(types,geo,out)
    print('3/7 Independent MILP / DP and two FFD orders',flush=True)
    optimize(types,boxes,geo,out,full_box=full_box)
    print('4/7 Complete Pareto and reserve events',flush=True)
    analyze(types,boxes,geo,out)
    crosscheck(nodes,types,boxes,geo,out)
    print('5/7 Independent raw-input validation',flush=True)
    validate(out)
    print('6/7 Five figures',flush=True)
    figures(out,figure_dir)
    environment=dict(python=sys.version,platform=platform.platform(),
                     dependencies={p:importlib.metadata.version(p) for p in
                                   ['numpy','scipy','openpyxl','tifffile','geographiclib','pyproj','matplotlib','pytest']},
                     full_box_milp_recomputed=full_box,runtime_s=time.perf_counter()-start)
    write_json(out/'environment.json',environment)
    print('7/7 Regression only after independent solution and validation',flush=True)
    from scripts.regression import regression
    regression(out)
    print(f'Complete: {out} ({time.perf_counter()-start:.1f} s)',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'results')
    parser.add_argument('--figures',type=Path,default=ROOT/'figures')
    parser.add_argument('--full-box-milp',action='store_true')
    args=parser.parse_args();run(args.output,args.figures,args.full_box_milp)
