# D题最终整合分支

本分支用于最终论文与复现，统一锁定 Q1–Q4 正式方案、证明范围与跨问数据继承。

- Q1：`problems/D/q1/`，18架次，59.131296 kWh。
- Q2：主解沿用 `q2_final/solution/main_23/`；最新证据放在 `problems/D/q2/evidence_v7/`，有效区间 `5433.956428 <= T* <= 5693.231490 s`，不宣称全局最优。外部网络论文22架次方案复核在 `problems/D/q2/external_audit/`，仅作对照。
- Q3：`problems/D/q3/release_final/primary/`，正式主方案 time：23运输+4中继，联合返航6340.439339 s，总能耗69.308531 kWh。
- Q4：`problems/D/q4/`，严格中继绑定为主口径；中继复制仅作敏感性。

仓库仅展开论文复现所需源码、文档、正式结果与关键审计；体量很大的历史搜索缓存和完整证书由 companion archive 的 SHA-256 锁定。机器可读选择见 `FINAL_SELECTION.json`。
