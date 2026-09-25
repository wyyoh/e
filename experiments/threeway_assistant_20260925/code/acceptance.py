"""Independent experiment acceptance and guard tests (not optimization)."""
from pathlib import Path
import json,hashlib,itertools,zipfile,argparse,sys,unittest,tempfile,io,copy
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text())
def review(root):
 R=root/'results';m=load(R/'pricing_micro.json');b=load(R/'pricing_benchmark.json');p=load(R/'pricing_summary.json');a=load(R/'full_accelerated_certificate_audit.json')
 assert len(m['records'])==72 and m['failures']==0
 for x in m['records']:assert x['baseline']['minimum_rc']==x['accelerated']['minimum_rc']==x['brute_min_rc']
 assert len(b['records'])==24
 for x in b['records']:
  assert hashlib.sha256((root/x['path']).read_bytes()).hexdigest()==x['input_sha256']
  for mode in ['baseline','accelerated']:
   assert len(x['runs'][mode])==3
   assert all(r['minimum_rc']==x['original_rc'] for r in x['runs'][mode])
 assert a['verified_lower_bound_s']==5433.956428 and a['failures']==0
 assert a['covering_certificates']==810 and a['complete_pricing_calls']==2430
 c=load(R/'resource_chain_records.json');counts={'Optimal':0,'Time limit reached':0};replays=[]
 for i,r in enumerate(c):
  counts[r['solver']['status']]+=1
  if 'replay' in r:checks=r['replay']
  else:
   n=i//2;checks=load(R/f'chains/{n}_{r["model"]}/replay_checks.json')
  assert len(checks)==3712 and all(x['pass'] for x in checks)
  assert abs(r['metrics']['makespan_s']-5693.231489105106)<1e-7
  assert not r['accepted_time_improvement'];replays.append(len(checks))
 assert len(c)==6
 for i in range(0,6,2):assert c[i]['option_counts']==c[i+1]['option_counts']
 q=load(R/'q3_sampling_records.json');assert len(q)==15
 for x in q:assert len(x['history'])==x['rf_evaluations']==192
 for s in range(92550,92555):
  x=next(r for r in q if r['seed']==s and r['method']=='uniform');y=next(r for r in q if r['seed']==s and r['method']=='feasible');assert x['history']==y['history']
 scores=load(R/'q3_score_scope_audit.json')
 for s in scores['rows']:assert abs(s['critical_point_score_db']-s['all_sample_points_score_db'])<1e-10
 f=load(R/'q3_schedule_followup.json');assert len(f)==2
 assert all(x['solver']['status']==2 and x['status']=='no_witness' for x in f)
 z=load(R/'q3_positive_control.json');assert z['validation']=='PASS' and z['same_transport_decisions_as_main_time']
 assert abs(z['metrics']['joint_makespan_s']-6369.026365292443)<1e-7
 return {'pricing_micro_instances':24,'pricing_micro_kernel_comparisons':72,'fixed_real_pricing_inputs':24,'full_cover_certificates':810,'full_cover_pricing_calls':2430,'chain_solver_status_counts':counts,'chain_full_replay_checks_per_plan':replays,'q3_arms':3,'q3_paired_seeds':5,'q3_total_rf_candidates':2880,'q3_scope_audit_points':scores['all_sample_points'],'q3_new_accepted_plans':0,'q3_known_positive_control':'PASS','formal_Q2_Q3_results_replaced':False,'failures':0}
class Guards(unittest.TestCase):
 def test_parity_compensation(self):
  # All three-cut parity/mask patterns and extension counts 0..3; an absent
  # live bit cannot have an odd extension. Nonnegative representative penalties.
  pen=[0,3,7];n=0
  for A,B,L in itertools.product(range(8),repeat=3):
   bound=sum(pen[k] for k in range(3) if A>>k&1 and not B>>k&1 and L>>k&1)
   for ext in itertools.product(range(4),repeat=3):
    if any(ext[k]%2 and not (L>>k&1) for k in range(3)):continue
    diff=sum(pen[k]*((((A>>k)&1)+ext[k])//2-(((B>>k)&1)+ext[k])//2) for k in range(3))
    self.assertLessEqual(diff,bound);n+=1
  self.assertGreater(n,1000)
 def test_uncompensated_parity_can_fail(self):
  # A=odd, B=even, odd continuation incurs a real penalty for A.
  self.assertGreater(7*((1+1)//2-(0+1)//2),0)
 def test_wrong_archive_rejected(self):
  from run_all import unpack
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a.zip';p.write_bytes(b'not-a-valid-source')
   with self.assertRaises(ValueError):unpack(p,Path(d)/'out','0'*64)
 def test_path_escape_rejected(self):
  from run_all import unpack
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a.zip'
   with zipfile.ZipFile(p,'w') as z:z.writestr('../escape','bad')
   with self.assertRaises(ValueError):unpack(p,Path(d)/'out',hashlib.sha256(p.read_bytes()).hexdigest())
 def test_bound_not_improvement(self):
  a=load(ROOT/'results/full_accelerated_certificate_audit.json');self.assertEqual(a['verified_lower_bound_s'],5433.956428);self.assertFalse(a['global_original_optimality_proven'])
 def test_pinned_main_identity(self):
  self.assertEqual(load(ROOT/'inputs/baseline_lock.json')['main_sha'],'c3ae26996c0e71cda066533b7ec33e9e142e3b9a')
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=ROOT);a=ap.parse_args();summary=review(a.root)
 tests=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Guards));assert tests.wasSuccessful()
 summary['additional_guard_tests']=tests.testsRun;(a.root/'results/acceptance.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary,ensure_ascii=False))
