import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from model.io import ROOT,write_csv
from model.physics import safe_payload,bisection_payload
from scripts.prepare import prepare


def payloads(types,geo,out,alpha=.2):
    rows=[]
    for s,g in geo.items():
        for m in types.values():
            row=safe_payload(m,g,alpha)
            independent=bisection_payload(m,g,alpha)
            if row['safe_payload_kg'] is None:
                assert independent is None
            else:
                assert abs(row['safe_payload_kg']-independent)<1e-8
            rows.append(row)
    write_csv(out/'max_safe_payload.csv',rows)
    return rows


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'results')
    args=parser.parse_args()
    _,types,_,_,geo=prepare(args.output)
    payloads(types,geo,args.output)
    print('45 payloads checked by Brent and bisection.')
