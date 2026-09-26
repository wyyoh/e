"""Checks saved numerical evidence; does not substitute for executing solvers."""
from pathlib import Path
import json,math,unittest
R=Path(__file__).resolve().parent/'results'
def load(n):return json.loads((R/n).read_text())
class Evidence(unittest.TestCase):
 def test_q1_baseline_and_exact_grid(self):
  r=load('q1_reoptimization.json');self.assertEqual(len(r),24)
  b=next(x for x in r if x['experiment']=='reserve' and x['alpha']==.2)
  self.assertEqual(b['sorties'],18);self.assertAlmostEqual(b['energy_kwh'],59.13129602205317,places=8)
  self.assertAlmostEqual(b['sum_work_min'],546.2669291485934,places=8)
  self.assertEqual(b['count_patterns_energy_feasible'],732)
  self.assertFalse(next(x for x in r if x['experiment']=='reserve' and x['alpha']==.353)['feasible'])
 def test_q2_nominal(self):
  q=load('q2_baseline_replay.json');self.assertEqual(q['boxes_verified'],80);self.assertEqual(q['flights_verified'],23)
  self.assertTrue(q['result']['zero_tardiness_feasible']);self.assertEqual(q['result']['resource_conflicts'],0)
  self.assertAlmostEqual(q['result']['makespan_s'],5693.231489105106)
 def test_q2_fixed_and_repair(self):
  x=load('q2_perturbations.json');self.assertEqual(len(x),262)
  for beta in [1.1,1.2,1.3]:
   a=next(r for r in x if r['experiment']=='charging' and r['charging_factor']==beta and r['adjustment_mode']=='fixed_calendar');b=next(r for r in x if r['experiment']=='charging' and r['charging_factor']==beta and r['adjustment_mode']=='right_shift_repair')
   self.assertFalse(a['zero_tardiness_feasible']);self.assertTrue(b['zero_tardiness_feasible'])
  for d in [15,30,60,120]:
   for mode,n in [('fixed_calendar',9),('right_shift_repair',23)]:
    rr=[r for r in x if r['experiment']=='single_first_handover_delay' and r['delay_s']==d and r['adjustment_mode']==mode]
    self.assertEqual(len(rr),23);self.assertEqual(sum(r['zero_tardiness_feasible'] for r in rr),n)
 def test_twenty_independent_searches(self):
  rows=load('q2_seed_summary.json');self.assertEqual(len(rows),20)
  self.assertEqual({r['seed'] for r in rows},set(range(1,21)))
  for r in rows:self.assertTrue(r['zero_tardy']);self.assertEqual(r['validation_failed'],0);self.assertEqual(r['iterations'],150)
 def test_energy_reoptimization_witnesses(self):
  for factor in [1.01,1.02]:
   x=load(f'q2_search/energy_factor_{factor:.2f}/independent_perturbed_replay.json');self.assertTrue(x['metrics']['zero_tardiness_feasible']);self.assertEqual(x['metrics']['energy_violations'],0)
 def test_continuous_radio_grid(self):
  x=load('q3_loss_grid.json');self.assertEqual(len(x),12)
  for r in x:self.assertEqual(r['feasible'],r['role']=='robust025' or r['extra_loss_db']==0)
  d=load('q3_delay_grid.json');self.assertEqual(len(d),24)
  for r in d:self.assertEqual(r['feasible'],all(float(v)==0 for v in r['delays_s'].values()))
 def test_all_twelve_recovery_plans(self):
  x=load('q3_repair_summary.json');self.assertEqual(len(x),12)
  for r in x:self.assertTrue(r['validation_pass']);self.assertEqual(r['validation_failed'],0);self.assertEqual(r['point_failures'],0);self.assertGreaterEqual(r['min_hard_slack_s'],0)
 def test_q4_all_resource_certificates(self):
  rows=load('q4_all_candidates.json');self.assertEqual(len(rows),4)
  counts=[0]
  def recurse(x):
   if isinstance(x,dict):
    if 'matching_minimum' in x:
     self.assertEqual(x['minimum'],x['matching_minimum']);self.assertEqual(len(x['resource_chains']),x['minimum']);counts[0]+=1
    for v in x.values():recurse(v)
   elif isinstance(x,list):
    for v in x:recurse(v)
  recurse(rows);self.assertGreater(counts[0],0)
 def test_q4_dominance(self):
  x=load('q4_componentwise_dominance.json');self.assertTrue(x['dominates_all_two_group_partitions'])
  for o in x['others']:self.assertTrue(all(a<=b for a,b in zip(x['selected'],o)));self.assertLess(sum(x['selected']),sum(o))
if __name__=='__main__':unittest.main(verbosity=2)
