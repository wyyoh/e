"""Publication-style static figures from computed CSV/JSON; no embedded answers."""
import argparse
import csv
import json
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator,PercentFormatter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from model.io import ROOT,load_inputs
from model.geometry import load_dem,ProjectedRoute
from scripts.validate import read_csv

COLORS={'A':'#2374AB','B':'#E09F3E','C':'#2A9D8F'}


def figures(out,folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
                         'axes.spines.right':False,'figure.facecolor':'white','savefig.facecolor':'white'})
    nodes,types,boxes=load_inputs();dem=load_dem()
    def save(fig,name):
        fig.savefig(folder/name,dpi=180,bbox_inches='tight');plt.close(fig)
    # The map is visualization only: complete cells are computed analytically elsewhere.
    fig,ax=plt.subplots(figsize=(9,8),layout='constrained')
    lons=[n.lon for n in nodes.values()];lats=[n.lat for n in nodes.values()]
    xlim=(min(lons)-.012,max(lons)+.012);ylim=(min(lats)-.012,max(lats)+.012)
    c0=max(0,int((xlim[0]-dem.x0)/dem.dx));c1=min(dem.values.shape[1],int((xlim[1]-dem.x0)/dem.dx)+1)
    r0=max(0,int((ylim[1]-dem.y0)/dem.dy));r1=min(dem.values.shape[0],int((ylim[0]-dem.y0)/dem.dy)+1)
    im=ax.imshow(dem.values[r0:r1,c0:c1],extent=[dem.x0+c0*dem.dx,dem.x0+c1*dem.dx,dem.y0+r1*dem.dy,dem.y0+r0*dem.dy],
                 cmap='terrain',alpha=.75,aspect=1/np.cos(np.radians(nodes['O01'].lat)))
    for s,n in nodes.items():
        if s=='O01':continue
        route=ProjectedRoute(nodes['O01'],n,dem)
        xy=route.xy0+np.linspace(0,1,200)[:,None]*(route.xy1-route.xy0)
        lon,lat=route.inverse.transform(xy[:,0],xy[:,1])
        ax.plot(lon,lat,color='#1D3557',lw=1.05,alpha=.75)
        ax.scatter(n.lon,n.lat,c='#1D3557',s=20)
        ax.annotate(s,(n.lon,n.lat),xytext=(4,5),textcoords='offset points',fontsize=9,
                    bbox=dict(facecolor='white',edgecolor='none',alpha=.65,pad=1))
    n=nodes['O01'];ax.scatter(n.lon,n.lat,marker='*',s=190,c='#C1121F',zorder=10)
    ax.annotate('O01',(n.lon,n.lat),xytext=(7,-12),textcoords='offset points',weight='bold')
    ax.set(xlim=xlim,ylim=ylim,xlabel='Longitude (WGS84 degrees)',ylabel='Latitude (WGS84 degrees)',
           title='Q1 | 15 single-service round trips\nStraight routes in O01-centred AEQD; inverse-projected on the DEM')
    fig.colorbar(im,ax=ax,shrink=.65,label='DEM elevation (m)')
    save(fig,'map_single_routes.png')

    rows=read_csv(out/'max_safe_payload.csv');areas=sorted({r['service_area'] for r in rows})
    values=np.array([[next(float(r['safe_payload_kg']) if r['safe_payload_kg'] else np.nan for r in rows
                          if r['service_area']==s and r['aircraft_type']==m) for m in types] for s in areas])
    fig,ax=plt.subplots(figsize=(6.8,8.4),layout='constrained')
    im=ax.imshow(values,cmap='YlGnBu',vmin=0,vmax=max(m.rated_kg for m in types.values()),aspect='auto')
    ax.set(xticks=range(3),xticklabels=[f'Type {m}' for m in types],yticks=range(len(areas)),yticklabels=areas,
           title='Maximum safe payload | 20% reserve')
    for (r,c),v in np.ndenumerate(values):
        ax.text(c,r,f'{v:.2f}' if np.isfinite(v) else 'Infeasible',ha='center',va='center',color='white' if v>42 else '#14213D')
    fig.colorbar(im,ax=ax,label='Payload (kg)',shrink=.8)
    save(fig,'safe_payload_heatmap.png')

    front=read_csv(out/'pareto_front.csv');x=[int(r['sorties']) for r in front];y=[float(r['energy_kwh']) for r in front]
    fig,ax=plt.subplots(figsize=(8,5),layout='constrained')
    ax.plot(x,y,'--',c='#9AA5B1',lw=1,zorder=1)
    ax.scatter(x,y,s=100,c=['#2A9D8F' if n==min(x) else '#E09F3E' for n in x],zorder=2)
    for r in front:
        n=int(r['sorties']);e=float(r['energy_kwh']);t=float(r['time_min'])
        ax.annotate(f'{n} trips | {e:.6f} kWh\nCumulative time: {t:.3f} min',(n,e),
                    xytext=(12,-40 if n==min(x) else 18),textcoords='offset points',fontsize=10)
    ax.set(xlim=(min(x)-.25,max(x)+.75),xlabel='Round-trip sorties (integer)',ylabel='Total energy (kWh)',
           title='Complete Pareto objective set | 20% reserve\nEvery labelled point includes the third objective: cumulative time')
    ax.xaxis.set_major_locator(MultipleLocator(1));ax.ticklabel_format(axis='y',useOffset=False);ax.grid(alpha=.2)
    ax.margins(y=.3);save(fig,'pareto_front.png')

    grid=read_csv(out/'reserve_payload_grid.csv')
    fig,axes=plt.subplots(3,5,figsize=(16,9),sharex=True,sharey=True,layout='constrained')
    for ax,s in zip(axes.flat,areas):
        for m in types:
            data=[r for r in grid if r['service_area']==s and r['aircraft_type']==m]
            ax.plot([float(r['reserve']) for r in data],
                    [float(r['safe_payload_kg']) if r['safe_payload_kg'] else np.nan for r in data],
                    c=COLORS[m],label=f'Type {m}',lw=1.8)
        ax.axvline(.2,c='#7A869A',ls=':',lw=.8);ax.set_title(s);ax.grid(alpha=.2)
        ax.xaxis.set_major_formatter(PercentFormatter(1,decimals=0))
    axes[0,0].legend(frameon=False);fig.supxlabel('Required return reserve');fig.supylabel('Maximum safe payload (kg)')
    fig.suptitle('Safe payload vs reserve | roots solved at each 1% increment\nBlank curve sections mean even the empty round trip is infeasible',fontsize=14)
    save(fig,'reserve_vs_safe_payload.png')

    segments=read_csv(out/'reserve_segments.csv')
    fig,axes=plt.subplots(1,2,figsize=(13,5),layout='constrained',gridspec_kw={'width_ratios':[1.5,1]})
    for ax,xlimits in zip(axes,[(.05,.4),(.33,.36)]):
        for r in segments:
            l,h=float(r['alpha_left']),float(r['alpha_right'])
            if not r['min_sorties']:
                ax.axvspan(max(l,xlimits[0]),min(h,xlimits[1]),color='#DFE3E8',zorder=0)
                continue
            n=int(r['min_sorties']);ax.plot([l,h],[n,n],color='#1D3557',lw=2)
            if xlimits[0]<=l<=xlimits[1]:ax.scatter([l],[n],s=28,facecolors='white',edgecolors='#1D3557',zorder=4)
            if xlimits[0]<=h<=xlimits[1]:ax.scatter([h],[n],s=28,color='#1D3557',zorder=5)
        ax.set(xlim=xlimits,ylim=(17.5,25.8),xlabel='Required return reserve');ax.grid(alpha=.15)
        ax.xaxis.set_major_formatter(PercentFormatter(1,decimals=1));ax.yaxis.set_major_locator(MultipleLocator(1))
    axes[0].set_ylabel('Minimum round-trip sorties')
    axes[0].set_title('Exact finite-event staircase | 5%–40%');axes[1].set_title('Detail | 33%–36%')
    for ax in axes:ax.text(.98,.08,'Grey: all-box delivery infeasible',transform=ax.transAxes,ha='right',fontsize=9)
    fig.suptitle('At each threshold, the lower trip count remains feasible; it changes strictly to the right',fontsize=12)
    save(fig,'reserve_vs_min_sorties.png')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'results')
    parser.add_argument('--figures',type=Path,default=ROOT/'figures');args=parser.parse_args()
    figures(args.output,args.figures)
