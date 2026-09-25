# main 分支状态与正式结果说明

`main` 是当前正式整合分支；“存在于main”不等于正式结果，正式选择以 `paper_integration/FINAL_SELECTION.json` 为准。

## 当前结果

- Q1：18架次，59.131296022053 kWh，546.266929148593 min。
- Q2：23架次，5693.231489105106 s，66.21445957313102 kWh；认证 `5433.956428 <= T* <= 5693.231490 s`，未证明makespan全局最优。
- Q3：**Q3-BOTTLENECK-V6/time**，23运输+4中继，**5836.969929328251 s，68.93941621018112 kWh**；物理模型 `Q3-HOVER-COMPATIBLE-V5`。
- Q4：**Q4-STRICT-FROM-Q3-V6**；严格K=2缺口1、K=3缺口7。

## Q3/Q4迁移边界

旧 `problems/D/q3/release_final/` 与旧Q4敏感性目录保留为历史证据。当前Q3展开主结果为 `problems/D/q3/release_v6/time/`；当前Q4输入为 `problems/D/q4/CURRENT_INPUT.json`。

V6不继承旧5755候选域四中继下界，也不继承旧+0.50/+0.55dB鲁棒结论。旧Q4 relay-copy/N-1/Pareto敏感性未针对V6日程重跑。

完整V6运行包已独立验证，但本次GitHub连接器更新不上传36MB二进制运行包；其SHA-256记录在选择锁和迁移说明中。仓库展开保存当前主方案决策、航班、交付、中继与验证摘要。

## 论文状态

LaTeX主文件仍为 `paper/latex/main.tex`。本次仅切换正式数据入口，没有机械修改所有旧Q3/Q4正文和图；提交最终论文前必须做一次数字和图表一致性检查。
