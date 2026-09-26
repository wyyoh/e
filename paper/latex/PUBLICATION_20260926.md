# 最新完整论文（2026-09-26发布）

编辑与编译入口：`main.tex`。各章直接位于`chapters/`，合并阅读版为`main_merged.tex`。

发布稿为92页检阅版，第1—9章正文72页；含40条实际引用的文献与来源记录（39条公开文献/书籍/标准等，1条候选来源记录）。

PDF位于`../review/D_paper_completed_20260926.pdf`。原交付文件和远端重编译文件哈希分别记录在`../review/completed_source_identity_20260926.json`。

发布时核对119份源文件及数据，远端19项正文测试通过。已提交所有必需插图；没有重新运行优化器，也没有改变正式模型参数、结果锁和稳健性试验代码。字体文件不分发。

## 2026-09-27工程维护

当前README与CI入口已经统一，旧`source_main.tex`、旧加载器和改稿说明归入`../archive/pre_cleanup_20260927/`。不要删除`chapters/`重新从旧稿生成。

从仓库根执行`python3 .github/scripts/ci_review.py`可在临时副本中严格编译，产物进入忽略的`review-build/`。也可在本目录执行`python3 scripts/build_pdf.py`。

发布身份记录描述2026-09-26的历史快照，不随README更新而改写。原README字节已归档；当前正文、文献数据、表格和发布PDF没有因工程维护而修改。新增仓库检查与实际构建结果由对应Actions运行保存，不混写为原发布时执行的测试。
