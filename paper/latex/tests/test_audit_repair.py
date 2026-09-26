from pathlib import Path
from collections import Counter,defaultdict
import json,re,hashlib,unittest
P=Path(__file__).resolve().parents[1];A=P/'audit_inputs';D=P/'figdata/audit_repair'
def read(p):return json.loads(p.read_text())
class AuditRepairChecks(unittest.TestCase):
 def test_inputs_hashes(self):
  for n,x in read(A/'manifest.json').items():self.assertEqual(hashlib.sha256((A/n).read_bytes()).hexdigest(),x['sha256'])
 def test_safe_payload_monotonicity(self):
  rows=read(D/'q1_safe_payload_vs_reserve.json');groups=defaultdict(list)
  for r in rows:groups[r['service_area'],r['aircraft_type']].append(r)
  self.assertEqual(len(groups),45)
  for g,rr in groups.items():
   yy=[r['safe_payload_kg'] for r in sorted(rr,key=lambda r:r['alpha'])]
   vals=[y for y in yy if y is not None]
   self.assertTrue(all(b<=a+1e-8 for a,b in zip(vals,vals[1:])),g)
   if None in yy:self.assertTrue(all(y is None for y in yy[yy.index(None):]),g)
  self.assertLess(read(D/'audit_generation_checks.json')['q1_nominal_max_abs_error_kg'],1e-7)
 def test_q3_full_schedule_identity(self):
  f=read(A/'q3_flights.json');d=read(A/'q3_deliveries.json')
  self.assertEqual(len(f),23);self.assertEqual(len(d),80);self.assertEqual(len({x['id'] for x in d}),80)
  self.assertAlmostEqual(max(x['return_s'] for x in f),5836.969929328251,7)
  self.assertEqual(Counter(x for row in f for x in row['box_ids']),Counter(x['id'] for x in d))
 def test_q3_same_transport_structure(self):
  self.assertEqual(read(A/'q3_v5_baseline.json')['decisions'],read(A/'q3_v6_selected.json')['decisions'])
 def test_q4_group_sums(self):
  rows=read(D/'q4_group_allocations.json');q=read(A/'q4_enumeration.json')
  for k in [2,3]:
   rr=[x for x in rows if x['K']==k];self.assertEqual(len(rr),k)
   self.assertEqual([sum(x['need'][i] for x in rr) for i in range(8)],q['by_group_count'][str(k)]['minimum_configuration']['need_vector'])
 def test_equivalent_boxes(self):
  groups=defaultdict(set)
  for x in read(A/'q2_boxes.json'):groups[x['site'],x['kind']].add((x['mass_kg'],x['volume_m3']))
  self.assertEqual(len(groups),53);self.assertTrue(all(len(x)==1 for x in groups.values()))
 def test_actual_methods_and_provenance(self):
  s=(P/'repair_sections/q2_search.tex').read_text();q=(P/'repair_sections/q3_search.tex').read_text();p=(P/'repair_sections/source_provenance.tex').read_text()
  for marker in ['eq:q2_regret','eq:q2_search_score','eq:q2_temperature','eq:q2_operator_weight','种子9201']:self.assertIn(marker,s)
  for marker in ['eq:q3_transport_paths','eq:q3_lp_start_bounds','eq:q3_lp_coverage','eq:q3_lp_energy','eq:q3_lp_charge','eq:q3_lp_resource','eq:q3_lp_objective']:self.assertIn(marker,q)
  self.assertIn('待核验',p);self.assertIn('dffa94db1788b976',p)
  self.assertIn('10.1287/trsc.1050.0135',(P/'references.bib').read_text())
 def test_lower_bound_cover_direction(self):
  s=(P/'repair_sections/q2_bound.tex').read_text()
  self.assertIn(r'LB=\min',s);self.assertIn('未解决的子域',s);self.assertIn('没有完成定价',s)
if __name__=='__main__':unittest.main(verbosity=2)
