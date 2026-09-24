"""Independent full box-subset enumeration + binary set partitioning / HiGHS."""
import math
import time
import numpy as np
from scipy.sparse import csc_matrix, vstack
from scipy.optimize import milp, Bounds, LinearConstraint
from model.physics import feasible,trip_energy,trip_time,ENERGY_TOL


def box_patterns(boxes,types,geo,alpha):
    out=[]
    # All nonempty box masks, no dominance reduction or FFD seed restriction.
    for mask in range(1,1<<len(boxes)):
        indices=[j for j in range(len(boxes)) if mask>>j&1]
        mass=math.fsum(boxes[j].mass_kg for j in indices)
        volume=math.fsum(boxes[j].volume_m3 for j in indices)
        for m in types.values():
            if feasible(m,geo,mass,volume,alpha):
                out.append(dict(mask=mask,indices=indices,aircraft=m.id,
                                energy=trip_energy(m,geo,mass),time=trip_time(m,geo,len(indices))))
    return out


def solve_area(boxes,types,geo,alpha,time_limit=300,box_level=False):
    raw_patterns=box_patterns(boxes,types,geo,alpha)
    area=geo['service_area']
    # Exact symmetry quotient: derive type counts from independently enumerated
    # box masks, then introduce binary copies (not unrestricted binary y per
    # count pattern). At most min_k demand_k/count_k copies can be used.
    kinds=sorted({b.kind for b in boxes})
    demand=np.array([sum(b.kind==k for b in boxes) for k in kinds])
    if box_level:
        patterns=raw_patterns;target=np.ones(len(boxes))
    else:
        unique={}
        for p in raw_patterns:
            counts=tuple(sum(boxes[j].kind==k for j in p['indices']) for k in kinds)
            unique[(p['aircraft'],counts)]=dict(p,counts=counts)
        patterns=[]
        for key,p in sorted(unique.items()):
            limit=min(d//c for d,c in zip(demand,p['counts']) if c)
            patterns.extend(dict(p,copy_index=j) for j in range(limit))
        target=demand.astype(float)
    if not patterns:raise RuntimeError(f'No feasible nonempty patterns: {area}')
    row=[];col=[];values=[]
    for j,p in enumerate(patterns):
        for i,value in ([(i,1) for i in p['indices']] if box_level else enumerate(p['counts'])):
            if value:row.append(i);col.append(j);values.append(value)
    A=csc_matrix((values,(row,col)),shape=(len(target),len(patterns)))
    ones=np.ones(len(patterns));energy=np.array([p['energy'] for p in patterns]);duration=np.array([p['time'] for p in patterns])
    logs=[]

    def solve(stage,c,n=None,e=None):
        mats=[A];lb=[target];ub=[target]
        if n is not None:
            mats.append(csc_matrix(ones[None,:]));lb.append([n]);ub.append([n])
        if e is not None:
            # Scale kWh -> mWh so solver feasibility tolerance is far below 1e-10 kWh.
            mats.append(csc_matrix(energy[None,:]*1e6));lb.append([-np.inf]);ub.append([(e+ENERGY_TOL)*1e6])
        matrix=vstack(mats,format='csc')
        started=time.perf_counter()
        print(f'  {area} {stage}: {len(patterns)} binary variables',flush=True)
        result=milp(c,integrality=np.ones(len(patterns)),bounds=Bounds(0,1),
                    constraints=LinearConstraint(matrix,np.concatenate(lb),np.concatenate(ub)),
                    options={'time_limit':time_limit,'mip_rel_gap':0.0,'presolve':True})
        elapsed=time.perf_counter()-started
        picked=np.flatnonzero(result.x>.5) if result.x is not None else []
        selected=[patterns[j] for j in picked]
        log=dict(service_area=area,stage=stage,status=int(result.status),message=str(result.message),
                 success=bool(result.success),mip_gap=getattr(result,'mip_gap',None),
                 dual_bound=getattr(result,'mip_dual_bound',None),objective_value=getattr(result,'fun',None),
                 objective_scale=1e6 if stage=='fixed_N_min_E' else 1,
                 variables=len(patterns),constraints=matrix.shape[0],runtime_s=elapsed,
                 formulation='box_set_partitioning' if box_level else 'exact_symmetry_quotient_binary_copies',
                 raw_box_subset_patterns=len(raw_patterns),
                 time_limit_s=time_limit,mip_node_count=getattr(result,'mip_node_count',None),
                 selected=[dict(aircraft_type=p['aircraft'],box_ids=[boxes[k].id for k in p['indices']]) for p in selected],
                 n=len(selected),e=math.fsum(p['energy'] for p in selected),t=math.fsum(p['time'] for p in selected))
        logs.append(log)
        if result.status!=0 or not result.success:
            raise SolverFailure(logs)  # status 1 never converted into infeasibility
        cover=np.asarray(A[:,picked].sum(axis=1)).ravel()
        if not np.array_equal(cover,target):raise AssertionError('MILP exact cover check failed')
        # Lift selected count patterns to original box IDs; this is a bijection
        # modulo interchangeable labels, with identical mass, volume, energy/time.
        if not box_level:
            pool={k:sorted(b.id for b in boxes if b.kind==k) for k in kinds}
            assigned=[]
            for p in selected:
                bids=[]
                for k,count in zip(kinds,p['counts']):
                    bids.extend(pool[k][:count]);del pool[k][:count]
                assigned.append(dict(aircraft_type=p['aircraft'],box_ids=bids))
            if any(pool.values()):raise AssertionError('Unassigned box after exact lifting')
            log['selected']=assigned
        if n is not None and len(selected)!=n:raise AssertionError('Fixed N violated')
        if e is not None and log['e']>e+ENERGY_TOL+1e-12:raise AssertionError('Lexicographic energy bound violated')
        return log

    first=solve('min_N',ones)
    second=solve('fixed_N_min_E',energy*1e6,n=first['n'])
    third=solve('fixed_N_E_min_T',duration,n=first['n'],e=second['e'])
    fourth=solve('min_T',duration)
    return logs


class SolverFailure(RuntimeError):
    def __init__(self,logs):
        self.logs=logs
        super().__init__('MILP not proven optimal; inspect status, bound and gap in logs')
