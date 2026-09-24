"""Distance sensitivity and an exact-integer numerical Pareto audit."""
from dataclasses import replace
import math
from geographiclib.geodesic import Geodesic
from model.io import write_json,write_csv
from model.physics import safe_payload
from solver.patterns import group_boxes,enumerate_patterns,available
from solver.sensitivity import solve_all
import solver.dp as dp


def crosscheck(nodes,types,boxes,geo,out):
    groups=group_boxes(boxes);base=enumerate_patterns(groups,types,geo)
    alternate={s:dict(g,distance_m=Geodesic.WGS84.Inverse(nodes['O01'].lat,nodes['O01'].lon,nodes[s].lat,nodes[s].lon)['s12']) for s,g in geo.items()}
    alt=enumerate_patterns(groups,types,alternate)
    baseline=solve_all(groups,base,.2);alternative=solve_all(groups,alt,.2)
    rows=[]
    for s,g in geo.items():
        for m in types.values():
            w=safe_payload(m,g,.2)['safe_payload_kg'];v=safe_payload(m,alternate[s],.2)['safe_payload_kg']
            rows.append(dict(service_area=s,aircraft_type=m.id,aeqd_safe_payload_kg=w,
                             geodesic_safe_payload_kg=v,absolute_payload_difference_kg=abs(w-v)))
    write_csv(out/'distance_payload_crosscheck.csv',rows)
    pattern_sets_equal=all({p.id for p in available(base[s],.2)}=={p.id for p in available(alt[s],.2)} for s in groups)
    report=dict(main_model='AEQD centred on O01',independent_distance='WGS84 GeographicLib inverse',
                max_absolute_distance_difference_m=max(abs(g['distance_m']-alternate[s]['distance_m']) for s,g in geo.items()),
                max_relative_distance_difference=max(abs(g['distance_m']-alternate[s]['distance_m'])/g['distance_m'] for s,g in geo.items()),
                max_absolute_payload_difference_kg=max(r['absolute_payload_difference_kg'] for r in rows),
                feasible_pattern_sets_equal=pattern_sets_equal,
                same_selected_count_pattern_representative=sorted(baseline.path)==sorted(alternative.path),
                sortie_difference=alternative.n-baseline.n,energy_difference_kwh=alternative.e-baseline.e,
                cumulative_time_difference_s=alternative.t-baseline.t)
    if not (pattern_sets_equal and baseline.n==alternative.n and abs(baseline.e-alternative.e)<=1e-10
            and abs(baseline.t-alternative.t)<=1e-7):
        raise AssertionError('Distance convention cross-check changes the optimization; report required')
    write_json(out/'distance_crosscheck.json',report)

    # Exact integer arithmetic for all additions/comparisons. Quantization error
    # is explicitly bounded and is below the main tolerance even at 80 sorties.
    scaled={s:[replace(p,energy=round(p.energy*1e12),time=round(p.time*1e9)) for p in available(ps,.2)] for s,ps in base.items()}
    et,tt=dp.ENERGY_TOL,dp.TIME_TOL
    try:
        dp.ENERGY_TOL=dp.TIME_TOL=0
        local={s:dp.pareto_dp(groups[s][3],ps) for s,ps in scaled.items()}
        exact=dp.global_pareto(local)
    finally:dp.ENERGY_TOL,dp.TIME_TOL=et,tt
    lookup={p.id:p for ps in base.values() for p in ps}
    lifted=[dp.Label(l.n,math.fsum(lookup[p].energy for p in l.path),math.fsum(lookup[p].time for p in l.path),l.path) for l in exact]
    reduced=dp.prune(lifted)
    original=dp.global_pareto({s:dp.pareto_dp(groups[s][3],available(ps,.2)) for s,ps in base.items()})
    if not (len(reduced)==len(original) and all(any(dp.equivalent(a,b) for b in original) for a in reduced)):
        raise AssertionError('Pareto numerical audit changes the distinct target vectors')
    audit=dict(integer_energy_unit_kwh=1e-12,integer_time_unit_s=1e-9,comparison_tolerance=0,
               integer_objective_vectors=len(exact),distinct_vectors_at_declared_tolerance=len(reduced),
               worst_80_sortie_energy_quantization_kwh=len(boxes)*.5e-12,
               worst_80_sortie_time_quantization_s=len(boxes)*.5e-9,
               original_front_unchanged=True,objectives=[l.record() for l in reduced])
    write_json(out/'pareto_integer_audit.json',audit)
    return report,audit
