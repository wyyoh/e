# 2026 研赛模板迁移与检阅说明

## 来源与分支

- 仓库：wyyoh/e。
- 原稿：main 分支快照 `86aa4da46d7218e001d1012f804f0acece94ca60` 的 `paper/latex/main.tex`。
- 检阅分支：`paper/template-2026-review-20260925`；本次没有修改 main。
- 模板：用户上传的“2026研赛LaTeX论文模板.zip”及配套说明，不将教学模板视为官方格式认证。

## 编译与编辑

正式入口仍是 `paper/latex/main.tex`。在该目录执行：

```sh
latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
```

也可依次执行 XeLaTeX、BibTeX、XeLaTeX、XeLaTeX。Overleaf 使用 XeLaTeX，主文档选择 `main.tex`，需要保留整个 `paper/latex/` 目录。

第一次编译时，`source_loader.tex` 将完整原稿快照 `source_main.tex` 自动拆成 `chapters/00_abstract.tex` 与 `chapters/01.tex`—`09.tex`，不需要 Python 或 shell-escape。其后编译直接使用这些分章文件，不覆盖人工修改。首次编译后可在分章文件中继续编辑；题目和关键词在 `main.tex` 修改。请将后续人工修改后的章节一并提交到版本控制。只有需要从原始快照重新生成、且已备份人工修改时，才移走现有的分章文件重新编译。

`appendices.tex`、`q2_v7_figures.tex`、`references.bib` 保持原文件。`source_main.tex` 是迁移前完整快照，不作为编译入口。

## 本次迁移范围

保留九章论证顺序、摘要全文、关键词、模型与数值、9幅Q2 TikZ图、12条参考文献和全部附录，也保留原稿的“当前证据放置说明”。没有混用其他研究分支，没有重跑优化或重新验证科学结论。

使用模板的A4、25 mm页边距、中文标题和字体、摘要、图表及章节编号样式。关闭教学提示，不带入示例图、示例数值、队号或虚构AI使用声明。摘要仅局部收紧行距，不删字；长公式、宽表格、跨页表格及哈希换行由 `layout_fixes.tex` 处理。参考文献与附录末尾证据清单局部紧凑排版，避免孤立尾页。

唯一正文级修复是原稿单位列表中的 LaTeX 语法：`\text{体积：m^3}` 改为 `\text{体积：m}^3`，不改变单位含义。该修复发生在分章提取时，原始快照仍逐字节保留。提取后正文及摘要已与原稿进行去空白一致性检查。

字体文件不提交、不打包。作者已有的完整模板 `fonts/` 可自行放回；缺省使用类文件中的字体回退。此次本地PDF使用用户上传模板中的中文字体及本机可用的西文字体，因此字体环境变化可能导致分页不同。

## PDF 检阅范围与重要限制

本次导出的 `D题论文_2026模板_排版检阅版.pdf` 为71页，正文、附录及Q2矢量图均已编译。最终日志未出现未定义引用、重复标签、缺字或Overfull警告；含12条实际引用的文献。已渲染页面检查排版。

**原稿本来有18处明确标注“占位”的图，本次如实保留，未用模板示例冒充。**

**另有5幅原始PNG未能下载到本地编译环境，PDF以“检阅稿：原始图片未载入”方框明确标记。它们不是仓库文件丢失，也不是新分支删图。** 原图已按原Git blob SHA复制到新分支的 `paper/latex/figures/`，下列文件均保持原始内容：

| 图片 | 原始 Git blob SHA |
|---|---|
| safe_payload_heatmap.png | d6d17d578516177466408d02b16c20a22f0d451b |
| pareto_front.png | 2e1dadda1d6f735cf486f7058f19f79ef3bc21ba |
| reserve_vs_min_sorties.png | bbe465c812a82063ee6f75569746d8ac7dc77a04 |
| reserve_vs_safe_payload.png | d9dc79af7bcb7edbd1e7236850813f1ea83ff25e |
| map_single_routes.png | 3a8b49de553e865cc985b3a086c81298392e093c |

`main.tex` 为严格图片模式：缺原图时报错，不会悄悄用空框替代。`review.tex` 是本次环境受限时使用的显式检阅入口；不要将其缺图容错模式用于正式提交。仓库中的原PNG齐全，可在具备完整文件的环境编译 `main.tex`；完整原图版PDF在本环境未能实编确认，图像尺寸可能使分页不同。

本PDF只用于检阅排版和原稿内容，不是已清除占位图、已完成内容审定或已经官方格式核验的提交版。

## 2026-09-26 structure revision

Review branch: paper/structure-revision-v2-20260926.

This revision keeps the formal numerical selections in paper_integration/FINAL_SELECTION.json unchanged and reorganizes the manuscript around the competition-facing chain **model -> solution process -> concrete plan -> verification**.

Main changes:

- Q1 expands the exact MILP / symmetry-compressed MILP / count-state DP methodology.
- Q2 expands the joint scheduling model, two-stage battery recovery, deterministic aircraft-battery event decoder, ALNS destroy/repair/local operators, and independent lower-bound certification route.
- Q3 corrects terrain blockage semantics (additional propagation loss, not a hard LoS veto), and expands communication-state constraints, relay lifecycle, candidate screening, joint scheduling, and continuous verification.
- Q4 explains how frozen transport/relay relations generate indivisible task blocks and distinguishes stock surplus from time-axis idleness.
- The editorial-only evidence-placement note was removed from the manuscript.
- Chapters 8 and 9 were shortened so that more of the body is devoted to Q2/Q3 modeling and solution steps.

No new formal Q1/Q2/Q3/Q4 headline result is introduced by this writing revision.
