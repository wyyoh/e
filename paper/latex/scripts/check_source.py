#!/usr/bin/env python3
"""Validate the actually loaded source graph without producing a manuscript PDF."""
from __future__ import annotations
import argparse, collections, hashlib, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def clean(s):
    return '\n'.join(re.split(r'(?<!\\)%',l,maxsplit=1)[0] for l in s.splitlines())

def source_graph():
    included=[]
    def visit(path,stack=()):
        path=path.resolve()
        if path in stack:raise ValueError('Cyclic input '+str(path))
        if not path.is_file():raise FileNotFoundError(path)
        included.append(path)
        text=clean(path.read_text(encoding='utf-8'))
        def sub(m):
            name=m.group(1);p=ROOT/name
            if p.suffix!='.tex':p=p.with_suffix('.tex')
            return '\n'+visit(p,stack+(path,))+'\n'
        return re.sub(r'\\(?:input|include)\s*\{([^}]+)\}',sub,text)
    text=visit(ROOT/'main.tex')
    return included,text

def check():
    files,text=source_graph();labels=re.findall(r'\\label\{([^}]+)\}',text)
    labels=[x for x in labels if '#' not in x]
    labels += [line.rsplit('{',1)[1].split('}',1)[0] for line in text.splitlines() if line.startswith(r'\fig')]
    dup=[k for k,v in collections.Counter(labels).items() if v>1]
    refs={x for x in re.findall(r'\\(?:eqref|ref|pageref|autoref)\{([^}]+)\}',text) if '#' not in x}
    bib=(ROOT/'references.bib').read_text();keys=re.findall(r'@\w+\s*\{\s*([^,]+),',bib)
    cites={k.strip() for v in re.findall(r'\\cite\w*\s*(?:\[[^\]]*\])?\{([^}]+)\}',text) for k in v.split(',')}
    images=re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}',text)
    images=[x for x in images if '#' not in x]
    images+=re.findall(r'^\\fig(?:\[[^\]]*\])?\{([^}]+)\}',text,re.M)
    missing_images=[]
    for x in images:
        if not any((b/x).is_file() for b in [ROOT,ROOT/'figures_generated']):missing_images.append(x)
    missing_refs=sorted(refs-set(labels));missing_cites=sorted(cites-set(keys))
    unused=sorted(set(keys)-cites)
    beg=collections.Counter(re.findall(r'\\begin\{([^}]+)\}',text));end=collections.Counter(re.findall(r'\\end\{([^}]+)\}',text))
    envdiff={k:[beg[k],end[k]] for k in beg.keys()|end.keys() if beg[k]!=end[k]}
    report={'check':'source graph only; not page-layout validation','pdf_generated':False,
      'loaded_tex_files':len(files),'unique_loaded_tex_files':len(set(files)),
      'chapters_present':all((ROOT/f'chapters/{i:02}.tex').is_file() for i in range(1,10)),
      'expanded_sections':len(list((ROOT/'expanded_sections').glob('*.tex'))),
      'revision_tables':len(list((ROOT/'revision_tables').glob('*.tex'))),
      'bibliography_entries':len(keys),'actually_cited_entries':len(cites),
      'bibliography_duplicate_keys':[k for k,v in collections.Counter(keys).items() if v>1],
      'unused_bibliography_entries':unused,'missing_citations':missing_cites,
      'labels':len(labels),'duplicate_labels':dup,'missing_references':missing_refs,
      'referenced_images':len(images),'missing_images':missing_images,'environment_count_mismatches':envdiff,
      'source_tex_characters':len(text),'CJK_characters':len(re.findall(r'[\u4e00-\u9fff]',text)),
      'source_graph':[str(p.relative_to(ROOT)) for p in files]}
    problems=[dup,missing_refs,missing_cites,missing_images,envdiff,report['bibliography_duplicate_keys'],unused]
    report['passed']=report['chapters_present'] and not any(problems)
    (ROOT/'checks').mkdir(exist_ok=True)
    (ROOT/'checks/source_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report
if __name__=='__main__':
    report=check();print(json.dumps({k:v for k,v in report.items() if k!='source_graph'},ensure_ascii=False,indent=2))
    raise SystemExit(0 if report['passed'] else 1)
