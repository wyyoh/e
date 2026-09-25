from pathlib import Path
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
from matplotlib.lines import Line2D
from matplotlib import font_manager as fm

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "q2_v7_visual_source.json"
OUT = ROOT / "figures" / "q2"
OUT.mkdir(parents=True, exist_ok=True)

data = json.loads(DATA.read_text(encoding="utf-8"))
flights = data["flights"]
bat = data["battery_cycles"]
nodes = data["nodes"]
metrics = data["metrics"]
status = data["status"]
w22 = data["witness22"]
pricing = data["pricing_summary"]
bfix = data["B_fixed"]

font_candidates = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Regular.otf",
]
font_path = next((p for p in font_candidates if Path(p).exists()), None)
if font_path:
    prop = fm.FontProperties(fname=font_path)
    plt.rcParams["font.family"] = prop.get_name()

plt.rcParams.update({
    "axes.unicode_minus": False,
    "font.size": 9,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
})

LIGHT = "#E4E8EB"
LMID = "#C4CDD3"
MID = "#98A8B2"
DARK = "#657A87"
DEEP = "#3F5663"
TEXT = "#30343A"
GRID = "#D9DDE0"
TYPE = {"A": "#C4CDD3", "B": "#657A87", "C": "#98A8B2"}

def save(fig, stem):
    fig.savefig(OUT / f"{stem}.pdf", bbox_inches="tight", pad_inches=0.05)
    fig.savefig(OUT / f"{stem}.png", dpi=300, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)

# Fig. 5-1
fig, ax = plt.subplots(figsize=(8.8, 5.5))
ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
def box(x, y, w, h, text, fc=LIGHT, bold=False):
    p = FancyBboxPatch((x,y), w,h, boxstyle="round,pad=0.012,rounding_size=0.012",
                       facecolor=fc, edgecolor=DARK, linewidth=1)
    ax.add_patch(p)
    ax.text(x+w/2, y+h/2, text, ha="center", va="center",
            fontsize=9, color=TEXT, fontweight="bold" if bold else "normal")
def arrow(x1,y1,x2,y2):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle="-|>",
                                 mutation_scale=10,color=DARK,linewidth=1))
box(.34,.84,.32,.09,"Q1安全可行批型 / 候选运输任务",bold=True)
box(.31,.68,.38,.10,"多点运输任务构造\n箱组 · 访问顺序 · 机型 · 时长 · 能耗 · 箱级送达偏移")
box(.31,.51,.38,.10,"飞机—电池联合资源排程\n实体飞机 · 共享电池 · 充电恢复 · deadline · 开始时刻",fc=LMID,bold=True)
box(.08,.27,.34,.14,"可行上界路线\n任务重构 → 事件排程 → 独立重放\n得到真实可执行 UB")
box(.58,.27,.34,.14,"全局下界路线\n任务列松弛 → 完整定价 → 分支覆盖证书\n得到有效 LB")
box(.34,.08,.32,.10,"确定性认证区间：  LB ≤ T* ≤ UB",fc=LMID,bold=True)
arrow(.50,.84,.50,.78); arrow(.50,.68,.50,.61); arrow(.42,.51,.25,.41)
arrow(.58,.51,.75,.41); arrow(.25,.27,.42,.18); arrow(.75,.27,.58,.18)
ax.text(.5,.015,"同时回答“方案能否真实执行”与“当前方案距离理论下界还有多远”",
        ha="center", va="bottom", fontsize=8.5, color=DARK)
save(fig, "F51_q2_framework_v7")

# Fig. 5-2
fig, ax = plt.subplots(figsize=(8.8,3.1))
ax.set_xlim(0,10); ax.set_ylim(-.2,2.1); ax.axis("off")
for x,label in [(1,"任务开始"),(7,"返航"),(9,"电池恢复满电")]:
    ax.plot([x,x],[.05,1.75],color=GRID,linewidth=.8,linestyle="--")
    ax.text(x,1.86,label,ha="center",va="bottom",fontsize=8.5,color=TEXT)
ax.text(.2,1.35,"运输无人机",ha="left",va="center",fontsize=9,color=TEXT)
ax.text(.2,.55,"共享电池",ha="left",va="center",fontsize=9,color=TEXT)
ax.add_patch(Rectangle((1,1.12),6,.46,facecolor=DARK,edgecolor="white"))
ax.text(4,1.35,"准备 + 飞行 + 配送 + 返航",ha="center",va="center",color="white",fontsize=8.5)
ax.add_patch(Rectangle((1,.32),6,.46,facecolor=DARK,edgecolor="white"))
ax.text(4,.55,"任务占用",ha="center",va="center",color="white",fontsize=8.5)
ax.add_patch(Rectangle((7,.32),2,.46,facecolor=LMID,edgecolor="white"))
ax.text(8,.55,"充电恢复",ha="center",va="center",color=TEXT,fontsize=8.5)
ax.text(4,1.02,r"$I_r^U=[s_r,s_r+p_r)$",ha="center",va="top",fontsize=9,color=DARK)
ax.text(5,.22,r"$I_r^B=[s_r,s_r+p_r+c_r)$",ha="center",va="top",fontsize=9,color=DARK)
ax.text(5,-.05,"飞机返航后可以释放，但原电池仍继续占用至充电恢复完成",
        ha="center",va="top",fontsize=8.5,color=DARK)
save(fig, "F52_resource_occupancy_v7")

# Fig. 5-3
fig, ax = plt.subplots(figsize=(8.6,5.8))
ax.axis("off"); ax.set_xlim(0,1); ax.set_ylim(0,1)
def b2(x,y,w,h,t,fc=LIGHT,bold=False):
    p=FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.01,rounding_size=0.01",
                     facecolor=fc,edgecolor=DARK,linewidth=1)
    ax.add_patch(p)
    ax.text(x+w/2,y+h/2,t,ha="center",va="center",fontsize=8.7,
            color=TEXT,fontweight="bold" if bold else "normal")
def ar(a,b,c,d):
    ax.add_patch(FancyArrowPatch((a,b),(c,d),arrowstyle="-|>",
                                 mutation_scale=10,color=DARK,linewidth=1))
b2(.32,.87,.36,.08,"当前完整可行方案",fc=LMID,bold=True)
b2(.27,.72,.46,.09,"识别关键链\n迟到风险 · makespan瓶颈 · 飞机链 · 电池链")
b2(.27,.56,.46,.09,"构造重构邻域\n货箱重分配 · 路线重构 · 机型调整 · 资源链释放")
b2(.27,.40,.46,.09,"快速物理筛选\n质量 · 体积 · 能量 · 时限必要条件")
b2(.27,.24,.46,.09,"精确事件排程 + 独立重放\n飞机 · 电池 · 充电 · 箱级deadline",fc=LMID,bold=True)
b2(.34,.08,.32,.08,"严格改善？",bold=True)
for y1,y2 in [(.87,.81),(.72,.65),(.56,.49),(.40,.33),(.24,.16)]:
    ar(.5,y1,.5,y2)
ax.text(.69,.12,"是 → 接受为新UB",fontsize=8.5,color=DARK,va="center")
ar(.66,.12,.78,.12)
ax.text(.08,.12,"否 → 拒绝并换邻域",fontsize=8.5,color=DARK,va="center")
ar(.34,.12,.20,.12)
ax.plot([.20,.08,.08,.27],[.12,.12,.60,.60],color=DARK,linewidth=1)
ax.text(.5,.015,"候选必须经过完整事件排程与重放后才能成为正式可行上界",
        ha="center",fontsize=8.3,color=DARK)
save(fig, "F53_upper_bound_search_v7")

# Fig. 5-4
node = {x["id"]:x for x in nodes}
fig, ax = plt.subplots(figsize=(7.5,6.6)); ax.set_aspect("equal")
for f in flights:
    coords=[(node[n]["x"]/1000,node[n]["y"]/1000) for n in f["route"]]
    xs=[c[0] for c in coords]; ys=[c[1] for c in coords]
    ls={"A":"-","B":"--","C":":"}[f["type"]]
    ax.plot(xs,ys,linestyle=ls,color=TYPE[f["type"]],linewidth=1.1,alpha=.65,zorder=1)
for n in nodes:
    x=n["x"]/1000; y=n["y"]/1000
    if n["id"]=="O01":
        ax.scatter(x,y,s=90,marker="*",color=DEEP,zorder=5)
        ax.text(x+.15,y-.35,"O01",fontsize=8.5,color=TEXT,fontweight="bold")
    else:
        ax.scatter(x,y,s=18,color=DEEP,zorder=4)
        ax.text(x+.10,y+.08,n["id"],fontsize=7.6,color=TEXT)
legend=[Line2D([0],[0],color=TYPE["A"],linestyle="-",label="A型"),
        Line2D([0],[0],color=TYPE["B"],linestyle="--",label="B型"),
        Line2D([0],[0],color=TYPE["C"],linestyle=":",label="C型")]
ax.legend(handles=legend,frameon=False,loc="lower right",ncol=3,fontsize=8)
ax.set_xlabel("AEQD x / km"); ax.set_ylabel("AEQD y / km")
ax.grid(alpha=.15,color=GRID)
ax.text(.02,.98,"23架次；A/B/C = 11/6/6",transform=ax.transAxes,
        ha="left",va="top",fontsize=8.5,color=DARK)
for sp in ["top","right"]: ax.spines[sp].set_visible(False)
save(fig, "F54_route_map_v7")

# Fig. 5-5
fig,(ax1,ax2)=plt.subplots(2,1,figsize=(11,8),sharex=True,
                           gridspec_kw={"height_ratios":[1,1.55]})
resources=sorted({x["aircraft"] for x in flights})
for row in flights:
    y=resources.index(row["aircraft"]); left=row["start_s"]/60
    width=(row["return_s"]-row["start_s"])/60
    ax1.barh(y,width,left=left,height=.58,color=TYPE[row["type"]],
             edgecolor="white",linewidth=.5)
    ax1.text(left+width/2,y,row["flight_id"].replace("Q2-R-","R"),
             ha="center",va="center",fontsize=6.5,color=TEXT)
ax1.axvline(metrics["makespan_s"]/60,color=DEEP,linestyle="--",linewidth=1)
ax1.set_yticks(range(len(resources)),resources); ax1.invert_yaxis()
ax1.set_ylabel("运输无人机"); ax1.grid(axis="x",alpha=.15,color=GRID)
ax1.text(.995,.02,"(a) 飞机占用",transform=ax1.transAxes,ha="right",va="bottom",
         fontsize=8.5,color=DARK)
bats=sorted({x["battery"] for x in bat})
for row in bat:
    y=bats.index(row["battery"]); left=row["task_start_s"]/60
    width=(row["return_s"]-row["task_start_s"])/60
    ax2.barh(y,width,left=left,height=.53,color=TYPE[row["type"]],
             edgecolor="white",linewidth=.4)
    ax2.barh(y,row["charge_duration_s"]/60,left=row["return_s"]/60,
             height=.53,color=LIGHT,edgecolor="white",linewidth=.4)
ax2.axvline(metrics["makespan_s"]/60,color=DEEP,linestyle="--",linewidth=1)
ax2.set_yticks(range(len(bats)),bats,fontsize=7); ax2.invert_yaxis()
ax2.set_ylabel("共享电池"); ax2.set_xlabel("从调度开始计时 / min")
ax2.grid(axis="x",alpha=.15,color=GRID)
ax2.text(.995,.02,"(b) 电池任务占用 + 充电恢复",transform=ax2.transAxes,
         ha="right",va="bottom",fontsize=8.5,color=DARK)
fig.tight_layout(h_pad=.5)
save(fig, "F55_aircraft_battery_gantt_v7")

# Fig. 5-6
fig, ax = plt.subplots(figsize=(6.8,4.6))
pts=[("23架次正式方案",metrics["energy_kwh"],metrics["makespan_s"]/60,True),
     ("22架次可行见证",w22["energy_kwh"],w22["makespan_s"]/60,False)]
for label,x,y,main in pts:
    if main:
        ax.scatter(x,y,s=90,color=DEEP,marker="o",zorder=3)
    else:
        ax.scatter(x,y,s=90,facecolors="white",edgecolors=MID,
                   linewidth=1.5,marker="o",zorder=3)
    ax.annotate(f"{label}\n{x:.3f} kWh, {y:.2f} min",(x,y),
                xytext=(8,8),textcoords="offset points",fontsize=8.5,color=TEXT)
ax.annotate("少1架次，但当前见证工期增加约34.56 min",
            xy=(w22["energy_kwh"],w22["makespan_s"]/60),xytext=(66.218,116),
            arrowprops=dict(arrowstyle="->",color=DARK,linewidth=1),
            fontsize=8.5,color=DARK)
ax.set_xlabel("总能耗 / kWh"); ax.set_ylabel("makespan / min")
ax.grid(alpha=.16,color=GRID); ax.set_xlim(66.19,66.35); ax.set_ylim(90,135)
for sp in ["top","right"]: ax.spines[sp].set_visible(False)
save(fig, "F56_22_vs_23_v7")

# Fig. 5-7
fig,(ax1,ax2)=plt.subplots(1,2,figsize=(8.4,3.7))
labels=["原版","支配强化"]
vals=[pricing["baseline_median_sum_s"],pricing["accelerated_median_sum_s"]]
ax1.bar(labels,vals,color=[LMID,DEEP],width=.55)
ax1.set_ylabel("24组固定输入的中位耗时之和 / s")
ax1.grid(axis="y",alpha=.14,color=GRID)
for i,v in enumerate(vals): ax1.text(i,v+.08,f"{v:.3f}",ha="center",fontsize=8.5)
ax1.text(.5,.92,f'比值 {pricing["ratio"]:.4f}×',
         transform=ax1.transAxes,ha="center",fontsize=9,color=DARK)
vals2=[pricing["baseline_labels"],pricing["accelerated_labels"]]
ax2.bar(labels,[v/1e6 for v in vals2],color=[LMID,DEEP],width=.55)
ax2.set_ylabel("生成标签数 / 百万"); ax2.grid(axis="y",alpha=.14,color=GRID)
for i,v in enumerate(vals2): ax2.text(i,v/1e6+.05,f"{v/1e6:.3f}M",ha="center",fontsize=8.5)
ax2.text(.5,.92,f'减少 {pricing["label_reduction_pct"]:.2f}%',
         transform=ax2.transAxes,ha="center",fontsize=9,color=DARK)
fig.text(.5,.015,
         f'{pricing["reduced_costs_preserved"]}固定真实定价输入的最小约化成本保持一致；3.1201×仅指受控pricing实验',
         ha="center",fontsize=8.1,color=DARK)
fig.tight_layout(rect=[0,.07,1,1])
save(fig, "F57_pricing_dominance_v7")

# Fig. 5-8
fig, ax = plt.subplots(figsize=(7.6,2.5))
lb=status["certified_lower_bound_s"]/60
ub=status["rational_upper_bound_s"]/60
ax.plot([lb,ub],[0,0],color=DARK,linewidth=2.6)
ax.scatter(lb,0,s=65,marker="s",color=DEEP,zorder=3)
ax.scatter(ub,0,s=65,marker="o",color=DEEP,zorder=3)
ax.annotate(f"有效全局下界\n{lb:.3f} min",(lb,0),
            xytext=(0,20),textcoords="offset points",ha="center",fontsize=8.5)
ax.annotate(f"认证可行上界\n{ub:.3f} min",(ub,0),
            xytext=(0,20),textcoords="offset points",ha="center",fontsize=8.5)
ax.text((lb+ub)/2,-.18,
        f'UB归一化间隙 = {status["gap_over_upper_bound"]*100:.3f}%',
        ha="center",fontsize=9,color=DARK)
ax.text((lb+ub)/2,-.31,"上下界尚未闭合：不宣称makespan全局最优",
        ha="center",fontsize=8.3,color=DARK)
ax.set_xlim(lb-.7,ub+.7); ax.set_ylim(-.43,.52); ax.set_yticks([])
ax.set_xlabel("零加权迟到最优面上的完成时间 / min")
for sp in ["top","right","left"]: ax.spines[sp].set_visible(False)
save(fig, "F58_certified_interval_v7")

# Fig. 5-9
bfl=[f for f in flights if f["type"]=="B"]
chains={u:sorted([f for f in bfl if f["aircraft"]==u],
                 key=lambda x:x["start_s"])
        for u in sorted({f["aircraft"] for f in bfl})}
fig, ax = plt.subplots(figsize=(8.4,3.5))
ypos={u:i for i,u in enumerate(chains)}
shades=[LIGHT,LMID,MID]
for u,chain in chains.items():
    cum=0
    for j,f in enumerate(chain):
        w=f["work_s"]
        ax.barh(ypos[u],w/60,left=cum/60,height=.52,
                color=shades[j],edgecolor="white")
        ax.text((cum+w/2)/60,ypos[u],
                f["flight_id"].replace("Q2-R-","R"),
                ha="center",va="center",fontsize=8,color=TEXT)
        cum += w
avg=bfix["average_lb_s"]/60
disc=bfix["exact_partition_lb_s"]/60
ax.axvline(avg,color=MID,linestyle=":",linewidth=1.2)
ax.axvline(disc,color=DEEP,linestyle="--",linewidth=1.2)
ax.text(avg,.98,"平均负载下界\n92.776 min",
        transform=ax.get_xaxis_transform(),ha="right",va="top",fontsize=8,color=DARK)
ax.text(disc,.98,"离散精确下界\n94.887 min",
        transform=ax.get_xaxis_transform(),ha="left",va="top",fontsize=8,color=DEEP)
ax.set_yticks(list(ypos.values()),list(ypos.keys())); ax.invert_yaxis()
ax.set_xlabel("固定B型任务累计工作量 / min"); ax.set_ylabel("B型实体无人机")
ax.grid(axis="x",alpha=.15,color=GRID)
for sp in ["top","right"]: ax.spines[sp].set_visible(False)
save(fig, "F59_B_discrete_bottleneck_v7")

manifest = {
    "formal_version": data["version"],
    "makespan_s": metrics["makespan_s"],
    "energy_kwh": metrics["energy_kwh"],
    "sorties": metrics["sorties"],
    "lb_s": status["certified_lower_bound_s"],
    "ub_s": status["rational_upper_bound_s"],
    "gap_over_ub": status["gap_over_upper_bound"],
    "global_makespan_optimality_proven": status["global_original_optimality_proven"],
    "figures": sorted(p.name for p in OUT.glob("F5*.pdf")),
}
(OUT/"FIGURE_MANIFEST.json").write_text(
    json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"
)
print(json.dumps(manifest,ensure_ascii=False,indent=2))
