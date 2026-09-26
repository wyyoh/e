# main仓库维护：2026-09-27

基线：`06ef89d99da85f2e1e293cc459a782f18e8aac71`。本次只调整工程入口、构建流程、忽略规则和历史归档，不改写论文的学术内容或正式结果。

## 修复范围

1. 统一`.github/workflows/build-review-pdf.yml`覆盖main推送、面向main的PR和手动构建；旧`render-review.yml`与`build-structure-review-pdf.yml`移至历史目录。当前流程没有删除独立章节或忽略BibTeX错误的步骤。
2. 新增`.github/scripts/ci_review.py`。它在不继承aux、bbl和目录缓存的临时副本中检查与编译，原仓库只读，输出进入忽略的`review-build/`，不自动覆盖正式发布PDF。
3. 移出源码根级`main.aux`、`main.blg`、`main.log`、`main.out`、`main.toc`以及`build_logs/`。旧版本仍保留于基线提交的Git历史；`main.bbl`作为已发布文献排版快照移至`paper/review/publication_references_20260926.bbl`。
4. 新增仅限论文输出路径的忽略规则。正式PDF、矢量图、BibTeX库、图表输入以及模型实验日志不受忽略规则影响。
5. 旧连续稿、加载器、旧排版片段、模板及改稿说明归入`paper/archive/pre_cleanup_20260927/`。20个归档条目的原路径、新路径、Git blob SHA见该目录`manifest.json`。
6. 统一根README、paper工作区说明、LaTeX说明、发布说明和仓库导航。当前编辑对象只有`chapters/`及其引用的扩展/修复文件，`main_merged.tex`是派生阅读版。

## 保持不变

- 第一至九章、摘要、附录及实际加载的全部正文TeX。
- `references.bib`、正式表格、图形及核验输入。
- 已发布`paper/review/D_paper_completed_20260926.pdf`及原发布身份记录。
- `problems/`、`q2_final/`、`paper_integration/`、`experiments/`和根级`archive/`。

`FINAL_SELECTION.json`的基线Git blob为`31b72d19ac8d72e173af8f576df78f8538546153`。论文发布身份清单描述2026-09-26快照，不因当前README维护而重写；原README已按原字节归档。

## 验收方法

仓库根运行`python3 .github/scripts/ci_review.py`。新增8项仓库回归检查覆盖：未跟踪编译输出、忽略规则的正反例、统一安全工作流、归档字节、真实源图、文档入口及隔离副本。原有19项正文和数据测试保持不动。

随后严格执行XeLaTeX和BibTeX多轮构建，并记录页数、文献条数、原源码是否未改变及构建前后Git状态。输出为`review-build/validation.json`、`source-check.json`、`hygiene-tests.log`、`tests.log`、完整编译日志和PDF。Actions通过`paper-review-pdf`产物提供这些结果。

本次本地验证副本通过8+19项检查，生成92页、40条文献记录；对比此前交付PDF，92页文本与72dpi逐页渲染完全一致。本地副本是由已交付文件及核对过的基线文件重建，不冒充网络clone；远端PR及main的真实checkout仍须由对应Actions运行验收。没有重跑优化器，构建通过不替代论文科学性或候选资料授权审查。
