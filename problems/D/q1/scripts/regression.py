"""External regression targets, separated from all model/solver code."""
import json
from pathlib import Path
from model.io import ROOT,write_json
from scripts.validate import read_csv


def regression(out):
    out=Path(out)
    target=json.loads((ROOT/'tests/regression_targets.json').read_text(encoding='utf-8'))
    actual=read_csv(out/'pareto_front.csv')
    matches=[]
    for expected in target['vectors']:
        observed=next((r for r in actual if int(r['sorties'])==expected['sorties']),None)
        ediff=float(observed['energy_kwh'])-expected['energy_kwh'] if observed else None
        tdiff=float(observed['time_min'])-expected['time_min'] if observed else None
        matches.append(dict(target=expected,energy_difference_kwh=ediff,time_difference_min=tdiff,
                            matches=observed is not None and abs(ediff)<=target['rounded_energy_tolerance_kwh']
                            and abs(tdiff)<=target['rounded_time_tolerance_min']))
    passed=len(actual)==len(target['vectors']) and all(m['matches'] for m in matches)
    report=dict(status='MATCH' if passed else 'REGRESSION_MISMATCH',comparisons=matches,
                note='Regression of rounded published targets only, not an optimality proof; not consumed by solver.')
    write_json(out/'regression_report.json',report)
    if not passed:
        text='''# REGRESSION_MISMATCH

Independent recomputation differs from the historical rounded targets. Do not change raw input or formulas to fit them.

- Raw inputs: compare data/raw_manifest.json and results/input_manifest.json; historical raw hashes were not supplied.
- DEM: inspect geometry.json, traversed_cells.json and geometry_validation.csv; historical cell sets were not supplied.
- Energy: confirmed 3/2 range and two climbs; inspect max_safe_payload.csv and independent validation_report.json.
- Batching: compare optimal_batches.csv, box_assignment.csv and pareto_assignments.json; historical assignments were not supplied.
- Solver: inspect fresh solver_logs and milp_dp_crosscheck.csv for status, bound, gap and objective agreement.

Numerical differences:
'''+json.dumps(report,ensure_ascii=False,indent=2)+'\n'
        (out/'REGRESSION_MISMATCH.md').write_text(text,encoding='utf-8')
        raise AssertionError('Historical regression mismatch; audit file written without fitting results')
    return report
