"""Regression: the bootstrap loader must preserve the maintained Chapter 2.

Run from paper/latex:
    python -m unittest discover -s tests -p 'test_ch02_source.py' -v
This tests file preservation and missing-file bootstrap, not numerical solvers.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

LATEX = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("xelatex"), "XeLaTeX is required")
class ChapterTwoSourceTest(unittest.TestCase):
    def test_preservation_and_missing_chapter_bootstrap(self):
        with tempfile.TemporaryDirectory(prefix="ch02-loader-") as tmp:
            root = Path(tmp)
            (root / "chapters").mkdir()
            shutil.copy2(LATEX / "source_loader.tex", root / "source_loader.tex")
            maintained = (LATEX / "chapters/02.tex").read_bytes()
            third = b"% maintained chapter three: preserve byte for byte\n"
            (root / "chapters/02.tex").write_bytes(maintained)
            (root / "chapters/03.tex").write_bytes(third)
            source = "\\begin{abstract}\nExample abstract.\n\\end{abstract}\n"
            for i in range(1, 10):
                source += f"\\section{{Legacy {i}}}\nLegacy chapter {i}.\n"
            source += "\\renewcommand{\\refname}{References}\n\\end{document}\n"
            (root / "source_main.tex").write_text(source, encoding="utf-8")
            (root / "probe.tex").write_text(
                "\\documentclass{article}\n\\input{source_loader.tex}\n"
                "\\begin{document}Loader test.\\end{document}\n", encoding="utf-8"
            )
            for run in range(3):
                if run == 2:
                    (root / "chapters/05.tex").unlink()
                result = subprocess.run(
                    ["xelatex", "-interaction=nonstopmode", "-halt-on-error", "probe.tex"],
                    cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    timeout=30, check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout.decode(errors="replace")[-5000:])
                self.assertEqual((root / "chapters/02.tex").read_bytes(), maintained)
                self.assertEqual((root / "chapters/03.tex").read_bytes(), third)
                self.assertTrue((root / "chapters/00_abstract.tex").is_file())
                self.assertIn("Legacy chapter 5.", (root / "chapters/05.tex").read_text())
                for i in range(1, 10):
                    self.assertTrue((root / f"chapters/{i:02}.tex").is_file())
                self.assertNotIn("References", (root / "chapters/09.tex").read_text())


if __name__ == "__main__":
    unittest.main()
