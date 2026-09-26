"""Regression tests for non-destructive chapter bootstrap; requires XeLaTeX."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("xelatex"), "XeLaTeX is required")
class ChapterLoaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        (self.work / "chapters").mkdir()
        shutil.copy2(ROOT / "source_loader.tex", self.work / "source_loader.tex")
        source = "\\begin{abstract}\nAbstract marker.\n\\end{abstract}\n"
        source += "".join(f"\\section{{Chapter {n}}}\nBody marker {n}.\n" for n in range(1, 10))
        source += "\\renewcommand{\\refname}{References}\nBACK-MATTER-MARKER\n\\end{document}\n"
        (self.work / "source_main.tex").write_text(source, encoding="utf-8")
        (self.work / "test.tex").write_text(
            "\\documentclass{article}\n\\input{source_loader.tex}\n"
            "\\begin{document}Loader test.\\end{document}\n", encoding="utf-8")

    def run_loader(self):
        run = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error", "test.tex"],
            cwd=self.work, capture_output=True, text=True, timeout=45)
        self.assertEqual(run.returncode, 0, run.stdout[-3000:] + run.stderr[-1000:])

    def snapshot(self):
        return {p.name: p.read_bytes() for p in (self.work / "chapters").glob("*.tex")}

    def test_clean_bootstrap_and_back_matter_cutoff(self):
        self.run_loader()
        files = self.snapshot()
        self.assertEqual(set(files), {"00_abstract.tex"} | {f"{n:02d}.tex" for n in range(1, 10)})
        self.assertIn(b"Body marker 9", files["09.tex"])
        self.assertNotIn(b"BACK-MATTER-MARKER", b"".join(files.values()))

    def test_preserves_actual_edited_chapter_and_regenerates_only_missing(self):
        edited = (ROOT / "chapters" / "03.tex").read_bytes()
        (self.work / "chapters" / "03.tex").write_bytes(edited)
        self.run_loader()
        first = self.snapshot()
        self.assertEqual(first["03.tex"], edited)
        self.run_loader()
        self.assertEqual(self.snapshot(), first)
        (self.work / "chapters" / "02.tex").unlink()
        self.run_loader()
        self.assertEqual(self.snapshot(), first)


if __name__ == "__main__":
    unittest.main()
