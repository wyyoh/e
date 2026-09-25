"""Rebuild four manuscript figure examples from traceable source data.
No new optimization or fabricated measurements. One plot per figure.
Uses Matplotlib defaults for colors; symbols and line styles provide redundancy.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import statistics
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]

def choose_font() -> str:
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in ['Noto Sans CJK SC', 'Noto Sans CJK JP', 'Microsoft YaHei', 'SimHei', 'WenQuanYi Zen Hei']:
        if name in available:
            return name
    raise RuntimeError('Install a CJK font; do not accept missing-glyph output.')

def main(out: Path) -> None:
    if out.exists() and any(out.iterdir()):
        raise FileExistsError('Use a new or empty figure output directory.')
    out.mkdir(parents=True, exist_ok=True)
    path = ROOT / 'data/visual_data.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    plt.rcParams.update({'font.family': choose_font(), 'font.size': 9,
                         'axes.unicode_minus': False, 'pdf.fonttype': 42,
                         'ps.fonttype': 42, 'svg.fonttype': 'none'})
    exported = []
    def export(fig, stem):
        for ext in ['pdf', 'svg', 'png']:
            dst = out / (stem + '.' + ext)
            fig.savefig(dst, format=ext, dpi=300)
            exported.append({'file': dst.name, 'bytes': dst.stat().st_size,
                             'sha256': hashlib.sha256(dst.read_bytes()).hexdigest()})
        plt.close(fig)

    # F1: each point is a matched pricing input; >1 means faster.
    p = data['pricing']
    fig, ax = plt.subplots(figsize=(6.30, 6.70))
    fig.subplots_adjust(left=.25, right=.94, top=.97, bottom=.14)
    ratios = [x['baseline_median_s'] / x['accelerated_median_s'] for x in p]
    for g, marker in zip('ABC', ['o', 's', '^']):
        ix = [i for i, x in enumerate(p) if x['type'] == g]
        ax.scatter([ratios[i] for i in ix], ix, marker=marker, s=30, label=g+'型定价')
    ax.axvline(1, linestyle='--', linewidth=.9, alpha=.65)
    ax.set_xscale('log', base=2)
    ax.set_xlim(.5, 8)
    ax.set_xticks([.5, 1, 2, 4, 8], ['0.5', '1', '2', '4', '8'])
    ax.set_yticks(range(len(p)), [str(x['node'])+' / '+x['type'] for x in p], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel('原版中位耗时 / 加速版中位耗时（倍，对数轴）')
    ax.set_ylabel('固定证书节点 / 机型')
    ax.spines[['top', 'right']].set_visible(False)
    ax.legend(loc='upper center', bbox_to_anchor=(.5, -.085), ncol=3, frameon=False, fontsize=8)
    export(fig, 'F01_pricing_paired_speedup')

    # F2: preserve paired seeds and duplicate uniform/feasible values.
    q = data['q3_sampling']
    methods = ['uniform', 'feasible', 'informed']
    fig, ax = plt.subplots(figsize=(6.30, 3.75))
    fig.subplots_adjust(left=.14, right=.96, top=.95, bottom=.27)
    for seed, marker in zip(sorted({x['seed'] for x in q}), ['o', 's', '^', 'D', 'v']):
        values = [next(x['sample_best_extra_db'] for x in q if x['seed'] == seed and x['method'] == m) for m in methods]
        ax.plot(range(3), values, marker=marker, linewidth=1, markersize=5, alpha=.8, label=str(seed))
    ax.axhline(.5, linestyle='--', linewidth=.9, alpha=.6)
    ax.text(2.05, .502, '0.5 dB', fontsize=8)
    ax.set_xlim(-.15, 2.40)
    ax.set_ylim(.40, .60)
    ax.set_xticks(range(3), ['均匀采样', '必要条件筛选', '关键点引导'])
    ax.set_ylabel('静态轨迹样本评分（dB）')
    ax.spines[['top', 'right']].set_visible(False)
    ax.legend(loc='upper center', bbox_to_anchor=(.5, -.15), ncol=5, frameon=False, fontsize=7.5, title='配对随机种子', title_fontsize=8)
    export(fig, 'F02_q3_paired_proxy_scores')

    # F3: a deterministic optimization interval, explicitly not a confidence band.
    b = data['q2_bounds']; lo = b['lb_s']/60; hi = b['ub_s']/60
    fig, ax = plt.subplots(figsize=(6.30, 2.20))
    fig.subplots_adjust(left=.10, right=.97, top=.95, bottom=.28)
    ax.plot([lo, hi], [0, 0], linewidth=2, marker='|', markersize=16)
    ax.scatter([lo], [0], marker='s', s=42)
    ax.scatter([hi], [0], marker='o', s=42)
    ax.annotate('有效下界\n'+f'{lo:.3f} min', (lo, 0), xytext=(0, 17), textcoords='offset points', ha='center')
    ax.annotate('可行上界\n'+f'{hi:.3f} min', (hi, 0), xytext=(0, 17), textcoords='offset points', ha='center')
    ax.text((lo+hi)/2, -.27, '确定性认证区间；不是统计置信区间', ha='center', fontsize=8)
    ax.set_xlim(89, 96.5); ax.set_ylim(-.48, .70); ax.set_yticks([])
    ax.set_xlabel('零加权迟到条件下的最优完成时间范围（min）')
    ax.spines[['top','left','right']].set_visible(False)
    export(fig, 'F03_q2_certified_interval')

    # F4: heterogeneous resources must remain separate, never a single cost bar.
    r = data['q4']; fig, ax = plt.subplots(figsize=(6.30, 4.15))
    fig.subplots_adjust(left=.24, right=.96, top=.96, bottom=.25)
    configs = [('inventory','原库存','o',-.21), ('pooled','全局共享最少','s',-.07),
               ('strict_2','严格两组','^',.07), ('strict_3','严格三组','D',.21)]
    for key, label, marker, offset in configs:
        ax.scatter(r[key], [i+offset for i in range(8)], marker=marker, s=33, label=label)
    ax.set_yticks(range(8), r['resource_names'])
    ax.invert_yaxis(); ax.set_xlim(0, 8); ax.set_xticks(range(9))
    ax.set_xlabel('分类型资源数量（架或组；不可跨类型抵扣）')
    ax.spines[['top','right']].set_visible(False)
    ax.legend(loc='upper center', bbox_to_anchor=(.4,-.19), ncol=4, frameon=False, fontsize=7.5)
    export(fig, 'F04_q4_typed_resource_counts')
    (out/'FIGURE_MANIFEST.json').write_text(json.dumps({'source_data_sha256':hashlib.sha256(path.read_bytes()).hexdigest(), 'font':choose_font(), 'outputs':exported, 'new_optimization':False}, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')

if __name__ == '__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=ROOT/'figures/generated');args=ap.parse_args();main(args.out)
