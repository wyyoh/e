import json
import pytest
from model.io import load_inputs,ROOT
from model.geometry import load_dem,geometry
from solver.patterns import group_boxes,enumerate_patterns,available
from solver.sensitivity import solve_all
from scripts.validate import read_csv


def test_reserve_threshold_boundary():
    nodes,types,boxes=load_inputs();geo,_=geometry(nodes,load_dem(),'aeqd_o01')
    groups=group_boxes(boxes);patterns=enumerate_patterns(groups,types,geo)
    rows=read_csv(ROOT/'results/reserve_thresholds.csv')
    lookup={p.id:p for ps in patterns.values() for p in ps}
    expected={p.rho for p in lookup.values() if 0<p.rho<1}
    assert {float(r['threshold']) for r in rows}==expected
    for row in rows:
        rho,eps=float(row['threshold']),float(row['epsilon'])
        for pid in json.loads(row['pattern_ids']):
            p=lookup[pid]
            assert p in available([p],rho-eps)
            assert p in available([p],rho)
            assert not available([p],rho+eps)
        if row['sorties_change']=='True':
            for field,alpha in [('sorties_left',rho-eps),('sorties_at',rho),('sorties_right',rho+eps)]:
                value=solve_all(groups,patterns,alpha)
                assert (value.n if value else None)==(int(row[field]) if row[field] else None)


def test_reserve_segments_are_complete():
    rows=read_csv(ROOT/'results/reserve_segments.csv')
    assert float(rows[0]['alpha_left'])==0 and float(rows[-1]['alpha_right'])==1
    for a,b in zip(rows,rows[1:]):
        assert a['alpha_right']==b['alpha_left']
        assert a['right_closed']=='True' and b['left_closed']=='False'
        assert not b['min_sorties'] or int(b['min_sorties'])>int(a['min_sorties'])
