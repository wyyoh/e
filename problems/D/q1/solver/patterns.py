"""Complete count patterns; identical attributes are interchangeable only within a service."""
from dataclasses import dataclass,asdict
from itertools import product
from collections import Counter
import math
from model.physics import trip_energy,trip_time,THRESHOLD_TOL,VOLUME_TOL


@dataclass(frozen=True)
class Pattern:
    id: str
    area: str
    aircraft: str
    counts: tuple
    mass: float
    volume: float
    energy: float
    time: float
    rho: float

    def record(self,kinds,alpha):
        return dict(pattern_id=self.id,service_area=self.area,aircraft_type=self.aircraft,
                    counts=dict(zip(kinds,self.counts)),n_boxes=sum(self.counts),mass_kg=self.mass,
                    volume_m3=self.volume,energy_kwh=self.energy,time_s=self.time,
                    max_reserve=self.rho,feasible_at_reserve=alpha<=self.rho+THRESHOLD_TOL)


def group_boxes(boxes):
    groups={}
    for area in sorted({b.area for b in boxes}):
        local=sorted((b for b in boxes if b.area==area),key=lambda b:b.id)
        kinds=tuple(sorted({b.kind for b in local}))
        attributes={}
        for b in local:
            if b.kind in attributes and attributes[b.kind]!=(b.mass_kg,b.volume_m3):
                raise ValueError('Unequal attributes cannot be compressed into one kind')
            attributes[b.kind]=(b.mass_kg,b.volume_m3)
        demand=tuple(sum(b.kind==k for b in local) for k in kinds)
        groups[area]=(local,kinds,attributes,demand)
    return groups


def enumerate_patterns(groups,types,geo):
    patterns={}
    for area,(_,kinds,attributes,demand) in groups.items():
        local=[]
        for counts in product(*(range(n+1) for n in demand)):
            if not sum(counts):continue
            mass=math.fsum(c*attributes[k][0] for k,c in zip(kinds,counts))
            volume=math.fsum(c*attributes[k][1] for k,c in zip(kinds,counts))
            for m in types.values():
                if mass>m.rated_kg or volume>m.volume_m3+VOLUME_TOL:continue
                energy=trip_energy(m,geo[area],mass)
                pid=area+'-'+m.id+'-'+'.'.join(map(str,counts))
                local.append(Pattern(pid,area,m.id,counts,mass,volume,energy,
                                     trip_time(m,geo[area],sum(counts)),1-energy/m.battery_kwh))
        patterns[area]=sorted(local,key=lambda p:p.id)
    return patterns


def available(patterns,alpha,aircraft=None):
    return [p for p in patterns if alpha<=p.rho+THRESHOLD_TOL and (aircraft is None or p.aircraft==aircraft)]


def assign_ids(label,lookup,groups):
    """Deterministic lift of count-pattern solution to the original box identifiers."""
    remaining={s:{k:sorted(b.id for b in data[0] if b.kind==k) for k in data[1]}
               for s,data in groups.items()}
    batches=[]
    for j,pid in enumerate(sorted(label.path),1):
        p=lookup[pid]
        chosen=[]
        for k,count in zip(groups[p.area][1],p.counts):
            chosen.extend(remaining[p.area][k][:count])
            del remaining[p.area][k][:count]
        if len(chosen)!=sum(p.counts):raise AssertionError('Invalid pattern reconstruction')
        batches.append(dict(batch_id=f'Q1-{j:03d}',service_area=p.area,aircraft_type=p.aircraft,
                            box_ids=sorted(chosen),mass_kg=p.mass,volume_m3=p.volume,
                            energy_kwh=p.energy,time_s=p.time,return_soc=p.rho,pattern_id=p.id))
    if any(ids for area in remaining.values() for ids in area.values()):
        raise AssertionError('Incomplete assignment')
    return batches
