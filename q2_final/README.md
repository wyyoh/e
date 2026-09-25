# Q2 当前正式 primal 与证据入口

Q2正式primal保持：
- 23架次；
- 加权迟到0；
- makespan 5693.231489105106 s；
- 能耗 66.21445957313102 kWh。

主方案位于 `solution/main_23/`。当前最优性证据以 `problems/D/q2/evidence_v7/`（`Q2-EVIDENCE-V7-FOCUSED`）为准；本目录早期proof已移入archive。

当前认证区间：`5433.956428 <= T* <= 5693.231490 s`，UB归一化间隙4.554093092%。零加权迟到最优值为0，但makespan全局最优尚未证明。

## 历史材料

- 封口搜索、22架次见证、原始DEM审计：`archive/q2/q2_closing/`
- verification V2/V3：`archive/q2/verification_v2/`、`archive/q2/verification_v3/`
- 第一轮global verify：`archive/q2/global_verify_v1/`
- q2_final早期proof：`archive/q2/q2_final_legacy_proof/`

## 22架次对照

构造性22架次见证仍有效，但已知工期显著长于23架次主方案。历史完整见证位于：
`archive/q2/q2_closing/results/feasible_22_incumbent.json`。

论文应表述为：获得零加权迟到的23架次可行方案，完成时间94.887 min、能耗66.214 kWh；结合V7覆盖与定价证据，完成时间有可核验上下界，但不宣称全局最优。
