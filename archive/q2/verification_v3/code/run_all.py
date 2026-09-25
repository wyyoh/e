"""Rebuild/check a proof experiment. Never labels unfinished original IP optimal."""
from pathlib import Path
import subprocess,sys,argparse,json,os
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--solve',action='store_true');p.add_argument('--nodes',type=int,default=500);a=p.parse_args()
 env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'}
 def run(name,*args):
  (ROOT/'logs').mkdir(exist_ok=True)
  with (ROOT/'logs'/('rebuild_'+name+'.log')).open('w') as f:subprocess.run([sys.executable,str(ROOT/'code'/name),*args],stdout=f,stderr=subprocess.STDOUT,check=True,env=env)
 run('prepare_v3.py')
 if a.solve:
  run('walk_cg.py','--seconds','300');run('branch_price.py','--seconds','600','--nodes',str(a.nodes))
 required=['bp_all/tree.json','walk_q0.001_certificate.json']
 if not all((ROOT/'results'/n).exists() for n in required):raise RuntimeError('No saved certificates: run with --solve or use the supplied evidence archive')
 run('audit_core.py')
 aud=json.loads((ROOT/'results/audit_core.json').read_text());m=json.loads((ROOT/'results/independent_csv/metrics.json').read_text());lb=aud['tree']['published_lower_bound_s'];ub=m['makespan_s']
 assert aud['failures']==0 and lb<=ub
 s={'version':'Q2-PROOF-UNIFIED-V3','verified_lower_bound_s':lb,'verified_upper_bound_s':ub,'gap_over_upper_bound':(ub-lb)/ub,'sorties':m['sorties'],'energy_kwh':m['energy_kwh'],'weighted_tardiness_optimum':0,'makespan_global_optimality_proven':False,'full_lexicographic_global_optimality_proven':False,'scope':'integer count/allocation branching of an optimistic route-energy relaxation; no complete original scheduling proof'}
 (ROOT/'results/status.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n');print(json.dumps(s,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
