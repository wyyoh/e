# D 题问题一实施计划

## 输入与版本基线

- 仓库：`wyyoh/e`；起点：`0d7b2d4`（main，干净工作区）。
- 分支：`research/d-q1-exact-model`。
- main 仅含 README；Q2 位于其他研究分支，无 `problems/D` 目录。
- 本实现只增加 `problems/D/q1`，不导入或更改 Q2/Q3/Q4 结果。
- 原始附件来自工作区赛题目录，复制原字节并记录 SHA256；逐箱清单为分配依据，同时核对需求汇总。
- 已核对原 DOCX 附录 2、三份 XLSX、DEM TIF/MAT、地理数据说明 PDF。
- 历史参数化说明：`origin/research/q2-proof-unified-v3:docs/EXPERIMENT_V1.md` 的能耗关系与 g=9.81，仅作为公式来源；不读取历史最优结果供求解使用。
- 用户已明确：以 O01 为中心的 WGS84 AEQD 局部米制投影，距离为平面欧氏距离；DEM 遍历对应投影直线的连续反投影轨迹；WGS84 椭球测地距离只作独立交叉检查。对于 Q1 的径向航段两者理论上相等，不能为匹配回归调整。

## 阶段与提交

1. **输入与几何**：原始附件、严格校验的 XLSX loader、TIF/MAT 一致性、PixelIsPoint 半像元处理、闭像元 supercover 遍历。独立 slab 线段/矩形相交与 ≤0.25 m 采样交叉检查。提交 `feat(D-Q1): add raw data loader and exact DEM geometry`。
2. **物理模型**：3/2 次幂航程、去程载货/返程空载且两次爬升、完整时间、端点检查与 Brent 安全载荷、二分交叉检查。提交 `feat(D-Q1): implement energy and safe-payload model`。
3. **精确组批**：完整类型数量模式用于 DP，展开箱级模式用于独立二元 set partitioning MILP；分别核对 min N、固定 N min E、min T，并输出逐箱分配。两种排序 FFD 与同机型精确解比较。提交 `feat(D-Q1): implement exact batching optimization`。
4. **多目标及敏感性**：局部完整 Pareto label DP 与全局卷积剪枝；5%–40% 的安全载荷网格；所有质量/体积可行模式的 rho 临界事件，包含阈值本身及两侧，输出严格阶梯与最优组批变化。提交 `feat(D-Q1): add Pareto and reserve sensitivity analysis`。
5. **独立验证与回归**：从原始输入独立重算几何、公式、每箱恰好一次、容量、安全余量、时间及目标，执行指定负例。最后才比对用户提供的回归数字；不一致写 `REGRESSION_MISMATCH.md`。隔离输出目录完整重跑并比对确定性文件，保留运行时差异。提交 `test(D-Q1): add independent cross-checks and regression tests`。

## 数值与建模边界

- 不添加飞机编号、电池排程、时限优先、通信、中继、几何三维装箱。
- 质量、体积独立约束；每个非空架次只服务一个服务区；不遗漏空载返程。
- Pareto 容差：能量 1e-10 kWh，时间 1e-7 s；容量与阈值另列容差，不用任意加权替代词典序。
- MILP 状态 1（限时）不能视为不可行或最优；记录 status、gap、dual bound、维度、耗时。
- 有限候选空间完备性来自枚举所有箱子子集/物资数量组合；DP 独立验证离散最优。
- 精确优化结论以题面模型、原始参数、几何口径和已声明浮点容差为条件，不等于真实无人机性能保证。

## 交付与验收

输出用户要求的全部 results、五张 figures、五份 docs、可运行 CLI、依赖清单和测试。
记录 45 个安全载荷、80 箱分配、Pareto 全部不同目标向量、临界事件及边界方向。
完成后报告文件范围、提交 hashes、公式、基准数值、FFD 差距、MILP/DP 一致性、回归及证明边界。
