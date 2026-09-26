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
| `paper/latex/main.tex` | 当前论文编译入口 |
| `paper/latex/chapters/` | 独立维护的摘要及第一至九章 |
| `paper/latex/expanded_sections/`、`paper/latex/repair_sections/` | 主文引用的扩展论证和修复推导 |
| `paper/review/` | 已发布PDF、来源身份及验收证据 |

`paper/latex/main_merged.tex`为派生阅读版；文献维护入口是`references.bib`，不是编译生成的`main.bbl`。

## 2. Research layer

`experiments/`保存仍值得参考的实验。它们只有通过正式验收、更新选择锁和论文后，才可以改变正式结论。`experiments/paper_robustness_20260926/`保存新增压力试验驱动及范围说明。实验日志、证明材料和原始输入不属于论文构建缓存。

## 3. Historical layer

`archive/`保存已退出当前入口的研究材料：

- `archive/q2/q2_closing/`：Q2封口搜索、22架次见证及raw audit。
- `archive/q2/verification_v2/`、`archive/q2/verification_v3/`：早期Q2证明迭代。
- `archive/q2/global_verify_v1/`：原根级`src/tests/results/logs/data`、V1 manifest与实验说明。

Q3旧`release_final/`和Q4旧`results_v2/`仍位于各自问题目录，承担版本迁移审计，不能冒充当前正式结果。

`paper/archive/pre_completed_20260926/`保留上一轮归档测试；`paper/archive/pre_cleanup_20260927/`保留旧连续稿、自动拆章加载器、旧排版片段、改稿说明和被替代工作流。归档的工作流不在`.github/workflows/`下，不会自动触发。历史README中的旧入口说明只描述当时版本。

## 4. Build and evidence boundary

`.github/workflows/build-review-pdf.yml`是统一推送、PR和手动构建入口，调用`.github/scripts/ci_review.py`。源码在临时副本中编译，当前检阅产物与日志写入忽略的`review-build/`，随后由Actions发布为artifact。原有正式PDF与身份记录不自动覆盖。

`paper/latex/`根级aux、bbl、blg、log、out、toc及`build_logs/`为可再生输出，不跟踪；已发布文献排版快照保存于`paper/review/publication_references_20260926.bbl`。忽略规则只针对论文输出与明确的临时目录，不覆盖全仓PDF或实验日志。

## 5. Why historical research files are archived

研究仓库保留结果演化、旧证书、反例、历史方案和外部素材审计记录。“干净”指入口唯一、输出边界清楚、正文不误用旧数值，不是删除所有旧研究文件。对普通编译中间文件，旧版本仍可从Git历史取得；不需要在当前源码目录长期堆积。
