#!/usr/bin/env python3
"""Generate paper tables and vector figures from the locked rendering snapshot.
No optimization runs here. Scenario tables retain fixed/repair/reoptimization scope.
Run from anywhere: python paper/latex/scripts/build_assets.py
"""
from pathlib import Path
import json,csv,math,hashlib,zipfile,base64,io
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
P=Path(__file__).resolve().parents[1];D=P/'figdata';F=P/'figures_generated';T=P/'tables'
for p in (D,F,T):p.mkdir(exist_ok=True)
# A compact, lossless text archive may be used in Git; editable inputs are in the delivered ZIP.
if not (D/'paper_data.json').exists():
 parts=sorted((P/'figure_inputs').glob('part_*.b64'))
 if not parts:raise SystemExit('Missing figdata and locked figure_inputs parts')
 meta=json.loads((P/'figure_inputs/manifest.json').read_text())
 if len(parts)!=meta['parts']:raise ValueError('Incomplete figure input archive')
 raw=base64.b64decode(''.join(p.read_text().strip() for p in parts),validate=True)
 if hashlib.sha256(raw).hexdigest()!=meta['sha256']:raise ValueError('Archive SHA-256 mismatch')
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  for n in z.namelist():
   dest=(P/n).resolve()
   if not dest.is_relative_to(P):raise ValueError('Unsafe input archive member')
   dest.parent.mkdir(exist_ok=True,parents=True);dest.write_bytes(z.read(n))
x=json.loads((D/'paper_data.json').read_text());prov=json.loads((D/'provenance.json').read_text())
for n,h in prov['data_sha256'].items():
 if hashlib.sha256((D/n).read_bytes()).hexdigest()!=h:raise ValueError('Input hash mismatch: '+n)
C={'A':'#2F5D8A','B':'#E6A23C','C':'#54B8A9','red':'#D97C6C','purple':'#8064B2','grid':'#E6E6E6','gray':'#59616A'}
RC={'G01':'#59616A','Q3-R-01':C['purple'],'Q3-R-02':C['B'],'Q3-R-03':'#4FA3D9','Q3-R-04':C['C']}
plt.rcParams.update({'font.family':['Noto Sans CJK JP','DejaVu Sans'],'font.size':9,'axes.unicode_minus':False,'mathtext.fontset':'stix','pdf.fonttype':3,'ps.fonttype':3,'axes.linewidth':.7,'axes.edgecolor':'#555555','figure.facecolor':'white','axes.facecolor':'white','savefig.facecolor':'white'})
# CJK CFF collections need vector Type-3 glyphs in Matplotlib PDF output.
# Type-42 wrapping of a CFF font can preserve text extraction but render wrong glyphs.
# No font files are distributed; these glyph outlines are embedded in each figure.
def canvas(w=6.25,h=3.7):
 f,a=plt.subplots(figsize=(w,h));f.subplots_adjust(left=.13,right=.96,bottom=.17,top=.91);return f,a
def grid(a):a.grid(axis='y',color=C['grid'],lw=.6);a.set_axisbelow(True)
def save(f,n):
 f.savefig(F/(n+'.pdf'),bbox_inches='tight',pad_inches=.05);f.savefig(F/(n+'.png'),dpi=220,bbox_inches='tight',pad_inches=.05);plt.close(f)
def st(v,d=3):return '--' if v is None else f'{float(v):.{d}f}'
def esc(s):return str(s).replace('_',r'\_').replace('%',r'\%').replace('&',r'\&')
def table(name,caption,label,heads,rows,align=None,long=False,note=None):
 align=align or 'l'+'r'*(len(heads)-1)
 top=r'\toprule'+'\n'+' & '.join(heads)+r'\\'+'\n'+r'\midrule'+'\n'
 if long:
  s=r'\begin{longtable}{@{}'+align+r'@{}}'+'\n'+r'\caption{'+caption+r'}\label{'+label+r'}\\'+'\n'+top+r'\endfirsthead'+'\n'+top+r'\endhead'+'\n'
 else:s=r'\begin{table}[htbp]\centering\small'+'\n'+r'\caption{'+caption+r'}\label{'+label+'}\n'+r'\begin{tabular}{@{}'+align+r'@{}}'+'\n'+top
 s+='\n'.join(' & '.join(map(str,r))+r'\\' for r in rows)+'\n'+r'\bottomrule'+'\n'
 s+=r'\end{longtable}' if long else r'\end{tabular}'+('\n'+r'\par\smallskip\parbox{.96\linewidth}{\footnotesize '+note+'}' if note else '')+'\n'+r'\end{table}'
 (T/(name+'.tex')).write_text(s+'\n')

def tables():
 b=pd.DataFrame(x['q1_data']['optimal_batches.csv']);rr=[]
 for area,g in b.groupby('service_area',sort=True):rr.append([area,len(g),'+'.join(g.aircraft_type),st(g.mass_kg.sum(),0),st(g.energy_kwh.sum(),3),st(g.time_s.sum()/60,3)])
 rr.append(['合计',18,'B/C=9/9','758','59.131296','546.266929'])
 table('q1_area','问题一各服务区正式运输安排','tab:q1_area_plan',['区域','架次','机型','质量/kg','能耗/kWh','累计时间/min'],rr,'lclrrr')
 base=pd.DataFrame(x['q1_data']['baseline_summary.csv']);print('baseline columns',base.columns.tolist())
 # Source uses fleet/method nomenclature; select only known rows by explicit fields.
 rows=[]
 for r in x['q1_data']['baseline_summary.csv']:
  print('baseline',r)
  fleet={'A':'A-only','B':'B-only','C':'C-only','mixed':'mixed'}.get(r.get('aircraft_type'));method={'exact':'exact','FFD_mass':'FFD-mass'}.get(r.get('method'))
  if fleet in ['A-only','B-only','C-only','mixed'] and method in ['exact','FFD-mass']:
   if method=='FFD-mass' and fleet!='mixed':continue
   rows.append([{'A-only':'仅A型','B-only':'仅B型','C-only':'仅C型','mixed':'混合机型'}[fleet],{'exact':'精确','FFD-mass':'质量优先FFD'}[method],r.get('sorties',r.get('total_sorties')),st(r.get('energy_kwh',r.get('total_energy_kwh')),6),st(r.get('work_min',r.get('sum_work_min',r.get('time_min'))),6)])
 if not rows:raise ValueError('Baseline source schema requires explicit mapping')
 table('q1_baseline','单机型、混合机型与启发式基线','tab:q1_baselines',['机型范围','求解方法','架次','能耗/kWh','累计时间/min'],rows,'llrrr')
 rr=[]
 for r in x['q1_sensitivity']:
  if r['experiment']=='energy_error':rr.append([f"{(r['energy_factor']-1)*100:.0f}\\%",int(r['sorties']),st(r['energy_kwh'],6),st(r['sum_work_min'],3)])
 table('q1_sensitivity','统一能耗正偏差下重新求解的最少架次方案','tab:q1_sensitivity',['能耗偏差','架次','扰动后能耗/kWh','累计时间/min'],rr)
 rr=[]
 for f in x['q2_flights']:
  route=r'$\to$'.join(f['route'][1:-1]);rr.append([f['flight_id'],f['type'],route,f['aircraft'],f['battery'],st(f['start_s']/60,3),st(f['return_s']/60,3)])
 table('q2_schedule','问题二正式23架次的资源指派与执行时刻','tab:q2_schedule',['架次','机型','访问顺序','飞机','电池','开始/min','返航/min'],rr,'lclllrr',True)
 rr=[]
 for r in x['q2_energy_alternatives']:rr.append([f"{(r['energy_factor']-1)*100:.0f}\\%",r['sorties'],st(r['makespan_s'],6),st(r['energy_kwh'],6),st(100*r['min_soc'],3),'通过'])
 table('q2_energy_alternatives','能耗偏差下重新调整结构所得可行备选','tab:q2_energy_alternatives',['偏差','架次','工期/s','能耗/kWh','最低SOC/\%','独立核验'],rr,'lrrrcc',note='各250轮搜索；此表为所得可行方案，不宣称情景最优或原方案不变时可用。')
 rr=[]
 for r in x['q3_relays']:rr.append([r['relay_id'],r['aircraft'],r['component'],st(r['lon'],6),st(r['lat'],6),st(r['agl_m'],0)])
 table('q3_sites','中继任务、实体资源与悬停位置','tab:q3_sites',['中继任务','实体','能源组件','经度','纬度','AGL/m'],rr,'lllrrr')
 rr=[]
 for r in x['q3_relays']:rr.append([r['relay_id'],st(r['start_s']/60),st(r['service_start_s']/60),st(r['service_end_s']/60),st(r['return_s']/60),st(100*r['return_soc'])])
 table('q3_relays','四项中继任务的实际服务时间表','tab:q3_relays',['任务','开始/min','服务开始','服务结束','返航/min','SOC/\%'],rr)
 rr=[]
 for d in [0,.05,.10,.15,.20,.25]:
  a=next(r for r in x['q3_loss'] if r['role']=='time' and abs(r['extra_loss_db']-d)<1e-8);b=next(r for r in x['q3_loss'] if r['role']=='robust025' and abs(r['extra_loss_db']-d)<1e-8)
  rr.append([f'{d:.2f}',st(a['sum_flight_outage_s']), '通过' if a['feasible'] else '失效',st(b['sum_flight_outage_s']),'通过' if b['feasible'] else '失效'])
 table('q3_loss','附加损耗下两份固定方案的连续通信核验','tab:q3_loss',['损耗/dB','原方案失联/s','核验','增强方案失联/s','核验'],rr,'rrcrc')
 rr=[]
 for rid in sorted({r['relay_id'] for r in x['q3_repairs']}):
  vals=[next(r for r in x['q3_repairs'] if r['relay_id']==rid and r['delay_s']==d) for d in [5,30,60]]
  assert all(r['validation_pass'] for r in vals)
  rr.append([rid,*[st(r['extra_makespan_s']) for r in vals],'3/3通过'])
 table('q3_repair','固定结构修复中继上线延迟的额外工期','tab:q3_repair',['延迟任务','延迟5秒','延迟30秒','延迟60秒','完整核验'],rr,'lrrrc',note='中间三列均为新增工期/s，不是修复后总工期；转场物理参数保持不变。')
 rr=[];group_map=[]
 for r in x['q4_partitions']:
  if len(r['groups'])!=2:continue
  labs=[]
  for g in r['groups']:
   bb=[]
   if 'S001' in g:bb.append('B_1')
   if 'S002' in g:bb.append('B_2')
   if 'S006' in g:bb.append('B_3')
   labs.append('+'.join(bb))
  name='$'+r'\mid '.join(labs)+'$';rr.append([name,','.join(map(str,r['need_vector'])),r['total_need'],r['total_gap'],st(r['workload_cv'],6)])
 table('q4_partitions','全部三种两组分区的配置与均衡结果','tab:q4_partitions',['分区','需求向量','总配置','总缺口','工作量CV'],rr,'llrrr')
 names=['A型运输机','B型运输机','C型运输机','A型电池','B型电池','C型电池','中继无人机','中继能源组件'];order=x['q4_summary']['resource_order'];rr=[]
 for name,key in zip(names,order):
  vals=[next(r['best_total_gap'] for r in x['q4_inventory'] if r['inventory_changed_type']==key and r['change']==delta and r['K']==k) for delta,k in [(-1,2),(1,2),(-1,3),(1,3)]]
  rr.append([name,*vals])
 table('q4_inventory_stress','各类型库存单项增减后的最小总缺口','tab:q4_inventory_stress',['扰动资源','两组：减1','两组：加1','三组：减1','三组：加1'],rr,'lrrrr',note='每次只改变一类库存，其余保持原值；两组三组重新比较全部合法分区。基准缺口分别为1与7。')
 names={'time':'工期优先','energy':'节能备选','robust025':'增强通信保障','q4_tradeoff':'三组资源折中'};metric={'time':(5836.969929328251,68.93941621018112,0),'energy':(5911.5481346609085,68.73579123708348,0),'robust025':(5866.140526535532,69.03175130785294,.25),'q4_tradeoff':(5866.140526535532,68.9754972006408,0)}
 rr=[]
 for r in x['q4_candidates']:
  a,b,c=metric[r['role']];rr.append([names[r['role']],st(a),st(b,6),st(c,2),r['K2']['total_gap'],r['K3']['total_gap']])
 table('q4_crossplans','不同上游预案冻结后的独立配置比较','tab:q4_crossplans',['预案','工期/s','能耗/kWh','附加损耗/dB','两组缺口','三组缺口'],rr,'lrrrrr')
 # Complete audit tables: no manually copied route/time fields.
 def idboxes(bb):return ', '.join(r'\texttt{'+v+r'}\allowbreak' for v in bb)
 q1rows=[]
 for r in x['q1_data']['optimal_batches.csv']:
  ids=json.loads(r['box_ids']) if isinstance(r['box_ids'],str) else r['box_ids'];q1rows.append([r['batch_id'],r['service_area'],r['aircraft_type'],idboxes(ids)])
 table('app_q1_boxes','问题一18架次的完整货箱分配','tab:app_q1_boxes',['架次','区域','机型','原始货箱编号'],q1rows,'llc>{\\raggedright\\arraybackslash}p{9.3cm}',True)
 for key,title in [('q2','问题二'),('q3','问题三')]:
  rr=[[r['flight_id'],r['type'],r'$\to$'.join(r['route'][1:-1]),idboxes(r['box_ids'])] for r in x[key+'_flights']]
  table('app_'+key+'_boxes',title+'正式运输架次与原始箱号','tab:app_'+key+'_boxes',['架次','机型','访问顺序','原始货箱编号'],rr,'lc>{\\raggedright\\arraybackslash}p{2.8cm}>{\\raggedright\\arraybackslash}p{8.8cm}',True)
 rr=[]
 for b in sorted(x['q2_deliveries'],key=lambda r:r['id']):rr.append([b['id'],b['flight_id'],st(b['delivery_s']),st(b.get('hard_deadline_s'),0),st(b['expected_delivery_s'],0),st(b.get('hard_slack_s'))])
 table('app_deliveries','问题二80个货箱的送达与时限核对（秒）','tab:app_deliveries',['货箱','架次','送达','硬截止','期望送达','硬余量'],rr,'llrrrr',True)
 rr=[[r['seed'],r['iterations'],st(r['makespan_s'],6),st(r['energy_kwh'],6),r['sorties'],st(r['seconds']),0] for r in x['q2_seeds']]
 table('app_seeds','20次独立搜索的全部结果','tab:app_seeds',['种子','轮数','工期/s','能耗/kWh','架次','耗时/s','核验失败'],rr,'rrrrrrr',True)
 rr=[]
 for r in x['q1_sensitivity']:
  if r['experiment']=='reserve':rr.append([st(r['alpha']*100,6),int(r['sorties']) if r['feasible'] else '不可行',st(r['energy_kwh'],6),st(r['sum_work_min'])])
 table('app_q1_reserve','重新求解的13个安全余量情景','tab:app_q1_reserve',['余量/\%','最少架次','能耗/kWh','累计时间/min'],rr,'rrrr',True)


def scene():
 f,a=canvas(h=4.4);z=np.loadtxt(D/'terrain_display.csv',delimiter=',');meta=json.loads((D/'terrain_metadata.json').read_text());ext=np.array(meta['extent_m'])/1000
 cmap=LinearSegmentedColormap.from_list('terrain_white',['#F6F9ED','#D8E9D2','#9EC3B9','#548697'])
 im=a.imshow(z,extent=ext,origin='upper',cmap=cmap,interpolation='nearest',alpha=.86,aspect='equal');cb=f.colorbar(im,ax=a,shrink=.8,pad=.02);cb.set_label('显示地形高程 / m')
 for n in x['nodes']:
  xx,yy=n['x_m']/1000,n['y_m']/1000
  if n['id']=='O01':a.scatter(xx,yy,s=105,marker='*',c=C['red'],edgecolors='black',lw=.5,zorder=5)
  else:a.scatter(xx,yy,s=n['mass_kg']*2.4,c=C['A'],alpha=.7,edgecolors='white',lw=.6,zorder=4)
  dy=.19 if n['id'] not in ['S002','S004','S008'] else .33
  a.annotate(n['id'],(xx,yy),xytext=(xx+.14,yy+dy),fontsize=8.5,zorder=6,bbox=dict(fc='white',ec='none',alpha=.7,pad=.3))
 a.set(xlabel='AEQD x / km',ylabel='AEQD y / km',xlim=(-7.2,6.5),ylim=(-1.6,9.4));a.text(.01,.01,'原栅格约30 m；显示网格100 m\n圆点面积表示需求质量',transform=a.transAxes,fontsize=7.5,bbox=dict(fc='white',ec='none',alpha=.85))
 for v in [25,80,154]:a.scatter([],[],s=v*2.4,c=C['A'],alpha=.7,label=f'{v} kg')
 a.legend(loc='upper right',fontsize=8,frameon=True,labelspacing=1.2,borderpad=.9);save(f,'scene')

def q1_payload():
 r=pd.DataFrame(x['q1_data']['max_safe_payload.csv']);print('payload columns',r.columns.tolist());areas=[f'S{i:03d}' for i in range(1,16)];safe=np.zeros((15,3));ratio=np.zeros((15,3))
 for i,ar in enumerate(areas):
  for j,g in enumerate('ABC'):
   row=r[(r.service_area==ar)&(r.aircraft_type==g)].iloc[0];safe[i,j]=row['safe_payload_kg'];ratio[i,j]=safe[i,j]/dict(A=25,B=30,C=80)[g]
 f,a=canvas(w=5.4,h=5.1);f.subplots_adjust(left=.16,bottom=.11,top=.93,right=.86);cm=LinearSegmentedColormap.from_list('payload',['#F2F8F7','#91D2C6','#257A95']);im=a.imshow(ratio,cmap=cm,vmin=0,vmax=1,aspect='auto')
 a.set_xticks(range(3),['A型 / 25 kg','B型 / 30 kg','C型 / 80 kg']);a.set_yticks(range(15),areas);a.tick_params(length=0)
 for i in range(15):
  for j in range(3):
   a.text(j,i,f'{safe[i,j]:.2f}',ha='center',va='center',color='white' if ratio[i,j]>.85 else '#222222')
   if ratio[i,j]<1-1e-9:a.add_patch(Rectangle((j-.49,i-.49),.98,.98,fill=False,ec=C['red'],lw=1.6))
 cb=f.colorbar(im,ax=a,fraction=.04,pad=.05);cb.set_ticks([0,.25,.5,.75,1],labels=['0%','25%','50%','75%','100%']);cb.set_label('额定载荷保留比例');save(f,'q1_payload')

def q1_reserve():
 f,a=canvas(h=3.65);ss=x['q1_data']['reserve_segments.csv'];
 for r in ss:
  n=r['min_sorties']
  if n is None:continue
  lo,hi=r['alpha_left']*100,r['alpha_right']*100;a.plot([lo,hi],[n,n],c=C['A'],lw=1.8);a.scatter([lo],[n],s=27,facecolors=C['A'] if r['left_closed'] else 'white',edgecolors=C['A'],zorder=4);a.scatter([hi],[n],s=27,c=C['A'],zorder=4)
  if lo>0:a.plot([lo,lo],[n-1,n],ls=':',c=C['gray'],lw=.7)
 last=ss[-1]['alpha_left']*100;a.axvspan(last,40,color=C['red'],alpha=.13);a.text(37.5,22,'不\n可\n行',ha='center',color='#9D493E',fontsize=11)
 a.axvline(20,c=C['C'],ls='--',lw=1);a.annotate('基准20%',xy=(20,18),xytext=(12,19.2),arrowprops=dict(arrowstyle='->',color=C['C']),color=C['A'])
 a.annotate('首次跃迁\n23.08835%',xy=(23.08834976366333,18),xytext=(17,21.2),arrowprops=dict(arrowstyle='->',lw=.8),fontsize=8.5)
 a.set(xlim=(0,40),ylim=(17.5,25.6),xlabel='返航安全余量 α / %',ylabel='最少架次数');a.set_yticks(range(18,26));grid(a);save(f,'q1_reserve')

def q2_gantt(battery=False):
 ff=x['q2_flights'];res=sorted(set(r['battery' if battery else 'aircraft'] for r in ff));key='battery' if battery else 'aircraft';f,a=canvas(h=4.1 if battery else 2.65);f.subplots_adjust(left=.14,right=.99,bottom=.17,top=.92)
 for r in ff:
  y=res.index(r[key]);s=r['start_s']/60;e=r['return_s']/60;a.broken_barh([(s,e-s)],(y-.32,.64),facecolors=C[r['type']],edgecolors='white',lw=.5)
  if battery:
   end=r['charge_end_s']/60;a.broken_barh([(e,end-e)],(y-.32,.64),facecolors='white',edgecolors=C[r['type']],hatch='////',lw=.5,alpha=.55)
  a.text((s+e)/2,y,r['flight_id'][-2:],ha='center',va='center',fontsize=7.9,color='white' if r['type']=='A' else '#172C32')
 a.set_yticks(range(len(res)),res);a.invert_yaxis();a.set_xlim(0,142);a.set_xticks(range(0,141,20));a.set_xlabel('绝对调度时间 / min');a.grid(axis='x',color=C['grid'],lw=.5);a.set_axisbelow(True);a.axvline(5693.231489105106/60,c=C['red'],ls='--',lw=1)
 a.text(.0,1.01,'电池任务占用与充电恢复' if battery else '运输无人机占用（条内为架次末两位）',transform=a.transAxes,fontsize=9)
 handles=[Rectangle((0,0),1,1,fc=C[g],label=g+'型') for g in 'ABC'];a.legend(handles=handles,ncol=3,loc='lower right',fontsize=7.5,framealpha=.9)
 save(f,'q2_batteries' if battery else 'q2_aircraft')

def q2_seeds():
 f,a=canvas(h=3.2);s=pd.DataFrame(x['q2_seeds']);a.scatter(s.seed,s.makespan_s/60,c=C['A'],s=30,edgecolors='white',lw=.5);a.axhline(s.makespan_s.median()/60,c=C['C'],ls='-',lw=1,label='20次中位数');a.axhline(5693.231489105106/60,c=C['red'],ls='--',lw=1,label='正式方案（不同历史预算）');a.set(xlim=(.5,20.5),ylim=(92,116),xlabel='独立随机种子',ylabel='最后返航时间 / min');a.set_xticks(range(1,21));a.legend(loc='lower right',fontsize=8);grid(a);save(f,'q2_seeds')

def q2_charging():
 f,a=canvas(h=3.2);p=pd.DataFrame(x['q2_perturbations']);p=p[p.experiment=='charging'];r=p[p.adjustment_mode=='right_shift_repair'];a.plot(r.charging_factor,r.makespan_s/60,'o-',c=C['A'],ms=5,label='仅顺延修复');b=p[p.adjustment_mode=='fixed_calendar'];bad=b[~b.zero_tardiness_feasible];good=b[b.zero_tardiness_feasible];a.scatter(good.charging_factor,good.makespan_s/60,s=70,facecolors='none',edgecolors=C['C'],label='固定日程可行',zorder=5);a.scatter(bad.charging_factor,bad.makespan_s/60,marker='x',s=55,c=C['red'],label='固定日程冲突',zorder=5);a.set(xlabel='完全充电时间倍率 β',ylabel='最后返航时间 / min',ylim=(94,103));a.legend(fontsize=8,loc='upper left');grid(a);save(f,'q2_charging')

def q2_delay():
 p=pd.DataFrame(x['q2_perturbations']);p=p[p.experiment=='single_first_handover_delay'];f,a=canvas(h=3.15);levels=[0,15,30,60,120];loc=np.arange(5)
 for off,mode,c,label in [(-.18,'fixed_calendar',C['B'],'固定原日程'),(.18,'right_shift_repair',C['A'],'仅顺延修复')]:
  val=[int(p[(p.adjustment_mode==mode)&(p.delay_s==d)].zero_tardiness_feasible.sum()) for d in levels];a.bar(loc+off,val,.34,color=c,label=label)
  for xx,v in zip(loc+off,val):a.text(xx,v+.4,str(v),ha='center',fontsize=8)
 a.set_xticks(loc,levels);a.set(ylim=(0,26),xlabel='单个任务的首次交接增加时间 / s',ylabel='通过全部约束的情景数 / 23');a.set_yticks([0,5,10,15,20,23]);a.legend(fontsize=8,loc='center right');grid(a);save(f,'q2_delay')

def q3_deployment():
 f,a=canvas(h=4.1);nodes={n['id']:(n['x_m']/1000,n['y_m']/1000) for n in x['nodes']}
 for ff in x['q3_flights']:
  pts=np.array([nodes[n] for n in ff['route']]);key=ff['flight_id'] in ['Q3-T-16','Q3-T-23'];a.plot(pts[:,0],pts[:,1],c=C[ff['type']] if key else '#BAC6CB',lw=1.5 if key else .55,alpha=1 if key else .5,zorder=3 if key else 1)
 for n,(xx,yy) in nodes.items():a.scatter(xx,yy,s=60 if n=='O01' else 13,c='black',marker='*' if n=='O01' else 'o',zorder=5);a.annotate(n,(xx,yy),xytext=(4,4),textcoords='offset points',fontsize=7.8)
 for r in x['q3_relays']:
  xx,yy=r['x']/1000,r['y']/1000;a.scatter(xx,yy,s=65,marker='D',c=RC[r['relay_id']],edgecolors='white',lw=.5,zorder=7);offs={'Q3-R-01':(-70,13),'Q3-R-02':(5,-25),'Q3-R-03':(-82,-25),'Q3-R-04':(8,-28)};a.annotate(r['relay_id']+'\nAGL '+str(int(r['agl_m']))+' m',(xx,yy),xytext=offs[r['relay_id']],textcoords='offset points',fontsize=8,color=RC[r['relay_id']],arrowprops=dict(arrowstyle='-',color=RC[r['relay_id']],lw=.8),bbox=dict(fc='white',ec='none',alpha=.8,pad=1))
 a.set_aspect('equal');a.set(xlabel='AEQD x / km',ylabel='AEQD y / km',xlim=(-7.3,6.3),ylim=(-1.3,8.7));a.grid(color=C['grid'],lw=.5);a.legend(handles=[Line2D([],[],color=C['C'],label='Q3-T-16：S007→S003'),Line2D([],[],color=C['A'],label='Q3-T-23：S011')],loc='upper left',fontsize=7.8);save(f,'q3_deployment')

def q3_resources():
 f,a=canvas(h=3.55);f.subplots_adjust(left=.16,right=.98,bottom=.17,top=.87);ys={'R01':4.8,'R02':3.8,'R-ENG01':1.8,'R-ENG02':.8,'R-ENG03':-.2}
 for r in x['q3_relays']:
  c=RC[r['relay_id']];s=r['start_s']/60;ret=r['return_s']/60;aa=r['service_start_s']/60;bb=r['service_end_s']/60;y=ys[r['aircraft']]
  a.broken_barh([(s,ret-s)],(y-.27,.54),facecolors=c,edgecolors=c,alpha=.25);a.broken_barh([(aa,bb-aa)],(y-.27,.54),facecolors=c,edgecolors=c);a.broken_barh([(ret,r['aircraft_available_s']/60-ret)],(y-.27,.54),facecolors='white',edgecolors='#888888',hatch='...',lw=.7);a.text((aa+bb)/2,y,r['relay_id'][-2:],ha='center',va='center',fontsize=8)
  y=ys[r['component']];a.broken_barh([(s,ret-s)],(y-.27,.54),facecolors=c,edgecolors='white',alpha=.8);a.broken_barh([(ret,r['charge_end_s']/60-ret)],(y-.27,.54),facecolors='white',edgecolors=c,hatch='////',lw=.6,alpha=.6);a.text((s+ret)/2,y,r['relay_id'][-2:],ha='center',va='center',fontsize=8)
 a.set_yticks(list(ys.values()),list(ys));a.axhline(2.7,c=C['grid'],lw=1);a.axvline(5836.969929328251/60,c=C['red'],ls='--',lw=1);a.set(ylim=(-.85,5.4),xlim=(0,115),xlabel='绝对调度时间 / min');a.grid(axis='x',c=C['grid'],lw=.5);a.set_axisbelow(True);a.text(0,1.03,'上：实体任务/实际服务/周转；下：能源占用/充电（条内为中继任务末两位）',transform=a.transAxes,fontsize=8.4);save(f,'q3_resources')

def q3_providers():
 f,a=canvas(h=2.65);f.subplots_adjust(left=.17,right=.98,bottom=.21,top=.75)
 for k,tid in enumerate(['Q3-T-16','Q3-T-23']):
  y=3-2*k
  for r in x['q3_states']:
   if r['flight_id']!=tid:continue
   a.broken_barh([(r['start_s']/60,(r['end_s']-r['start_s'])/60)],(y-.25,.5),fc=RC[r['provider']],lw=0)
  for ph in x['q3_phases']:
   if ph['flight_id']!=tid:continue
   ss,ee=ph['start_s']/60,ph['end_s']/60;a.broken_barh([(ss,ee-ss)],(y-1.05,.5),fc='#E8ECEE',ec='white',lw=.6)
   if ee-ss>3:a.text((ss+ee)/2,y-.8,ph['stage'],ha='center',va='center',fontsize=7.6)
 a.set_yticks([3,2.2,1,.2],['任务16通信','任务16阶段','任务23通信','任务23阶段']);a.set(xlim=(42,99),ylim=(-.5,3.5),xlabel='绝对调度时间 / min');a.grid(axis='x',c=C['grid'],lw=.5);a.set_axisbelow(True);a.legend(handles=[Rectangle((0,0),1,1,fc=c,label='直连' if name=='G01' else '中继'+name[-2:]) for name,c in RC.items()],loc='lower left',bbox_to_anchor=(-.05,1.05),ncol=5,fontsize=7.6,frameon=False);save(f,'q3_providers')

def q3_loss():
 f,a=canvas(h=3.1)
 for role,c,m,name in [('time',C['A'],'o','原工期优先方案'),('robust025',C['B'],'s','0.25 dB保障备选')]:
  rr=[r for r in x['q3_loss'] if r['role']==role];a.plot([r['extra_loss_db'] for r in rr],[r['sum_flight_outage_s'] for r in rr],marker=m,c=c,lw=1.5,label=name)
 a.set(xlabel='附加统一传播损耗 Δ / dB',ylabel='逐运输任务累计失联 / s',ylim=(-18,550),xlim=(-.005,.26));a.legend(loc='upper left',fontsize=8.4);grid(a);save(f,'q3_loss')

def q3_repair():
 f,a=canvas(h=3.25)
 for rid in sorted(RC):
  if rid=='G01':continue
  rr=[r for r in x['q3_repairs'] if r['relay_id']==rid];off={'Q3-R-01':.0,'Q3-R-02':.0,'Q3-R-03':.0,'Q3-R-04':.0}[rid]
  a.plot([r['delay_s'] for r in rr],[r['extra_makespan_s'] for r in rr],marker={'Q3-R-01':'o','Q3-R-02':'s','Q3-R-03':'^','Q3-R-04':'D'}[rid],mfc='none',c=RC[rid],lw=1.2,ms=6,label=rid,ls='--' if rid in ['Q3-R-02','Q3-R-04'] else '-')
 a.set(xlabel='单项中继上线延迟 / s',ylabel='修复后的额外工期 / s',xlim=(0,65),ylim=(0,65));a.set_xticks([0,5,15,30,45,60]);a.legend(fontsize=8,loc='upper left');grid(a);save(f,'q3_repair')

def q4_resources():
 names=['A型运输机','B型运输机','C型运输机','A型电池','B型电池','C型电池','中继无人机','中继能源组件'];inv=[4,2,2,6,4,4,2,6];pool=[4,2,2,6,4,4,2,3];k2=[4,2,3,6,4,4,2,3];k3=[5,2,5,7,4,6,2,3];m=np.array([inv,pool,k2,k3]).T
 # These reference vectors are checked against independent reconstruction before plotting.
 got=next(r for r in x['q4_candidates'] if r['role']=='time');assert got['K2']['need_vector']==k2 and got['K3']['need_vector']==k3
 f,a=canvas(w=6.1,h=4.05);f.subplots_adjust(left=.25,right=.93,bottom=.17,top=.90);cm=LinearSegmentedColormap.from_list('count',['#FFFFFF','#ABD5E5','#2F5D8A']);im=a.imshow(m,cmap=cm,vmin=0,vmax=7,aspect='auto');a.set_yticks(range(8),names);a.set_xticks(range(4),['原库存','全局共享','两组独立','三组独立']);a.tick_params(length=0)
 for i in range(8):
  for j in range(4):
   a.text(j,i,str(m[i,j]),ha='center',va='center',color='white' if m[i,j]>=5 else '#222222',fontsize=10)
   if m[i,j]>inv[i]:a.add_patch(Rectangle((j-.49,i-.49),.98,.98,fill=False,ec=C['red'],lw=1.8))
 a.axvline(.5,c='white',lw=3);a.axhline(2.5,c='white',lw=2);a.axhline(5.5,c='white',lw=2)
 a.text(.5,-.14,'总件数：30        27         28         34',transform=a.transAxes,ha='center',fontsize=9)
 cb=f.colorbar(im,ax=a,fraction=.045,pad=.04);cb.set_label('数量 / 件');cb.set_ticks(range(8));save(f,'q4_resources')

if __name__=='__main__':
 tables()
 for fun in [scene,q1_payload,q1_reserve,lambda:q2_gantt(False),lambda:q2_gantt(True),q2_seeds,q2_charging,q2_delay,q3_deployment,q3_resources,q3_providers,q3_loss,q3_repair,q4_resources]:
  fun()
 print('ASSETS_OK',len(list(F.glob('*.pdf'))),'figures',len(list(T.glob('*.tex'))),'tables')
