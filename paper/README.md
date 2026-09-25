# 论文工作区

当前唯一LaTeX主文件：
- `latex/main.tex`
- 附录：`latex/appendices.tex`
- 参考文献：`latex/references.bib`

正式数值以 `../paper_integration/FINAL_SELECTION.json` 为准。

## 当前口径

- Q1：18架次 / 59.131296 kWh。
- Q2：V7证据，5693.231489 s，LB 5433.956428 s。
- Q3：**Q3-BOTTLENECK-V6/time**，5836.969929 s，68.939416 kWh。
- Q4：严格继承V6/time，K2缺口1、K3缺口7。

主稿与附录已同步到上述口径。Q3旧Q3-FINAL-V1、旧5755候选域下界、旧0.50/0.55 dB方案以及Q4旧V2敏感性仅作为历史材料，不再作为当前结论。

## 图表与数据

- Q2正式绘图数据：`data/q2_v7_visual_source.json`
- Q3 V6正式绘图数据：`data/q3_v6_visual_source.json`
- `data/visual_data.json` 中pricing/q3_sampling数组是历史算法实验；当前Q4资源字段已同步到V6 strict结果。

最终投稿前仍需按官方模板检查版式、图号、交叉引用和生成PDF。
