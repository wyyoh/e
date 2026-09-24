"""Verify selected plan; optional full-domain proof repricing. No implicit search."""
from pathlib import Path
import json,sys,subprocess,argparse,csv
from bootstrap import main as bootstrap
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--proof',action='store_true');a=ap.parse_args();inputs=bootstrap()
 from core import from_decisions
 from export_solution import produce
 from verify_solution import run
 from negative_tests import tests
 from verify_csv import run as direct
 selected=[{'type':r['type'],'boxes':r['box_ids'].split('|'),'route':r['route'].split('|')[1:-1]} for r in csv.DictReader((ROOT/'inputs/selected_incumbent.csv').open())]
 metrics=produce(from_decisions(selected),ROOT/'results/selected','Q2-ASSIST-V5')
 result=run(ROOT/'results/selected');assert result['failed']==0 and metrics['weighted_tardiness_s']<1e-7
 independent=direct()
 for key in ['makespan_s','energy_kwh','sorties','last_delivery_s','min_hard_slack_s','min_return_soc']:
  assert abs(metrics[key]-independent[key])<1e-7,(key,metrics[key],independent[key])
 neg=tests(ROOT/'results/selected');assert all(n['detected'] for n in neg)
 (ROOT/'results/negative_tests.json').write_text(json.dumps(neg,ensure_ascii=False,indent=2)+'\n')
 report={'input':inputs,'checks':result['checks'],'independent_csv_checks':independent['checks'],'negative_tests':len(neg),'failures':0,'metrics':metrics,'proof_repriced':False}
 if a.proof:
  subprocess.run([sys.executable,str(ROOT/'proof/code/audit_bound.py')],check=True)
  report['proof_repriced']=True
 (ROOT/'results/rebuild_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
