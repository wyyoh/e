# D题：山区洪涝灾害下无人机运输与通信协同优化

`main` 是当前正式结果与论文工程的唯一入口。**先读 `paper_integration/FINAL_SELECTION.json`，再进入各问目录。** 历史实验保留在 `archive/` 或 `experiments/`，存在于仓库不等于当前正式结论。

## 当前正式结果

| 问题 | 正式入口 | 当前结果 |
|---|---|---|
| Q1 | `problems/D/q1/` | 18架次；59.131296022053 kWh；546.266929148593 min累计作业 |
| Q2 | `q2_final/solution/main_23/` + `problems/D/q2/evidence_v7/` | 23架次；5693.231489105106 s；66.21445957313102 kWh；认证LB 5433.956428 s |
| Q3 | `problems/D/q3/release_v6/time/` | 23运输+4中继；5836.969929328251 s；68.93941621018112 kWh |
| Q4 | `problems/D/q4/CURRENT_INPUT.json` | 严格K=2缺口1；K=3缺口7 |

Q2和Q3都**不宣称完整原问题全局最优**。Q3采用明确记录的 hover-compatible 中继转场模型；旧5755候选域的4中继下界和旧0.50/0.55 dB鲁棒结论不继承。Q4严格继承Q3 V6/time日程；旧relay-copy等敏感性未针对V6重跑。新增压力检验的范围与结果见 `experiments/paper_robustness_20260926/`，不与旧实验混用。

## 论文入口

- [当前LaTeX工程](paper/latex/README.md)：从 `paper/latex/main.tex` 编译；编辑 `chapters/`、`expanded_sections/` 和 `repair_sections/`。
- [已发布检阅PDF](paper/review/D_paper_completed_20260926.pdf)：2026-09-26发布版共92页，正文72页，40条文献及来源记录。
- `paper/latex/main_merged.tex` 是派生阅读版；修改分章后用导出脚本更新，不作为另一套独立维护的正文。
- 在仓库根运行 `python3 .github/scripts/ci_review.py`，在临时副本中检查与编译，输出到忽略的 `review-build/`，不改写源码和已发布PDF。
- `main` 推送、面向 `main` 的PR和手动构建统一使用 `.github/workflows/build-review-pdf.yml`。

旧连续稿、自动拆章加载器及旧流程已经归入 [论文历史目录](paper/archive/pre_cleanup_20260927/README.md)。不要删除当前 `chapters/` 后再从旧稿生成。

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
5. 历史研究材料归档，普通编译缓存不跟踪；正式PDF、矢量图和实验日志不得一并清除。
6. 最终投稿前仍需以当前选择锁对论文正文、附录和图表做一致性检查。
