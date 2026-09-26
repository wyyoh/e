#!/usr/bin/env python3
"""Expand main.tex's input graph for single-file editing; leave image/class/BibTeX assets external."""
from pathlib import Path
import importlib.util
P=Path(__file__).resolve().parents[1]

def main():
    spec=importlib.util.spec_from_file_location('source_graph',P/'scripts/check_source.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    files,text=m.source_graph()
    header='''% !TeX program = xelatex
% Merged source, generated from the complete maintained chapter graph.
% Keep this file at the project root alongside format.cls, references.bib and figures.
% No PDF was generated for this delivery; pagination is not asserted.
% For routine maintenance edit chapters/*.tex, then run scripts/export_merged_tex.py.
'''
    (P/'main_merged.tex').write_text(header+text+'\n',encoding='utf-8')
    print(f'Expanded {len(files)} source files into main_merged.tex')
if __name__=='__main__':main()
