# Repository structure

## 1. Authoritative layer

| Path | Role |
|---|---|
| `paper_integration/FINAL_SELECTION.json` | 唯一机器可读正式选择 |
| `paper_integration/SELECTION_LOCK.json` | 与FINAL_SELECTION同步的锁文件 |
| `problems/D/q1/` | Q1正式模型 |
| `q2_final/solution/main_23/` | Q2正式primal |
| `problems/D/q2/evidence_v7/` | Q2当前证明证据 |
| `problems/D/q3/release_v6/time/` | Q3当前主方案 |
| `problems/D/q4/CURRENT_INPUT.json` | Q4当前冻结输入 |
| `paper/latex/main.tex` | 论文主文件 |

## 2. Research layer

`experiments/` 保存当前仍值得参考的实验。它们只有在通过正式验收、更新选择锁和论文后，才可以改变正式结论。

## 3. Historical layer

`archive/` 保存已退出当前入口的研究材料：

- `archive/q2/q2_closing/`：Q2封口搜索、22架次见证及raw audit。
- `archive/q2/verification_v2/`、`archive/q2/verification_v3/`：早期Q2证明迭代。
- `archive/q2/global_verify_v1/`：原根级 `src/tests/results/logs/data`、V1 manifest与实验说明。

这些目录可以引用，但不得在论文中被称为“当前正式结果”。

Q3旧 `problems/D/q3/release_final/` 和Q4旧 `results_v2/` 留在各自问题目录内，是因为它们直接承担版本迁移审计；入口文件已经明确标注为历史。

## 4. Why old files are archived instead of deleted

研究仓库需要保留：
- 结果演化证据；
- 旧证书与反例；
- 可复现的历史方案；
- 第三方/外部方案审计痕迹。

“干净”指**入口唯一、边界清楚、正文不误用旧数值**，不是删除所有旧文件。
