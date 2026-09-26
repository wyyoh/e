# D题论文 LaTeX 扩写续写完成版

## 打开与编辑

**主入口：`main.tex`。** 本包是一套完整的论文排版工程，不是仅含部分章节的增量补丁。

- `chapters/00_abstract.tex`：摘要。
- `chapters/01.tex`—`09.tex`：第一至九章。
- `expanded_sections/`：接入正文的22份新增方法推导、机制解释与结果分析。
- `repair_sections/`：保留上一轮修复的搜索步骤、有效下界、联合求解与来源说明。
- `tables/`、`revision_tables/`：完整可编辑表格；后者为12份新增描述性分析表及逐表CSV。
- `references.bib`：40条实际引用的文献及来源记录。
- `appendices.tex`：完整箱号、执行日程、参数记录与来源披露。
- `figures/`、`figures_generated/`：正文引用的现有插图，包含原有矢量图形PDF，不是本轮新生成的论文PDF。
- `main_merged.tex`：将72份实际加载的TeX文件展开后的单文件阅读/编辑版本。

`main_merged.tex`也需与本包的`format.cls`、`references.bib`和图片目录放在同一根目录，不能只拷贝一份tex就丢弃依赖。日常维护建议编辑分章文件，再运行合并脚本。

## 本轮完成内容

本包以上一轮完整风险修复稿为基础，重新接入已保存的扩写内容，并补齐第七至九章、表格依赖、参考文献和源文件接口。扩充集中于需求结构、能量函数性质、精确组批可分离性、双资源调度、定价与下界、中继事件区间、固定结构恢复以及逐组资源核算，没有用占位段落补齐篇幅。

新增12份表由锁定方案重新汇总，包括机型分工、飞机占用、逐箱交付进度、电池接续、运输和中继能耗、实际通信保障工作量及组织配置代价。它们属于对保存结果的描述性复算，不是本轮重新运行优化器所得的新最优解。

参考文献共40条，其中39条为公开论文、书籍、标准或勘误，1条为已经披露的非公开候选资料记录。40条均在实际正文/附录中引用，没有使用`nocite{*}`堆积未引用条目。新增26条公开文献的核对来源与引用用途见`reference_audit.json`和`reference_audit.csv`。

## 与此前版本的关系

- 完整文本基础：上一轮68页风险修复稿的真实源码，不把68页旧稿改名冒充扩写成稿。
- 扩写参考：已保存的`e6329c2bbc2cdd983c0dc412bef93d80820f2356`中间快照及本轮完成内容。
- 本轮检查时远端main：`773567ffe32e6827889aef4f35b0d72aa8e6698f`。
- 本包是**现在新完成的源文件交付**，不是此前所谓“96页成稿”的找回版本。
- 本轮未修改GitHub main，也没有改写正式结果锁、物理参数或求解器。

## 本轮检查（不生成论文PDF）

1. 源图递归检查：第一至九章、全部输入文件、引用图片、公式标签、图表标签和BibTeX键。
2. 19项单元检查全部通过，保留了输入哈希、箱号唯一性、正式数值、分组向量和方法来源检查。
3. 12份新增表及匹配CSV、分析JSON共25个文件重新生成后逐字节一致。
4. `main.tex`与`main_merged.tex`分别运行XeLaTeX **`-no-pdf`** 和BibTeX检查；不调用PDF驱动。最终缺字、未定义引用、重复标签、Overfull、Underfull和LaTeX警告均为0。

这类无PDF排版处理只验证TeX处理与引用依赖，不等同于整篇PDF的逐页视觉检查。本轮未生成论文PDF，不声明正文或总PDF页数。不同字体、TeX版本与最终图表布局可能改变分页。

查看：`checks/source_check.json`、`checks/unit_tests.log`、`checks/table_regeneration.json`和两个`*_tex_no_pdf.json`。

## 源码自检与表格复算

以下命令不生成论文PDF，也不重跑四问优化器：

```sh
python scripts/check_source.py
python -m unittest discover -s tests -v
python scripts/build_expanded_tables.py
python scripts/export_merged_tex.py
```

需要验证TeX处理时：

```sh
python scripts/check_tex_no_pdf.py
python scripts/check_tex_no_pdf.py --entry main_merged.tex
```

`check_tex_no_pdf.py`需要安装XeLaTeX，以及BibTeX或bibtex8；临时XDV文件会自动删除，只保留核验日志。纯Python源图检查与新增表生成使用Python标准库；原有完整绘图/审计生成器还会使用NumPy、SciPy、pandas、matplotlib等，不是打开本包的前置要求。

## 之后自行生成PDF

用户需要PDF时，可在根目录以XeLaTeX编译`main.tex`：

```sh
xelatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
xelatex -interaction=nonstopmode -halt-on-error main.tex
xelatex -interaction=nonstopmode -halt-on-error main.tex
```

也可使用包内`python scripts/build_pdf.py`。上述PDF生成命令**本轮没有执行**。若环境只有`bibtex8`，构建脚本会使用该备选。

字体文件没有随包分发。类文件保留现有字体回退，测试使用TeX可用的中文字体环境；上传到在线LaTeX环境时选择XeLaTeX。无需为编译正文重新准备几十MB的模型运行包，因为本包已包含使用到的图表与源数据摘要。

## 结果与来源说明

四问正式数值不变：问题一18架次；问题二23架次、5693.231489 s与既有有效上下界；问题三23运输+4中继、5836.969929 s；问题四两组/三组缺口1/7。

保存方案的名义可行性、有限预算搜索、固定方案抗扰动和允许修复后的结果分别呈现。来源披露及历史记录状态仍保留在附录：候选资料的作者/团队归属/授权待核验，历史最好解的全程搜索日志未补造。这些事项没有通过删除段落或修改方法名称来规避。

`provenance/previous_delivery/`为历史交付说明，里面的旧页数和检查结果仅指旧版本；本轮以根目录README及`checks/`为准。
