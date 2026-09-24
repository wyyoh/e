# Q2 Final Provenance

## Git history

最终整合分支：`research/q2-final-integration`。

其首个整合提交为真正的双亲 merge：

- `research/q2-closing` head: `1534e5370a29a0dc3d762cdee240c974abf9655a`
- `research/q2-assistant-parallel-v5` head: `0d6fb536889f6c9cead3ec7b9e851a2b7a0bbb54`

共同祖先为 `97187484cdf90ee3f90e194679ce231e97c0baa2`。

## What is selected

1. **主可行解**：assistant V5 的 23 架次解，因其与 closing 的 23 架次解具有相同零迟到、相同 makespan、相同架次数，但能耗更低。
2. **22 架次备选**：closing 构造性见证，作为“少架次但更慢”的多目标对照。
3. **原始数据与 DEM 审计**：closing 的 raw audit。
4. **固定任务瓶颈分析**：closing 的 B 型两机精确分配下界。
5. **全局有效下界**：assistant V5 重新定价确认的 5414.564006 s。
6. **搜索充分性证据**：closing 的 330 个定向邻域 + assistant 的扩展 ALNS / MILP；只用于支持“未发现更优”，不用于宣称全局最优。

## Important boundaries

- 第一层加权迟到 0 为全局最优。
- makespan 尚未证明全局最优。
- 23 架次不是最少可行架次数，因为 closing 已构造 22 架次可行解。
- 5414.564006 s 下界属于与原问题共享同一物理输入/流程的有效松弛证据；它不意味着存在 5414 s 的可执行方案。
- q2_closing 和 assistant V5 原始目录全部保留，不以 q2_final 覆盖历史证据。
