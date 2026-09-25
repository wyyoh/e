# 论文制作入口

本目录提供科研绘图、制表与制作规范，不是官方比赛母版，不是新优化结果。

先读 [图表与制作规范](docs/VISUAL_STYLE_GUIDE.md)，公开来源见 [研究来源](docs/RESEARCH_SOURCES.md)。四问叙事结构继续使用 `paper_integration/PAPER_OUTLINE.md`，正式数值以 `paper_integration/FINAL_SELECTION.json` 为准。

`data/visual_data.json`保存冻结实验的24组配对耗时中位数、15组采样分数、Q2认证区间与Q4严格资源向量。每组耗时的3次技术重复原值及完整定价输入仍保留在其哈希绑定的实验归档中，不冒充新增测量。

```bash
python paper/scripts/render_figures.py --out /path/new_figures
python paper/scripts/build_tables.py --out /path/new_tables
```

需要Python、Matplotlib、python-docx和本机中文字体。图脚本拒绝缺字输出，不随包分发字体。生成4图的PDF/SVG/PNG及3张Word原生表、booktabs表代码和数据清单。生成目录应为新目录，避免覆盖已验收输出。

本轮配套下载包额外含6页图表样张PDF、可编辑DOCX、完整画图数据和LaTeX样张源码；这些生成物不作为比赛官方模板，也不需要全部打印进正文。主图与主表选择应以论证需要决定，勿重复整组数据。

范围：0.573414dB是静态样本评分，不是新可行裕度；3.1201倍是固定输入定价中位耗时合计比，不是整个求解器速度比；4.554093%是以上界为分母的确定性认证间隙，不是统计误差。当前合并验收没有重启原优化。
