from pathlib import Path
import sys, json, hashlib, copy, math
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'));sys.path.insert(0,str(ROOT/'code_v4'))
from precompute import load
from pool_master import routekey,highs_run
from joint_solver import Model,color_intervals
from split_atoms import refine

def test_pattern_identity_ignores_box_order_but_preserves_stop_order():
 a={'type':'C','boxes':['b','a'],'route':['S001','S002']};assert routekey(a)==routekey({**a,'boxes':['a','b']});assert routekey(a)!=routekey({**a,'route':['S002','S001']})

def test_backend_solves_integer_not_lp_relaxation(tmp_path):
 m=Model();x=m.var('x',hi=4,integer=True);m.row({x:1},lo=1.2);sol,status=highs_run(m,np.array([1.]),10,tmp_path/'highs.log');assert status['model_status'].endswith('kOptimal');assert abs(sol[x]-2)<1e-9

def test_bad_mip_start_rejected(tmp_path):
 m=Model();x=m.var('x',hi=4,integer=True);m.row({x:1},lo=2);sol,status=highs_run(m,np.array([1.]),10,tmp_path/'highs.log',start=[0]);assert status['mip_start_used'] is False;assert abs(sol[x]-2)<1e-9

def test_backend_infeasibility_is_not_a_solution(tmp_path):
 m=Model();x=m.var('x',hi=1,integer=True);m.row({x:1},lo=2);sol,status=highs_run(m,np.array([1.]),10,tmp_path/'highs.log');assert sol is None;assert status['model_status'].endswith('kInfeasible')

def test_half_open_resources_and_inventory():
 labels=color_intervals([(0,0.,1.),(1,1.,2.)],1);assert labels[0]==labels[1]
 with pytest.raises(ValueError):color_intervals([(0,0.,2.),(1,1.,3.)],1)

@pytest.mark.parametrize('dt',[15.,30.,120.])
def test_certified_atom_refinement_preserves_coverage(dt):
 d=load(ROOT/'experiments_v3/cargo_joint/energy_polish/precomputed.json');old=copy.deepcopy(d);r=refine(d,dt);assert d==old;assert r['input_identity']==d['input_identity'];assert r['phases']==d['phases'];assert r['certificate_point_events']==d['certificate_point_events'];assert r['cache_key']!=d['cache_key']
 for phase in range(len(d['phases'])):
  before=[v for v in d['rows'] if v['phase']==phase];after=[v for v in r['rows'] if v['phase']==phase];assert abs(before[0]['a']-after[0]['a'])<1e-9;assert abs(before[-1]['b']-after[-1]['b'])<1e-9
  for a,b in zip(after[:-1],after[1:]):assert abs(a['b']-b['a'])<1e-8
  for row in after:
   parents=[p for p in before if p['a']<=row['a']+1e-8 and p['b']>=row['b']-1e-8];assert any(p['available']==row['available'] for p in parents)
   if not row['available'][0] and sum(row['available'][1:])>1:assert row['b']-row['a']<=dt+1e-8
 covered={rid for q in r['compact'] for rid in q['row_ids']};assert covered=={i for i,q in enumerate(r['rows']) if not q['available'][0]}

def test_original_frozen_selection_not_replaced():
 r=load(ROOT/'release_final/primary/selected.json');assert abs(r['makespan_s']-6340.439338658365)<1e-10;assert abs(r['total_energy_kwh']-69.30853085578303)<1e-10;assert len(r['decisions'])==23 and len(r['active_jobs'])==4
