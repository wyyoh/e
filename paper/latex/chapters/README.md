# 分章文件

\`main.tex\` 是正式编译入口。首次编译时，\`source_loader.tex\` 从 \`source_main.tex\` 中提取：

- \`00_abstract.tex\`：摘要；
- \`01.tex\`--\`09.tex\`：九章正文。

参考文献与附录不属于第9章，分别由 \`main.tex\` 直接调用 \`references.bib\` 和 \`appendices.tex\`。

如本地已经生成旧的分章文件，而 \`source_main.tex\` 已更新，应先备份人工修改，再重新生成分章文件，避免旧的 \`09.tex\` 携带历史参考文献或附录内容。
