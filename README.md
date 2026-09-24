# D题：山区洪涝灾害下无人机运输与通信协同优化

## 当前研究分支：Q2-PROOF-UNIFIED-V3

最新说明在 [verification_v3/README.md](verification_v3/README.md)，证明范围在 [verification_v3/docs/model_v3.md](verification_v3/docs/model_v3.md)，机器可读结论在 [verification_v3/results/status.json](verification_v3/results/status.json)。

|项目|本轮核验结果|
|---|---:|
|完整可行上界|5693.231489105107秒（94分53.231秒）|
|全80箱有效下界|5390.423694秒（约89分50.424秒）|
|相对上界间隙|5.318733%|
|上界架次与能耗|23趟，66.252068563 kWh|
|全局最优|尚未证明|

23趟来自父版本已有的 `verification_v2/selected_incumbent.csv`，本轮独立重建并核验，不冒称本轮启发式新发现。仍为80箱零迟到、8架飞机、14组电池。

已统一旧5349.079436秒与4899.348242秒两份证据；旧强界不被弱界覆盖。新版运行完整松弛定价、500个部分整数分支节点、250份覆盖证书和750次复定价，原问题完整路线整数化与电池排程证明仍未闭合。

## 运行V3

```bash
python -m pip install numpy scipy
python verification_v3/code/run_all.py --solve --nodes 500
```

本次从无既有结果的新目录实际运行了相同代码及规范化输入，核心结果一致；7份源文件与GitHub回读blob一致。记录见 [clean_rebuild.json](verification_v3/results/clean_rebuild.json)。不承诺跨平台搜索路径或浮点字节一致。

核心代码和状态已提交到本研究分支，完整节点证据、23趟CSV/JSON、辅助子集行割与截止前缀实验随对应计算包交付。不要把辅助实验与分支树的提升相加，也不要把有限列池或固定任务最优标记为原问题最优。

## 历史版本

- 原V1源码仍在 `src/`，说明 `docs/EXPERIMENT_V1.md`，原结果在根 `results/`；这些不是V3当前结论。
- V2代码与候选在 `verification_v2/`。
- `data/encoded/*.b64` 为原有无损输入分片，V3直接复用并验证父manifest，不重新提取DEM，也不改变物理参数。

第一、三、四问及正式综合模板不因当前Q2研究自动覆盖。研究分支不强推、不改main。所有上下界限定于已明确的航程标定、能耗推导、精确时间与准备前满电操作流程；最低SOC仍20.097383%，不得称为实飞鲁棒保证。
