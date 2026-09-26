#!/usr/bin/env python3
"""Run XeLaTeX/BibTeX checks with -no-pdf; never invoke the PDF driver.

Writes a JSON report and final logs into checks/. Temporary XDV/aux files are removed.
This detects TeX processing errors, not a visual page-layout inspection.
"""
from __future__ import annotations
import argparse,json,os,re,shutil,subprocess,tempfile
from pathlib import Path
P=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--entry',default='main.tex')
    args=parser.parse_args()
    entry=P/args.entry
    if not entry.is_file():raise SystemExit(f'Missing entry: {entry}')
    xe=shutil.which('xelatex');bib=next((p for n in ('bibtex','bibtex8') if (p:=shutil.which(n))),None)
    if not xe or not bib:raise SystemExit('Requires xelatex and bibtex or bibtex8')
    result_dir=P/'checks';result_dir.mkdir(exist_ok=True)
    name=entry.stem
    with tempfile.TemporaryDirectory(prefix='latex_no_pdf_') as tmp:
        out=Path(tmp);env=dict(os.environ);env['BIBINPUTS']=str(P)+os.pathsep+env.get('BIBINPUTS','')
        # Explicit -no-pdf prevents xdvipdfmx and leaves only temporary XDV.
        tex=[xe,'-no-pdf','-interaction=nonstopmode','-halt-on-error',f'-output-directory={tmp}',str(entry)]
        stages=[(tex,P),([bib,name],out),(tex,P),(tex,P),(tex,P)]
        for i,(cmd,cwd) in enumerate(stages,1):
            run=subprocess.run(cmd,cwd=cwd,env=env,capture_output=True,timeout=180)
            if run.returncode:
                (result_dir/f'{name}_failed_stage_{i}.log').write_bytes(run.stdout+run.stderr)
                raise SystemExit(f'TeX/BibTeX stage {i} failed; see checks/')
        if list(out.glob('*.pdf')):raise RuntimeError('Unexpected PDF output')
        log=(out/f'{name}.log').read_text(errors='replace')
        counts={k:len(re.findall(pattern,log)) for k,pattern in {
            'overfull':r'Overfull \\hbox|Overfull \\vbox',
            'underfull':r'Underfull',
            'missing_glyphs':r'Missing character',
            'undefined_references_or_citations':r'undefined',
            'duplicate_labels':r'multiply defined',
            'latex_warnings':r'LaTeX Warning|Package .* Warning',
        }.items()}
        report={'entry':args.entry,'method':'XeLaTeX -no-pdf and BibTeX, five stages',
                'manuscript_pdf_generated':False,'visual_layout_inspection':False,
                'counts':counts,'passed':not any(counts.values())}
        # Log may include XDV internal pagination; no PDF or page-count assertion is made.
        shutil.copyfile(out/f'{name}.log',result_dir/f'{name}_tex_no_pdf.log')
        shutil.copyfile(out/f'{name}.blg',result_dir/f'{name}_bibtex.log')
        shutil.copyfile(out/f'{name}.bbl',result_dir/f'{name}.bbl')
        (result_dir/f'{name}_tex_no_pdf.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
