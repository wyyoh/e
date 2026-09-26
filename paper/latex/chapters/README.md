# 分章编辑入口

主文件直接加载00_abstract.tex和01.tex—09.tex。这些文件及其明确引用的expanded_sections、repair_sections为当前编辑源，不从source_main.tex或source_loader自动生成。修改后运行scripts/check_source.py，再按需要运行无PDF检查。

main_merged.tex是派生阅读版本；用scripts/export_merged_tex.py重新生成。不要同时独立修改分章与合并稿后混用。
