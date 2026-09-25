import copy,math,csv,itertools
import pytest
from common import ROOT,load,inputs
from physics import Model,partition_bound
from replay import verify
from raw_audit import spreadsheet_inputs,Raster,Curve
from pyproj import CRS,Transformer
from search import workload_master,internal_check

@pytest.fixture(scope='module')
def baseline():return load(ROOT/'results/baseline_incumbent.json')

def test_baseline_recomputed(baseline):
    r,*_=verify(baseline);assert r['failed']==0
    assert r['metrics']['makespan_s']==pytest.approx(5693.231489105106,abs=1e-7)
    assert r['metrics']['energy_kwh']==pytest.approx(66.22567019577254,abs=1e-9)

def test_best_dual_logic():
    p=load(ROOT/'results/best_incumbent.json');internal_check(p['flights'],Model(inputs()));r,*_=verify(p);assert r['failed']==0

def test_raw_parameters():
    raw=spreadsheet_inputs();canonical=inputs()
    for key in ['boxes','types','nodes']:
        for i,r in raw[key].items():
            for field,v in r.items():assert canonical[key][i][field]==v

@pytest.mark.parametrize('origin,destination',[('O01','S003'),('S007','S003'),('S012','S014'),('S002','S013')])
def test_dem_continuous_full_traversal(origin,destination):
    d=spreadsheet_inputs();o=d['nodes']['O01'];dem=Raster();crs=CRS.from_proj4(f"+proj=aeqd +lat_0={o['lat']} +lon_0={o['lon']} +datum=WGS84 +units=m")
    curve=Curve(d['nodes'][origin],d['nodes'][destination],o,dem,Transformer.from_crs(4326,crs,always_xy=True),Transformer.from_crs(crs,4326,always_xy=True))
    a=curve.cells();b=curve.strip_cells();assert a==b
    assert dem.max(a)==inputs()['geo'][origin,destination][1]

def test_fixed_B_partition_bound(baseline):
    assert partition_bound(baseline['flights'],inputs()['types'])['B']==pytest.approx(baseline['claimed_makespan_s'],abs=1e-8)

def test_workload_master_contains_baseline(baseline):
    d=inputs();p,ids,log=workload_master(baseline['flights'],[],d['types'],baseline['claimed_makespan_s']+1e-5,23,10,[])
    assert p is not None and len(p)==23,log

def test_volume_prevents_all_B_to_A(baseline):
    m=Model(inputs())
    for j in baseline['flights']:
        if j['type']=='B':assert 'volume' in m.job('A',j['box_ids'],j['route'])['failures']

@pytest.mark.parametrize('mutant',['duplicate','omit','return_time','energy','return_climb','return_loaded','aircraft_overlap','battery_overlap','short_charge','late','volume','forged_pass'])
def test_independent_replay_rejects_mutations(baseline,mutant):
    p=copy.deepcopy(baseline);jobs=p['flights'];j=jobs[0]
    if mutant=='duplicate':j['box_ids'].append(j['box_ids'][0])
    elif mutant=='omit':j['box_ids'].pop()
    elif mutant=='return_time':j['return_s']-=1
    elif mutant=='energy':j['energy_kwh']*=.9
    elif mutant=='return_climb':
        t=inputs()['types'][j['type']];j['energy_kwh']-=t['empty_mass_kg']*9.81*j['legs'][-1]['up_m']/(t['up_efficiency']*3600000)
    elif mutant=='return_loaded':j['energy_kwh']+=.1
    elif mutant=='aircraft_overlap':jobs[1]['aircraft']=j['aircraft']
    elif mutant=='battery_overlap':jobs[1]['battery']=j['battery']
    elif mutant=='short_charge':j['charge_end_s']-=10
    elif mutant=='late':j['start_s']+=10000
    elif mutant=='volume':
        j=next(x for x in jobs if x['type']=='B');j['type']='A';j['aircraft']='U01';j['battery']='A-BAT01'
    elif mutant=='forged_pass':j['return_s']-=10;p['pass']=True;p['independent_validation']={'failed':0}
    result,*_=verify(p);assert result['failed']>0

def test_22_witness_if_present():
    path=ROOT/'results/feasible_22_incumbent.json'
    if not path.exists():pytest.skip('No 22-flight witness found in bounded search')
    p=load(path);r,*_=verify(p);assert r['failed']==0 and r['metrics']['sorties']==22
