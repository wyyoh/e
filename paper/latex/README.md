# D题论文：当前LaTeX工程

**主入口：`main.tex`。** 直接维护 `chapters/00_abstract.tex` 和 `chapters/01.tex`—`09.tex`，不通过旧连续稿生成章节。

## 编辑对象

- `chapters/`：摘要与第一至九章。
- `expanded_sections/`：接入正文的22份方法推导、机制解释和结果分析。
- `repair_sections/`：搜索步骤、有效下界、联合求解及来源说明。
- `tables/`、`revision_tables/`：可编辑表格及对应CSV；后者含12份扩展分析表。
- `references.bib`：40条实际引用的文献与来源记录；来源核对见 `reference_audit.json` 和 `reference_audit.csv`。
- `appendices.tex`：完整箱号、执行日程、参数与来源附录。
- `figures/`、`figures_generated/`：当前编译需要的图形；矢量PDF应保留。
- `audit_inputs/`、`revision_inputs/`、`figdata/`、`figure_inputs/`：核验、复算与图表的输入，不能按“缓存”删除。
- `main_merged.tex`：派生阅读版。修改分章后运行 `python3 scripts/export_merged_tex.py` 更新，不并行维护两套正文。

当前已发布PDF位于 [`../review/D_paper_completed_20260926.pdf`](../review/D_paper_completed_20260926.pdf)，为92页检阅稿，其中第一至九章正文72页。40条记录包含39条公开论文、书籍、标准或勘误以及1条已披露的候选来源记录。实际发布身份见 `../review/completed_source_identity_20260926.json`。

## 推荐：隔离构建

在仓库根执行：

```sh
python3 .github/scripts/ci_review.py
```

需要Python 3、git、XeLaTeX、BibTeX（或bibtex8）及pdfinfo。脚本先运行仓库整洁性回归检查，再复制当前论文到临时目录，重新执行源图检查、正文测试、BibTeX和多轮XeLaTeX。临时副本不继承旧的aux、bbl、toc或编译日志，构建结束后自动释放。

新PDF、编译日志、测试记录和 `validation.json` 写入仓库根的 `review-build/`。脚本核对原论文目录和Git状态未被构建改变；已发布PDF不会被覆盖。`main`推送、PR和手动运行均使用同一份 `.github/workflows/build-review-pdf.yml`，该流程只读挂载仓库，只给产物目录写权限。

GitHub Actions中的Debian工具链安装清单见工作流，已包含模板所需的 `texlive-science`、`texlive-plain-generic` 和中文字体。编译现有正文不需要重跑优化器或安装绘图依赖。

## 独立工程的直接构建

只有本目录的独立副本时，在该目录运行：

```sh
python3 scripts/build_pdf.py
```

或执行：

```sh
xelatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
xelatex -interaction=nonstopmode -halt-on-error main.tex
xelatex -interaction=nonstopmode -halt-on-error main.tex
```

这些命令生成本目录的 `main.pdf`、辅助文件和 `build_logs/`。它们不纳入版本控制，不影响 `../review/` 的正式发布文件。需要再次跑全部测试时优先使用隔离构建，避免“独立交付包不含main.pdf”的检查被本地生成文件触发。

`references.bib`是文献维护来源；本目录的 `main.bbl`由BibTeX重新生成。2026-09-26的冻结文献排版快照保存在 `../review/publication_references_20260926.bbl`，不参与当前编译。

## 自检与复算

```sh
python3 scripts/check_source.py
python3 scripts/build_expanded_tables.py
python3 scripts/export_merged_tex.py
python3 scripts/check_tex_no_pdf.py
```

上述脚本各有明确用途：源图检查不等于页面视觉验收；表格复算不重跑优化器；`check_tex_no_pdf.py`不生成PDF。检查输出可能更新 `checks/` 下的记录；正式发布证据另保存在 `../review/`。无PDF检查日志和普通TeX中间输出已按论文路径忽略，不使用全仓 `*.pdf` 或 `*.log` 忽略规则。

## 版本与历史

本工程是实际完成的92页版，不是此前未完成的96页扩写检查点。旧 `source_main.tex`、`source_loader.tex`、缺图检阅入口、旧排版片段及改稿说明已移至 [`../archive/pre_cleanup_20260927/`](../archive/pre_cleanup_20260927/README.md)，不再作为当前入口。当前源码缺章时应恢复对应Git版本，不能运行旧加载器覆盖人工维护的章节。

2026-09-26发布身份记录中的119个哈希描述当时交付快照；本次README导航修改单独记录，原README保留于归档，不改写历史身份记录。正文TeX、模型参数、正式结果锁、图表和验证数据保持不变。字体文件不随仓库分发。
