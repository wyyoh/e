from pathlib import Path
import re,json,unittest,hashlib
P=Path(__file__).resolve().parents[1]
class SourceChecks(unittest.TestCase):
 def test_maintained_chapters(self):
  main=(P/'main.tex').read_text();self.assertNotIn(r'\input{source_loader',main)
  for i in range(1,10):self.assertIn(f'chapters/{i:02}.tex',main);self.assertTrue((P/f'chapters/{i:02}.tex').exists())
 def test_heading_depth_and_scope(self):
  for i in range(1,10):
   t=(P/f'chapters/{i:02}.tex').read_text()
   h=re.findall(r'\\(?:sub)*section\{([^}]+)\}',t)
   self.assertFalse(any(re.search(r'V[1-9]|robust025|time方案|Q3-BOTTLENECK|历史敏感性',s) for s in h))
  for i in range(4,8):self.assertIn('稳健性与敏感性分析',(P/f'chapters/{i:02}.tex').read_text())
  self.assertIn(r'\setcounter{tocdepth}{3}',(P/'deep_layout.tex').read_text())
 def test_no_duplicate_labels_or_unknown_refs(self):
  text='\n'.join(f.read_text() for f in [*sorted((P/'chapters').glob('*.tex')),P/'appendices.tex',*sorted((P/'tables').glob('*.tex'))])
  labels=re.findall(r'\\label\{([^}]+)\}',text);labels += [line.rsplit('{',1)[1].split('}',1)[0] for line in text.splitlines() if line.startswith(r'\fig')];self.assertEqual(len(labels),len(set(labels)))
  refs=re.findall(r'\\(?:eqref|ref|pageref)\{([^}]+)\}',text);self.assertFalse(set(refs)-set(labels))
 def test_images_present(self):
  text='\n'.join(p.read_text() for p in (P/'chapters').glob('*.tex'))
  images=re.findall(r'\{([a-z0-9_]+\.pdf)\}',text)
  self.assertGreaterEqual(len(set(images)),14)
  for n in images:self.assertTrue((P/'figures_generated'/n).exists(),n)
  self.assertNotIn('未载入',text);self.assertNotIn('占位图',text)
 def test_input_fingerprints(self):
  x=json.loads((P/'figdata/provenance.json').read_text())
  for n,h in x['data_sha256'].items():self.assertEqual(hashlib.sha256((P/'figdata'/n).read_bytes()).hexdigest(),h)
if __name__=='__main__':unittest.main(verbosity=2)
