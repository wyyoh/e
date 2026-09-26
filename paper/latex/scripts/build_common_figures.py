#!/usr/bin/env python3
"""Render missing chapter 1/3/appendix PDFs without running any solver.

The supplied ready-to-use PDF kit needs no Python plotting dependencies.
A clean Git checkout uses this script once (also invoked by .latexmkrc).
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

LATEX = Path(__file__).resolve().parents[1]
REPO = LATEX.parents[1]
ASSETS = LATEX / 'figures/common_model'
NAMES = ('fig1_1_decision_inheritance', 'fig3_1_terrain_and_demand',
         'fig3_2_transport_physics', 'figA1_dem_cells')


def validate_inputs() -> dict:
    manifest = json.loads((ASSETS / 'data/source_identity.json').read_text(encoding='utf-8'))
    for row in manifest['files']:
        source = REPO / row['repository_path']
        if not source.is_file():
            raise FileNotFoundError(f'Required original input not found: {source}')
        data = source.read_bytes()
        digest = hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()
        if digest != row['git_blob_sha1']:
            raise ValueError(f'Input changed: {source}. Refresh and review the figure data before rebuilding.')
    nodes = json.loads((ASSETS / 'data/nodes_demand.json').read_text(encoding='utf-8'))
    service = [n for n in nodes if n['id'] != 'O01']
    if len(nodes) != 16 or len({n['id'] for n in nodes}) != 16:
        raise ValueError('Unexpected node identifiers.')
    if len(service) != 15 or sum(n['box_count'] for n in service) != 80:
        raise ValueError('Unexpected service or box counts.')
    if sum(n['mass_kg'] for n in service) != 758:
        raise ValueError('Unexpected aggregate mass.')
    if abs(sum(n['volume_m3'] for n in service) - 2.011) > 1e-12:
        raise ValueError('Unexpected aggregate volume.')
    return {'input_commit': manifest['commit'], 'checked_raw_files': len(manifest['files']),
            'service_areas': 15, 'boxes': 80, 'mass_kg': 758, 'volume_m3': 2.011}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--force', action='store_true', help='Rebuild even when all four PDFs already exist.')
    args = parser.parse_args()
    if all((ASSETS / f'{name}.pdf').is_file() for name in NAMES) and not args.force:
        print('Common-model PDFs already present; no drawing or solver run needed.')
        return 0
    audit = validate_inputs()
    try:
        spec = importlib.util.spec_from_file_location('common_figure_renderer', LATEX / 'scripts/render_common_figures.py')
        renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(renderer)
    except ImportError as exc:
        raise SystemExit('Missing plotting dependency. Install scripts/common_figures_requirements.txt, '
                         'or copy the four reviewed PDFs into figures/common_model/.\n' + str(exc)) from exc
    # Matplotlib must not silently replace CJK text with missing-glyph squares.
    candidates = ['Noto Sans CJK JP', 'Noto Sans CJK SC', 'Source Han Sans SC', 'Microsoft YaHei', 'SimHei']
    font = None
    for name in candidates:
        try:
            renderer.fm.findfont(renderer.fm.FontProperties(family=name), fallback_to_default=False)
            font = name
            break
        except ValueError:
            continue
    if font is None:
        raise SystemExit('Install a CJK font such as Noto Sans CJK, then rebuild. No font files are distributed here.')
    renderer.plt.rcParams['font.family'] = [font, 'Arimo', 'DejaVu Sans']
    renderer.main()
    if not all((ASSETS / f'{name}.pdf').is_file() for name in NAMES):
        raise RuntimeError('One or more required figure PDFs were not generated.')
    audit.update({'font_family': font, 'solver_rerun': False,
                  'figures': {name: hashlib.sha256((ASSETS / f'{name}.pdf').read_bytes()).hexdigest() for name in NAMES}})
    (ASSETS / 'build_audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
