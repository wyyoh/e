from pathlib import Path
import sys,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'));sys.path.insert(0,str(ROOT/'code_v4'))
from precompute import load,dump
from pool_master import solve
p=load(ROOT/'experiments_v4/path_pool/pool.json');ref=load(ROOT/'release_final/primary/selected.json')
s,st=solve(p['routes'],p['sites'],p['profiles'],ROOT/'experiments_v4/energy_tie',seconds=75,upper=ref['makespan_s']+1e-6,slack=30,reference=ref,objective='energy')
