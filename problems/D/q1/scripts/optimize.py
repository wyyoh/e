"""Run complete patterns, independent MILP/DP and FFD; never read old answers."""
import argparse
import sys
import math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from model.io import ROOT,write_json,write_csv
from model.physics import ENERGY_TOL,TIME_TOL
from scripts.prepare import prepare
from scripts.payload import payloads
from solver.patterns import group_boxes,enumerate_patterns,available,assign_ids
from solver.dp import Label,scalar_dp
from solver.milp import solve_area,box_patterns,SolverFailure
from solver.baseline import compare


def optimize(types,boxes,geo,out,alpha=.2,full_box=False):
    groups=group_boxes(boxes)
    patterns=enumerate_patterns(groups,types,geo)
    lookup={p.id:p for ps in patterns.values() for p in ps}
    write_csv(out/'all_capacity_patterns.csv',
              (p.record(groups[s][1],alpha) for s,ps in patterns.items() for p in ps))
    write_csv(out/'candidate_patterns.csv',
              (p.record(groups[s][1],alpha) for s,ps in patterns.items() for p in available(ps,alpha)))
    def binary_records():
        for s,data in groups.items():
            local=data[0]
            for p in box_patterns(local,types,geo[s],alpha):
                selected=[local[j] for j in p['indices']]
                yield dict(pattern_id=f'{s}-{p["aircraft"]}-mask-{p["mask"]}',service_area=s,
                           aircraft_type=p['aircraft'],covered_boxes=[b.id for b in selected],
                           mass_kg=math.fsum(b.mass_kg for b in selected),volume_m3=math.fsum(b.volume_m3 for b in selected),
                           energy_kwh=p['energy'],time_s=p['time'])
    write_csv(out/'candidate_box_patterns.csv',binary_records())
    combined=Label();checks=[]
    for area,(_,_,_,demand) in groups.items():
        feasible=available(patterns[area],alpha)
        best=scalar_dp(demand,feasible)
        best_time=scalar_dp(demand,feasible,'time')
        if best is None:raise ValueError(f'Baseline infeasible at {area}')
        try:logs=solve_area(groups[area][0],types,geo[area],alpha)
        except SolverFailure as failure:
            write_json(out/'solver_logs'/f'{area}.json',failure.logs)
            raise
        write_json(out/'solver_logs'/f'{area}.json',logs)
        if full_box:
            try:original_logs=solve_area(groups[area][0],types,geo[area],alpha,box_level=True)
            except SolverFailure as failure:
                write_json(out/'solver_logs/full_box'/f'{area}.json',failure.logs)
                raise
            write_json(out/'solver_logs/full_box'/f'{area}.json',original_logs)
        checks.append(dict(service_area=area,dp_min_N=best.n,milp_min_N=logs[0]['n'],
                           dp_fixed_N_min_E=best.e,milp_fixed_N_min_E=logs[1]['e'],
                           dp_lex_time_s=best.t,milp_lex_time_s=logs[2]['t'],
                           dp_min_T_s=best_time.t,milp_min_T_s=logs[3]['t']))
        assert best.n==logs[0]['n']
        assert abs(best.e-logs[1]['e'])<=ENERGY_TOL
        assert abs(best.t-logs[2]['t'])<=TIME_TOL
        assert abs(best_time.t-logs[3]['t'])<=TIME_TOL
        combined=combined.combine(best)
        print(f'{area}: count patterns={len(feasible)}, binary box patterns={logs[0]["variables"]}; MILP/DP agree.',flush=True)
    write_csv(out/'milp_dp_crosscheck.csv',checks)
    batches=assign_ids(combined,lookup,groups)
    write_csv(out/'optimal_batches.csv',batches)
    by_id={b.id:b for b in boxes}
    assignment=[dict(box_id=bid,batch_id=p['batch_id'],service_area=by_id[bid].area,
                     aircraft_type=p['aircraft_type'],mass_kg=by_id[bid].mass_kg,
                     volume_m3=by_id[bid].volume_m3) for p in batches for bid in p['box_ids']]
    write_csv(out/'box_assignment.csv',sorted(assignment,key=lambda b:b['box_id']))
    baseline,totals=compare(groups,patterns,types,geo,alpha)
    write_csv(out/'baseline_by_area.csv',baseline);write_csv(out/'baseline_summary.csv',totals)
    summary=dict(reserve=alpha,objective_order=['sorties','energy_kwh','cumulative_time_s'],
                 lexicographic=combined.record(),independent_MILP_DP_agree=True,
                 energy_tol_kwh=ENERGY_TOL,time_tol_s=TIME_TOL,
                 count_patterns_capacity=sum(map(len,patterns.values())),
                 count_patterns_feasible=sum(len(available(ps,alpha)) for ps in patterns.values()),
                 boxes=len(boxes),baseline=totals)
    write_json(out/'objective_summary.json',summary)
    return groups,patterns,summary


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'results')
    parser.add_argument('--full-box-milp',action='store_true')
    args=parser.parse_args()
    _,types,boxes,_,geo=prepare(args.output)
    payloads(types,geo,args.output)
    optimize(types,boxes,geo,args.output,full_box=args.full_box_milp)
