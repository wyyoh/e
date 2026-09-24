from dataclasses import replace
import numpy as np
import pytest
from model.io import load_inputs
from model.geometry import geometry,load_dem
from model.physics import equivalent_range,trip_energy,energy_parts,trip_time,safe_payload,bisection_payload


@pytest.fixture(scope='module')
def instance():
    nodes,types,boxes=load_inputs();geo,_=geometry(nodes,load_dem(),'aeqd_o01')
    return types,geo


def reference_energy(m,g,w,exponent=1.5,return_payload=0,omit_back_climb=False):
    # Independent expression, does not invoke model.physics.
    L=lambda q:m.empty_range_m-(m.empty_range_m-m.full_range_m)*(q/m.rated_kg)**exponent
    horiz=m.battery_kwh*g['distance_m']*(1/L(w)+1/L(return_payload))
    grav=(m.empty_kg+w)*9.81*g['out_up_m']/(m.up_eff*3600000)
    if not omit_back_climb:grav+=(m.empty_kg+return_payload)*9.81*g['back_up_m']/(m.up_eff*3600000)
    return horiz+grav


def test_range_at_empty(instance):
    for m in instance[0].values():assert equivalent_range(m,0)==m.empty_range_m


def test_range_at_full(instance):
    for m in instance[0].values():assert equivalent_range(m,m.rated_kg)==m.full_range_m


def test_range_monotonic(instance):
    for m in instance[0].values():
        assert np.all(np.diff([equivalent_range(m,q) for q in np.linspace(0,m.rated_kg,101)])<0)


def test_range_formula_3_over_2(instance):
    for m in instance[0].values():
        assert equivalent_range(m,m.rated_kg/4)==m.empty_range_m-(m.empty_range_m-m.full_range_m)/8


def test_energy_at_empty(instance):
    for m in instance[0].values():
        for g in instance[1].values():
            assert trip_energy(m,g,0)==pytest.approx(reference_energy(m,g,0),abs=1e-12)
            assert energy_parts(m,g,0)['back_horizontal_kwh']>0
            assert energy_parts(m,g,0)['back_climb_kwh']>0


def test_energy_monotonicity(instance):
    for m in instance[0].values():
        for g in instance[1].values():
            assert np.all(np.diff([trip_energy(m,g,q) for q in np.linspace(0,m.rated_kg,101)])>0)


def test_safe_payload_root(instance):
    for m in instance[0].values():
        for g in instance[1].values():
            for alpha in (.05,.2,.4,.99):
                r=safe_payload(m,g,alpha);b=bisection_payload(m,g,alpha)
                if b is None:assert not r['empty_trip_feasible'];continue
                assert r['safe_payload_kg']==pytest.approx(b,abs=1e-8)
                assert reference_energy(m,g,b) <= (1-alpha)*m.battery_kwh+1e-10
                if r['energy_limited']:
                    assert abs(reference_energy(m,g,b)-(1-alpha)*m.battery_kwh)<1e-10


def test_return_empty_payload(instance):
    for m in instance[0].values():
        for g in instance[1].values():
            a,b=energy_parts(m,g,0),energy_parts(m,g,m.rated_kg)
            assert a['back_horizontal_kwh']==b['back_horizontal_kwh']
            assert a['back_climb_kwh']==b['back_climb_kwh']


def test_trip_time(instance):
    for m in instance[0].values():
        for g in instance[1].values():
            expected=m.prep_s+5*m.load_s+m.handover_s+5*m.handover_box_s
            expected+=(g['out_up_m']+g['back_up_m'])/m.up_mps
            expected+=(g['out_down_m']+g['back_down_m'])/m.down_mps+2*g['distance_m']/m.cruise_mps
            assert trip_time(m,g,5)==pytest.approx(expected,abs=1e-10)


@pytest.mark.parametrize('mutation', ['linear','omit_return_climb','loaded_return'])
def test_negative_energy_mutations(instance,mutation):
    m=instance[0]['C'];g=instance[1]['S001'];w=m.rated_kg/2
    opts={'exponent':1} if mutation=='linear' else {'omit_back_climb':True} if mutation=='omit_return_climb' else {'return_payload':w}
    corrupted=reference_energy(m,g,w,**opts)
    with pytest.raises(AssertionError):
        assert abs(corrupted-trip_energy(m,g,w)) <= 1e-10
