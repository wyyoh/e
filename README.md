# D题：山区洪涝灾害下无人机运输与通信协同优化

本仓库的 **main 分支是当前论文与正式结果的唯一发布入口**。历史验证目录、研究分支和实验分支保留用于追溯，不自动覆盖 main 中已经冻结的正式结果。

## 1. 唯一正式选择入口

四问正式版本、证据范围和 companion archive 哈希统一由：

- [`paper_integration/FINAL_SELECTION.json`](paper_integration/FINAL_SELECTION.json)

决定。

如果历史文件、实验分支、旧报告与该文件冲突，以 `FINAL_SELECTION.json` 及其引用的正式目录为准。

| 问题 | main 中正式版本 | 当前正式结论 |
|---|---|---|
| Q1 | `problems/D/q1` / frozen exact model | 18架次；59.131296022053 kWh；546.266929148593 min累计作业时间 |
| Q2 | `Q2-EVIDENCE-V7-FOCUSED` | 23架次、零加权迟到；5693.231489105106 s；66.21445957313102 kWh；认证下界5433.956428 s |
| Q3 | `Q3-FINAL-V1 / time` | 23运输+4中继；6340.439338658365 s；69.30853085578303 kWh |
| Q4 | `Q4-SENSITIVITY-V2 / strict` | K=2缺口2；K=3缺口7；relay clone仅为敏感性 |

### Q2证据边界

当前Q2正式认证区间为：

[
5433.956428 \le T^* \le 5693.231490\quad \mathrm{s}.
]

UB归一化间隙为 **4.554093092%**。零加权迟到最优值为0，但 **makespan全局最优尚未证明**。

### Q3证据边界

Q3正式主方案仍是 `Q3-FINAL-V1/time`。当前研究分支中存在更晚的架构验证与候选生成实验，但它们均明确记录：

- `formal_q3_primary_unchanged = true`
- `adopted_new_plan = false`

因此这些研究分支不替换main中的正式Q3。

### Q4证据边界

Q4严格模型冻结Q3正式任务、时序、路线和实际通信关系。严格K=2/K=3分别完整枚举3种/1种合法分区；relay-copy模型只用于反事实敏感性，不能作为正式主答案。

## 2. 当前论文入口

论文当前唯一LaTeX主文件：

- [`paper/latex/main.tex`](paper/latex/main.tex)

配套文件：

- [`paper/latex/appendices.tex`](paper/latex/appendices.tex)：附录A--F
- [`paper/latex/references.bib`](paper/latex/references.bib)：参考文献
- [`paper/latex/q2_v7_figures.tex`](paper/latex/q2_v7_figures.tex)：Q2最新V7正式TikZ图组
- [`paper/data/q2_v7_visual_source.json`](paper/data/q2_v7_visual_source.json)：Q2正式绘图数据

旧的 `current_draft_ch*.tex` 文件已从main删除，避免出现多个“主稿”入口。

## 3. 目录职责

- `problems/D/q1/`：Q1正式精确模型、结果、测试、图和验证
- `problems/D/q2/evidence_v7/`：Q2 V7正式证据
- `q2_final/solution/main_23/`：Q2正式23架次primal方案
- `problems/D/q3/release_final/`：Q3正式冻结release
- `problems/D/q4/`：Q4正式strict结果与敏感性
- `paper/`：论文正文、数据、图、参考文献与QA
- `paper_integration/`：四问正式选择、论文组织与整合证据
- `experiments/`：已合入main、但不自动替换正式结果的实验记录

## 4. 历史目录说明

下列目录保留是为了可追溯，不是当前正式入口：

- `q2_closing/`
- `verification_v2/`
- `verification_v3/`
- 早期 `results/`、`logs/`
- 历史研究分支中的Q2 proof / Q3 candidate experiments

不得因为这些目录中存在旧数值，就覆盖当前正式论文结果。

## 5. 分支规则

- `main`：当前正式结果 + 论文主稿
- `research/*`、`experiments/*`：研究与验证材料，只有通过正式验收并明确更新 `FINAL_SELECTION.json` 后，才能改变main正式口径
- `release/*`：历史发布快照，不作为比main更新的自动来源

截至本次整理，Q1/Q2正式研究分支均已被main完整包含；Q3较新的研究分支只提供“没有实质改进”的审计材料，不改变正式Q3。

更详细的main状态说明见：

- [`docs/MAIN_BRANCH_STATUS.md`](docs/MAIN_BRANCH_STATUS.md)

## 6. 论文制作

论文制作入口：

- [`paper/README.md`](paper/README.md)
- [`paper/docs/VISUAL_STYLE_GUIDE.md`](paper/docs/VISUAL_STYLE_GUIDE.md)
- [`paper/docs/RESEARCH_SOURCES.md`](paper/docs/RESEARCH_SOURCES.md)

当前Q2图已经统一为V7正式口径，不再引用 `q2_closing` 旧版图。

## 7. 使用原则

1. 先读 `FINAL_SELECTION.json`，再读取各问正式目录。
2. 不把历史试验、静态proxy、有限邻域“未改善”扩大为全局最优证明。
3. Q1累计作业时间与Q2/Q3并行makespan不是同一指标。
4. Q3的4中继下界只对固定运输轨迹+5755候选位置的有限域成立。
5. Q4的clone结果只作敏感性。
6. 最终论文提交仍需按当届官方模板完成封面、匿名、版式和上传格式检查。
