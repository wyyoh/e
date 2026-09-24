"""Compute complete Pareto front and all reserve events from raw inputs."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from model.io import ROOT,write_json,write_csv
from scripts.prepare import prepare
from solver.patterns import group_boxes,enumerate_patterns,assign_ids
from solver.sensitivity import reserve_analysis,pareto_analysis


def analyze(types,boxes,geo,out):
    groups=group_boxes(boxes);patterns=enumerate_patterns(groups,types,geo)
    front=pareto_analysis(groups,patterns,out)
    lookup={p.id:p for ps in patterns.values() for p in ps}
    write_json(out/'pareto_assignments.json',
               [dict(objective=l.record(),batches=assign_ids(l,lookup,groups)) for l in front])
    print(f'Complete Pareto objective vectors: {len(front)}',flush=True)
    sensitivity=reserve_analysis(groups,patterns,types,geo,out)
    write_json(out/'sensitivity_summary.json',sensitivity)
    print(f'Reserve events: {sensitivity["candidate_events"]}; sortie transitions: {sensitivity["sortie_change_events"]}',flush=True)
    return front,sensitivity


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'results')
    args=parser.parse_args()
    _,types,boxes,_,geo=prepare(args.output)
    analyze(types,boxes,geo,args.output)
