# Environments

本仓库没有一个可以覆盖所有历史实验的全局Python环境。各模块优先使用自己的requirements/lock文件。

- Q1：`problems/D/q1/requirements.txt`
- Q2历史closing：`archive/q2/q2_closing/requirements.txt`
- Q2 V1全局验证：`archive/q2/global_verify_v1/requirements.txt`
- Q3完整V6运行环境：由 `paper_integration/FINAL_SELECTION.json` 中记录的 companion archive SHA-256 锁定；GitHub当前只展开正式决策和验证摘要。
- 论文绘图：按 `paper/scripts/` 实际import安装依赖。

根目录不再维护一个误导性的统一 `requirements.txt`。
