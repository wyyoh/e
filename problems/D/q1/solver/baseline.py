"""FFD is a heuristic baseline; no claim of global optimality."""
from model.physics import feasible,trip_energy,trip_time
from .dp import Label,scalar_dp
from .patterns import available


def ffd(boxes,types,geo,alpha,order,aircraft=None):
    key=(lambda b:(-b.mass_kg,-b.volume_m3,b.id)) if order=='mass' else (lambda b:(-b.volume_m3,-b.mass_kg,b.id))
    types=[m for m in types.values() if aircraft is None or m.id==aircraft]
    # Explicit heterogeneous policy: largest rated mass, then volume, then type id.
    types=sorted(types,key=lambda m:(-m.rated_kg,-m.volume_m3,m.id))
    bins=[]
    for b in sorted(boxes,key=key):
        for trip in bins:
            if feasible(trip['type'],geo,trip['mass']+b.mass_kg,trip['volume']+b.volume_m3,alpha):
                trip['mass']+=b.mass_kg;trip['volume']+=b.volume_m3;trip['boxes'].append(b.id)
                break
        else:
            m=next((m for m in types if feasible(m,geo,b.mass_kg,b.volume_m3,alpha)),None)
            if m is None:return None
            bins.append(dict(type=m,mass=b.mass_kg,volume=b.volume_m3,boxes=[b.id]))
    return Label(len(bins),sum(trip_energy(b['type'],geo,b['mass']) for b in bins),
                 sum(trip_time(b['type'],geo,len(b['boxes'])) for b in bins))


def compare(groups,patterns,types,geo,alpha):
    rows=[]
    for area,(boxes,kinds,attrs,demand) in groups.items():
        for aircraft in [*types,None]:
            label=scalar_dp(demand,available(patterns[area],alpha,aircraft))
            for method,solution in [('exact',label),('FFD_mass',ffd(boxes,types,geo[area],alpha,'mass',aircraft)),
                                    ('FFD_volume',ffd(boxes,types,geo[area],alpha,'volume',aircraft))]:
                rows.append(dict(service_area=area,aircraft_type=aircraft or 'mixed',method=method,
                                 feasible=solution is not None,sorties=solution.n if solution else None,
                                 energy_kwh=solution.e if solution else None,time_min=solution.t/60 if solution else None))
    totals=[]
    for aircraft in [*types,'mixed']:
        for method in ('exact','FFD_mass','FFD_volume'):
            subset=[r for r in rows if r['aircraft_type']==aircraft and r['method']==method]
            ok=all(r['feasible'] for r in subset)
            totals.append(dict(aircraft_type=aircraft,method=method,feasible=ok,
                               sorties=sum(r['sorties'] for r in subset) if ok else None,
                               energy_kwh=sum(r['energy_kwh'] for r in subset) if ok else None,
                               time_min=sum(r['time_min'] for r in subset) if ok else None))
    return rows,totals
