"""Lightweight integration tests; no drawing, optimizer or network required."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CommonFigureIntegrationTests(unittest.TestCase):
    def read(self, name):
        return (ROOT / name).read_text(encoding='utf-8')

    def test_actual_entry_and_chapters(self):
        main = self.read('main.tex')
        self.assertIn(r'\input{common_figures.tex}', main)
        self.assertIn(r'\input{chapters/01.tex}', main)
        self.assertIn(r'\input{chapters/03.tex}', main)
        self.assertLess(main.index(r'\input{appendices.tex}'), main.index(r'\input{appendix_dem_figure.tex}'))

    def test_single_insertion_and_correct_order(self):
        one = self.read('chapters/01.tex')
        three = self.read('chapters/03.tex')
        self.assertEqual(one.count(r'\CommonDecisionFigure'), 1)
        self.assertNotIn(r'\begin{tikzpicture}', one)
        self.assertEqual(three.count(r'\CommonTerrainFigure'), 1)
        self.assertEqual(three.count(r'\CommonTransportFigure'), 1)
        self.assertNotIn(r'\begin{tikzpicture}', three)
        self.assertLess(three.index(r'\CommonTerrainFigure'), three.index(r'\subsubsection{运输机参数}'))
        self.assertLess(three.index(r'\subsection{运输任务表示与逐段载荷递推}'), three.index(r'\CommonTransportFigure'))
        self.assertLess(three.index(r'\CommonTransportFigure'), three.index(r'\subsection{飞行时间、交付时刻与返航时间}'))

    def test_unique_labels_and_legacy_aliases(self):
        definitions = self.read('common_figures.tex')
        labels = re.findall(r'\\label\{([^}]+)\}', definitions)
        self.assertEqual(len(labels), len(set(labels)))
        self.assertIn('fig:overall_framework', labels)
        self.assertIn('fig:common_leg_geometry', labels)
        self.assertIn('fig:dem_closed_cells', labels)
        self.assertEqual(definitions.count(r'\includegraphics'), 4)
        self.assertEqual(definitions.count(r'\begin{figure}'), 4)
        self.assertEqual(definitions.count(r'\end{figure}'), 4)

    def test_appendix_explanation_and_backward_reference(self):
        appendix = self.read('appendix_dem_figure.tex')
        three = self.read('chapters/03.tex')
        self.assertIn(r'\label{sec:dem_figure_notes}', appendix)
        self.assertEqual(appendix.count(r'\CommonDEMFigure'), 1)
        self.assertIn(r'\ref{sec:dem_figure_notes}', three)
        self.assertIn('不对应', appendix)

    def test_build_hook_does_not_install_dependencies(self):
        rc = self.read('.latexmkrc')
        self.assertIn('scripts/build_common_figures.py', rc)
        self.assertNotIn('pip install', rc)
        script = self.read('scripts/build_common_figures.py')
        self.assertIn("row['git_blob_sha1']", script)
        self.assertNotIn('run_all.py', script)
        self.assertNotIn('subprocess', script)


if __name__ == '__main__':
    unittest.main()
