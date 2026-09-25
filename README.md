# D题：山区洪涝灾害下无人机运输与通信协同优化

本仓库 `main` 是当前论文与正式结果的发布入口。正式机器可读选择统一由 [`paper_integration/FINAL_SELECTION.json`](paper_integration/FINAL_SELECTION.json) 决定；历史目录与研究分支用于追溯，不自动覆盖该选择。

| 问题 | 当前正式版本 | 正式结果 |
|---|---|---|
| Q1 | `problems/D/q1` | 18架次；59.131296022053 kWh；546.266929148593 min累计作业时间 |
| Q2 | `Q2-EVIDENCE-V7-FOCUSED` | 23架次；5693.231489105106 s；66.21445957313102 kWh；LB 5433.956428 s |
| **Q3** | **`Q3-BOTTLENECK-V6 / time`** | **23运输+4中继；5836.969929328251 s；68.93941621018112 kWh** |
| **Q4** | **`Q4-STRICT-FROM-Q3-V6`** | **严格K=2缺口1；K=3缺口7** |

Q2 makespan全局最优尚未证明。Q3完整问题也未证明全局最优；V6使用明确记录的hover-compatible中继转场高度模型，旧有限候选域四中继下界与旧0.50/0.55dB鲁棒结论不继承。Q4严格继承V6/time日程；旧relay-copy敏感性未针对V6重跑。

当前Q3入口：[`problems/D/q3/README_CURRENT.md`](problems/D/q3/README_CURRENT.md)。当前Q4入口：[`problems/D/q4/README_CURRENT.md`](problems/D/q4/README_CURRENT.md)。论文主文件仍为 `paper/latex/main.tex`；本次结果切换后，论文中的旧Q3/Q4数字需单独做一致性更新。
