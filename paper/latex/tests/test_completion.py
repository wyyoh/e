from pathlib import Path
import collections, hashlib, importlib.util, json, math, re, unittest
P=Path(__file__).resolve().parents[1]
class CompletionChecks(unittest.TestCase):
 def test_all_new_tables_present(self):
  self.assertEqual(len(list((P/'revision_tables').glob('*.tex'))),12)
  self.assertEqual(len(list((P/'revision_tables').glob('*.csv'))),12)
 def test_actual_source_graph(self):
  spec=importlib.util.spec_from_file_location('graph',P/'scripts/check_source.py')
  m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  report=m.check();self.assertTrue(report['passed'],report)
  self.assertEqual(report['expanded_sections'],22)
  self.assertEqual(report['bibliography_entries'],40)
  self.assertEqual(report['actually_cited_entries'],40)
 def test_new_analysis_inputs(self):
  d=json.loads((P/'revision_analysis.json').read_text())
  for path,h in d['input_files'].items():
   self.assertEqual(hashlib.sha256((P/path).read_bytes()).hexdigest(),h)
 def test_saved_result_totals(self):
  d=json.loads((P/'revision_analysis.json').read_text())
  self.assertAlmostEqual(sum(x[3] for x in d['q1_types']),59.13129602205317,7)
  self.assertAlmostEqual(sum(x[4] for x in d['q2_types']),66.21445957313102,7)
  self.assertAlmostEqual(sum(x[3] for x in d['q3_transport_energy']),66.25127994199477,7)
  self.assertAlmostEqual(sum(x[3] for x in d['q3_relay_energy']),2.688136268186355,7)
  self.assertEqual(d['q2_battery_reuse_edges'],9)
  self.assertEqual(d['q2_zero_slack_edges'],3)
 def test_bibliography_identity(self):
  d=json.loads((P/'reference_audit.json').read_text())
  self.assertEqual(d['total_entries'],40)
  self.assertEqual(d['public_entries_including_corrections_standards_books'],39)
  self.assertEqual(d['nonpublic_candidate_records'],1)
  bib=(P/'references.bib').read_text()
  self.assertIn('candidateArchive',bib)
  self.assertNotIn('nocite{*}',(P/'main.tex').read_text())
 def test_no_external_fonts_or_manuscript_pdf(self):
  self.assertFalse(any(p.suffix.lower() in {'.ttf','.otf','.ttc','.woff','.woff2'} for p in P.rglob('*') if p.is_file()))
  self.assertFalse((P/'main.pdf').exists())
if __name__=='__main__':unittest.main(verbosity=2)
