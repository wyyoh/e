"""Regression checks for the maintained manuscript and its build boundary."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / 'paper/latex'
WORKFLOW = ROOT / '.github/workflows/build-review-pdf.yml'
ARCHIVE = ROOT / 'paper/archive/pre_cleanup_20260927'


class RepositoryHygiene(unittest.TestCase):
    def ignored(self, path):
        result = subprocess.run(['git', 'check-ignore', '-q', '--no-index', path], cwd=ROOT)
        self.assertIn(result.returncode, (0, 1))
        return result.returncode == 0

    def test_no_tracked_build_outputs(self):
        paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
        pattern = re.compile(r'^paper/latex/(?:[^/]+\.(?:aux|bbl|blg|log|out|toc|lof|lot|fls|xdv|fdb_latexmk|synctex\.gz)|(?:main|main_merged|review)\.pdf|build_logs/.*|build/.*)$')
        bad = [p for p in paths if pattern.match(p) or p.startswith(('review-build/', 'review-output/', 'publication-output/'))]
        self.assertEqual(bad, [])

    def test_generated_outputs_are_ignored(self):
        for path in ('paper/latex/main.aux', 'paper/latex/main.bbl', 'paper/latex/main.log',
                     'paper/latex/main.toc', 'paper/latex/main.pdf',
                     'paper/latex/main_merged.pdf', 'paper/latex/build_logs/pass_1.log',
                     'paper/latex/checks/main_tex_no_pdf.log', 'review-build/validation.json'):
            with self.subTest(path=path):
                self.assertTrue(self.ignored(path))

    def test_publications_and_model_evidence_are_not_ignored(self):
        for path in ('paper/review/D_paper_completed_20260926.pdf',
                     'paper/review/publication_references_20260926.bbl',
                     'paper/latex/figures_generated/q1_payload.pdf',
                     'paper/latex/figures/common_model/fig3_1_terrain_and_demand.pdf',
                     'paper/latex/references.bib', 'paper/latex/chapters/02.tex',
                     'paper/latex/audit_inputs/q3_flights.json',
                     'problems/D/q2/evidence_v7/verification.log',
                     'experiments/paper_robustness_20260926/run.log',
                     'paper_integration/FINAL_SELECTION.json'):
            with self.subTest(path=path):
                self.assertFalse(self.ignored(path))

    def test_push_and_pr_share_one_safe_workflow(self):
        text = WORKFLOW.read_text()
        for event in ('push', 'pull_request', 'workflow_dispatch'):
            self.assertRegex(text, rf'(?m)^  {event}:')
        self.assertNotIn('pull_request_target:', text)
        self.assertIn('contents: read', text)
        self.assertIn('persist-credentials: false', text)
        self.assertIn('$PWD:/work:ro', text)
        self.assertEqual(text.count('python3 .github/scripts/ci_review.py'), 1)
        for path in (ROOT / '.github/workflows').glob('*.y*ml'):
            content = path.read_text()
            self.assertNotRegex(content, r'(?m)^.*\brm\b[^\n]*chapters/')
            self.assertNotRegex(content, r'bibtex[^\n]*\|\|\s*true')
        self.assertFalse((WORKFLOW.parent / 'render-review.yml').exists())
        self.assertFalse((WORKFLOW.parent / 'build-structure-review-pdf.yml').exists())

    def test_archived_files_keep_their_original_blob_hashes(self):
        entries = json.loads((ARCHIVE / 'manifest.json').read_text())['entries']
        self.assertGreaterEqual(len(entries), 17)
        for item in entries:
            data = (ROOT / item['destination']).read_bytes()
            actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            self.assertEqual(actual, item['blob_sha'], item['destination'])
            if item['remove_source']:
                self.assertFalse((ROOT / item['source']).exists(), item['source'])

    def test_actual_source_graph_does_not_use_legacy_loader(self):
        spec = importlib.util.spec_from_file_location('hygiene_source_graph', PAPER / 'scripts/check_source.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        loaded, _ = module.source_graph()
        self.assertEqual(len(loaded), len(set(loaded)))
        for p in loaded:
            self.assertNotIn('archive', p.relative_to(ROOT).parts)
            self.assertNotIn(p.name, ('source_main.tex', 'source_loader.tex', 'review.tex'))
        self.assertTrue((PAPER / 'chapters/09.tex').exists())

    def test_navigation_matches_active_entry(self):
        for name in ('README.md', 'paper/README.md', 'paper/latex/README.md'):
            text = (ROOT / name).read_text()
            self.assertIn('main.tex', text)
            self.assertIn('chapters/', text)
        self.assertIn('pre_cleanup_20260927', (ROOT / 'docs/REPOSITORY_STRUCTURE.md').read_text())
        self.assertTrue((ROOT / 'paper/review/D_paper_completed_20260926.pdf').read_bytes().startswith(b'%PDF-'))

    def test_disposable_copy_preserves_inputs_without_root_outputs(self):
        spec = importlib.util.spec_from_file_location('hygiene_ci', ROOT / '.github/scripts/ci_review.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        before = module.fingerprints(PAPER)
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / 'latex'
            module.copy_source(destination)
            self.assertFalse((destination / 'main.pdf').exists())
            self.assertFalse((destination / 'main.aux').exists())
            self.assertFalse((destination / 'main.bbl').exists())
            self.assertFalse((destination / 'build_logs').exists())
            for name in ('main.tex', 'format.cls', 'references.bib', 'chapters/09.tex',
                         'figures_generated/q1_payload.pdf'):
                self.assertEqual((destination / name).read_bytes(), (PAPER / name).read_bytes())
        self.assertEqual(before, module.fingerprints(PAPER))


if __name__ == '__main__':
    unittest.main(verbosity=2)
