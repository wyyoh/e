# 23架次正式主方案

本目录固定Q2正式primal的决策与核心指标。

- `decisions.json`：23个架次的机型、箱号集合和服务区访问顺序。
- `metrics.json`：完整事件排程后的核心指标。
- `actual_box_changes.json`：相对历史closing/V4方案的箱子交换说明。

完整飞机、电池、逐箱、航段和阶段表可由 `experiments/q2_assistant_parallel_v5/code/` 对本目录决策重建；历史closing及raw replay已归档到 `archive/q2/q2_closing/`。

正式指标：
- 23架次，A/B/C=11/6/6；
- 8架实体运输机，14组共享电池；
- 加权迟到0；
- makespan 5693.231489105106 s；
- energy 66.21445957313102 kWh。

当前全局证明证据请使用 `problems/D/q2/evidence_v7/`；历史固定任务瓶颈分析只作为机制解释。
