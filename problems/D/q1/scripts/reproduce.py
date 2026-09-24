"""Clean output reconstruction with byte comparison of deterministic artifacts."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from model.io import ROOT,write_json

FILES=[
    'input_manifest.json','geometry.csv','geometry.json','traversed_cells.json','geometry_validation.csv',
    'max_safe_payload.csv','all_capacity_patterns.csv','candidate_patterns.csv','candidate_box_patterns.csv',
    'optimal_batches.csv','box_assignment.csv','objective_summary.json','milp_dp_crosscheck.csv',
    'baseline_by_area.csv','baseline_summary.csv','pareto_front.csv','pareto_local.csv','pareto_assignments.json',
    'reserve_payload_grid.csv','reserve_thresholds.csv','reserve_segments.csv','reserve_optimal_segments.csv',
    'sensitivity_summary.json','distance_crosscheck.json','distance_payload_crosscheck.csv',
    'pareto_integer_audit.json','regression_report.json']


def reproduce():
    destination=ROOT/'results_reproduce'
    if destination.exists():
        raise RuntimeError('Reproduction destination already exists; choose a new directory with --output (no automatic deletion)')
    return reproduce_to(destination)


def reproduce_to(destination):
    destination=Path(destination)
    if destination.exists():raise RuntimeError('Use a new empty reproduction directory')
    subprocess.run([sys.executable,str(ROOT/'scripts/run_all.py'),'--output',str(destination),
                    '--figures',str(destination/'figures')],check=True,cwd=ROOT)
    rows=[]
    for name in FILES:
        baseline=(ROOT/'results'/name).read_bytes();fresh=(destination/name).read_bytes()
        rows.append(dict(file=name,sha256=hashlib.sha256(fresh).hexdigest(),byte_identical=baseline==fresh))
    plots=[]
    for path in sorted((ROOT/'figures').glob('*.png')):
        fresh=(destination/'figures'/path.name).read_bytes()
        plots.append(dict(file=path.name,sha256=hashlib.sha256(fresh).hexdigest(),byte_identical=path.read_bytes()==fresh))
    base=json.loads((ROOT/'results/validation_report.json').read_text(encoding='utf-8'))
    fresh=json.loads((destination/'validation_report.json').read_text(encoding='utf-8'))
    same_independent_objective=base['objective']==fresh['objective']
    report=dict(status='REPRODUCIBLE' if all(r['byte_identical'] for r in rows+plots) and same_independent_objective else 'MISMATCH',
                numeric_files=rows,figures=plots,independent_objective_identical=same_independent_objective,
                excluded=['environment.json (runtime)','solver_logs (runtime and interchangeable box choices)',
                          'validation_report.json full-box historical evidence count (main objectives compared separately)'])
    write_json(ROOT/'results/reproducibility_report.json',report)
    if report['status']!='REPRODUCIBLE':raise AssertionError('Reproduction differences; inspect report')
    print('All deterministic numerical files and five figures are byte-identical.')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    reproduce_to(args.output) if args.output else reproduce()
