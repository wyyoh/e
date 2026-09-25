"""Baseline reconstruction and diagnostics, before any route search."""
from common import *
from physics import Model,workloads,partition_bound
from schedule import schedule
from collections import defaultdict,Counter
import itertools

def main():
    d=inputs();m=Model(d);raw=load(REPO/'verification_v3/selected_incumbent_energy_v4.json')
    print(type(raw),flush=True)
    jobs=[m.job(j['type'],j['boxes'],j['route'],f'V4-{i+1:02d}') for i,j in enumerate(raw)]
    assert all(j['feasible'] for j in jobs)
    status=load(REPO/'verification_v3/results/status_v4.json');cap=status['verified_upper_bound_s']
    plan,log=schedule(jobs,d['types'],cap,trials=100000)
    save(ROOT/'logs/baseline_reconstruction.json',log)
    assert plan is not None,log
    meta=dict(source='V4 tasks; newly reconstructed continuous-time schedule, not a recovered historical timeline',flights=plan,
              claimed_makespan_s=max(j['return_s'] for j in plan),energy_kwh=sum(j['energy_kwh'] for j in plan))
    assert abs(meta['claimed_makespan_s']-cap)<1e-6
    assert abs(meta['energy_kwh']-status['energy_kwh'])<1e-9
    save(ROOT/'results/baseline_incumbent.json',meta)
    wl=workloads(jobs,d['types']);bounds=partition_bound(jobs,d['types'])
    wrows=[dict(type=g,sorties=sum(j['type']==g for j in jobs),total_work_s=wl[g],aircraft=len(t['aircraft']),average_work_s=wl[g]/len(t['aircraft']),partition_bound_s=bounds[g]) for g,t in d['types'].items()]
    table(ROOT/'results/baseline_type_workloads.csv',wrows)
    chainrows=[]
    for rid in sorted({j['aircraft'] for j in plan}):
        chain=sorted([j for j in plan if j['aircraft']==rid],key=lambda j:j['start_s'])
        chainrows.append(dict(aircraft=rid,chain=[j['flight_id'] for j in chain],work_s=sum(j['duration_s'] for j in chain),last_return_s=max(j['return_s'] for j in chain)))
    table(ROOT/'results/baseline_aircraft_chains.csv',chainrows)
    table(ROOT/'results/baseline_battery_chains.csv',[dict(battery=rid,chain=[dict(flight_id=j['flight_id'],start_s=j['start_s'],return_s=j['return_s'],full_s=j['charge_end_s']) for j in sorted(plan,key=lambda j:j['start_s']) if j['battery']==rid]) for rid in sorted({j['battery'] for j in plan})])
    rows=[];migrations=[]
    for j in plan:
        due=min(d['boxes'][b]['expected_delivery_s'] for b in j['box_ids'])
        hard=[d['boxes'][b]['hard_deadline_s']-j['start_s']-j['delivery_offsets'][b] for b in j['box_ids'] if d['boxes'][b]['hard_deadline_s'] is not None]
        rows.append({k:j[k] for k in ['flight_id','type','route','aircraft','battery','start_s','takeoff_s','return_s','duration_s','prep_load_s','flight_s','handover_s','payload_kg','volume_m3','energy_kwh','return_soc']}|dict(earliest_expected_s=due,min_hard_slack_s=min(hard) if hard else None,min_zero_lateness_slack_s=j['latest_start_s']-j['start_s']))
        if j['type']=='B':
            for g in ['A','C']:
                c=m.job(g,j['box_ids'],j['route'])
                alternative=[x for x in jobs if x['flight_id']!=j['flight_id']]+[c]
                migrations.append(dict(flight_id=j['flight_id'],route=j['route'],target_type=g,feasible=c['feasible'],failures=c['failures'],new_duration_s=c.get('duration_s'),new_energy_kwh=c.get('energy_kwh'),average_work_lower_bound_s=max(workloads(alternative,d['types'])[h]/len(t['aircraft']) for h,t in d['types'].items()) if c['feasible'] else None))
    table(ROOT/'results/baseline_task_details.csv',rows);table(ROOT/'results/baseline_type_migrations.csv',migrations)
    # Diagnostic priority, not optimized or claimed to be the five best neighbours.
    choices=[(['V4-13','V4-14','V4-09'],'S008 两趟 B 与 S005 的 C：同一北部走廊，测试 B+B 合并及 C 货箱重新分配。'),
             (['V4-11','V4-20'],'S004 同区 B（水+卫生）与 A（水+食品）：容量互补交换，首先尝试卫生移出 B。'),
             (['V4-11','V4-06'],'S004 的 B 与 S002 的 C：两北部服务区联合配送，释放一趟 B 工作量。'),
             (['V4-05','V4-16','V4-17'],'S012 的 B 与东部 S009/S002/S013 的两趟 A：医疗箱挪移和两/三点路线重构。'),
             (['V4-10','V4-12','V4-17'],'S014/S010 两趟 B 与 S013 的 A：东侧邻近服务区，测试 B+B→A+C 或跨区箱交换。')]
    byid={j['flight_id']:j for j in jobs};top=[]
    for rank,(ids,why) in enumerate(choices,1):
        top.append(dict(rank=rank,flight_ids=ids,reason=why,box_count=sum(len(byid[i]['box_ids']) for i in ids),B_work_s=sum(byid[i]['duration_s'] for i in ids if byid[i]['type']=='B')))
    save(ROOT/'results/top5_neighborhoods.json',top)
    lines=['# 当前 23 架次瓶颈诊断','',meta['source']+'。这里只重建一次基线资源计划；未改变任何任务。',
           f"\n重算能耗 {meta['energy_kwh']:.12f} kWh，makespan {meta['claimed_makespan_s']:.12f} s。",'','## 机型工作量','', '|机型|架次|总工作秒|平均负荷下界秒|精确机器分配下界秒|','|---|---:|---:|---:|---:|']
    for r in wrows:lines.append(f"|{r['type']}|{r['sorties']}|{r['total_work_s']:.9f}|{r['average_work_s']:.9f}|{r['partition_bound_s']:.9f}|")
    lines+=['','## 飞机任务链','', '|飞机|任务链|累计工作秒|最后返回秒|','|---|---|---:|---:|']
    for r in chainrows:lines.append(f"|{r['aircraft']}|{' → '.join(r['chain'])}|{r['work_s']:.9f}|{r['last_return_s']:.9f}|")
    lines+=['','## B 型任务分解','', '|任务|路线|准备装载秒|飞行秒|交接秒|总秒|质量kg|体积m³|','|---|---|---:|---:|---:|---:|---:|---:|']
    for j in sorted(jobs,key=lambda j:j['flight_id']):
        if j['type']=='B':lines.append(f"|{j['flight_id']}|{' → '.join(j['route'])}|{j['prep_load_s']}|{j['flight_s']:.6f}|{j['handover_s']}|{j['duration_s']:.6f}|{j['payload_kg']}|{j['volume_m3']}|")
    binding=[r for r in chainrows if abs(r['last_return_s']-cap)<1e-6]
    lines+=['',f"决定 makespan 的飞机与任务链：{binding}。B 型固定任务的精确两机分配下界等于当前 makespan，因此单纯换序不能严格改善。",
            '','全部 6 趟 B 固定箱集换 A 均受到体积限制：医疗+水+食品为 0.067 m³，水+卫生为 0.062 m³，均大于 A 的 0.060 m³。换 C 的物理可行性及机型工作量筛选见 baseline_type_migrations.csv；必须考虑 C 现有负荷，不能只看 B 负荷下降。',
            '','## 优先重构的前五个局部任务集合','', '以下是搜索前按 B 可释放工作量、空间邻近和容量互补性选择的优先级，不是已优化结论。','']
    for r in top:lines.append(f"{r['rank']}. {' + '.join(r['flight_ids'])}：{r['reason']} 共 {r['box_count']} 箱，涉及 B 工作量 {r['B_work_s']:.6f} s。")
    lines+=['','## 可复核数据','', 'results/baseline_task_details.csv 给出起飞/返回、能耗和时限余量；baseline_aircraft_chains.csv 与 baseline_battery_chains.csv 给出完整资源链。逐箱时限及独立重放另由验证程序生成。V4 历史最紧余量不可直接当作本次重建排程的余量。']
    (ROOT/'bottleneck_analysis.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(workloads=wrows,chains=chainrows,migrations=migrations,logs=log),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
