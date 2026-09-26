#!/usr/bin/env python3
"""Create audit-repair evidence and editable tables from hash-locked inputs.
No optimization, rounding of stored schedules, or source rewriting is performed.
Charts use exact single-point physics; the background display never replaces DEM.
"""
from pathlib import Path
import json,csv,math,hashlib
from collections import defaultdict,Counter
import numpy as np
from scipy.optimize import brentq
P=Path(__file__).resolve().parents[1]; A=P/'audit_inputs'; D=P/'figdata/audit_repair'; D.mkdir(parents=True,exist_ok=True)
def read(n):return json.loads((A/n).read_text())
def write(n,x): (D/n).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def csvwrite(n,rows):
 with (D/n).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
for name,v in read('manifest.json').items():
 assert hashlib.sha256((A/name).read_bytes()).hexdigest()==v['sha256'],name
T={d['id']:d for d in read('q2_types.json')};N={d['id']:d for d in read('q2_nodes.json')};B={d['id']:d for d in read('q2_boxes.json')};G={(d['from'],d['to']):d for d in read('q2_legs.json')}
def energy(site,typ,mass):
 t=T[typ];e=0.
 for a,b,q in [('O01',site,mass),(site,'O01',0.)]:
  h=G[a,b]['cruise_z']-N[a]['work_z'];assert h>=-1e-8
  dist=math.hypot(N[a]['x']-N[b]['x'],N[a]['y']-N[b]['y'])
  L=t['empty_range_m']-(t['empty_range_m']-t['full_range_m'])*(q/t['max_payload_kg'])**1.5
  e+=t['battery_kwh']*dist/L+(t['empty_mass_kg']+q)*9.81*h/(t['up_efficiency']*3600000)
 return e

def safe(site,typ,alpha):
 q=T[typ]['max_payload_kg'];cap=(1-alpha)*T[typ]['battery_kwh']
 if energy(site,typ,0)>cap+1e-12:return None
 if energy(site,typ,q)<=cap:return float(q)
 return brentq(lambda m:energy(site,typ,m)-cap,0,q,xtol=1e-11)
critical=0.35267806887191433
levels=sorted(set([i/100 for i in range(41)]+[critical,.2308834976366333,.353]))
sites=sorted({b['site'] for b in B.values()})
rows=[{'service_area':s,'aircraft_type':g,'alpha':a,'safe_payload_kg':safe(s,g,a)} for s in sites for g in 'ABC' for a in levels]
csvwrite('q1_safe_payload_vs_reserve.csv',rows);write('q1_safe_payload_vs_reserve.json',rows)
# Compare to independently saved Q1's 20% output (column names inspected explicitly).
with (A/'q1_payload_reference.csv').open(encoding='utf-8-sig') as f:ref=list(csv.DictReader(f))
errs=[]
for r in ref:
 s=r.get('service_area',r.get('site'));g=r.get('aircraft_type',r.get('type'))
 errs.append(abs(safe(s,g,.2)-float(r['safe_payload_kg'])))
assert len(errs)==45 and max(errs)<1e-7, max(errs)
small=[]
for site in ['S001','S004','S008']:
 for a in [.2,.3,critical]:
  small.append({'service_area':site,'alpha':a,**{g:safe(site,g,a) for g in 'ABC'}})
csvwrite('q1_payload_selected.csv',small)
lines=[r'\begin{table}[htbp]\centering\small',r'\caption{安全余量变化下代表服务区的最大安全载荷/kg}\label{tab:q1_payload_response}',r'\begin{tabular}{lrrrr}\toprule 服务区 & 安全余量/\% & A型 & B型 & C型\\\midrule']
for r in small:
 lines.append(r['service_area']+' & '+f"{100*r['alpha']:.4f}"+' & '+' & '.join('---' if r[g] is None else f"{r[g]:.3f}" for g in 'ABC')+r'\\')
lines+= [r'\bottomrule\end{tabular}',r'\par\smallskip\footnotesize 临界余量计算使用未舍入值；表中35.2678\%仅为显示值。载荷是质量上限，组批还需检查货箱体积。',r'\end{table}']
(P/'tables/q1_payload_response.tex').write_text('\n'.join(lines)+'\n')
# Q3 schedule: every task and cargo event from the same expanded selected plan.
fl=read('q3_flights.json');de=read('q3_deliveries.json');assert len(fl)==23 and len(de)==80
assert len({x['id'] for x in de})==80
schedule=[]
for f in fl:
 ev=[d for d in de if d['flight_id']==f['flight_id']]
 assert {d['id'] for d in ev}==set(f['box_ids'])
 assert f['start_s']<=min(d['delivery_s'] for d in ev)<=max(d['delivery_s'] for d in ev)<=f['return_s']
 schedule.append({'task_id':f['flight_id'],'type':f['type'],'route':'→'.join(x for x in f['route'] if x!='O01'),'aircraft':f['aircraft'],'battery':f['battery'],'start_s':f['start_s'],'last_delivery_s':max(d['delivery_s'] for d in ev),'return_s':f['return_s']})
csvwrite('q3_full_transport_schedule.csv',schedule)
lines=[r'\begingroup\small\setlength{\tabcolsep}{3pt}',r'\begin{longtable}{llp{2.9cm}llrrr}',r'\caption{问题三正式23架次的运输资源与执行时刻（时间单位：min）}\label{tab:q3_full_schedule}\\',r'\toprule 任务 & 型号 & 访问顺序 & 飞机 & 电池 & 开始 & 末箱交付 & 返航\\\midrule',r'\endfirsthead',r'\toprule 任务 & 型号 & 访问顺序 & 飞机 & 电池 & 开始 & 末箱交付 & 返航\\\midrule',r'\endhead']
for r in schedule:
 lines.append(r['task_id'].replace('Q3-T-','T-')+' & '+r['type']+' & '+r['route'].replace('→',r'$\to$')+' & '+r['aircraft']+' & '+r['battery']+' & '+' & '.join(f"{r[k]/60:.3f}" for k in ['start_s','last_delivery_s','return_s'])+r'\\')
lines += [r'\bottomrule\end{longtable}',r'\endgroup']
(P/'tables/q3_full_schedule.tex').write_text('\n'.join(lines)+'\n')
# Group allocations from all-partition audit, with exact per-resource certificates.
q4=read('q4_enumeration.json');rr=q4['resource_order']; groups=[]
for k in ['2','3']:
 p=q4['by_group_count'][k]['minimum_configuration'];sums=[0]*8
 for i,ss in enumerate(p['groups']):
  c=p['resource_certificates'][str(i)];ns=[c[x]['minimum'] for x in rr]
  for a,x in enumerate(rr):assert c[x]['minimum']==c[x]['matching_minimum']==len(c[x]['resource_chains']);sums[a]+=ns[a]
  groups.append({'K':int(k),'group':i+1,'sites':ss,'need':ns,'work_s':p['workload_s'][i]})
 assert sums==p['need_vector']
write('q4_group_allocations.json',groups)
lines=[r'\begin{table}[htbp]\centering\small\setlength{\tabcolsep}{4pt}',r'\caption{两组与三组方案中各执行组的独立资源配置}\label{tab:q4_each_group}',r'\begin{tabular}{llrrrrrrrrr}\toprule',r'分组 & 服务区 & \multicolumn{3}{c}{运输机/架} & \multicolumn{3}{c}{电池/组} & 中继机 & 组件 & 作业/min\\',r' & & A & B & C & A & B & C & /架 & /组 & \\\midrule']
for r in groups:
 name=('除S006外14区' if len(r['sites'])==14 else '其余13区' if len(r['sites'])==13 else r['sites'][0])
 lines.append(f"{r['K']}组-G{r['group']} & {name} & "+' & '.join(map(str,r['need']))+' & '+f"{r['work_s']/60:.3f}"+r'\\')
lines +=[r'\bottomrule\end{tabular}',r'\par\smallskip\footnotesize 两组与三组的G编号分别定义，不是跨方案固定实体；作业时间不包含充电和返航周转，资源配置区间则按各类实际释放规则核算。',r'\end{table}']
(P/'tables/q4_each_group.tex').write_text('\n'.join(lines)+'\n')
# Source-identical transport modes before/after the same-physics relay optimization.
a=read('q3_v5_baseline.json');b=read('q3_v6_selected.json')
write('audit_generation_checks.json',{'source_files_hash_checked':True,'q1_nominal_combinations':45,'q1_nominal_max_abs_error_kg':max(errs),'q1_grid_rows':len(rows),'q3_tasks':23,'q3_unique_boxes':80,'q3_last_return_s':max(f['return_s'] for f in fl),'q4_group_rows':len(groups),'q4_sums_match':True,'q4_resource_chains_matching_checked':True})
print(json.dumps({'q1_grid_rows':len(rows),'q1_maxerr':max(errs),'q3_rows':len(schedule),'q4_rows':len(groups)},indent=2))
