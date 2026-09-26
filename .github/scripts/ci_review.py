#!/usr/bin/env python3
"""Build the maintained manuscript in a disposable copy, never in the checkout.

Requires Python, git, XeLaTeX, BibTeX and pdfinfo. Does not run any optimizer,
regenerate figures, update publication snapshots or edit maintained chapters.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'paper/latex'
OUTPUT = ROOT / 'review-build'
AUX_SUFFIXES = ('.aux', '.bbl', '.blg', '.log', '.out', '.toc', '.lof', '.lot',
                '.fls', '.fdb_latexmk', '.xdv', '.synctex.gz', '.nav', '.snm',
                '.vrb', '.idx', '.ilg', '.ind')
ROOT_OUTPUTS = {'build', 'build_logs', 'checks', 'main.pdf', 'main_merged.pdf',
                'review.pdf', '.latex-cache'}


def git(*args: str) -> bytes:
    return subprocess.check_output(['git', *args], cwd=ROOT)


def fingerprints(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def copy_source(destination: Path) -> None:
    def ignore(directory: str, names: list[str]) -> set[str]:
        excluded = {n for n in names if n == '__pycache__' or n.endswith('.pyc')}
        if Path(directory) == SOURCE:
            excluded.update(n for n in names
                            if n in ROOT_OUTPUTS or n.endswith(AUX_SUFFIXES))
        return excluded
    shutil.copytree(SOURCE, destination, ignore=ignore)


def run(command: list[str], cwd: Path, log_name: str, env: dict[str, str]) -> None:
    print('+', ' '.join(command), flush=True)
    with (OUTPUT / log_name).open('wb') as stream:
        result = subprocess.run(command, cwd=cwd, env=env, stdout=stream,
                                stderr=subprocess.STDOUT, check=False)
    if result.returncode:
        tail = (OUTPUT / log_name).read_text(errors='replace').splitlines()[-35:]
        raise RuntimeError(f'{log_name}: exit {result.returncode}\n' + '\n'.join(tail))


def main() -> int:
    for name in ('git', 'xelatex', 'pdfinfo'):
        if not shutil.which(name):
            raise SystemExit(f'Missing required executable: {name}')
    if not any(shutil.which(n) for n in ('bibtex', 'bibtex.original', 'bibtex8')):
        raise SystemExit('Missing BibTeX')
    status_before = git('status', '--porcelain=v1', '--untracked-files=all')
    if os.environ.get('GITHUB_ACTIONS') == 'true' and status_before:
        raise SystemExit('CI requires a clean checkout before building')
    if subprocess.run(['git', 'check-ignore', '-q', '--no-index',
                       'review-build/probe.txt'], cwd=ROOT).returncode != 0:
        raise SystemExit('review-build/ must be ignored before building')
    source_before = fingerprints(SOURCE)
    OUTPUT.mkdir(exist_ok=True)
    # Remove only known stale outputs from an earlier invocation, not arbitrary files.
    for name in ('D_paper_review.pdf', 'validation.json', 'source-check.json',
                 'hygiene-tests.log', 'tests.log', 'build-console.log',
                 'main.log', 'main.aux', 'main.bbl', 'pdfinfo.txt', 'preflight.json'):
        (OUTPUT / name).unlink(missing_ok=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
    report: dict[str, object] = {'commit': git('rev-parse', 'HEAD').decode().strip(),
                                 'passed': False, 'optimizers_rerun': False,
                                 'source_copy': 'temporary directory'}
    error: Exception | None = None
    with tempfile.TemporaryDirectory(prefix='paper-review-') as temporary:
        work = Path(temporary) / 'latex'
        try:
            run([sys.executable, '-m', 'unittest', 'discover', '-s', '.github/tests',
                 '-v'], ROOT, 'hygiene-tests.log', env)
            copy_source(work)
            run([sys.executable, 'scripts/check_source.py'], work,
                'source-check.json', env)
            run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                work, 'tests.log', env)
            run([sys.executable, 'scripts/build_pdf.py'], work,
                'build-console.log', env)
            run(['pdfinfo', 'main.pdf'], work, 'pdfinfo.txt', env)
            shutil.copy2(work / 'main.pdf', OUTPUT / 'D_paper_review.pdf')
            pages = re.search(r'^Pages:\s+(\d+)',
                              (OUTPUT / 'pdfinfo.txt').read_text(), re.MULTILINE)
            if not pages:
                raise RuntimeError('pdfinfo did not report a page count')
            report['pdf_pages'] = int(pages.group(1))
            report['pdf_sha256'] = hashlib.sha256((work / 'main.pdf').read_bytes()).hexdigest()
            report['bibliography_records'] = len(re.findall(r'\\bibitem',
                                                          (work / 'main.bbl').read_text()))
            for log, key in (('tests.log', 'manuscript_tests'),
                             ('hygiene-tests.log', 'hygiene_tests')):
                match = re.search(r'Ran (\d+) tests?', (OUTPUT / log).read_text())
                if not match:
                    raise RuntimeError(f'Test count missing from {log}')
                report[key] = int(match.group(1))
            report['passed'] = True
        except Exception as exc:
            error = exc
            report['error'] = str(exc)
        finally:
            # Keep diagnostics on failure as well. Nothing is copied into source paths.
            for name in ('main.log', 'main.aux', 'main.bbl'):
                if (work / name).is_file():
                    shutil.copy2(work / name, OUTPUT / name)
            if (work / 'build_logs').is_dir():
                shutil.copytree(work / 'build_logs', OUTPUT / 'build_logs', dirs_exist_ok=True)
            status_after = git('status', '--porcelain=v1', '--untracked-files=all')
            report['source_unchanged'] = fingerprints(SOURCE) == source_before
            report['git_status_unchanged'] = status_after == status_before
            report['worktree_clean'] = not status_after
            if not report['source_unchanged'] or not report['git_status_unchanged']:
                report['passed'] = False
                report['error'] = 'Build changed the original checkout'
            (OUTPUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    if error:
        print(str(error), file=sys.stderr)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
