# D题：山区洪涝灾害下无人机运输与通信协同优化

`main` 是当前正式结果与论文工程的唯一入口。**先读 `paper_integration/FINAL_SELECTION.json`，再进入各问目录。** 历史实验保留在 `archive/` 或 `experiments/`，存在于仓库不等于当前正式结论。

## 当前正式结果

| 问题 | 正式入口 | 当前结果 |
|---|---|---|
| Q1 | `problems/D/q1/` | 18架次；59.131296022053 kWh；546.266929148593 min累计作业 |
| Q2 | `q2_final/solution/main_23/` + `problems/D/q2/evidence_v7/` | 23架次；5693.231489105106 s；66.21445957313102 kWh；认证LB 5433.956428 s |
| Q3 | `problems/D/q3/release_v6/time/` | 23运输+4中继；5836.969929328251 s；68.93941621018112 kWh |
| Q4 | `problems/D/q4/CURRENT_INPUT.json` | 严格K=2缺口1；K=3缺口7 |

Q2和Q3都**不宣称完整原问题全局最优**。Q3采用明确记录的 hover-compatible 中继转场模型；旧5755候选域的4中继下界和旧0.50/0.55 dB鲁棒结论不继承。Q4严格继承Q3 V6/time日程；旧relay-copy等敏感性未针对V6重跑。

## 目录

- `problems/D/q1/`：Q1正式精确模型、结果与验证。
- `q2_final/`：Q2正式primal方案；证明以 `problems/D/q2/evidence_v7/` 为准。
- `problems/D/q3/`：Q3当前V6及历史release。
- `problems/D/q4/`：Q4当前严格交接与历史V2敏感性。
- `paper/`：论文正文、附录、数据、图表脚本与QA。
- `paper_integration/`：四问正式选择锁、跨问接口与版本迁移说明。
- `experiments/`：仍有复用价值、但不自动改变正式口径的实验。
- `archive/`：已退出正式入口的历史研究材料；只用于追溯。
- `docs/`：仓库结构、环境与主干状态说明。

详细导航见 `docs/REPOSITORY_STRUCTURE.md`。

## 使用规则

1. 机器可读正式口径只认 `paper_integration/FINAL_SELECTION.json` 与 `SELECTION_LOCK.json`。
2. 旧目录、旧论文数字、有限域证书和历史搜索状态不得覆盖当前选择锁。
3. Q1累计作业时间与Q2/Q3并行makespan不是同一指标。
4. Q4不同型号资源不能互相抵扣；总件数不等于采购成本。
5. 历史目录不删除，只归档；需要恢复旧路径时通过Git历史或 `archive/` 读取。
6. 最终投稿前仍需以当前选择锁对论文正文、附录和图表做一致性检查。
