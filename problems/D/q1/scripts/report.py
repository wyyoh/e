"""Create the two numerical narrative reports from inspected computed outputs."""
import argparse
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from model.io import ROOT
from scripts.validate import read_csv


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(map(str,row))+' |' for row in rows])+'\n'


def report(out,docs):
    out=Path(out);docs=Path(docs);docs.mkdir(exist_ok=True,parents=True)
    load=lambda name:json.loads((out/name).read_text(encoding='utf-8'))
    summary=load('objective_summary.json');lex=summary['lexicographic']
    front=read_csv(out/'pareto_front.csv');payload=read_csv(out/'max_safe_payload.csv')
    batches=read_csv(out/'optimal_batches.csv');sens=load('sensitivity_summary.json')
    thresholds=[r for r in read_csv(out/'reserve_thresholds.csv') if r['sorties_change']=='True']
    distance=load('distance_crosscheck.json');validation=load('validation_report.json')
    regression=load('regression_report.json')
    text=f'''# 问题一计算结果

数据全部由原始附件重新读取。主模型采用用户确认的 O01 中心 WGS84 AEQD 平面直线与完整像元遍历，基准返航余量20%。所有数值是给定物理模型的计算结果，不是实际飞行测试数据。

## 基准词典序方案

先最少架次，再最低能耗，再最短累计作业时间：**{lex['sorties']} 架次、{lex['energy_kwh']:.12f} kWh、{lex['time_min']:.12f} min**。这里的能耗最低以固定最少架次为前提；无架次限制的最低能耗见第二个 Pareto 点。逐箱分配共80行，见 `results/box_assignment.csv`，完整批次见 `optimal_batches.csv`。

'''
    text+=table(['架次','服务区','机型','箱数','质量 kg','体积 m³','能耗 kWh','累计贡献 min'],
                [(b['batch_id'],b['service_area'],b['aircraft_type'],len(json.loads(b['box_ids'])),
                  f"{float(b['mass_kg']):g}",f"{float(b['volume_m3']):.3f}",f"{float(b['energy_kwh']):.9f}",f"{float(b['time_s'])/60:.6f}") for b in batches])
    text+='\n## 45 个最大安全载荷\n\n'
    text+=table(['服务区','A / kg','B / kg','C / kg'],
                [(s,*[f"{float(next(r['safe_payload_kg'] for r in payload if r['service_area']==s and r['aircraft_type']==m)):.9f}" for m in 'ABC'])
                 for s in sorted({r['service_area'] for r in payload})])
    limited=[r for r in payload if r['energy_limited']=='True']
    text+=f"\n共45项，{len(limited)}项受能量约束，其余达到额定质量上限；这不是箱子体积容量，组批仍独立检查体积。载荷表包括预算、能量和返航SOC。\n"
    text+='\n## 完整不同 Pareto 目标向量\n\n'
    text+=table(['架次 N','总能耗 kWh','累计时间 min'],[(r['sorties'],f"{float(r['energy_kwh']):.12f}",f"{float(r['time_min']):.12f}") for r in front])
    if len(front)==2:
        a,b=front
        de=float(a['energy_kwh'])-float(b['energy_kwh']);dt=float(b['time_min'])-float(a['time_min'])
        text+=f"\n增加1架次可节省 {de:.9f} kWh（{100*de/float(a['energy_kwh']):.6f}%），累计时间增加 {dt:.9f} min。差异来自 S008 从一趟C型改为两趟B型。全部代表分配在 `pareto_assignments.json`；不声称枚举所有同目标的箱号互换方案。\n"
    text+='\n## FFD 与精确解\n\n'
    text+=table(['机型范围','算法','架次','能耗 kWh','累计 min'],
                [(r['aircraft_type'],r['method'],r['sorties'],f"{float(r['energy_kwh']):.9f}",f"{float(r['time_min']):.6f}")
                 for r in read_csv(out/'baseline_summary.csv')])
    text+='\nFFD 两种排序均明确是启发式 baseline。混型 FFD 新开架次优先额定载荷较大的机型，所以本数据选到C型；其18架次虽达到最少架次，能耗仍显著高于精确混型方案。不同新建架次策略会有不同FFD结果，不能将本对照解释为所有启发式的能力上限。\n'
    text+='\n## 安全余量临界点\n\n'
    text+=f"在完整 [0,1) 范围枚举 {sens['candidate_events']} 个不同候选事件；{sens['sortie_change_events']} 个全局架次变化（最后一个转为不可行），{sens['batching_change_events']} 个最优模式代表变化。5%–40% 网格另有36×45条安全载荷记录。\n\n"
    text+=table(['阈值 α / %','受影响服务区','左侧与阈值自身架次','严格右侧架次'],
                [(f"{100*float(r['threshold']):.12f}",', '.join(json.loads(r['affected_areas'])),r['sorties_at'],r['sorties_right'] or '不可行') for r in thresholds])
    text+='\n阈值本身仍可行：区间采用首段左闭、后续左开、右闭；1是定义域外端点。阈值CSV保留未四舍五入的完整浮点值，百分比展示值不可直接用于边界判定。\n'
    text+='\n超过最后阈值时，S008 的14kg饮用水单箱已无任何机型可行，而货箱不能拆分，因此全任务不可行。最优模式改变的详细区间在 `reserve_optimal_segments.csv`；架次不变也可能因某种批型失效而更换机型或拆分组合。\n'
    text+='\n## 空间交叉检查与回归\n\n'
    text+=f"AEQD 与 WGS84 测地距离最大绝对差 {distance['max_absolute_distance_difference_m']:.12g} m，最大相对差 {distance['max_relative_distance_difference']:.12g}；最大载荷差 {distance['max_absolute_payload_difference_kg']:.12g} kg。两者可行模式集合和选中组批代表完全相同；目标差低于数值容差。Q1 径向投影性质解释了这种一致性，主模型没有改成测地距离。\n\n"
    text+=f"原始箱级 MILP、对称压缩 MILP 与 DP 在15区的目标均一致。最后的历史回归状态：**{regression['status']}**。完整枚举与独立重算才构成优化证据，回归匹配只作外部一致性检查。\n"
    text+='\n## 图\n\n'+''.join(f'![{label}](../figures/{name}.png)\n\n' for label,name in [
        ('单点直达路线','map_single_routes'),('安全载荷','safe_payload_heatmap'),('Pareto','pareto_front'),
        ('余量与载荷','reserve_vs_safe_payload'),('余量与架次阶梯','reserve_vs_min_sorties')])
    (docs/'q1_results.md').write_text(text,encoding='utf-8')

    tree=ET.parse(out/'tests.junit.xml');suite=tree.getroot().find('testsuite')
    tests=suite.attrib
    reproduced=load('reproducibility_report.json')
    integer=load('pareto_integer_audit.json')
    geocheck=read_csv(out/'geometry_validation.csv')
    failed=int(tests['failures'])+int(tests['errors'])
    if failed:raise AssertionError('Cannot publish successful validation narrative with failed tests')
    logs=[l for p in (out/'solver_logs').rglob('*.json') for l in json.loads(p.read_text(encoding='utf-8'))]
    max_gap=max(l['mip_gap'] for l in logs)
    nonzero=[l for l in logs if l['mip_gap']!=0]
    if any(l['status']!=0 for l in logs):raise AssertionError('Unproven MILP stage in report')
    text=f'''# 问题一验证报告

## Material Passport

- 模式：确定性数值实验与可复现验证（academic-research-suite）。
- 数据：7个原始附件；SHA256固定清单；不读取Q2/Q3/Q4求解结果。
- 验证状态：独立重算 + 新目录完整复现；不是读取历史 pass 标志。
- 统计假设检验、p值、抽样因果推断等11类统计谬误检查均不适用，本任务是确定性有限组合优化。

## 新执行测试

`python -m pytest tests -q --junitxml=results/tests.junit.xml`：**{tests['tests']}项，{tests['failures']}失败，{tests['errors']}错误，{tests['skipped']}跳过**。原始输出 `tests.log` 和 JUnit XML 已保存。

覆盖 DEM 完整遍历、作业高度、空/满航程与3/2指数、单调性、空载能耗、唯一安全载荷根、80箱恰好一次、不跨区、质量、独立体积、安全余量、返程空载和爬升、完整作业时间、目标重算、MILP/DP、精确事件边界、重复计数模式副本与限时状态处理。

## 独立几何与物理

- TIF和MAT逐像元、中心坐标及仿射边界一致；15条航段的全部相交像元集合与 GeographicLib 条带区间求交一致。
- 0.25m密采样总计漏过 {sum(int(r['sample_missed_cells']) for r in geocheck)} 个真实相交像元；采样最大值是否相同逐区记录，不把采样当完整性证明。
- AEQD/测地线距离最大差 {distance['max_absolute_distance_difference_m']:.12g} m，相对差 {distance['max_relative_distance_difference']:.12g}。
- 45个安全载荷 Brent 根与独立公式二分根全部一致，最大差 {validation['max_payload_root_error_kg']:.12g} kg。
- 独立检查从原始箱子质量/体积重算所有选中架次、两套 Pareto 分配，以及 {validation['milp_solutions_recalculated']} 个MILP阶段解（含原始完整箱级日志），不相信日志中的能耗、时间或PASS字段。

## 求解器交叉验证

每区完整箱子子集二元MILP和数量DP均核对 min N、固定N min E、固定N/E min T、无N约束min T；对称压缩二元副本MILP再次得到相同目标。60个原始箱级求解阶段及60个压缩阶段均保存 status、mip gap、dual bound、变量/约束数、runtime和箱号解。全部 status=0，{len(logs)-len(nonzero)}个阶段gap=0，另{len(nonzero)}个阶段有机器精度残差，最大相对gap={max_gap:.12g}。该残差出现在原始S001第3阶段，原目标上下界差约3.70e−8 s，低于1e−7 s时间容差；DP与压缩MILP再次一致。限时负例要求明确返回未证明最优，不转换为infeasible。

整数系数零容差 Pareto 复算得到 {integer['integer_objective_vectors']} 个向量，恢复原系数后仍为相同的两个容差不同向量。量化单位1e−12 kWh/1e−9 s，80架次误差上界4e−11 kWh/4e−8 s，明确低于主比较容差。该审计检验容差敏感性，不是对真实物理模型的验证。

## 七类指定负例

| 错误 | 检出方式 |
|---|---|
| 将3/2改成1 | 独立航程中间值与独立能量重算不符 |
| 漏返程爬升 | 独立往返能量检查失败 |
| 起飞载荷套用返程 | 返程载荷独立公式检查失败 |
| 跨区混箱 | 交换两区箱子仍保留全覆盖，区域检查失败 |
| 重复分配同箱 | 原始ID计数检查失败 |
| 只看质量不看体积 | S001两箱卫生用品质量可行但A型体积超限，独立检查拒绝 |
| thin Bresenham替代 | 原始S001航段像元集合与完整集合不等；另测角点/沿边界 |

以上负例是真正执行故障注入并断言检查器抛错，不是把应当失败的注释当验证。

## 阈值边界

569个不同rho事件逐模式验证 rho−ε 可行、rho本身可行、rho+ε不可行；8个改变全局最少架次的事件重新求解左/中/右全问题。左连续边界和不可行区间均有测试。19个最优代表变化记录在独立区间表。

## 清洁复现与最终回归

`python scripts/reproduce.py` 在此前不存在的新目录从原始输入完整重跑：**{reproduced['status']}**。{len(reproduced['numeric_files'])}个确定性数值文件与5幅图逐字节一致；独立检查器的目标也完全相同。求解耗时、平台元数据与可交换箱号的求解器代表不要求字节一致，完整箱级历史证据数量单独记录。

历史回归在所有计算和独立检查之后执行：**{regression['status']}**。回归目标只位于 tests/regression_targets.json，model/solver不导入它；出现不一致会写 REGRESSION_MISMATCH.md，而不会改输入或拟合公式。

## 可证明与不可证明

在已指定AEQD几何、原始参数、统一物理公式和显式数值容差下，有限候选完备、整数模型与DP互证，支持Q1模型全局最优和完整Pareto向量集。仍不是无限精度形式化证书、现实飞行试验、天气/电池/障碍物安全保证，也不证明Q2/Q3/Q4。
'''
    (docs/'q1_validation.md').write_text(text,encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'results')
    parser.add_argument('--docs',type=Path,default=ROOT/'docs');args=parser.parse_args()
    report(args.output,args.docs)
