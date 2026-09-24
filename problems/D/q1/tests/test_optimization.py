from copy import deepcopy
from dataclasses import replace
import json
import pytest
from model.io import load_inputs,ROOT
from model.geometry import load_dem,geometry
from solver.patterns import group_boxes,enumerate_patterns,available,assign_ids
from solver.dp import Label,scalar_dp,pareto_dp,global_pareto
from solver.milp import solve_area,box_patterns
from scripts.validate import validate_batches,check_batch,reference_energy,reference_time


@pytest.fixture(scope='module')
def instance():
    nodes,types,boxes=load_inputs();geo,_=geometry(nodes,load_dem(),'aeqd_o01')
    groups=group_boxes(boxes);patterns=enumerate_patterns(groups,types,geo)
    combined=Label()
    for s,g in groups.items():combined=combined.combine(scalar_dp(g[3],available(patterns[s],.2)))
    lookup={p.id:p for ps in patterns.values() for p in ps}
    batches=assign_ids(combined,lookup,groups)
    return types,boxes,geo,groups,patterns,combined,batches


def test_box_exactly_once(instance):
    _,boxes,_,_,_,_,batches=instance
    ids=[i for b in batches for i in b['box_ids']]
    assert len(ids)==len(set(ids))==len(boxes)
    assert set(ids)=={b.id for b in boxes}


def test_no_cross_service_grouping(instance):
    _,boxes,_,_,_,_,batches=instance;by_id={b.id:b for b in boxes}
    for p in batches:assert {by_id[i].area for i in p['box_ids']}=={p['service_area']}


def test_mass_capacity(instance):
    types,boxes,_,_,_,_,batches=instance;by_id={b.id:b for b in boxes}
    for p in batches:assert sum(by_id[i].mass_kg for i in p['box_ids'])<=types[p['aircraft_type']].rated_kg


def test_volume_capacity(instance):
    types,boxes,_,_,_,_,batches=instance;by_id={b.id:b for b in boxes}
    for p in batches:assert sum(by_id[i].volume_m3 for i in p['box_ids'])<=types[p['aircraft_type']].volume_m3+1e-12


def test_energy_reserve(instance):
    types,boxes,geo,_,_,_,batches=instance
    for p in batches:
        m=types[p['aircraft_type']]
        assert reference_energy(m,geo[p['service_area']],p['mass_kg'])<=.8*m.battery_kwh+1e-10


def test_objective_recalculation(instance):
    types,boxes,geo,_,_,opt,batches=instance
    v=validate_batches(batches,types,boxes,geo)
    assert v['sorties']==opt.n
    assert abs(v['energy_kwh']-opt.e)<=1e-10
    assert abs(v['time_s']-opt.t)<=1e-7


def test_milp_vs_dp(instance):
    types,boxes,geo,groups,patterns,_,_=instance
    for s,g in groups.items():
        logs=solve_area(g[0],types,geo[s],.2)
        opt=scalar_dp(g[3],available(patterns[s],.2))
        mint=scalar_dp(g[3],available(patterns[s],.2),'time')
        assert opt.n==logs[0]['n']
        assert abs(opt.e-logs[1]['e'])<=1e-10
        assert abs(opt.t-logs[2]['t'])<=1e-7
        assert abs(mint.t-logs[3]['t'])<=1e-7
        assert all(l['status']==0 and l['mip_gap']==0 for l in logs)


def test_pattern_enumeration_completeness(instance):
    types,_,geo,groups,patterns,_,_=instance
    for s,g in groups.items():
        raw=box_patterns(g[0],types,geo[s],.2)
        recovered={(p['aircraft'],tuple(sum(g[0][j].kind==k for j in p['indices']) for k in g[1])) for p in raw}
        assert recovered=={(p.aircraft,p.counts) for p in available(patterns[s],.2)}


@pytest.mark.parametrize('mutation',['cross_service','duplicate','linear_energy','omit_back_climb','loaded_return','wrong_time'])
def test_negative_assignment_and_physics(instance,mutation):
    types,boxes,geo,_,_,_,original=instance;batches=deepcopy(original)
    if mutation=='duplicate':batches[0]['box_ids'].append(batches[0]['box_ids'][0])
    elif mutation=='cross_service':
        j=next(j for j in range(1,len(batches)) if batches[j]['service_area']!=batches[0]['service_area'])
        batches[0]['box_ids'][0],batches[j]['box_ids'][0]=batches[j]['box_ids'][0],batches[0]['box_ids'][0]
    else:
        p=batches[0];m=types[p['aircraft_type']];g=geo[p['service_area']]
        if mutation=='wrong_time':p['time_s']-=m.prep_s
        else:
            kwargs=({'exponent':1} if mutation=='linear_energy' else {'omit_return_climb':True}
                    if mutation=='omit_back_climb' else {'back_payload':p['mass_kg']})
            p['energy_kwh']=reference_energy(m,g,p['mass_kg'],**kwargs)
    with pytest.raises(AssertionError):validate_batches(batches,types,boxes,geo)


def test_negative_mass_only_ignores_volume(instance):
    types,boxes,geo,*_=instance
    bs=[b for b in boxes if b.area=='S001' and b.kind=='生活卫生用品']
    assert sum(b.mass_kg for b in bs)<=types['A'].rated_kg
    assert sum(b.volume_m3 for b in bs)>types['A'].volume_m3
    p=dict(service_area='S001',aircraft_type='A',box_ids=[b.id for b in bs])
    with pytest.raises(AssertionError,match='Volume'):check_batch(p,{b.id:b for b in boxes},types,geo,.2)


def test_pareto_not_just_fixed_N(instance):
    _,_,_,groups,patterns,lex,_=instance
    fronts={s:pareto_dp(g[3],available(patterns[s],.2)) for s,g in groups.items()}
    front=global_pareto(fronts)
    assert front[0].n==lex.n and abs(front[0].e-lex.e)<1e-10
    # Do not assert a historical vector here: independently compare min energy and min time.
    assert min(l.e for l in front)==pytest.approx(sum(min(l.e for l in f) for f in fronts.values()),abs=1e-10)
    assert min(l.t for l in front)==pytest.approx(sum(scalar_dp(g[3],available(patterns[s],.2),'time').t for s,g in groups.items()),abs=1e-7)


def test_repeated_count_pattern_binary_copies(instance):
    types,boxes,geo,*_=instance
    local=[b for b in boxes if b.area=='S001' and b.kind=='饮用水'][:5]
    # A cannot carry two 14kg boxes; the identical singleton pattern must repeat.
    logs=solve_area(local,{'A':types['A']},geo['S001'],.2)
    assert all(l['n']==len(local) for l in logs)
    assert {b for p in logs[0]['selected'] for b in p['box_ids']}=={b.id for b in local}


def test_time_limit_not_infeasible(instance,monkeypatch):
    import importlib
    from types import SimpleNamespace
    module=importlib.import_module('solver.milp')
    types,boxes,geo,*_=instance
    monkeypatch.setattr(module,'milp',lambda *args,**kwargs:SimpleNamespace(
        status=1,success=False,message='Time limit',x=None,fun=None,mip_gap=None,mip_dual_bound=0.,mip_node_count=0))
    with pytest.raises(module.SolverFailure) as exc:
        module.solve_area([boxes[0]],types,geo['S001'],.2)
    assert exc.value.logs[0]['status']==1
    assert not exc.value.logs[0]['success']
