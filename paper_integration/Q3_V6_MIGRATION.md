# Q3 V6 migration note

当前正式选择已经推进到 **Q3-BOTTLENECK-V6 / time**：5836.969929328251 s、68.93941621018112 kWh、23运输+4中继。物理模型为 **Q3-HOVER-COMPATIBLE-V5**。

Q1/Q2不变。Q4 strict已从V6/time日程重新计算：K=2缺口1，K=3缺口7。旧Q4 relay-copy/N-1/Pareto敏感性仍为历史结果。

旧Q3 `release_final/` 保留作审计；当前入口为 `problems/D/q3/release_v6/time/`。完整运行包 `q3_bottleneck_v6_full.zip` 的SHA-256为 `f8efc0cb0859fe0bd39f0f23f1a18e824d3848873344ef3e7a93b11a93b257bf`，未作为36MB二进制提交。

后续仓库清理已经同步更新 `paper/latex/main.tex`、`appendices.tex`、论文数据源和README。因此旧“论文尚未同步”的迁移备注不再适用。

旧有限域四中继下界和旧+0.50/+0.55 dB鲁棒结论不转移到V6。V6主方案为名义0 dB；+0.25 dB只属于单独的robust025候选。
