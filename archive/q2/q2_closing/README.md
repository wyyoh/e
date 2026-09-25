# Q2 封口优化

本轮已结束：330 个定向局部邻域未找到严格改善的上界，保留 23 趟、5693.231489105106 s、66.22567019577254 kWh、零迟到的最优已知方案。另有经过完整验证的 **22 趟可行见证**，makespan 为 7767.058323174642 s；它不改善当前词典序目标。

基于 `research/q2-proof-cuts-v4` / `97187484cdf90ee3f90e194679ce231e97c0baa2`，本目录独立保存研究代码与结果，不修改既有 V1–V4 或 Q1/Q3/Q4。

## 阅读入口

- [瓶颈诊断与前五个重构集合](bottleneck_analysis.md)
- [封口结论及论文表述](closing_report.md)
- [逐箱分配](results/box_assignment.csv)、[时限余量](results/deadline_slack.csv)
- [飞机排程](results/aircraft_schedule.csv)、[电池排程](results/battery_schedule.csv)
- [全部邻域结果](results/neighborhood_summary.csv)、[22 趟可行性结论](results/feasibility_22_sorties.json)
- [最终完整见证](results/best_incumbent.json)、[22 趟完整见证](results/feasible_22_incumbent.json)

V4 的节能文件只有任务构成，没有资源时间表。本轮 `baseline_incumbent.json` 是重新构造并验证的同目标见证，不是历史排程原件。其最紧硬截止余量为 202.096057697 s；不能把 V4 状态文件中的历史值 337.292930515 s 套用到本次时间表。

## 环境与验证

工作目录取仓库根目录。独立 Python 3.11 环境安装本目录 requirements.txt，具体实际环境见 logs/environment.json。无需修改仓库根部旧实验依赖。

```powershell
python -m venv q2_closing/.venv
q2_closing/.venv/Scripts/python -m pip install -r q2_closing/requirements.txt
q2_closing/.venv/Scripts/python -X utf8 q2_closing/src/raw_audit.py
q2_closing/.venv/Scripts/python -X utf8 q2_closing/src/replay.py baseline
q2_closing/.venv/Scripts/python -X utf8 q2_closing/src/replay.py best
q2_closing/.venv/Scripts/python -X utf8 q2_closing/src/replay.py feasible_22
q2_closing/.venv/Scripts/python -X utf8 -m pytest q2_closing/tests -q
```

Linux/macOS 将可执行文件路径替换为 `q2_closing/.venv/bin/python`。验证程序重新计算，不把存档的通过标记当作证据。

## 重现已完成的有界搜索

本轮已按停止条件封口，下面是供复现实验使用的命令，不是建议继续扩展搜索。清单保存实际完成的 330 个邻域及其顺序，不包含预设最优数字；每个 MILP 最长 8 s。一个邻域达到时限，未被当成不可行。

```powershell
python -X utf8 q2_closing/src/diagnose.py
python -X utf8 q2_closing/src/search.py --manifest q2_closing/data/search_neighborhoods.json --max-neighborhoods 330 --seconds 8
python -X utf8 q2_closing/src/feasibility.py
python -X utf8 q2_closing/src/replay.py best
python -X utf8 q2_closing/src/replay.py feasible_22
python -X utf8 q2_closing/src/report.py
```

默认搜索种子为 20260924，邻域调度种子由序号确定。优化器运行时间和达到时限的搜索路径会随硬件变化；最终可行性始终由未舍入的连续时间和独立重放判定。数值容差：资源与时限 `1e-7 s`，能量 `1e-10 kWh`（能量绑定比对 `1e-9 kWh`），改进保护量 `1e-5 s`。这不支持排除任意微小改进的形式化全局结论。

## 算法范围

对被移除的 1/2/3 个任务，按真实箱号穷举非空子集和 A/B/C 机型；每个子集至多包含三个服务区，对访问次序全排列。每段都重算当前剩余载荷、爬升/下降、巡航、交接、返航及充电。每个候选分别通过质量和体积限制、返航 SOC、从时刻 0 出发的截止时间必要条件。

工作量 MILP 变量为候选架次分配到同型实体飞机的 0/1 变量；每个箱号覆盖等式为 1，单机累计工作不超过 T，架次数受本次邻域上限约束。未移除任务的箱集及路线保留，实体飞机归属可以改变。MILP 只作必要条件筛选，不把工作量当成真实排程；潜在解还必须经过飞机与满电电池的连续时间解码及独立 replay。失败只记为未找到。

## 共同物理口径

主空间口径为 WGS84 经纬度投影到以 O01 为中心的 AEQD，投影平面线段与原始 DEM 栅格完整相交；不是经纬度直接当米、不是 thin Bresenham。服务区作业高度为原始海拔加 30 m，O01 为地面海拔，每条腿巡航高度是经过像元最高值加 50 m。

\[
L_g(q)=L_g^0-(L_g^0-L_g^F)(q/Q_g)^{3/2},\qquad
E_{ij}(q)=E_g^{use}\frac{d_{ij}}{L_g(q)}+
\frac{(m_g^0+q)9.81h^+_{ij}}{\eta_g\,3.6\times10^6}.
\]

每站卸货后重新爬升；末段空载，但仍计算返程爬升和水平能量。下降不另加能耗。单趟耗电不得超过可用电池能量的 80%。时间包含准备、逐箱装载、每段飞行、每站基础交接及逐箱交接。准备前分配满电电池，电池占用持续到返航后的两阶段充电完成；不同电池并行充电，同机型共享、不同机型不可混用。

零迟到是本轮保留的第一层最优面，所以所有期望时限都满足；医疗和首批硬截止还单独验证。makespan 是最后返航时刻，不是最后一组电池充满的时刻。

## 可证明与不能证明

- 加权迟到达到非负目标的下界 0，是全局最优。
- 保留方案是真实可行上界；固定 B 任务的两机精确分配下界达到该上界。
- 原问题 makespan 没有全局最优证明。继承 V4 的有效下界 5411.2162 s，gap 为 4.953519%；本轮没有重新运行下界证书的大规模定价。
- 22 趟已经由构造性见证证明可行；其最优 makespan 未知。
- 有限列池、有限三任务邻域、启发式调度及 solver time limit 都不构成原问题不可行证明；计算结果不等于现实无人机性能认证。
