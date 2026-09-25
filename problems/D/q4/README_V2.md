# Q4 当前严格结果与历史敏感性

当前正式严格结果继承 `Q3-BOTTLENECK-V6/time` 的固定任务、时序与实际通信关系。

- K=2：完整枚举3种严格合法分区，最小分类缺口 **1**（仅缺1架C型运输机）。
- K=3：严格合法分区1种，分类缺口 **7**。

机器可读输入见 `CURRENT_INPUT.json`，结果见 `results_q3_v6/summary.json`。

旧 `Q4-SENSITIVITY-V2` 的relay-copy、N-1、Pareto与库存敏感性仍作为历史研究保留，但**未针对V6日程重新计算**，不得与当前严格主答案混用。
