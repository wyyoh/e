#!/usr/bin/env python3
"""Strict whole-manuscript build; no missing-figure fallback or source rewriting."""
from pathlib import Path
import shutil,subprocess,sys,json,re
P=Path(__file__).resolve().parents[1]
def command(name, alternatives=()):
 for n in (name,*alternatives):
  q=shutil.which(n)
  if q:return q
 raise SystemExit(f'Missing executable: {name}')
xe=command('xelatex');bib=command('bibtex',('bibtex.original','bibtex8'))
for f in ['00_abstract',*[f'{i:02}' for i in range(1,10)]]:
 if not (P/'chapters'/f'{f}.tex').exists():raise SystemExit('Missing maintained chapter '+f)
logs=P/'build_logs';logs.mkdir(exist_ok=True)
commands=[[xe,'-interaction=nonstopmode','-halt-on-error','main.tex'],[bib,'main']]+[[xe,'-interaction=nonstopmode','-halt-on-error','main.tex']]*3
for i,cmd in enumerate(commands,1):
 with (logs/f'pass_{i}.log').open('wb') as o:
  r=subprocess.run(cmd,cwd=P,stdout=o,stderr=subprocess.STDOUT,check=False)
 if r.returncode:raise SystemExit(f'Build failed at pass {i}; see build_logs/pass_{i}.log')
log=(P/'main.log').read_text(errors='replace')
checks={k:len(re.findall(p,log)) for k,p in {'overfull':r'Overfull \\hbox|Overfull \\vbox','missing_glyph':r'Missing character','undefined':r'undefined','duplicate_label':r'multiply defined','underfull':r'Underfull'}.items()}
(logs/'preflight.json').write_text(json.dumps(checks,indent=2)+'\n')
if any(checks[k] for k in ['overfull','missing_glyph','undefined','duplicate_label']):raise SystemExit('Preflight needs attention: '+str(checks))
print('BUILT',P/'main.pdf',checks)
