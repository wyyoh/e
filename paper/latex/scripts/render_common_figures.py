#!/usr/bin/env python3
"""Chapter 1–3 publication figures, pinned to wyyoh/e main e9e5ddea.

Run via build_common_figures.py. Drawing routines retained from the reviewed package.
Inputs: validated repository raw data and its checked aggregation snapshot.
Schematic coordinates are layout units, never observed geography or task time.
"""
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle, FancyArrowPatch, Polygon
from matplotlib.colors import LinearSegmentedColormap
from matplotlib import patheffects as pe
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_origin
from pyproj import CRS, Transformer, Geod
import fitz

LATEX = Path(__file__).resolve().parents[1]
ROOT = LATEX / 'figures/common_model'
FIG = ROOT; FIG.mkdir(parents=True, exist_ok=True)
DATA = ROOT / 'data'
RAW = LATEX.parents[1] / 'problems/D/q1/data/raw'
C = {'blue':'#2F5D8A','amber':'#E6A23C','teal':'#54B8A9',
     'lake':'#4FA3D9','purple':'#8064B2','red':'#D97C6C',
     'ink':'#222222','grid':'#E6E6E6','muted':'#62676B'}
plt.rcParams.update({'font.family':['Arial','Arimo','Noto Sans CJK JP','DejaVu Sans'],
                     'font.size':9.5,'axes.unicode_minus':False,'mathtext.fontset':'stix',
                     'pdf.fonttype':3,'ps.fonttype':42,'svg.fonttype':'path',
                     'axes.edgecolor':C['muted'],'axes.linewidth':.7,
                     'text.color':C['ink'],'axes.labelcolor':C['ink'],
                     'xtick.color':C['ink'],'ytick.color':C['ink'],
                     'figure.facecolor':'white','axes.facecolor':'white',
                     'savefig.facecolor':'white'})
# Explicitly choose an installed CJK family without shipping font files.
font_path='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
if Path(font_path).exists():
    fm.fontManager.addfont(font_path)
    plt.rcParams['font.family']=[fm.FontProperties(fname=font_path).get_name(),'Arimo','DejaVu Sans']


def txt(ax,x,y,s,sz=9.5,**kw):
    return ax.text(x,y,s,fontsize=sz,ha=kw.pop('ha','left'),va=kw.pop('va','center'),**kw)

def rect(ax,x,y,w,h,color=None,alpha=1,edge=None,lw=.8,**kw):
    p=Rectangle((x,y),w,h,facecolor=color or 'white',edgecolor=edge or 'none',
                linewidth=lw,alpha=alpha,**kw); ax.add_patch(p);return p

def arrow(ax,a,b,color=None,lw=1.3,style='-|>',ms=9,**kw):
    p=FancyArrowPatch(a,b,arrowstyle=style,mutation_scale=ms,color=color or C['blue'],
                      linewidth=lw,shrinkA=0,shrinkB=0,**kw);ax.add_patch(p);return p

def canvas(size):
    f=plt.figure(figsize=size)
    a=f.add_axes([.02,.025,.96,.95]);a.set_xlim(0,100);a.set_ylim(0,100);a.axis('off')
    return f,a

def save(f,name,dpi=500):
    f.savefig(FIG/(name+'.pdf'), metadata={'CreationDate': None, 'ModDate': None})
    plt.close(f)

def fig11():
    f,a=canvas((7.55,5.85))
    cols=[(.9,23.4),(25.9,23.4),(50.9,23.4),(75.9,23.2)]
    colors=[C['blue'],C['amber'],C['teal'],C['purple']]
    inputs=['节点与地形\n位置表 · DEM','货箱与需求\n逐箱清单 · 目的地','运输装备与能源\n机型 · 电池 · 恢复','时限与通信条件\n配送要求 · 链路参数']
    for (x,w),s in zip(cols,inputs):
        rect(a,x,88,w,11,color='#F7F9FA',edge=C['grid'])
        txt(a,x+w/2,93.5,s,9.2,ha='center',linespacing=1.5)
        a.plot([x+w/2,x+w/2],[88,86.3],color=C['muted'],lw=.7)
        arrow(a,(x+w/2,86.3),(x+w/2,84.8),C['muted'],.85,ms=7)
    a.plot([12.6,87.5],[86.3,86.3],color=C['muted'],lw=.7)
    titles=['Q1  单点安全能力\n与货箱组批','Q2  异构运输\n与双资源调度','Q3  运输—中继\n联合执行','Q4  冻结日程后的\n独立资源配置']
    objects=['O01—单服务区—O01\n不可拆货箱','多点运输任务\n有限飞机与共享电池\n箱级配送时限','真实运输轨迹\n连续通信需求','Q3 正式 time 日程\n实际运输 / 中继关联\n组间资源不共享']
    decisions=['安全载荷 · 可行批型\n运输机型','箱组 · 路线 · 机型\n飞机 · 电池 · 开始时刻','运输时刻 · 中继位置\n高度 · 窗口 · 提供方\n中继实体与能源组件','不可拆分组\n同型配置 · 分型缺口']
    outputs=['单点能力与组批方案\n架次 · 能耗 · 累计时间','箱级交付记录\n可执行运输日程','经过完整验证的\n运输—中继日程','独立分组方案\n资源需求向量']
    changes=['单点往返特例','多点访问 + 有限资源\n箱级配送时限','新增连续通信约束','新增组间不共享']
    for i,((x,w),co) in enumerate(zip(cols,colors)):
        rect(a,x,36,w,48.5,'white',edge=co,lw=1.0)
        rect(a,x,76.5,w,8,color=co,alpha=.13)
        rect(a,x,76.5,.6,8,color=co)
        txt(a,x+w/2,80.4,titles[i],10.0,ha='center',weight='bold',linespacing=1.4)
        txt(a,x+1.3,72.7,'研究对象',8.8,color=co,weight='bold')
        txt(a,x+1.3,67.1,objects[i],8.8,linespacing=1.35)
        a.plot([x+1.3,x+w-1.3],[62.5,62.5],color=C['grid'],lw=.7)
        txt(a,x+1.3,60,'主要决策',8.8,color=co,weight='bold')
        txt(a,x+1.3,54.1,decisions[i],8.7,linespacing=1.45)
        a.plot([x+1.3,x+w-1.3],[46.8,46.8],color=C['grid'],lw=.7)
        txt(a,x+1.3,44.5,'任务输出',8.8,color=co,weight='bold')
        txt(a,x+1.3,39.7,outputs[i],8.9,linespacing=1.45)
    for i in range(3):
        x1=cols[i][0]+cols[i][1]+.1;x2=cols[i+1][0]-.25
        arrow(a,(x1,68),(x2,68),C['red'] if i==2 else C['muted'],1.05,ms=6)
    # Explicit freeze boundary; no ambiguity about inheriting Q2 absolute times.
    for x in [74.8,75.2]: a.plot([x,x],[35.5,85.8],color=C['red'],lw=.85)
    transitions=[('Q1 → Q2','能力与组批分析基础\nQ2 重新联合决策'),
                 ('Q2 → Q3','运输结构与物理属性\n重新安排联合时序'),
                 ('Q3 → Q4  严格冻结','time 日程、任务及\n实际通信保障关系')]
    for i,(h,s) in enumerate(transitions):
        x=1+i*33.15;w=31.8;co=C['red'] if i==2 else C['blue']
        rect(a,x,20,w,12,'white',edge=C['grid'])
        txt(a,x+1.2,29,h,9.1,color=co,weight='bold')
        txt(a,x+1.2,23.9,s,8.9,linespacing=1.45)
    # Common foundation and a single external reuse bus.
    rect(a,1,1,98,14.6,'#F7F9FA',edge=C['grid'])
    txt(a,3,13.0,'四问共同复用的物理模型',9.1,weight='bold')
    items=[('AEQD / DEM\n航段几何',13),('逐段载荷',38),('时间 / 能耗',61),('任务属性',86)]
    for s,x in items: txt(a,x,6.5,s,9.5,ha='center',linespacing=1.4)
    for x1,x2 in [(24,29),(46,51),(72,76)]:arrow(a,(x1,6.5),(x2,6.5),C['muted'],1.15,ms=7)
    a.plot([.2,.2,99.7,99.7],[15.6,34.6,34.6,15.6],color=C['muted'],lw=.7)
    for x,w in cols:arrow(a,(x+w/2,34.6),(x+w/2,36),C['muted'],.7,ms=5)
    txt(a,50,17.6,'模块颜色仅区分问题；Q2 放开多点访问，四问可行域并非严格逐层嵌套。',8.3,ha='center',color=C['muted'])
    save(f,'fig1_1_decision_inheritance')


def prepare_dem():
    ns=json.loads((DATA/'nodes_demand.json').read_text()); o=next(n for n in ns if n['id']=='O01')
    crs=CRS.from_proj4(f"+proj=aeqd +lat_0={o['lat']} +lon_0={o['lon']} +datum=WGS84 +units=m")
    # Figure-only reprojection; raw raster remains untouched for model geometry.
    xmin,xmax,ymin,ymax=-7200.,6500.,-1600.,9400.;res=25.
    nx=round((xmax-xmin)/res);ny=round((ymax-ymin)/res)
    dst=np.full((ny,nx),np.nan,dtype='float32');transform=from_origin(xmin,ymax,res,res)
    with rasterio.open(RAW/'镇龙乡及周边30米DEM.tif') as ds:
        origin_meta=json.loads((DATA/'dem_metadata.json').read_text())
        tie=origin_meta['geotiff_metadata']['ModelTiepoint']; scale=origin_meta['geotiff_metadata']['ModelPixelScale']
        assert abs(ds.transform.c-(tie[3]-scale[0]/2))<1e-11
        assert abs(ds.transform.f-(tie[4]+scale[1]/2))<1e-11
        raw=ds.read(1).astype('float32')
        from scipy.io import loadmat
        actual_nodata=float(loadmat(RAW/'镇龙乡及周边30米DEM.mat', variable_names=['nodata'])['nodata'][0,0])
        raw[(~np.isfinite(raw)) | (raw == actual_nodata)] = np.nan
        reproject(raw,dst,src_transform=ds.transform,src_crs=ds.crs,src_nodata=np.nan,
                  dst_transform=transform,dst_crs=crs,dst_nodata=np.nan,resampling=Resampling.nearest)
    assert np.isfinite(dst).all(), 'Map bounds contain invalid data; display with a mask rather than zero.'
    np.savez_compressed(DATA/'dem_display_aeqd.npz',elevation_m=dst,extent_m=np.array([xmin,xmax,ymin,ymax]))
    geod=Geod(ellps='WGS84');d=1/3600
    ew=geod.inv(o['lon'],o['lat'],o['lon']+d,o['lat'])[2]
    nsmet=geod.inv(o['lon'],o['lat'],o['lon'],o['lat']+d)[2]
    (DATA/'map_display_metadata.json').write_text(json.dumps({
        'projection':crs.to_wkt(),'centre':{'lon':o['lon'],'lat':o['lat']},
        'original_spacing_degrees':[scale[0],scale[1]],'original_spacing_arcseconds':1,
        'spacing_at_O01_m':{'east_west':ew,'north_south':nsmet},
        'display_resampling':'nearest','display_pixel_m':res,'extent_m':[xmin,xmax,ymin,ymax],
        'model_geometry_recomputed_from_display_raster':False,
        'display_elevation_min_m':float(np.nanmin(dst)), 'display_elevation_max_m':float(np.nanmax(dst)),
        'PixelIsPoint_half_pixel_correction':'rasterio transform checked against tiepoint; not applied a second time',
        'nodata':{'source': 'MAT nodata field', 'value': actual_nodata, 'display_window_has_invalid_pixels': False}},ensure_ascii=False,indent=2))
    return ns,crs,dst,(xmin/1000,xmax/1000,ymin/1000,ymax/1000)


def terrain_map():
    ns,crs,z,extent=prepare_dem()
    f=plt.figure(figsize=(5.3,4.95));a=f.add_axes([.115,.245,.865,.68])
    cmap=LinearSegmentedColormap.from_list('terrain_sequential',['#FFFEFA','#F2E6CA','#DCC298','#B69768','#806341'])
    im=a.imshow(np.ma.masked_invalid(z),extent=extent,origin='upper',cmap=cmap,vmin=0,vmax=800,interpolation='nearest')
    a.set_aspect('equal');a.set_xlim(extent[:2]);a.set_ylim(extent[2:])
    x=np.linspace(extent[0]+.0125,extent[1]-.0125,z.shape[1]);y=np.linspace(extent[3]-.0125,extent[2]+.0125,z.shape[0])
    a.contour(x,y,z,levels=[300,600,900],colors='#816D52',linewidths=.33,alpha=.30)
    a.set_xticks(np.arange(-6,7,2));a.set_yticks(np.arange(0,10,2))
    a.grid(color='white',lw=.65,alpha=.7)
    a.set_xlabel(r'$x\,/\,\mathrm{km}$',labelpad=1,fontsize=10.5)
    a.set_ylabel(r'$y\,/\,\mathrm{km}$',labelpad=1,fontsize=10.5)
    services=[n for n in ns if n['id']!='O01']
    k=2.55
    a.scatter([n['x_m']/1000 for n in services],[n['y_m']/1000 for n in services],
              s=[n['mass_kg']*k for n in services],c=C['lake'],alpha=.88,
              edgecolor=C['blue'],linewidth=1.0,zorder=5)
    a.scatter([0],[0],marker='*',s=195,c=C['amber'],edgecolor=C['blue'],linewidth=1,zorder=7)
    # Greedy label collision avoidance; only text is moved, never node locations.
    f.canvas.draw();rend=f.canvas.get_renderer();accepted=[];label_rows=[]
    base_offsets=[(10,9),(10,-12),(-10,9),(-10,-12),(15,0),(-15,0),(0,17),(0,-18)]
    preferred={'S001':(15,13),'S004':(10,9),'S008':(-10,9),'S014':(-10,-12),'S003':(12,10),
               'S012':(-10,-12),'S015':(-10,9),'S011':(-10,-12),'O01':(11,-16)}
    point_boxes=[]
    from matplotlib.transforms import Bbox
    for n in ns:
        xx,yy=a.transData.transform((n['x_m']/1000,n['y_m']/1000))
        radius=(math.sqrt(k*n['mass_kg'])/2+1.5) * f.dpi/72 if n['id']!='O01' else 9*f.dpi/72
        point_boxes.append(Bbox.from_extents(xx-radius,yy-radius,xx+radius,yy+radius))
    for n in sorted(ns,key=lambda n:-n['mass_kg']):
        xy=(n['x_m']/1000,n['y_m']/1000);best=None
        candidates=[preferred.get(n['id'],(10,9))]+base_offsets
        for dx,dy in candidates:
            ha='left' if dx>0 else ('right' if dx<0 else 'center')
            label=n['id'] if n['id']!='O01' else 'O01 调度中心'
            t=a.annotate(label,xy,xytext=(dx,dy),textcoords='offset points',ha=ha,va='center',fontsize=9.3,
                         color=C['ink'],zorder=9,path_effects=[pe.withStroke(linewidth=2.8,foreground='white',alpha=.95)])
            b=t.get_window_extent(rend).expanded(1.10,1.2)
            score=sum(b.overlaps(q) for q in accepted)*100+sum(b.overlaps(q) for q in point_boxes)*50
            if not a.bbox.contains(b.x0,b.y0) or not a.bbox.contains(b.x1,b.y1):score+=300
            t.remove()
            if best is None or score<best[0]: best=(score,dx,dy,ha)
            if score==0:break
        _,dx,dy,ha=best
        t=a.annotate(label,xy,xytext=(dx,dy),textcoords='offset points',ha=ha,va='center',fontsize=9.3,
                     color=C['ink'],zorder=9,path_effects=[pe.withStroke(linewidth=2.8,foreground='white',alpha=.95)],
                     arrowprops={'arrowstyle':'-','color':C['blue'],'lw':.6,'shrinkA':1,'shrinkB':max(4,math.sqrt(k*n['mass_kg'])/2)})
        accepted.append(t.get_window_extent(rend).expanded(1.08,1.1))
        label_rows.append({'id':n['id'],'offset_points':[dx,dy],'location_unchanged':True})
    # Map scale is a scale in this explicitly stated AEQD plane.
    x0,y0=-6.55,-1.04
    for j in range(2):rect(a,x0+j,y0,1,.11,C['blue'] if j==0 else 'white',edge=C['blue'],lw=.6,zorder=6)
    a.text(x0,y0+.25,'0',fontsize=8.4,ha='center');a.text(x0+2,y0+.25,'2 km',fontsize=8.4,ha='center')
    # True north is computed locally, not assumed parallel to the grid y axis.
    inv=Transformer.from_crs(crs,4326,always_xy=True);fw=Transformer.from_crs(4326,crs,always_xy=True)
    px,py=-6200,8000;lo,la=inv.transform(px,py);lo2,la2,_=Geod(ellps='WGS84').fwd(lo,la,0,650);qx,qy=fw.transform(lo2,la2)
    arrow(a,(px/1000,py/1000),(qx/1000,qy/1000),C['blue'],1.15,ms=10,zorder=7)
    a.text(qx/1000,qy/1000+.2,'N',ha='center',fontsize=9,weight='bold',zorder=7)
    a.text(px/1000+.28,py/1000+.27,'真北',fontsize=8.1,va='center',zorder=7)
    f.text(.035,.967,'(a) 地形与需求位置',fontsize=10.3,weight='bold',va='top')
    cbax=f.add_axes([.17,.135,.47,.024]);cb=f.colorbar(im,cax=cbax,orientation='horizontal',ticks=[0,200,400,600,800])
    cb.outline.set_linewidth(.45);cb.ax.tick_params(labelsize=8.0,length=2,pad=1.5)
    cb.set_label('地形高程 / m',fontsize=8.8,labelpad=2)
    # Three area-reference markers live outside the geographic plotting area.
    leg_handles=[a.scatter([],[],s=m*k,c=C['lake'],edgecolor=C['blue'],linewidth=.8,alpha=.88) for m in [25,80,150]]
    f.legend(leg_handles,['25','80','150'],title='需求质量 / kg（面积）',loc='center',bbox_to_anchor=(.805,.13),
             ncol=3,frameon=False,fontsize=8.0,title_fontsize=8.3,handletextpad=.5,columnspacing=.55,labelspacing=.7)
    f.text(.115,.032,'WGS84 AEQD，以 O01 为中心；原始 DEM 间隔 1″（经纬度）。',fontsize=8.0,color=C['muted'])
    f.text(.115,.007,'显示重投影不用于航段几何计算；点位与节点高程保留原表。',fontsize=8.0,color=C['muted'])
    (DATA/'map_label_positions.json').write_text(json.dumps(label_rows,ensure_ascii=False,indent=2))
    save(f,'fig3_1a_terrain_demand')


def demand_panel():
    ss=[n for n in json.loads((DATA/'nodes_demand.json').read_text()) if n['id']!='O01']
    f=plt.figure(figsize=(2.20,4.95));a=f.add_axes([.26,.245,.69,.68])
    y=np.arange(len(ss));m=[n['mass_kg'] for n in ss]
    a.hlines(y,0,m,color=C['lake'],lw=2.2,alpha=.72)
    a.scatter(m,y,s=25,c=C['lake'],edgecolor=C['blue'],lw=.7,zorder=3)
    for yi,mi in zip(y,m):a.text(mi+5,yi,str(mi),va='center',ha='left',fontsize=8.5)
    a.set_yticks(y,[n['id'] for n in ss],fontsize=8.8);a.set_ylim(14.6,-.6)
    a.set_xlim(0,185);a.set_xticks([0,50,100,150]);a.tick_params(axis='x',labelsize=8.2,pad=3)
    a.tick_params(axis='y',length=0,pad=4)
    for s in ['top','right','left']:a.spines[s].set_visible(False)
    a.spines['bottom'].set_color(C['muted']);a.grid(axis='x',color=C['grid'],lw=.7)
    a.set_axisbelow(True);a.set_xlabel('需求质量 / kg',fontsize=8.8,labelpad=4)
    f.text(.03,.967,'(b) 服务区需求质量',fontsize=10.3,weight='bold',va='top')
    f.text(.26,.144,'15 个服务区',fontsize=9.2,weight='bold')
    f.text(.26,.100,'80 箱  |  758 kg',fontsize=9.2)
    f.text(.26,.058,'总体积 2.011 m³',fontsize=9.2)
    f.text(.26,.009,'按原编号排列，非优化结果。',fontsize=8.0,color=C['muted'])
    save(f,'fig3_1b_demand_mass')


def combine_horizontal(names,name):
    doc=fitz.open();sizes=[];srcdocs=[]
    for n in names:
        sd=fitz.open(FIG/(n+'.pdf'));srcdocs.append(sd);sizes.append(sd[0].rect)
    page=doc.new_page(width=sum(r.width for r in sizes),height=max(r.height for r in sizes));x=0
    for sd,r in zip(srcdocs,sizes):
        page.show_pdf_page(fitz.Rect(x,0,x+r.width,r.height),sd,0);x+=r.width
    doc.save(FIG/(name+'.pdf'),deflate=True)
    doc.close()
    for sd in srcdocs: sd.close()

def fig32():
    f,a=canvas((7.55,7.1))
    txt(a,1,98,'(a) 多航段几何与作业高度',10.5,weight='bold')
    txt(a,99,98,'机制示意：非实际任务、非真实地形剖面',8.5,ha='right',color=C['muted'])
    # Each panel is a self-contained leg, with differing cruise altitudes.
    legs=[(7,34,67.5,70,77,21.5,'①  O01 → $S_i$'),
          (38,65,70,72,81,53,'②  $S_i$ → $S_j$'),
          (69,96,72,67.5,78.5,83.7,'③  $S_j$ → O01')]
    points=[(7,67.5,'O01'),(34,72.7,r'$S_i$'),(38,72.7,r'$S_i$'),(65,74.7,r'$S_j$'),(69,74.7,r'$S_j$'),(96,67.5,'O01')]
    for k,(x0,x1,z0,z1,peak,xpeak,label) in enumerate(legs):
        xx=np.array([x0,x0+3,x0+7,xpeak-4,xpeak,xpeak+4,x1-3,x1]);
        zz=np.array([z0,z0+.7,z0+2.7,peak-2.1,peak,peak-2.8,z1+.8,z1])
        # Layout curves are intentionally qualitative and are never mapped to DEM.
        a.fill_between(xx,65.3,zz,color=C['amber'],alpha=.16,linewidth=0)
        a.plot(xx,zz,color='#AB9067',lw=1.0)
        hs=z0+(0 if k==0 else 2.7);he=z1+(0 if k==2 else 2.7);H=peak+4.5
        arrow(a,(x0,hs),(x0,H),C['lake'],1.5,ms=7)
        arrow(a,(x0,H),(x1,H),C['lake'],1.5,ms=8)
        arrow(a,(x1,H),(x1,he),C['lake'],1.5,ms=7)
        a.plot([x0,x1],[H,H],color=C['lake'],lw=.5,alpha=.2)
        arrow(a,(xpeak,peak),(xpeak,H),C['red'],.95,style='<->',ms=7)
        txt(a,xpeak+1,peak+2.1,'50 m',8.5,color=C['red'])
        txt(a,(x0+x1)/2,92.0,label,10,ha='center',weight='bold')
        txt(a,(x0+x1)/2,H+1.5,r'$H_{ij}=\max_{c\in\mathcal{C}_{ij}}Z_c+50$',8.4,ha='center')
        txt(a,x0+1.0,(hs+H)/2,'爬升 '+r'$H_{ij}-h_i$' if k==0 else '爬升',8.1,rotation=90,ha='left')
        txt(a,x1-1.1,(he+H)/2,'下降',8.1,rotation=90,ha='right')
        # Node surface-to-work height is a different quantity from clearance.
        if k<2:
            a.plot([x1-1.9,x1+1.0],[z1,z1],color=C['muted'],lw=.65,linestyle=':')
            arrow(a,(x1-1.4,z1),(x1-1.4,he),C['teal'],.75,style='<->',ms=5)
    for x,y,label in points:
        a.plot(x,y,'o',ms=4.5,mfc=C['teal'],mec=C['blue'],mew=.6,zorder=5)
        txt(a,x,64.1,label,9,ha='center')
    arrow(a,(3,65.3),(3,88.8),C['muted'],.75,ms=6)
    txt(a,1.5,77.5,'海拔 $z$',8.4,rotation=90,ha='center')
    txt(a,50,60.8,r'作业海拔：$h_i=z_i+30\,\mathrm{m}$（30 m 为 AGL），$h_{O01}=z_{O01}$；横轴为累计路径距离示意。',8.8,ha='center')
    a.plot([1,99],[58.7,58.7],color=C['grid'],lw=.85)

    txt(a,1,56.4,'(b) 任务阶段、交付时刻与逐段载荷',10.5,weight='bold')
    txt(a,99,56.4,'相对时间 τ；阶段长度仅示意',8.6,ha='right',color=C['muted'])
    bd=[9,21,38,47,62,72,96]
    labels=['准备\n与装载','① 首段\n飞行','$S_i$\n交接','② 第二段\n飞行','$S_j$\n交接','③ 空载\n返航']
    for i,(l,r,s) in enumerate(zip(bd,bd[1:],labels)):
        col=C['amber'] if i in [2,4] else (C['lake'] if i else C['muted'])
        rect(a,l,46.2,r-l,6.8,col,.17,edge=col,lw=.85,hatch='///' if i in [2,4] else None)
        txt(a,(l+r)/2,49.6,s,9,ha='center',linespacing=1.4)
    arrow(a,(9,44.8),(98,44.8),C['muted'],.8,ms=6)
    times=[(9,'0'),(38,r'$a_{ri}$'),(47,r'$\theta_{ri}$'),(62,r'$a_{rj}$'),(72,r'$\theta_{rj}$'),(96,r'$p_r$')]
    for x,s in times:
        a.plot([x,x],[44.3,45.3],color=C['muted'],lw=.7)
        txt(a,x,42.8,s,9.8,ha='center')
    txt(a,9,54.5,'开始准备',8.3)
    # Payload is an accounting staircase updated at handover completion.
    a.plot([21,47,47,72,72,96],[38.7,38.7,35.5,35.5,32.2,32.2],color=C['teal'],lw=1.7)
    a.fill_between([21,47,47,72,72,96],[38.7,38.7,35.5,35.5,32.2,32.2],32.2,color=C['teal'],alpha=.12)
    for y,s in [(38.7,r'$D_i+D_j$'),(35.5,r'$D_j$'),(32.2,'0')]:txt(a,18.8,y,s,9.5,ha='right')
    txt(a,9,36,'逐段载荷',8.5,rotation=90,ha='center')
    for x in [47,72]:a.plot([x,x],[32.2,42],ls=':',lw=.7,color=C['muted'])
    txt(a,33.5,40.2,r'$q_{r,0}$',9.5,ha='center')
    txt(a,59.5,37.0,r'$q_{r,1}$',9.5,ha='center')
    txt(a,84,34.9,r'$q_{r,2}=0$',9.3,ha='center')
    txt(a,83,30.5,'空载返航：水平与爬升能耗仍计入',8.4,ha='center',color=C['red'],weight='bold')
    txt(a,6,28.8,r'同站货箱：$\delta_{rb}=\theta_{rj}$；绝对送达：$C_b=s_r+\delta_{rb}$。',9.6)
    txt(a,6,25.8,'到达 ≠ 交接完成；阶梯为模型载荷，并非实测卸货曲线；准备装载不展开逐秒过程。',8.3,color=C['muted'])
    a.plot([1,99],[23.9,23.9],color=C['grid'],lw=.85)

    txt(a,1,21.8,'(c) 载荷—能耗关系与公共输出',10.5,weight='bold')
    xx=[1,35,69];ww=[32,32,30]
    heads=['载荷—航程','逐段累加能耗','返航安全约束']
    formulas=[r'$L_m(q)=L_m^0-(L_m^0-L_m^F)(q/Q_m)^{3/2}$',
              r'$E_r=\sum_{\mathrm{legs}}(E^{\mathrm{hor}}+E^{\mathrm{up}})$',
              r'$SOC_r^{\mathrm{return}}=1-E_r/E_m\geq\alpha_m$']
    for i,(x,w,h,s) in enumerate(zip(xx,ww,heads,formulas)):
        rect(a,x,11.6,w,7.9,'#F7F9FA',edge=C['grid'],lw=.7)
        txt(a,x+1.0,17.8,h,8.8,color=C['blue'],weight='bold')
        txt(a,x+w/2,14.1,s,8.6 if i==0 else 9.5,ha='center')
    txt(a,2,8.6,r'公共输出：$p_r$、$E_r$、$SOC_r^{\mathrm{return}}$、$c_r$、$\delta_{rb}$',10,weight='bold')
    txt(a,2,5.5,r'$c_r$ 按两阶段充电公式计算；最后充电不并入 $p_r$ 或本轮最后返航时间。',8.6)
    txt(a,2,2.0,'当前模型约定：下降计入时间、不另加下降能耗；普通交接不额外添加未给定的悬停功率。',8.3,color=C['muted'])
    save(f,'fig3_2_transport_physics')
    (DATA/'mechanism_semantics.json').write_text(json.dumps({
        'kind':'mechanism schematic, not a measured or scheduled task',
        'example_route':['O01','S_i','S_j','O01'],'Q1_is_K1_special_case':True,
        'profile_coordinates':'qualitative drawing units, not DEM elevations or flight results',
        'timeline_positions':bd,'timeline_units':'schematic layout only; not seconds or minutes',
        'payloads':['D_i + D_j','D_j','0'],'handover_definition':'delivery at completion, not arrival',
        'normal_transport_clearance_m':50,'service_work_AGL_m':30,
        'ordinary_transport_height_conflict_handling':'report H_ij < max(h_i,h_j); do not clip negative climb',
        'charge_excluded_from_task_duration':True},ensure_ascii=False,indent=2))


def fig_a1():
    f,a=canvas((7.55,4.2))
    txt(a,1,96,'(a) 像元中心与边界',10.5,weight='bold')
    txt(a,52,96,'(b) 稀疏采样与完整相交',10.5,weight='bold')
    # Grid A. Rows grow downward, longitude grows rightward.
    x0,y0,cw,ch=7,79,8,14
    for r in range(3):
        for c in range(4):
            rect(a,x0+c*cw,y0-(r+1)*ch,cw,ch,C['lake'],.07,edge=C['muted'],lw=.55)
            a.plot(x0+(c+.5)*cw,y0-(r+.5)*ch,'o',ms=3,mfc=C['blue'],mec='white',mew=.3)
    rect(a,x0,y0-ch,cw,ch,C['amber'],.18,edge=C['amber'],lw=1)
    a.plot(x0,y0,'s',ms=4,mfc='white',mec=C['red'],mew=1)
    arrow(a,(7,84),(40,84),C['muted'],.8,ms=7);txt(a,24,87,'经度 λ 增大',8.8,ha='center')
    arrow(a,(3,78),(3,38),C['muted'],.8,ms=7);txt(a,1,58,'行号增大',8.5,rotation=90,ha='center')
    a.plot([x0+cw/2,x0+cw/2],[y0-ch/2,y0],ls='--',color=C['red'],lw=.8)
    a.plot([x0,x0+cw/2],[y0-ch/2,y0-ch/2],ls='--',color=C['red'],lw=.8)
    txt(a,16.0,75.0,r'中心 $(\lambda_c,\varphi_c)$',9.0)
    txt(a,16.0,81.0,r'边界 $(\lambda_0,\varphi_0)$',9.0)
    txt(a,23,28.0,r'$\lambda_0=\lambda_c-\Delta\lambda/2$',11,ha='center')
    txt(a,23,20.5,r'$\varphi_0=\varphi_c+\Delta\varphi/2$',11,ha='center')
    txt(a,23,12,'半像元转换是坐标约定，不是平移地形。',8.5,ha='center',color=C['muted'])
    # Grid B: diagonal touches corners; all closed cells at a touch are included.
    bx,by,sw,sh=57,81,7.1,12.5
    start=np.array([.25,.25]);end=np.array([4.75,4.75]);closed=set()
    # Same point-cell convention as project geometry.py, evaluated only for this schematic.
    def pc(p):
        def idx(v):return (round(v)-1,round(v)) if abs(v-round(v))<1e-9 else (math.floor(v),)
        return {(rr,cc) for cc in idx(p[0]) for rr in idx(p[1])}
    ts=[0.,1.]+[(k-.25)/4.5 for k in range(1,5)]
    for t in ts+[(u+v)/2 for u,v in zip(sorted(ts),sorted(ts)[1:])]:closed.update(pc(start+t*(end-start)))
    sample_ts=[0,.45,1];sample_cells={(math.floor((start+t*(end-start))[1]),math.floor((start+t*(end-start))[0])) for t in sample_ts}
    for r in range(5):
        for c in range(5):
            if (r,c) in sample_cells:color,alpha,hatch=C['lake'],.30,None
            elif (r,c) in closed:color,alpha,hatch=C['amber'],.20,'///'
            else:color,alpha,hatch='white',1,None
            rect(a,bx+c*sw,by-(r+1)*sh,sw,sh,color,alpha,edge=C['muted'],lw=.6,hatch=hatch)
    def xy(p):return (bx+p[0]*sw,by-p[1]*sh)
    p0,p1=xy(start),xy(end)
    a.plot([p0[0],p1[0]],[p0[1],p1[1]],color=C['blue'],lw=1.35)
    for t in sample_ts:
        x,y=xy(start+t*(end-start));a.plot(x,y,'o',ms=5.0,mfc='white',mec=C['blue'],mew=1.25)
    x,y=xy(np.array([3,3]));a.plot(x,y,'s',ms=6,mfc='none',mec=C['red'],mew=1.1)
    a.annotate('角点接触：\n相邻闭像元均计入',(x,y),xytext=(97,60),textcoords='data',ha='right',va='center',fontsize=8.8,
               arrowprops={'arrowstyle':'-','color':C['red'],'lw':.8})
    rect(a,54,11.0,2.4,3.5,C['lake'],.3,edge=C['blue'],lw=.5);txt(a,57,12.8,'采样点所在像元',8.4)
    rect(a,77,11.0,2.4,3.5,C['amber'],.2,edge=C['muted'],lw=.5,hatch='///');txt(a,80,12.8,'仅被轨迹接触',8.4)
    txt(a,50,4.7,'像元相交机制示意，不对应某条实际航段；实际 AEQD 直线须反投影到 DEM 坐标后求交。',8.3,ha='center',color=C['muted'])
    txt(a,50,.8,'完整遍历仍受 DEM 分辨率限制，不能识别像元尺度以下的全部障碍物。',8.3,ha='center',color=C['muted'])
    save(f,'figA1_dem_cells')
    (DATA/'dem_schematic_cells.json').write_text(json.dumps({'kind':'schematic, not an actual flight leg',
        'grid_shape':[5,5],'path_start':start.tolist(),'path_end':end.tolist(),
        'sampling_parameters':sample_ts,'closed_cells':sorted(closed),
        'sample_cells':sorted(sample_cells),'not_a_reproduced_counterexample':True},indent=2))


def main():
    fig11();terrain_map();demand_panel()
    combine_horizontal(['fig3_1a_terrain_demand','fig3_1b_demand_mass'],'fig3_1_terrain_and_demand')
    fig32();fig_a1()
    print('Generated',len(list(FIG.glob('*.pdf'))),'PDF files in',FIG)

if __name__=='__main__':
    raise SystemExit('Use python scripts/build_common_figures.py to validate source data before rendering.')
