"""Permit repeated relay sorties at the same site without changing inventory.
Number of physical relay aircraft is still TWO, energy components at most SIX.
"""
from pathlib import Path
import sys,copy,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'));sys.path.insert(0,str(ROOT/'code_v4'))
from precompute import load,dump
from pool_master import solve
ap=argparse.ArgumentParser();ap.add_argument('--max-relays',type=int,default=5);ap.add_argument('--seconds',type=float,default=90);a=ap.parse_args()
p=load(ROOT/'experiments_v4/path_pool/pool.json');ref=load(ROOT/'release_final/primary/selected.json');sites=p['sites']+copy.deepcopy(p['sites']);profiles=[[{**d,'allowed':d['allowed']+[j+4 for j in d['allowed']]} for d in row] for row in p['profiles']];out=ROOT/f'experiments_v4/repeated_{a.max_relays}';dump(out/'pool.json',{'routes':p['routes'],'sites':sites,'profiles':profiles,'continuous_profiles':True,'max_sorties':a.max_relays});s,st=solve(p['routes'],sites,profiles,out/'master',seconds=a.seconds,upper=6341,slack=30,max_relays=a.max_relays,reference=ref)
