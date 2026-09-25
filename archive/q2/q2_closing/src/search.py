"""Bounded route LNS. Finite-pool workload MILP proposes, full replay accepts.
All candidate routes use unrounded physical energy and time. No relaxed route
can become an incumbent. Stop at the first independently verified improvement.
"""
from common import *
from physics import Model,workloads,partition_bound
from schedule import schedule
from replay import verify
from collections import Counter
import itertools,time,math,argparse
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import coo_matrix

def patterns(model,removed,outside,cap,max_sites=3):
    ids=sorted({b for j in removed for b in j['box_ids']});outside_work=workloads(outside,model.types)
    budget={g:len(t['aircraft'])*cap-outside_work[g] for g,t in model.types.items()}
    pool=[];seen=set();stats=Counter()
    for mask in range(1,1<<len(ids)):
        bs=[b for i,b in enumerate(ids) if mask>>i&1];sites=sorted({model.boxes[b]['site'] for b in bs})
        if len(sites)>max_sites:continue
        for g in model.types:
            if budget[g]<300:continue
            # Cheap exact capacity filter before route evaluation.
            t=model.types[g]
            if sum(model.boxes[b]['mass_kg'] for b in bs)>t['max_payload_kg'] or sum(round(model.boxes[b]['volume_m3']*1000) for b in bs)>round(t['max_volume_m3']*1000):continue
            for route in itertools.permutations(sites):
                stats['physical_evaluations']+=1;j=model.job(g,bs,route)
                if not j['feasible']:
                    stats.update(j['failures']);continue
                if j['duration_s']>budget[g]+1e-7:stats['workload_pruned']+=1;continue
                key=g,tuple(bs),route
                if key not in seen:pool.append(j);seen.add(key)
    return pool,dict(stats)

def workload_master(pool,outside,types,cap,max_routes,seconds,nogoods):
    jobs=outside+pool;nfixed=len(outside);ids=sorted({b for j in jobs for b in j['box_ids']});rindex={b:i for i,b in enumerate(ids)}
    acs=[u for t in types.values() for u in t['aircraft']];arow={u:len(ids)+i for i,u in enumerate(acs)}
    rows=[];cols=[];vals=[];lower=[1.]*len(ids)+[-np.inf]*len(acs)+[-np.inf];upper=[1.]*len(ids)+[0.]*len(acs)+[float(max_routes)]
    choices=[];objective=[];lbs=[];ubs=[];integrality=[]
    for i,j in enumerate(jobs):
        for aircraft in types[j['type']]['aircraft']:
            k=len(choices);choices.append((i,aircraft));objective.append(0.);lbs.append(0.);ubs.append(1.);integrality.append(1)
            for b in j['box_ids']:rows.append(rindex[b]);cols.append(k);vals.append(1.)
            rows.extend([arow[aircraft],len(ids)+len(acs)]);cols.extend([k,k]);vals.extend([j['duration_s'],1.])
    kT=len(choices);objective.append(1.);lbs.append(0.);ubs.append(cap);integrality.append(0)
    for row in arow.values():rows.append(row);cols.append(kT);vals.append(-1.)
    for ban in nogoods:
        r=len(lower);lower.append(-np.inf);upper.append(len(ban)-1)
        for k,(i,a) in enumerate(choices):
            if i-nfixed in ban:rows.append(r);cols.append(k);vals.append(1.)
    # Only remove identical-resource label symmetry for fixed flights is optional;
    # keep all assignments to avoid excluding a physical alternative.
    A=coo_matrix((vals,(rows,cols)),shape=(len(lower),len(objective))).tocsc();st=time.perf_counter()
    result=milp(np.array(objective),integrality=np.array(integrality),bounds=Bounds(lbs,ubs),constraints=LinearConstraint(A,lower,upper),options={'time_limit':seconds,'mip_rel_gap':0.001})
    def number(name):
        v=getattr(result,name,None);return float(v) if v is not None and math.isfinite(v) else None
    log=dict(status=int(result.status),message=result.message,objective_s=number('fun'),dual_bound_s=number('mip_dual_bound'),mip_gap=number('mip_gap'),variables=len(objective),constraints=len(lower),elapsed_s=time.perf_counter()-st,scope='finite-neighborhood route selection and aircraft workload only; no infeasibility claim for full problem')
    selected=None;indices=None
    if result.x is not None:
        selected_ids=sorted({choices[k][0] for k,v in enumerate(result.x[:-1]) if v>.5});selected=[jobs[i] for i in selected_ids];indices=[i-nfixed for i in selected_ids if i>=nfixed]
        assert Counter(b for j in selected for b in j['box_ids'])==Counter(ids)
    return selected,indices,log

def internal_check(plan,m):
    assert Counter(b for j in plan for b in j['box_ids'])==Counter(m.boxes.keys())
    for j in plan:
        r=m.job(j['type'],j['box_ids'],j['route']);assert r['feasible']
        t=m.types[j['type']]
        assert j['aircraft'] in t['aircraft']
        assert j['battery'] in [f"{j['type']}-BAT{k+1:02d}" for k in range(t['battery_count'])]
        assert j['start_s']>=-1e-7
        assert j['start_s']<=r['latest_start_s']+1e-7
        assert abs(j['return_s']-j['start_s']-r['duration_s'])<1e-7
        assert abs(j['charge_end_s']-j['return_s']-r['charge_s'])<1e-7
    for resource,end in [('aircraft','return_s'),('battery','charge_end_s')]:
        for rid in {j[resource] for j in plan}:
            chain=sorted([j for j in plan if j[resource]==rid],key=lambda j:j['start_s'])
            for a,b in zip(chain,chain[1:]):assert a[end]<=b['start_s']+1e-7
    return {'box_count':len(m.boxes),'coverage':True,'physical_job_recomputations':len(plan),'aircraft_chains_checked':len({j['aircraft'] for j in plan}),'battery_chains_checked':len({j['battery'] for j in plan}),'zero_lateness':True}

def main():
    p=argparse.ArgumentParser();p.add_argument('--seconds',type=float,default=15);p.add_argument('--max-neighborhoods',type=int,default=150);p.add_argument('--resume',action='store_true');p.add_argument('--manifest');a=p.parse_args()
    d=inputs();m=Model(d);baseline=load(ROOT/'results/baseline_incumbent.json');jobs=sorted(baseline['flights'],key=lambda j:j['flight_id']);byid={j['flight_id']:j for j in jobs}
    cap=baseline['claimed_makespan_s']-1e-5;summary=[];alllogs=[];winner=None
    # Highest-value eastern/northern pairs, then diagnostic top five (including
    # 22-sortie attempts), then remaining B-involving pairs and selected triples.
    neighborhoods=[]
    bjobs=[j['flight_id'] for j in jobs if j['type']=='B']
    for b in bjobs:neighborhoods.append(('1-route/type', [b],23))
    preferred=[['V4-10','V4-17'],['V4-11','V4-20'],['V4-11','V4-06'],['V4-13','V4-14'],['V4-05','V4-16'],['V4-12','V4-17']]
    for ids in preferred:neighborhoods.append(('2-route',ids,23))
    for row in load(ROOT/'results/top5_neighborhoods.json'):
        if len(row['flight_ids'])==3:
            neighborhoods.append(('22-feasibility',row['flight_ids'],22));neighborhoods.append(('3-route',row['flight_ids'],23))
    used={tuple(sorted(ids)) for _,ids,n in neighborhoods if n==23}
    for pair in itertools.combinations([j['flight_id'] for j in jobs],2):
        if set(pair)&set(bjobs) and tuple(sorted(pair)) not in used:neighborhoods.append(('2-route',list(pair),23))
    extra=[]
    for b in ['V4-10','V4-11','V4-14']:
        for c in [j['flight_id'] for j in jobs if j['type']=='C']:
            for x in [j['flight_id'] for j in jobs if j['type']!='C' and j['flight_id']!=b]:
                sites={s for i in [b,c,x] for s in byid[i]['route']}
                distances=[m.geo[u,v][0] for u,v in itertools.combinations(sites,2)]
                extra.append((max(distances,default=0),[b,c,x]))
    for _,ids in sorted(extra):neighborhoods.append(('3-route',ids,23))
    for b in ['V4-10','V4-11','V4-14']:
        for pair in itertools.combinations([j['flight_id'] for j in jobs if j['type']=='A'],2):neighborhoods.append(('3-route', [b,*pair],23))
    if a.manifest:
        neighborhoods=[(r['kind'],r['removed'],r['max_sorties']) for r in load(a.manifest)]
    start=time.perf_counter();twentytwo=[]
    if a.resume:
        summary=load(ROOT/'logs/neighborhood_records.json');alllogs=load(ROOT/'logs/search_details.json')
        twentytwo=[r for r in summary if r['max_sorties']==22]
    done={(tuple(sorted(r['removed'])),r['max_sorties']) for r in summary};pending=[]
    for kind,ids,ncap in neighborhoods:
        key=tuple(sorted(ids)),ncap
        if key not in done:pending.append((kind,ids,ncap));done.add(key)
    for kind,ids,ncap in pending[:a.max_neighborhoods]:
        ni=len(summary)
        print('NEIGHBORHOOD',ni,kind,ids,ncap,flush=True);st=time.perf_counter()
        outside=[j for j in jobs if j['flight_id'] not in ids];removed=[byid[i] for i in ids]
        pool,stats=patterns(m,removed,outside,cap);record=dict(index=ni,kind=kind,removed=ids,max_sorties=ncap,pool_size=len(pool),**stats);nogoods=[]
        for attempt in range(5):
            selected,indices,log=workload_master(pool,outside,d['types'],cap,ncap,a.seconds,nogoods)
            detail=dict(neighborhood=ni,attempt=attempt,master=log);alllogs.append(detail)
            if selected is None:
                record['outcome']='finite_pool_no_candidate' if log['status']==2 else 'solver_limit_no_candidate';break
            for k,j in enumerate(selected):
                if j['flight_id']=='candidate':selected[k]=dict(j,flight_id=f'LNS-{ni:03d}-{k+1:02d}')
            bounds=partition_bound(selected,d['types']);detail['partition_bounds_s']=bounds
            if max(bounds.values())>cap+1e-7:record['outcome']='partition_bound_rejected';nogoods.append(set(indices));continue
            plan,slog=schedule(selected,d['types'],cap,seed=20260924+ni*10+attempt,trials=40000);detail['schedule_search']=slog
            if plan is not None:
                internal=internal_check(plan,m);res,*_=verify(plan);detail['independent_replay']=res
                if res['failed']==0 and res['metrics']['makespan_s']<cap:
                    winner=dict(source_neighborhood=record,flights=plan,claimed_makespan_s=res['metrics']['makespan_s'],metrics=res['metrics'],internal_validation=internal,independent_validation=res)
                    save(ROOT/'results/best_incumbent.json',winner);record['outcome']='verified_improvement';record['new_makespan_s']=res['metrics']['makespan_s'];break
                record['outcome']='independent_validation_rejected'
            else:record['outcome']='schedule_search_failed'
            nogoods.append(set(indices))
        record['elapsed_s']=time.perf_counter()-st;summary.append(record)
        if ncap==22:twentytwo.append(record)
        save(ROOT/'logs/search_details.json',alllogs);save(ROOT/'logs/neighborhood_records.json',summary)
        fields=list(dict.fromkeys(k for r in summary for k in r));table(ROOT/'results/neighborhood_summary.csv',summary,fields)
        print('OUTCOME',record,flush=True)
        if winner:break
    save(ROOT/'results/feasibility_22_sorties.json',dict(status='not_exhausted_stopped_after_verified_improvement' if winner else 'search_failed_to_find_feasible',proven_infeasible=False,globally_optimal=False,scope='bounded local neighborhoods, not complete 22-sortie space',attempts=twentytwo,reason='User stop rule: end main search after verified improvement' if winner else 'Bounded search budget reached'))
    save(ROOT/'logs/search_summary.json',dict(elapsed_s=time.perf_counter()-start,neighborhoods=len(summary),improved=winner is not None,stopped_by='verified_improvement' if winner else 'bounded_search_budget',max_neighborhoods=a.max_neighborhoods,seconds_per_master=a.seconds))
    if winner is None:save(ROOT/'results/best_incumbent.json',baseline)
    print('FINAL',winner['metrics'] if winner else 'no improvement',flush=True)
if __name__=='__main__':main()
