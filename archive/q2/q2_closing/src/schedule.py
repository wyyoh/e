"""Deterministic bounded list scheduling; full continuous seconds, no rounding.
This is a primal heuristic, not an infeasibility or optimality certificate.
"""
import heapq,itertools,random,math

def decode(jobs,t,order,detail=False):
    aa=[(0.,i) for i in range(len(t['aircraft']))];bb=[(0.,i) for i in range(t['battery_count'])]
    endall=0.;late=0.;out=[]
    for idx in order:
        j=jobs[idx];ar,ai=heapq.heappop(aa);br,bi=heapq.heappop(bb)
        start=max(ar,br);end=start+j['duration_s'];late=max(late,start-j['latest_start_s'])
        heapq.heappush(aa,(end,ai));heapq.heappush(bb,(end+j['charge_s'],bi));endall=max(endall,end)
        if detail:out.append(dict(j,start_s=start,return_s=end,takeoff_s=start+j['prep_load_s'],charge_end_s=end+j['charge_s'],aircraft=t['aircraft'][ai],battery=f"{t['id']}-BAT{bi+1:02d}"))
    return (late,endall,out) if detail else (late,endall)

def group(jobs,t,cap,seed=20260924,trials=4000):
    n=len(jobs)
    if not n:return [],{'tested':0,'status':'feasible_empty'}
    rng=random.Random(seed);seen=set();tested=0;best=(math.inf,math.inf);bestorder=None
    orders=[sorted(range(n),key=lambda k:jobs[k]['latest_start_s']),sorted(range(n),key=lambda k:-jobs[k]['duration_s'])]
    if n<=8:orders=itertools.chain(orders,itertools.permutations(range(n)))
    else:
        initial_orders=orders
        def random_orders():
            yield from initial_orders
            base=list(range(n))
            for _ in range(trials):
                rng.shuffle(base);yield base.copy()
        orders=random_orders()
    for order in orders:
        key=tuple(order)
        if key in seen:continue
        seen.add(key);tested+=1;v=decode(jobs,t,order)
        if v<best:best,bestorder=v,key
        if v[0]<=1e-7 and v[1]<=cap+1e-7:
            return decode(jobs,t,order,True)[2],{'tested':tested,'status':'feasible','makespan_s':v[1],'seed':seed}
    return None,{'tested':tested,'status':'search_failed','best_lateness_s':best[0],'best_span_s':best[1],'seed':seed}

def schedule(jobs,types,cap,seed=20260924,trials=4000):
    plan=[];logs={}
    for g,t in types.items():
        p,log=group([j for j in jobs if j['type']==g],t,cap,seed,trials);logs[g]=log
        if p is None:return None,logs
        plan.extend(p)
    return plan,logs
