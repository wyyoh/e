# main 分支状态与正式结果说明

`main` 是当前正式整合分支；“存在于main”不等于正式结果，正式选择以 `paper_integration/FINAL_SELECTION.json` 为准。

## 当前结果

- Q1：18架次，59.131296022053 kWh，546.266929148593 min。
- Q2：23架次，5693.231489105106 s，66.21445957313102 kWh；认证 `5433.956428 <= T* <= 5693.231490 s`，未证明makespan全局最优。
- Q3：**Q3-BOTTLENECK-V6/time**，23运输+4中继，**5836.969929328251 s，68.93941621018112 kWh**。
- Q4：**Q4-STRICT-FROM-Q3-V6**；严格K=2缺口1、K=3缺口7。

## 当前目录边界

正式层：`problems/`、`q2_final/`、`paper/`、`paper_integration/`。

研究层：`experiments/`。

历史层：`archive/`；Q3旧 `release_final/` 和Q4旧 `results_v2/` 因直接承担版本审计，留在各问题目录并明确标记历史。

Q2早期 `q2_closing`、verification V2/V3、根级global verify代码和旧q2_final proof均已归档到 `archive/q2/`。

## Q3/Q4边界

V6采用hover-compatible中继转场模型。旧5755候选域四中继下界、旧+0.50/+0.55 dB鲁棒结论不继承。旧Q4 relay-copy/N-1/Pareto敏感性也未针对V6日程重跑。

## 论文状态

`paper/latex/main.tex`、`appendices.tex`、论文数据入口和当前Q3/Q4主数字已同步到V7/V6口径。旧代理筛查数据仅作为历史对照，并在数据文件中标注scope。

完整V6运行包未作为36MB二进制提交到仓库；其SHA-256由选择锁记录，仓库展开保存正式决策、航班、中继与验证摘要。
