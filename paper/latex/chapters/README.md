# 当前分章编辑入口

`00_abstract.tex` 和 `01.tex`—`09.tex` 全部为本轮独立维护的正文源文件。`../main.tex` 直接加载它们，不再调用旧 `source_loader.tex`，也不从 `source_main.tex` 自动重生成。旧连续稿与加载器仅作为历史材料保留，不是本轮编辑入口。

第二章继承上一轮独立改稿；第三章基于此前独立维护的 `03.tex` 重组，保留实际物理模型、关键公式标签及数值边界，没有用旧连续稿覆盖。其他章节按本轮三级目录重写。

图表在 `../scripts/build_assets.py` 中从锁定输入生成。正文增删或公式调整后运行 `python -m unittest discover -s tests -p test_sources.py -v`，再运行 `python scripts/build_pdf.py`。该源码检查在 `paper/latex/` 运行。全部模型实验另在 `experiments/paper_robustness_20260926/`，编译不自动重跑优化器。
