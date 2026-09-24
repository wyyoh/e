
"""ALNS experiment for competition D Q2. Physical evaluator/decoder inherited unchanged.
This is an experimental solver, not a proof of global optimality.
"""
from __future__ import annotations
from core import *
import random, math, time, json, argparse
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[1]

def finite_key(m):
    return (m['hard_late_boxes'], max(0,round(m['hard_lateness_s'],6)),
            max(0,round(m['weighted_tardiness_s'],6)),m['makespan_s'],
            m['energy_kwh'],m['sorties'])
def feasible(m):
    return m is not None and m['hard_late_boxes']==0 and m['weighted_tardiness_s']<1e-7
def score(m, mode="time"):
    # Search criterion only. Final comparison is lexicographic.
    ew,nw = {'time':(1.5,2.),'balanced':(25.,8.),'energy':(110.,12.)}[mode]
    return 2e6*m['hard_late_boxes']+2000*m['hard_lateness_s']+100*m['weighted_tardiness_s']+m['makespan_s']+ew*m['energy_kwh']+nw*m['sorties']+.0002*m['sum_delivery_s']

def canonicalize(plan):
    """Assign identical same-site/type cartons with earlier deadlines to earlier drops.
       Every original ID and attributes are preserved."""
    _,s=schedule(plan,True)
    groups=defaultdict(list)
    for p,row in enumerate(s):
        for i,off in evaluate(row['task'])['delivery']:
            groups[(B[i]['site'],B[i]['kind'])].append((row['start_s']+off,p,i))
    alloc=[[] for _ in plan]
    for events in groups.values():
        ids=sorted((i for _,_,i in events),key=lambda i:(B[i]['hard_deadline_s'] if B[i]['hard_deadline_s'] is not None else 1e12,B[i]['expected_delivery_s'],B[i]['id']))
        for ev,i in zip(sorted(events),ids):alloc[ev[1]].append(i)
    return [task(k[0],ids,k[2]) for k,ids in zip(plan,alloc)]

def route_options(ids, old=()):
    sites=set(B[i]['site'] for i in ids)
    preserved=tuple(s for s in old if s in sites)
    extra=sites-set(preserved)
    if len(extra)==0:return [preserved] if preserved else []
    if len(extra)==1:
        s=next(iter(extra))
        return [preserved[:j]+(s,)+preserved[j:] for j in range(len(preserved)+1)]
    # Construction only. Up to 5 unique sites enumerate; larger routes retain
    # supplied order plus greedy and reverse. This is a search filter, not a cap.
    if len(sites)<=5:return list(itertools.permutations(sorted(sites)))
    remaining=set(sites);a='O01';route=[]
    while remaining:
        b=min(remaining,key=lambda s:G[a,s]['distance_m']);route.append(b);remaining.remove(b);a=b
    return [tuple(route),tuple(reversed(route))]

def choose_task(ids,g,old=(),rng=None):
    opts=[task(g,ids,r) for r in route_options(ids,old)]
    opts=[k for k in opts if evaluate(k) is not None]
    if not opts:return None
    if rng is not None and rng.random()<.2:return rng.choice(opts)
    return min(opts,key=lambda k:(max(0,-evaluate(k)['latest']),evaluate(k)['duration']+.1*evaluate(k)['energy']))

def rank_partial(plan,k,new,index,mode):
    # only a cheap shortlist key; actual decoder decides each retained option
    loads={g:0. for g in T};energy=0.
    for j,p in enumerate(plan):
        if index is not None and j==index:continue
        e=evaluate(p);loads[p[0]]+=e['duration'];energy+=e['energy']
    e=evaluate(k);loads[k[0]]+=e['duration'];energy+=e['energy']
    ew={'time':1.5,'balanced':25,'energy':110}[mode]
    return max(loads[g]/len(T[g]['aircraft']) for g in T)+ew*energy+max(0,-e['latest'])*1e4

def insertion_options(plan,b,rng,mode):
    options=[];seen=set()
    # one-box insertion may resize the target to any compatible aircraft type
    for j,old in enumerate(plan):
        ids=tuple(sorted(old[1]+(b,)))
        for g in T:
            for route in route_options(ids,old[2]):
                k=task(g,ids,route);ev=evaluate(k)
                if ev is None:continue
                key=(j,k)
                if key in seen:continue
                seen.add(key);options.append((rank_partial(plan,k,False,j,mode),j,k))
    for g in T:
        k=task(g,(b,))
        if evaluate(k) is not None:options.append((rank_partial(plan,k,True,None,mode),None,k))
    if not options:return []
    options.sort(key=lambda x:x[0])
    # Retain both proxy-best alternatives and the least incremental-work
    # alternatives. This filter is documented rather than claimed exhaustive.
    chosen=options[:10]
    bytype=[]
    for g in T:
        vals=[o for o in options if o[2][0]==g]
        if vals:bytype.append(vals[0])
    chosen+=bytype
    actual=[];seen2=set()
    for _,j,k in chosen:
        sig=(j,k)
        if sig in seen2:continue
        seen2.add(sig)
        # All positions in dispatch sequence are tested for the changed task.
        pp=plan[:j]+plan[j+1:] if j is not None else list(plan)
        # Cross-type order has no effect, so only type-relative positions matter.
        ids=[a for a,q in enumerate(pp) if q[0]==k[0]]
        positions=[0]+[a+1 for a in ids]
        best=None
        for pos in positions:
            cand=pp[:pos]+[k]+pp[pos:];m=schedule(cand)
            if m is None:continue
            s=score(m,mode)
            if best is None or s<best[0]:best=(s,cand)
        if best is not None:actual.append(best)
    actual.sort(key=lambda x:x[0])
    return actual

def destroy(plan,rng,name):
    ids=[i for p in plan for i in p[1]]
    count=rng.randint(3,7)
    if name=='random':
        remove=set(rng.sample(ids,min(count,len(ids))))
    elif name=='route':
        ps=rng.sample(plan,min(len(plan),rng.choice([1,1,2])))
        remove={i for p in ps for i in p[1]}
    elif name=='related':
        seed=rng.choice(ids);s=B[seed]['site']
        dist=lambda i:0 if B[i]['site']==s else G[s,B[i]['site']]['distance_m']
        ordered=sorted(ids,key=lambda i:dist(i)+rng.random()*1800)
        remove=set(ordered[:count])
    else:
        m,ss=schedule(plan,True)
        # Ruin the most heavily loaded type or late finishing route.
        weight={g:sum(evaluate(p)['duration'] for p in plan if p[0]==g)/len(T[g]['aircraft']) for g in T}
        g=max(weight,key=weight.get);ps=[p for p in plan if p[0]==g]
        ps.sort(key=lambda p:evaluate(p)['duration'],reverse=True)
        picks=ps[:min(3,len(ps))]
        p=rng.choice(picks);remove=set(p[1])
        if len(remove)<count:
            others=[i for i in ids if i not in remove]
            remove.update(rng.sample(others,min(count-len(remove),len(others))))
    remainder=[]
    for old in plan:
        keep=tuple(i for i in old[1] if i not in remove)
        if not keep:continue
        # Removing a stop could expose a different high terrain leg. Always re-evaluate.
        k=choose_task(keep,old[0],old[2],rng)
        if k is None:
            remove.update(keep)
        else:remainder.append(k)
    return remainder, sorted(remove)

def repair(plan,removed,rng,name,mode):
    while removed:
        options=[]
        # Evaluate all removed boxes; q<=~16; no hard-date guessing.
        for i in removed:
            opts=insertion_options(plan,i,rng,mode)
            if not opts:return None
            k=1 if name=='greedy' else (2 if name=='regret2' else 3)
            best=opts[0][0]
            regret=sum(opts[min(j,len(opts)-1)][0]-best for j in range(1,k))
            selection=(-best if k==1 else regret)+rng.random()*1e-6
            options.append((selection,i,opts[0][1]))
        _,i,plan=max(options,key=lambda x:x[0]);removed.remove(i)
    return canonicalize(plan)

def local(plan,rng):
    n=len(plan);u=rng.random();pp=list(plan)
    if n<2:return plan
    if u<.4:
        same=rng.choice(tuple(T));ix=[i for i,k in enumerate(pp) if k[0]==same]
        if len(ix)<2:return None
        a,b=rng.sample(ix,2)
        if rng.random()<.5:pp[a],pp[b]=pp[b],pp[a]
        else:pp.insert(b,pp.pop(a))
    elif u<.58:
        i=rng.randrange(n);p=pp[i];k=choose_task(p[1],rng.choice(tuple(T)),p[2],rng)
        if k is None:return None
        pp[i]=k
    elif u<.8:
        a,b=rng.sample(range(n),2);pa,pb=pp[a],pp[b]
        i=rng.choice(pa[1]);j=rng.choice(pb[1])
        ka=choose_task(tuple(x for x in pa[1] if x!=i)+(j,),pa[0],pa[2],rng)
        kb=choose_task(tuple(x for x in pb[1] if x!=j)+(i,),pb[0],pb[2],rng)
        if ka is None or kb is None:return None
        pp[a]=ka;pp[b]=kb
    else:
        a,b=rng.sample(range(n),2);pa,pb=pp[a],pp[b];i=rng.choice(pa[1])
        ka=choose_task(tuple(x for x in pa[1] if x!=i),pa[0],pa[2],rng) if len(pa[1])>1 else None
        kb=choose_task(pb[1]+(i,),pb[0],pb[2],rng)
        if kb is None or (len(pa[1])>1 and ka is None):return None
        pp[b]=kb
        if ka is None:pp.pop(a)
        else:pp[a]=ka
    return canonicalize(pp)

def run(start,seed=1,iterations=500,adaptive=True,mode='time',out=None,max_seconds=3600):
    rng=random.Random(seed);plan=canonicalize(start);m=schedule(plan);best=(m,plan);s=score(m,mode)
    dn=['random','route','related','critical'];rn=['greedy','regret2','regret3']
    dw=[1.]*4;rw=[1.]*3;ds=[0.]*4;rs=[0.]*3;du=[0]*4;ru=[0]*3
    total_use=[0]*4;total_rep=[0]*3;history=[];trace=[];archive=[];t0=time.monotonic();accepted=0
    if feasible(m):archive=[(m,plan)]
    for it in range(iterations):
        if time.monotonic()-t0>max_seconds:break
        d=rng.choices(range(4),weights=dw)[0];r=rng.choices(range(3),weights=rw)[0]
        partial,removed=destroy(plan,rng,dn[d]);cand=repair(partial,removed,rng,rn[r],mode)
        du[d]+=1;ru[r]+=1;total_use[d]+=1;total_rep[r]+=1
        reward=0
        if cand is not None:
            mm=schedule(cand);sv=score(mm,mode)
            temp=55*(1-it/iterations)**2+1.
            isnew=finite_key(mm)<finite_key(best[0])
            if sv<s or rng.random()<math.exp(min(0,(s-sv)/temp)):
                reward=6 if sv<s-1e-8 else 1.
                plan,m,s=cand,mm,sv;accepted+=1
            if isnew:
                best=(mm,cand);reward=20.
                history.append({'iteration':it,'elapsed_s':time.monotonic()-t0,**mm})
                print('BEST',seed,it,mm['makespan_s']/60,mm['energy_kwh'],mm['sorties'],flush=True)
            if feasible(mm):
                if not any(a[0]['makespan_s']<=mm['makespan_s']+1e-7 and a[0]['energy_kwh']<=mm['energy_kwh']+1e-9 and a[0]['sorties']<=mm['sorties'] for a in archive):
                    archive=[a for a in archive if not (mm['makespan_s']<=a[0]['makespan_s']+1e-7 and mm['energy_kwh']<=a[0]['energy_kwh']+1e-9 and mm['sorties']<=a[0]['sorties'])]
                    archive.append((mm,cand))
        ds[d]+=reward;rs[r]+=reward
        # Same local intensification for adaptive and uniform-control variants.
        for _ in range(20):
            cand=local(plan,rng)
            if cand is None:continue
            mm=schedule(cand);sv=score(mm,mode);temp=25*(1-it/iterations)**2+.2
            if sv<s or rng.random()<math.exp(min(0,(s-sv)/temp)):
                plan,m,s=cand,mm,sv
            if finite_key(mm)<finite_key(best[0]):
                best=(mm,cand);history.append({'iteration':it,'local':True,'elapsed_s':time.monotonic()-t0,**mm})
                print('BEST_LOCAL',seed,it,mm['makespan_s']/60,mm['energy_kwh'],mm['sorties'],flush=True)
            if feasible(mm) and not any(a[0]['makespan_s']<=mm['makespan_s']+1e-7 and a[0]['energy_kwh']<=mm['energy_kwh']+1e-9 and a[0]['sorties']<=mm['sorties'] for a in archive):
                archive=[a for a in archive if not(mm['makespan_s']<=a[0]['makespan_s']+1e-7 and mm['energy_kwh']<=a[0]['energy_kwh']+1e-9 and mm['sorties']<=a[0]['sorties'])]
                archive.append((mm,cand))
        if (it+1)%25==0:
            if adaptive:
                dw=[max(.15,.8*w+.2*(v/u if u else w)) for w,v,u in zip(dw,ds,du)]
                rw=[max(.15,.8*w+.2*(v/u if u else w)) for w,v,u in zip(rw,rs,ru)]
            trace.append({'iteration':it+1,'elapsed_s':time.monotonic()-t0,'destroy_weights':dw.copy(),'repair_weights':rw.copy(),'best':best[0]})
            ds=[0.]*4;rs=[0.]*3;du=[0]*4;ru=[0]*3
            if out:
                out.mkdir(parents=True,exist_ok=True)
                (out/'best.json').write_text(json.dumps({'metrics':best[0],'decisions':as_decisions(best[1])},ensure_ascii=False,indent=2))
                (out/'progress.json').write_text(json.dumps(trace,ensure_ascii=False,indent=2))
            if it%100==99:
                print('STEP',seed,it+1,'seconds',round(time.monotonic()-t0,2),'cache',evaluate.cache_info(),flush=True)
        # Capped cache prevents runaway memory and does not change values.
        if evaluate.cache_info().currsize>70000:evaluate.cache_clear();variants.cache_clear()
        if it%80==79:plan=best[1];m=best[0];s=score(m,mode)
    result={'seed':seed,'adaptive':adaptive,'mode':mode,'iterations_completed':it+1,'elapsed_s':time.monotonic()-t0,
            'accepted_large_moves':accepted,'destroy_use':dict(zip(dn,total_use)),
            'repair_use':dict(zip(rn,total_rep)),'weights':{'destroy':dw,'repair':rw},
            'metrics':best[0],'decisions':as_decisions(best[1]),'history':history,'weight_trace':trace,
            'archive':[{'metrics':m,'decisions':as_decisions(p)} for m,p in archive]}
    if out:
        (out/'run.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
        (out/'best.json').write_text(json.dumps({'metrics':best[0],'decisions':as_decisions(best[1])},ensure_ascii=False,indent=2))
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,default=1);ap.add_argument('--iterations',type=int,default=500);ap.add_argument('--seconds',type=float,default=3600);ap.add_argument('--uniform',action='store_true');ap.add_argument('--mode',default='time');ap.add_argument('--input',default='selected_main.json');ap.add_argument('--output',default='run1');a=ap.parse_args()
    d=json.loads((ROOT/'inputs'/a.input).read_text());p=from_decisions(d['decisions'])
    res=run(p,a.seed,a.iterations,not a.uniform,a.mode,ROOT/'results'/a.output,a.seconds)
    print('FINAL',json.dumps({k:v for k,v in res.items() if k not in ['decisions','history','weight_trace','archive']},ensure_ascii=False),flush=True)
