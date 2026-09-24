# 23 架次最终主方案

本目录固定最终论文主方案的“决策层”和核心指标。

- `decisions.json`：23 个架次的机型、原始箱号集合和服务区访问顺序。
- `metrics.json`：经完整事件排程后的最终指标。
- `actual_box_changes.json`：相对 q2_closing / V4 任务构成的唯一节能交换。

完整飞机、电池、逐箱、航段和阶段表可由已合并的
`experiments/q2_assistant_parallel_v5/code/`
对本目录的 decisions 重建；原始 closing 方案及其独立 raw replay 保留在 `q2_closing/`。

最终方案仍为：
- 23 架次，A/B/C=11/6/6；
- 8 架实体运输机，14 组共享电池；
- 零加权迟到；
- makespan 5693.231489105106 s；
- energy 66.21445957313102 kWh。

该方案没有改变决定 makespan 的 B 型六趟任务，因此 q2_closing 的固定 B 任务两机分配下界解释仍适用。
