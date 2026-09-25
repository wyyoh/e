# 论文制作入口

## 当前唯一主稿

- [`latex/main.tex`](latex/main.tex)

配套文件：

- [`latex/appendices.tex`](latex/appendices.tex)：附录A--F
- [`latex/references.bib`](latex/references.bib)：参考文献
- [`latex/q2_v7_figures.tex`](latex/q2_v7_figures.tex)：Q2 V7正式TikZ图
- [`data/q2_v7_visual_source.json`](data/q2_v7_visual_source.json)：Q2图源数据

旧的分章节整合草稿已经从main删除，避免出现多个主稿入口。需要历史版本时请直接查Git提交记录。

## 正式数值入口

四问论文数字始终以：

- [`../paper_integration/FINAL_SELECTION.json`](../paper_integration/FINAL_SELECTION.json)

为最高优先级。

Q1--Q4正式目录及证据边界见根目录 [`README.md`](../README.md) 和 [`../docs/MAIN_BRANCH_STATUS.md`](../docs/MAIN_BRANCH_STATUS.md)。

## 当前图表状态

- Q1：现有安全载荷、Pareto、余量敏感性图已经接入主稿
- Q2：已统一切换到V7正式数据驱动的9张TikZ图，不再引用 `q2_closing` 旧图
- Q3：正文仍按当前正式 `Q3-FINAL-V1/time` 口径；若未来正式Q3发生替换，必须同步重画第6章并重算Q4
- Q4：strict主模型不变，clone仅作敏感性
- 第1/4/6/7/8章仍有待完成的部分图位，以主稿中的 `\figplaceholder` 为准

## 论文组成

当前主稿已包含：

- 摘要与关键词
- 第1--9章
- 参考文献
- 附录A--F

当前文件还是论文工程稿，不是官方比赛母版。最终提交前仍需迁移到当届官方模板并做版式检查。

## 绘图与制表

已有工具：

- [`scripts/render_figures.py`](scripts/render_figures.py)
- [`scripts/build_tables.py`](scripts/build_tables.py)
- [`scripts/generate_q2_v7_figures.py`](scripts/generate_q2_v7_figures.py)

视觉规范：

- [`docs/VISUAL_STYLE_GUIDE.md`](docs/VISUAL_STYLE_GUIDE.md)

公开研究来源：

- [`docs/RESEARCH_SOURCES.md`](docs/RESEARCH_SOURCES.md)

## 解释边界

- 0.573414 dB 是Q3静态proxy评分，不是新连续可行通信裕度
- 3.1201× 是固定pricing输入的中位耗时合计比，不是整个Q2求解器加速比
- 4.554093% 是Q2确定性认证间隙，不是统计误差
- Q3四中继下界仅适用于冻结运输几何+5755候选位置有限域
- Q4 relay clone只作反事实敏感性
