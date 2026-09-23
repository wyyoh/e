# 来源与版本

- 当前原问题：2026年研究生数学建模D题《山区洪涝灾害下无人机运输与通信协同优化》，问题二及附录2。
- 上游附件：D题_第二问_ALNS对照与可复现代码.zip，Q2_ALNS_REVIEW/inputs及results/main_time。逐箱字段、机型、派单来源不改变；来源SHA256见snapshot.json和inputs/snapshot_manifest.json。
- 当前源数据快照是从已经核验的240方向航段取得，不重新解释DEM栅格、海拔或路线。
- 文献4：Dorling et al. (2017), Vehicle Routing Problems for Drone Delivery, DOI 10.1109/TSMC.2016.2582745，公开稿 https://arxiv.org/abs/1608.02305 。
- 文献5：Zhang et al. (2021), Energy Consumption Models for Delivery Drones: A Comparison and Assessment, DOI 10.1016/j.trd.2020.102668。继承作者公开稿p13式3、p46式B1的已核对推导；未新核验正式版勘误。
- Lam & Van Hentenryck (2016), A branch-and-price-and-check model for the vehicle routing problem with location congestion: https://research.monash.edu/en/publications/a-branch-and-price-and-check-model-for-the-vehicle-routing-proble/ 。这是后续方法参考，不表示本轮已经完成原问题的branch-price-and-check。
- SciPy MILP文档：https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html 。限时的mip_dual_bound才是该MILP的下界，不是fun；该MILP又是原问题松弛。

报告中的数值由本目录程序产生，不从文献借用其他设备参数。本地实测Python/NumPy/SciPy/Numba版本在evidence/environment.json中记录。
