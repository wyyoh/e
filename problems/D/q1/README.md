# D 题 Q1：原始附件 → 精确组批 → 独立验证

独立实现问题一。主模型采用用户确认的 **O01 中心 WGS84 AEQD** 平面直线与对应的连续 DEM 像元遍历。没有 Q2/Q3/Q4 导入、实体飞机或电池排程依赖。

## 运行

需要 Python **3.11**。在本目录运行：

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe scripts/run_all.py
.venv/Scripts/python.exe -m pytest tests -q --junitxml=results/tests.junit.xml
.venv/Scripts/python.exe scripts/reproduce.py
.venv/Scripts/python.exe scripts/report.py
```

Linux/macOS 使用 `.venv/bin/python`。默认完整流程约一分钟量级，依赖机器速度；首次全箱级 MILP 会明显更慢。测试会重新求解，不能只看已有的 PASS 文件。

完整箱级模型和对称压缩模型都已求过，日志分别保存在 `results/solver_logs/full_box/` 和 `results/solver_logs/`。默认复现选择严格等价的对称压缩。强制另跑原始箱级模型：

```powershell
.venv/Scripts/python.exe scripts/run_all.py --full-box-milp
```

隔离输出（不覆盖交付结果）：

```powershell
.venv/Scripts/python.exe scripts/run_all.py --output results_new --figures results_new/figures
.venv/Scripts/python.exe scripts/validate.py --output results_new
```

`reproduce.py` 默认要求 `results_reproduce` 尚不存在，避免自动删除用户文件；可指定 `--output` 为其他未存在目录。它从原始输入重新计算，逐字节比较27个确定性数值文件和5幅图，运行时间、求解器对称代表选择另作处理。

## 目录

- `data/raw/`：三份 XLSX、TIF/MAT、原题 DOCX、地理说明 PDF，保留原字节；`raw_manifest.json` 固定哈希。
- `model/`：原始读取、AEQD连续轨迹完整像元遍历、非线性航程与能量/时间。
- `solver/`：数量模式、原始箱子子集 MILP、DP、完整Pareto、FFD、精确事件分析。
- `scripts/`：单阶段和一键复现、独立验证、最终回归、图和报告。
- `tests/`：单元、独立求解器、全部指定负例、边界、回归（目标仅存这里）。
- `results/`：全部可检查的数值与逐箱安排；候选数量模式在 `candidate_patterns.csv`，完整箱号候选在 `candidate_box_patterns.csv`。
- `docs/`：数学模型、算法、结果、验证、假设和证明边界。
- `figures/`：路线、45项载荷、Pareto、余量载荷和架次阶梯。

## 阅读顺序

[结果](docs/q1_results.md) → [数学模型](docs/q1_mathematical_model.md) → [验证](docs/q1_validation.md) → [算法](docs/q1_algorithm.md) → [假设和限制](docs/assumptions_and_limits.md)。

优化结果仅适用于给定物理模型、原始附件、空间口径及数值容差，不能作为现实飞行安全保证。FFD明确是启发式对照。历史数值仅在一键流程最后用于回归，绝不用于选参数或引导求解。
