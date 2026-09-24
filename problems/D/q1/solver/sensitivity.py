"""Finite-event reserve analysis; no interpolation of discrete trip counts."""
from collections import defaultdict
from .patterns import available
from .dp import Label,scalar_dp,pareto_dp,global_pareto
from model.physics import safe_payload,THRESHOLD_TOL
from model.io import write_csv,write_json


def add_local(labels):
    if any(l is None for l in labels.values()):return None
    answer=Label()
    for area,l in sorted(labels.items()):answer=answer.combine(l)
    return answer


def solve_all(groups,patterns,alpha):
    return add_local({s:scalar_dp(g[3],available(patterns[s],alpha)) for s,g in groups.items()})


def objectives(label):
    return (label.n,label.e,label.t) if label is not None else (None,None,None)


def signature(label):
    return tuple(sorted(label.path)) if label is not None else None


def reserve_analysis(groups,patterns,types,geo,out,low=0.,high=1.):
    grid=[]
    for percent in range(5,41):
        alpha=percent/100
        for g in geo.values():
            for m in types.values():
                grid.append(dict(reserve=alpha,**safe_payload(m,g,alpha)))
    write_csv(out/'reserve_payload_grid.csv',grid)
    events=defaultdict(list)
    for ps in patterns.values():
        for p in ps:
            if low<p.rho<high:events[p.rho].append(p)
    thresholds=sorted(events)
    local={s:scalar_dp(g[3],available(patterns[s],low)) for s,g in groups.items()}
    current=add_local(local)
    records=[];segments=[];batch_segments=[]
    n_left=low;batch_left=low
    initial=current
    for j,rho in enumerate(thresholds):
        previous=thresholds[j-1] if j else low
        following=thresholds[j+1] if j+1<len(thresholds) else high
        epsilon=min(1e-8,(rho-previous)/4,(following-rho)/4)
        if epsilon <= 4*THRESHOLD_TOL:
            raise ValueError('Numerically unresolved reserve events; do not silently merge')
        before=current
        affected=sorted({p.area for p in events[rho]})
        # At the exact threshold all equal-rho patterns remain available.
        exact_local=local.copy()
        for s in affected:exact_local[s]=scalar_dp(groups[s][3],available(patterns[s],rho))
        exact=add_local(exact_local)
        if objectives(exact)!=objectives(before):
            raise AssertionError('Exact threshold must retain left feasible set')
        for s in affected:local[s]=scalar_dp(groups[s][3],available(patterns[s],(rho+following)/2))
        after=add_local(local)
        nchange=objectives(before)[0]!=objectives(after)[0]
        bchange=signature(before)!=signature(after)
        left_n=right_n=None
        if nchange:
            leftcheck=solve_all(groups,patterns,rho-epsilon)
            rightcheck=solve_all(groups,patterns,rho+epsilon)
            left_n=objectives(leftcheck)[0];right_n=objectives(rightcheck)[0]
            if left_n!=objectives(before)[0] or right_n!=objectives(after)[0]:
                raise AssertionError('Threshold boundary direction failed')
            segments.append(dict(alpha_left=n_left,alpha_right=rho,left_closed=n_left==low,
                                 right_closed=True,min_sorties=objectives(before)[0]))
            n_left=rho
        if bchange:
            batch_segments.append(dict(alpha_left=batch_left,alpha_right=rho,left_closed=batch_left==low,
                                       right_closed=True,sorties=objectives(before)[0],energy_kwh=objectives(before)[1],
                                       time_s=objectives(before)[2],pattern_ids=signature(before)))
            batch_left=rho
        records.append(dict(threshold=rho,pattern_ids=[p.id for p in events[rho]],affected_areas=affected,
                            pattern_count=len(events[rho]),sorties_left=objectives(before)[0],
                            sorties_at=objectives(exact)[0],sorties_right=objectives(after)[0],
                            sorties_change=nchange,batching_change=bchange,
                            energy_left_kwh=objectives(before)[1],energy_right_kwh=objectives(after)[1],
                            time_left_s=objectives(before)[2],time_right_s=objectives(after)[2],
                            epsilon=epsilon,boundary_left_recomputed=left_n,boundary_right_recomputed=right_n))
        current=after
    segments.append(dict(alpha_left=n_left,alpha_right=high,left_closed=n_left==low,right_closed=False,
                         min_sorties=objectives(current)[0]))
    batch_segments.append(dict(alpha_left=batch_left,alpha_right=high,left_closed=batch_left==low,right_closed=False,
                               sorties=objectives(current)[0],energy_kwh=objectives(current)[1],time_s=objectives(current)[2],
                               pattern_ids=signature(current)))
    write_csv(out/'reserve_thresholds.csv',records)
    write_csv(out/'reserve_segments.csv',segments)
    write_csv(out/'reserve_optimal_segments.csv',batch_segments)
    return dict(candidate_events=len(records),sortie_change_events=sum(r['sorties_change'] for r in records),
                batching_change_events=sum(r['batching_change'] for r in records),
                domain=[low,high],right_endpoint_excluded=True,segments=segments)


def pareto_analysis(groups,patterns,out,alpha=.2):
    local={s:pareto_dp(g[3],available(patterns[s],alpha)) for s,g in groups.items()}
    global_front=global_pareto(local)
    write_csv(out/'pareto_local.csv',
              (dict(service_area=s,**label.record()) for s,labels in local.items() for label in labels))
    write_csv(out/'pareto_front.csv',(l.record() for l in global_front))
    return global_front
