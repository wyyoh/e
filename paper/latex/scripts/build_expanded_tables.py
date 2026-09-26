#!/usr/bin/env python3
"""Rebuild descriptive tables from frozen saved results; no solver/plot/PDF run."""
from __future__ import annotations
import csv, hashlib, json, math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'revision_tables'

def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))

def close(a, b, tol=1e-6):
    if not math.isclose(float(a), float(b), rel_tol=0, abs_tol=tol):
        raise AssertionError((a,b,tol))

def latex_table(name, caption, headers, rows, spec=None):
    if spec is None: spec = 'l'+'r'*(len(headers)-1)
    lines = [r'\begin{table}[htbp]\centering\small',
             r'\caption{'+caption+r'}\label{tab:rev_'+name+'}',
             r'\begin{tabular}{'+spec+r'}\toprule', ' & '.join(headers)+r'\\\midrule']
    lines += [' & '.join(map(str,row))+r'\\' for row in rows]
    lines += [r'\bottomrule\end{tabular}',r'\end{table}']
    (OUT/(name+'.tex')).write_text('\n'.join(lines)+'\n',encoding='utf-8')

def csv_table(name, headers, rows):
    with (OUT/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(headers);w.writerows(rows)

def main():
    OUT.mkdir(exist_ok=True)
    d=load('figdata/paper_data.json'); types=load('audit_inputs/q2_types.json')
    type_map={r.get('name',r.get('type',r.get('id'))):r for r in types}
    boxes=d['q2_deliveries']; assert len({b['id'] for b in boxes})==80
    close(sum(b['mass_kg'] for b in boxes),758);close(sum(b['volume_m3'] for b in boxes),2.011)
    analysis={'scope':'Descriptive recomputation of saved solutions, not optimizer or geometry reruns', 'input_files':{}}
    for rel in ['figdata/paper_data.json','revision_inputs/all_communication_phases.json','revision_inputs/communication_states.json','revision_inputs/legs.json']:
        analysis['input_files'][rel]=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
    cargo=[]
    for kind in ['医疗物资','应急食品','饮用水','生活卫生用品']:
        bs=[b for b in boxes if b['kind']==kind]
        assert bs,kind
        cargo.append([kind,len(bs),sum(b['mass_kg'] for b in bs),sum(b['volume_m3'] for b in bs),100*sum(b['mass_kg'] for b in bs)/758])
    csv_table('cargo',['物资类型','箱数','质量kg','体积m3','质量占比%'],cargo)
    latex_table('cargo','逐箱需求的类型结构与容量规模',['物资类型','箱数','质量/kg','体积/m$^3$','质量占比/\\%'],[[r[0],r[1],f'{r[2]:.0f}',f'{r[3]:.3f}',f'{r[4]:.2f}'] for r in cargo])
    analysis['cargo']=cargo

    q1=d['q1_data']['optimal_batches.csv']; a=[]
    for m in 'ABC':
        rr=[r for r in q1 if r['aircraft_type']==m]
        a.append([m,len(rr),sum(r['mass_kg'] for r in rr),sum(r['energy_kwh'] for r in rr),sum(r['time_s'] for r in rr)/60])
    close(sum(r[3] for r in a),59.13129602205317);close(sum(r[4] for r in a),546.2669291485934)
    latex_table('q1_types','18架次正式组批方案的机型分工',['机型','架次','质量/kg','能耗/kWh','累计作业/min'],[[r[0],r[1],f'{r[2]:.0f}',f'{r[3]:.6f}',f'{r[4]:.3f}'] for r in a]);csv_table('q1_types',['机型','架次','质量kg','能耗kWh','作业min'],a);analysis['q1_types']=a

    f=d['q2_flights'];T=max(r['return_s'] for r in f);close(T,5693.231489105106)
    types_rows=[]
    for m in 'ABC':
        rr=[r for r in f if r['type']==m];n=len({r['aircraft'] for r in rr});work=sum(r['work_s'] for r in rr)
        types_rows.append([m,len(rr),n,sum(r['payload_kg'] for r in rr),sum(r['energy_kwh'] for r in rr),work,work/n])
    latex_table('q2_types','正式运输日程的分机型任务与负载',['机型','架次','实体数','质量/kg','能耗/kWh','累计作业/s','平均负载/s'],[[*r[:3],f'{r[3]:.0f}',f'{r[4]:.6f}',f'{r[5]:.3f}',f'{r[6]:.3f}'] for r in types_rows]);csv_table('q2_types',['机型','架次','实体数','质量kg','能耗kWh','总时长s','平均负载s'],types_rows);analysis['q2_types']=types_rows
    util=[]
    for u in sorted({r['aircraft'] for r in f}):
        rr=[r for r in f if r['aircraft']==u];work=sum(r['work_s'] for r in rr)
        util.append([u,rr[0]['type'],len(rr),work/60,(T-work)/60,100*work/T])
    latex_table('q2_util','共同执行时间窗口内的运输机作业占用',['实体','机型','架次','作业/min','非占用/min','占用率/\\%'],[[*r[:3],f'{r[3]:.3f}',f'{r[4]:.3f}',f'{r[5]:.2f}'] for r in util],spec='llrrrr');csv_table('q2_util',['飞机','机型','架次','作业min','非占用min','占用率%'],util)
    analysis['q2_fleet_util_pct']=100*sum(r['work_s'] for r in f)/(8*T)
    ms=[]
    for t in [15,30,45,60,75,90]:
        bs=[b for b in boxes if b['delivery_s']<=t*60]
        ms.append([t,len(bs),sum(b['mass_kg'] for b in bs),sum(b['volume_m3'] for b in bs),100*len(bs)/80])
    latex_table('q2_milestones','交接完成口径下的累计配送进度',['时刻/min','已交付箱数','质量/kg','体积/m$^3$','箱数进度/\\%'],[[r[0],r[1],f'{r[2]:.0f}',f'{r[3]:.3f}',f'{r[4]:.2f}'] for r in ms]);csv_table('q2_milestones',['时刻min','箱数','质量kg','体积m3','箱数进度%'],ms);analysis['delivery_milestones']=ms
    kinds=[]
    for kind in [x[0] for x in cargo]:
        rr=[b for b in boxes if b['kind']==kind]
        hard=[b['hard_slack_s'] for b in rr if b['hard_slack_s'] is not None]
        kinds.append([kind,len(rr),min(b['delivery_s'] for b in rr)/60,max(b['delivery_s'] for b in rr)/60,len(hard),min(hard)/60 if hard else None])
    latex_table('delivery_kind','各物资类别的实际交付时段与硬时限余量',['物资类型','箱数','最早交付/min','最后交付/min','硬时限箱数','最小硬余量/min'],[[r[0],r[1],f'{r[2]:.3f}',f'{r[3]:.3f}',r[4],f'{r[5]:.3f}' if r[5] is not None else '--'] for r in kinds]);csv_table('delivery_kind',['物资','箱数','最早min','最晚min','硬箱数','硬余量min'],kinds)
    edges=[]
    for k in sorted({r['battery'] for r in f}):
        rr=sorted([r for r in f if r['battery']==k],key=lambda r:r['start_s'])
        for a,b in zip(rr,rr[1:]):
            slack=b['start_s']-a['charge_end_s'];assert slack>-1e-6
            edges.append([k,a['flight_id'],b['flight_id'],a['charge_end_s'],b['start_s'],slack])
    latex_table('q2_tight_chains','共享电池再次投入任务的接续关系',['电池','前任务','后任务','恢复/s','后项开始/s','接续余量/s'],[[*r[:3],f'{r[3]:.3f}',f'{r[4]:.3f}',f'{max(0,r[5]):.3f}'] for r in edges],spec='lllrrr');csv_table('q2_tight_chains',['电池','前任务','后任务','恢复s','后项s','余量s'],edges)
    analysis['q2_battery_reuse_edges']=len(edges);analysis['q2_zero_slack_edges']=sum(abs(r[5])<1e-6 for r in edges)

    legs=load('revision_inputs/legs.json');q3=d['q3_flights'];rels=d['q3_relays'];t_energy=[]
    for m in 'ABC':
        ids={r['flight_id'] for r in q3 if r['type']==m};rr=[x for x in legs if x['flight_id'] in ids]
        h=sum(r['horizontal_kwh'] for r in rr);c=sum(r['climb_kwh'] for r in rr)
        t_energy.append([m,h,c,h+c])
    close(sum(r[3] for r in t_energy),66.25127994199477)
    latex_table('q3_transport_energy','联合方案运输能耗的物理分解',['机型','水平能耗/kWh','爬升能耗/kWh','总能耗/kWh'],[[r[0],*[f'{v:.6f}' for v in r[1:]]] for r in t_energy]);csv_table('q3_transport_energy',['机型','水平kWh','爬升kWh','总kWh'],t_energy);analysis['q3_transport_energy']=t_energy
    r_energy=[]
    for r in rels:
        service=r['service_end_s']-r['service_start_s'];work=r['return_s']-r['start_s'];e=r['energy_kwh']-r['transit_kwh']
        close(e,1.10*(30+service)/3600)
        r_energy.append([r['relay_id'],r['transit_kwh'],e,r['energy_kwh'],service/60,100*service/work])
    latex_table('q3_relay_energy','中继任务的转场、建链与悬停服务成本',['中继任务','转场/kWh','建链及服务/kWh','总能耗/kWh','服务/min','服务占用比/\\%'],[[r[0],*[f'{v:.6f}' for v in r[1:4]],f'{r[4]:.3f}',f'{r[5]:.2f}'] for r in r_energy]);csv_table('q3_relay_energy',['任务','转场kWh','建链服务kWh','总kWh','服务min','占用比%'],r_energy);analysis['q3_relay_energy']=r_energy
    phases=load('revision_inputs/all_communication_phases.json');states=load('revision_inputs/communication_states.json')
    phase_total=sum(r['end_s']-r['start_s'] for r in phases)
    state_total=sum(r['end_s']-r['start_s'] for r in states);close(phase_total,state_total)
    byflight=defaultdict(list)
    for r in states: assert r['end_s']>=r['start_s'];byflight[r['flight_id']].append(r)
    providers=[]
    for prov in ['G01']+[r['relay_id'] for r in rels]:
        rr=[r for r in states if r['provider']==prov];sec=sum(r['end_s']-r['start_s'] for r in rr)
        providers.append([prov,len(rr),len({r['flight_id'] for r in rr}),sec,sec/60,100*sec/state_total])
    latex_table('q3_provider','实际通信提供方的累计保障工作量',['提供方','区间数','运输任务数','累计保障/min','比例/\\%'],[[r[0],r[1],r[2],f'{r[4]:.3f}',f'{r[5]:.2f}'] for r in providers]);csv_table('q3_provider',['提供方','区间数','任务数','时长s','时长min','比例%'],providers)
    comm=[];switches=0
    for fid,rr in sorted(byflight.items()):
        rr=sorted(rr,key=lambda r:(r['start_s'],r['end_s']));direct=sum(r['end_s']-r['start_s'] for r in rr if r['provider']=='G01');relay=sum(r['end_s']-r['start_s'] for r in rr if r['provider']!='G01')
        nsw=sum(a['provider']!=b['provider'] for a,b in zip(rr,rr[1:]));switches+=nsw
        comm.append([fid,direct/60,relay/60,nsw])
        own=sum(r['end_s']-r['start_s'] for r in phases if r['flight_id']==fid);close(60*(comm[-1][1]+comm[-1][2]),own)
    longest=sorted(comm,key=lambda r:r[2],reverse=True)[:8]
    latex_table('q3_comm_tasks','中继保障需求较大的运输任务',['运输任务','直连/min','中继/min','提供方切换数'],[[r[0],f'{r[1]:.3f}',f'{r[2]:.3f}',r[3]] for r in longest]);csv_table('q3_comm_tasks',['任务','直连min','中继min','切换数'],comm)
    analysis.update(q3_phase_count=len(phases),q3_state_count=len(states),q3_comm_duration_s=phase_total,q3_direct_duration_s=providers[0][3],q3_relay_duration_s=state_total-providers[0][3],q3_relay_flights=sum(r[2]>1e-8 for r in comm),q3_direct_only_flights=sum(r[2]<1e-8 for r in comm),q3_provider_switches=switches)
    inv=d['q4_summary']['inventory'];order=d['q4_summary']['resource_order'];I=[inv[k] for k in order];pool=d['q4_global_pool'];poolvec=[pool[k] for k in order]
    assert poolvec == [4,2,2,6,4,4,2,3], poolvec
    ps=d['q4_partitions'];best2=min([r for r in ps if len(r['groups'])==2],key=lambda r:(r['total_gap'],r['total_need'],r['workload_cv']));best3=[r for r in ps if len(r['groups'])==3][0]
    rows=[]
    for name,vec in [('全局共享',poolvec),('两组独立',best2['need_vector']),('三组独立',best3['need_vector'])]:
        loss=sum(vec)-sum(poolvec);gap=sum(max(0,a-b) for a,b in zip(vec,I));remaining=sum(max(0,b-a) for a,b in zip(vec,I));assert sum(vec)-sum(I)==gap-remaining
        rows.append([name,sum(vec),loss,100*loss/sum(poolvec),gap,remaining])
    latex_table('q4_organization','固定日程不同组织方式的配置与库存关系',['组织方式','总配置','较共享增加','增幅/\\%','库存正缺口','库存剩余'],[[*r[:3],f'{r[3]:.2f}',*r[4:]] for r in rows]);csv_table('q4_organization',['组织','配置','增加','增幅%','缺口','剩余'],rows);analysis['q4_organization']=rows
    analysis['generated_tables']=sorted(x.stem for x in OUT.glob('*.tex'))
    (ROOT/'revision_analysis.json').write_text(json.dumps(analysis,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in analysis.items() if k not in ['cargo','input_files','generated_tables']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
