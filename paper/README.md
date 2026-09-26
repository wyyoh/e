# 论文工作区

**编辑与编译入口：`latex/main.tex`。** 当前论文直接加载独立维护的 `latex/chapters/00_abstract.tex` 和 `01.tex`—`09.tex`，不自动从旧连续稿生成章节。

## 当前文件分工

| 路径 | 作用 |
|---|---|
| `latex/chapters/` | 摘要和第一至九章 |
| `latex/expanded_sections/` | 正文接入的22份扩展论证 |
| `latex/repair_sections/` | 搜索过程、下界推导、联合求解与来源说明 |
| `latex/tables/`、`latex/revision_tables/` | 可编辑结果表与对应CSV |
| `latex/references.bib` | 参考文献与来源记录的维护入口 |
| `latex/appendices.tex` | 箱号、日程、实验参数与来源附录 |
| `latex/figures/`、`latex/figures_generated/` | 编译使用的图形资产 |
| `latex/main_merged.tex` | 从分章导出的阅读版，不单独维护 |
| `review/D_paper_completed_20260926.pdf` | 已发布92页检阅稿 |
| `review/completed_source_identity_20260926.json` | 2026-09-26发布快照及文件身份记录 |

正文与正式结果的对应仍以 `../paper_integration/FINAL_SELECTION.json` 为准。发布稿为92页，正文72页，40条实际引用的文献和来源记录；后续编译的实际分页以新构建产物为准。

## 检查与编译

从仓库根运行：

```sh
python3 .github/scripts/ci_review.py
```

它在临时副本中执行仓库检查、正文自检、单元测试与严格XeLaTeX/BibTeX编译，输出到根目录的 `review-build/`。不会运行求解器，也不会覆盖发布PDF。

已安装TeX工具链时也可进入 `latex/` 运行 `python3 scripts/build_pdf.py`，根级生成的 `main.pdf` 和辅助文件均由论文路径限定的忽略规则管理。详细依赖和独立工程用法见 [LaTeX说明](latex/README.md)。

## 历史材料

旧连续稿、拆章加载器、旧版排版片段、改稿说明和被替代工作流位于 [archive/pre_cleanup_20260927/](archive/pre_cleanup_20260927/README.md)，只供追溯。不要将其作为当前编辑或CI入口，也不要删除 `chapters/` 来恢复旧稿。

已发布的身份记录是历史快照，不随日常README维护重写。原README同样保存在归档目录。正文、模型参数、结果锁和研究验证证据未在本次仓库维护中修改。
