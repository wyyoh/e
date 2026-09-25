# D题当前证据整合入口

正式选择只认 `FINAL_SELECTION.json` 与 `SELECTION_LOCK.json`。

| 问题 | 当前版本 | 当前主结果 |
|---|---|---|
| Q1 | frozen exact model | 18架次；59.131296022053 kWh |
| Q2 | Q2-EVIDENCE-V7-FOCUSED | 23架次；5693.231489105106 s；66.21445957313102 kWh；LB 5433.956428 s |
| Q3 | Q3-BOTTLENECK-V6 / time | 23+4架次；5836.969929328251 s；68.93941621018112 kWh |
| Q4 | Q4-STRICT-FROM-Q3-V6 | K2缺口1；K3缺口7 |

## Cross-question handoff

- Q1→Q2：共用原始物理输入，不强制继承Q1组批。
- Q2→Q3：Q2提供运输参照；Q3允许联合调整运输/通信，但当前V6主选使用已验证的23运输+4中继结构。
- Q3→Q4：严格冻结V6/time任务、绝对时刻和实际保障关系。

## Evidence boundaries

- Q2：V7给出全域有效LB/UB，但没有闭合全局最优。
- Q3：采用hover-compatible中继转场高度；旧5755候选域四中继下界和旧0.50/0.55dB鲁棒结论不继承。V6主选只证明在保存模型中的完整可行性，不证明全局最优。
- Q4：当前严格结果已按V6/time重新核算；旧relay-copy、N-1、Pareto敏感性仍是历史结果，未针对V6重跑。

历史选择锁位于 `history/pre_q3_v6/`。V6迁移说明见 `Q3_V6_MIGRATION.md`。
