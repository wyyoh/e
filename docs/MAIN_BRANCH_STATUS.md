# main 分支状态与正式结果说明

> 目的：给论文撰写、代码复现和后续实验提供一个不会误用旧结果的统一入口。

## 1. main 的定位

`main` 是本项目当前正式整合分支。它同时包含：

- Q1--Q4当前正式结果；
- 论文主稿；
- 已验收的对照/验证实验；
- 历史材料的可追溯副本。

“存在于main”不等于“正式主结果”。正式结果必须由 `paper_integration/FINAL_SELECTION.json` 选中。

## 2. 四问正式状态

### Q1

- 正式来源：`problems/D/q1`
- 冻结提交：`f905acc8482966cef7f65be0caeda69fb9f02b5c`
- 结果：18架次，59.131296022053 kWh，546.266929148593 min累计作业时间
- 证据：下界18 + 可行构造18；箱级MILP、压缩MILP、DP一致

### Q2

- primal：`q2_final/solution/main_23`
- 正式证据：`problems/D/q2/evidence_v7`
- 版本：`Q2-EVIDENCE-V7-FOCUSED`
- 结果：23架次，零加权迟到，5693.231489105106 s，66.21445957313102 kWh
- 认证：5433.956428 <= T* <= 5693.231490 s
- UB归一化间隙：4.554093092%
- 边界：未证明makespan全局最优

### Q3

- 正式入口：`problems/D/q3/release_final/index.json`
- 版本：`Q3-FINAL-V1`
- 主变体：`time`
- 结果：23运输+4中继，6340.439338658365 s，69.30853085578303 kWh
- 状态：FROZEN
- 边界：完整Q3未证明全局最优；4中继下界只属于固定轨迹+5755候选位置的有限域

#### Q3较新研究分支

`research/q3-architecture-v4` 比main多1个实验提交，但实验结论是：

- `NO_MATERIAL_IMPROVEMENT_FOUND`
- `adopted_new_plan = false`
- `formal_q3_primary_unchanged = true`

它记录了更广的架构验证、候选搜索和假改善审计，不是新的正式Q3。

`research/exp-q3-informed-candidates-v1` 同样只说明候选筛选效率，不修改正式Q3。

### Q4

- 正式版本：`Q4-SENSITIVITY-V2`
- 正式模型：`strict`
- K2缺口向量：`[0,0,1,0,0,1,0,0]`
- K3缺口向量：`[1,0,3,1,0,2,0,0]`
- strict合法分区：K2=3，K3=1
- clone合法分区：K2=511，K3=9330
- 边界：clone是敏感性，不是正式主答案

## 3. 当前论文文件

唯一主稿：

- `paper/latex/main.tex`

配套：

- `paper/latex/appendices.tex`
- `paper/latex/references.bib`
- `paper/latex/q2_v7_figures.tex`

旧的 `current_draft_ch3_ch7.tex`、`current_draft_ch1_ch7.tex`、`current_draft_ch1_ch9.tex` 已从main删除；历史仍可通过Git提交记录恢复。

## 4. Q2图状态

Q2论文图已从旧的 `q2_closing` PNG口径切换到V7正式数据驱动的TikZ图。

正式数据：

- `paper/data/q2_v7_visual_source.json`

正式图宏：

- `paper/latex/q2_v7_figures.tex`

主稿中不再引用：

- `q2_closing/figures/aircraft_gantt.png`
- `q2_closing/figures/battery_gantt.png`
- `q2_closing/figures/incumbent_comparison.png`

## 5. main 中保留历史目录的原因

本项目不通过物理删除旧求解记录来“制造干净”。历史目录保留用于：

- 验证结论演化；
- 复核版本差异；
- 回溯旧证书；
- 审计负结果。

因此“main干净”定义为：

> 正式入口唯一、版本边界清楚、论文只引用正式结果、历史材料不会被误认为最新结果。

而不是要求仓库只剩最后一版代码。

## 6. PR与实验分支管理

过期的Q2阶段性PR应关闭，不再作为待合并候选。研究分支可以保留，但默认不合并其结果，除非：

1. 结果通过正式验证；
2. 明确替换原正式版本；
3. 同步更新 `FINAL_SELECTION.json`；
4. 同步更新论文、附录和结果说明。

## 7. 修改正式结果的最低要求

任何以后想修改Q1--Q4正式口径的提交，至少必须同步：

- 机器可读结果；
- 独立验证；
- 论文正文；
- 图表；
- 摘要/结论中相关数字；
- `FINAL_SELECTION.json`；
- 本状态文档。

如果只增加实验结果但没有满足以上要求，应留在研究分支或标记为non-authoritative。
