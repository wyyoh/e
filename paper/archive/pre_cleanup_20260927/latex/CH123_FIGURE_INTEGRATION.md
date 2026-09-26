# 第一、三章插图整合

核对基线：`main @ e9e5ddea20a43f23661e7a39179e6b720efbc00f`。
图件来自 `Chapters_1-3_Figures_Reviewed`，不是重新设计的示意或外部结果。

## 已接入的位置

| 图件 | 正文入口与位置 | 处理 |
|---|---|---|
| 四问决策与继承关系 | `chapters/01.tex`，总体建模思路 | 替换旧TikZ总框架；保留旧标签别名 |
| 地形与需求分布 | `chapters/03.tex`，数据关联与一致性检查之后 | 新增真实DEM与逐箱需求图 |
| 多点运输物理机制 | `chapters/03.tex`，载荷递推之后、飞行时间公式之前 | 替换旧单航段图；保留旧标签别名 |
| DEM像元解释 | `appendix_dem_figure.tex`，现有附录之后 | 新增补充附录；第三章反向引用 |

图注及图片路径集中在 `common_figures.tex`。实际图号由原模板生成，不将文件名中的章节编号硬编码进计数器。
第一章现已与第三章一样独立维护；不要删除 `chapters/01.tex` 后让加载器恢复旧图。
第二章、第四至九章、旧附录、模型方程、原始输入和求解结果均未改写。
第三章第一张机型参数表只压缩了局部行距并限制浮动位置，以与地形图相邻；数值不变。

## 图件与编译

Git中保存可审查的绘图源码、已核对数据快照和自动构建入口；本次PDF二进制文件另随即用整合包提供。

从仓库干净检出构建，先安装绘图依赖及可用的中文字体（例如Noto Sans CJK），再在 `paper/latex` 中运行：

```sh
python -m pip install -r scripts/common_figures_requirements.txt
python scripts/build_common_figures.py
latexmk -xelatex main.tex
```

`.latexmkrc`会先检查四张PDF；缺失时调用同一生成器。它不会联网安装依赖，也不会运行任何求解器。
生成器会验证原始三张工作簿与TIF/MAT的Git blob哈希，输入发生变化时停止，要求更新并核验图件数据，而不是静默使用旧图。

直接使用即用包时，将其 `paper/latex/figures/common_model/` 中的四张PDF复制到同名目录即可；所有PDF齐全后不需要绘图依赖，也不会重新绘图。适合只用XeLaTeX或在Overleaf编译的场景。

## 本次检查范围

- 基线第三章与新第三章的全部数学环境逐段相同。
- 四张重新生成的图在144 dpi下与上一版PDF的渲染完全相同。
- 第一、三章及新增附录的局部图文检阅通过XeLaTeX与BibTeX编译，交叉引用已收敛。
- 局部检阅采用同一用户模板系列及当前字体定义；不以其替代整篇main的最终分页验收。
- 未重新运行四问优化器；未声称完成全文编译或远端CI验收。
- 不附带或分发字体文件。
