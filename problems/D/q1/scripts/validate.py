"""Recompute from original inputs. Never consume a stored `pass` flag."""
from collections import Counter
from pathlib import Path
import csv
import json
import math
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from model.io import ROOT,load_inputs,write_json,provenance
from model.geometry import load_dem,ProjectedRoute


def read_csv(path):
    with Path(path).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))


def independent_geometry(nodes):
    dem=load_dem();origin=nodes['O01'];geometries={};cells={}
    for area,n in sorted(nodes.items()):
        if area=='O01':continue
        route=ProjectedRoute(origin,n,dem)
        touched=route.independent_cells()
        h=max(float(dem.values[r,c]) for r,c in touched)+50
        # AEQD radial distance = GeographicLib geodesic distance to < nanometres.
        geometries[area]=dict(service_area=area,distance_m=route.geod['s12'],max_dem_m=h-50,
                              cruise_altitude_m=h,out_up_m=h-origin.ground_m,
                              out_down_m=h-n.ground_m-30,back_up_m=h-n.ground_m-30,
                              back_down_m=h-origin.ground_m,traversed_cells_count=len(touched))
        cells[area]=touched
    return geometries,cells


def reference_energy(m,g,w,exponent=1.5,back_payload=0,omit_return_climb=False):
    outward_range=m.empty_range_m-(m.empty_range_m-m.full_range_m)*math.pow(w/m.rated_kg,exponent)
    back_range=m.empty_range_m-(m.empty_range_m-m.full_range_m)*math.pow(back_payload/m.rated_kg,exponent)
    cruise=m.battery_kwh*g['distance_m']/outward_range+m.battery_kwh*g['distance_m']/back_range
    ascent=(m.empty_kg+w)*9.81*g['out_up_m']
    if not omit_return_climb:ascent+=(m.empty_kg+back_payload)*9.81*g['back_up_m']
    return cruise+ascent/(m.up_eff*3600000)


def reference_time(m,g,n):
    return (m.prep_s+n*m.load_s+m.handover_s+n*m.handover_box_s+
            (g['out_up_m']+g['back_up_m'])/m.up_mps+
            (g['out_down_m']+g['back_down_m'])/m.down_mps+2*g['distance_m']/m.cruise_mps)


def check_batch(batch,by_id,types,geo,alpha):
    bids=batch['box_ids']
    if not bids or len(set(bids))!=len(bids):raise AssertionError('Empty or duplicate box batch')
    boxes=[by_id[b] for b in bids]
    area=batch['service_area'];m=types[batch['aircraft_type']]
    if any(b.area!=area for b in boxes):raise AssertionError('Cross-service grouping')
    mass=math.fsum(b.mass_kg for b in boxes);volume=math.fsum(b.volume_m3 for b in boxes)
    if mass>m.rated_kg+1e-9:raise AssertionError('Mass capacity')
    if volume>m.volume_m3+1e-12:raise AssertionError('Volume capacity')
    energy=reference_energy(m,geo[area],mass)
    duration=reference_time(m,geo[area],len(boxes))
    if energy>(1-alpha)*m.battery_kwh+1e-10:raise AssertionError('Energy reserve')
    expected=dict(mass_kg=mass,volume_m3=volume,energy_kwh=energy,time_s=duration,return_soc=1-energy/m.battery_kwh)
    for field,want in expected.items():
        tolerance=1e-7 if field=='time_s' else 1e-10
        if field in batch and abs(float(batch[field])-want)>tolerance:
            raise AssertionError(f'Independent {field} recalculation')
    return energy,duration


def validate_batches(batches,types,boxes,geo,alpha=.2):
    counts=Counter(b for p in batches for b in p['box_ids'])
    if counts!=Counter({b.id:1 for b in boxes}):raise AssertionError('Each original box must occur exactly once')
    by_id={b.id:b for b in boxes}
    values=[check_batch(p,by_id,types,geo,alpha) for p in batches]
    return dict(sorties=len(batches),energy_kwh=math.fsum(e for e,t in values),time_s=math.fsum(t for e,t in values))


def independent_safe_payload(m,g,alpha):
    budget=(1-alpha)*m.battery_kwh
    if reference_energy(m,g,0)>budget+1e-10:return None
    if reference_energy(m,g,m.rated_kg)<=budget:return float(m.rated_kg)
    lo,hi=0.,float(m.rated_kg)
    for _ in range(70):
        mid=(lo+hi)/2
        if reference_energy(m,g,mid)<=budget:lo=mid
        else:hi=mid
    return lo


def validate(out):
    out=Path(out);nodes,types,boxes=load_inputs()
    expected=json.loads((ROOT/'data/raw_manifest.json').read_text(encoding='utf-8'))
    if provenance()!=expected:raise AssertionError('Raw input hash mismatch')
    geo,cells=independent_geometry(nodes)
    observed=json.loads((out/'geometry.json').read_text(encoding='utf-8'))
    claimed_cells=json.loads((out/'traversed_cells.json').read_text(encoding='utf-8'))
    for s,g in geo.items():
        if set(map(tuple,claimed_cells[s]))!=cells[s]:raise AssertionError('Incomplete/extra traversed cells')
        for field in g:
            if field=='service_area':continue
            tolerance=1e-7 if field=='distance_m' else 1e-10
            if abs(g[field]-observed[s][field])>tolerance:raise AssertionError(f'Geometry: {s} {field}')
    payload_rows=read_csv(out/'max_safe_payload.csv')
    if len(payload_rows)!=45 or len({(r['service_area'],r['aircraft_type']) for r in payload_rows})!=45:
        raise AssertionError('Incomplete 45-payload table')
    max_root_error=0.
    for row in payload_rows:
        m=types[row['aircraft_type']];g=geo[row['service_area']]
        root=independent_safe_payload(m,g,.2)
        if root is None:
            if row['safe_payload_kg']!='':raise AssertionError('Empty-infeasible payload mislabeled')
        else:
            error=abs(root-float(row['safe_payload_kg']));max_root_error=max(max_root_error,error)
            if error>1e-8:raise AssertionError('Safe payload independent root mismatch')
    batches=read_csv(out/'optimal_batches.csv')
    for b in batches:b['box_ids']=json.loads(b['box_ids'])
    recalculated=validate_batches(batches,types,boxes,geo)
    assignment=read_csv(out/'box_assignment.csv')
    if len(assignment)!=len(boxes):raise AssertionError('Wrong assignment row count')
    expected_pairs={(bid,b['batch_id']) for b in batches for bid in b['box_ids']}
    if {(r['box_id'],r['batch_id']) for r in assignment}!=expected_pairs:
        raise AssertionError('Box assignment and batches disagree')
    by_id={b.id:b for b in boxes};by_batch={b['batch_id']:b for b in batches}
    for r in assignment:
        b=by_id[r['box_id']]
        if r['service_area']!=b.area or r['aircraft_type']!=by_batch[r['batch_id']]['aircraft_type']:
            raise AssertionError('Wrong assignment metadata')
        if float(r['mass_kg'])!=b.mass_kg or float(r['volume_m3'])!=b.volume_m3:
            raise AssertionError('Wrong assignment attributes')
    summary=json.loads((out/'objective_summary.json').read_text(encoding='utf-8'))['lexicographic']
    for field,value in recalculated.items():
        if abs(value-summary[field])>(1e-7 if field=='time_s' else 1e-10):
            raise AssertionError('Objective recalculation mismatch')
    pareto=json.loads((out/'pareto_assignments.json').read_text(encoding='utf-8'))
    for solution in pareto:
        values=validate_batches(solution['batches'],types,boxes,geo)
        for k,v in values.items():
            if abs(v-solution['objective'][k])>(1e-7 if k=='time_s' else 1e-10):
                raise AssertionError('Pareto objective mismatch')
    milp_solutions=0
    for file in sorted((out/'solver_logs').rglob('*.json')):
        for log in json.loads(file.read_text(encoding='utf-8')):
            area=log['service_area']
            local_batches=[dict(p,service_area=area) for p in log['selected']]
            values=validate_batches(local_batches,types,[b for b in boxes if b.area==area],geo)
            for field,key in [('sorties','n'),('energy_kwh','e'),('time_s','t')]:
                if abs(values[field]-log[key])>(1e-7 if field=='time_s' else 1e-10):
                    raise AssertionError('MILP recorded solution independent recalculation')
            milp_solutions+=1
    report=dict(status='VERIFIED_BY_RECOMPUTATION',raw_files=len(expected),boxes=len(boxes),
                geometry_routes=len(geo),payloads=len(payload_rows),max_payload_root_error_kg=max_root_error,
                objective=recalculated,pareto_assignments=len(pareto),milp_solutions_recalculated=milp_solutions,
                checked=['raw_hashes','TIF_MAT','independent_geodesic_cell_intersections','geometry',
                         'safe_payload_roots','exactly_once','no_cross_service','mass','volume','energy',
                         'return_empty_with_climb','full_time','assignment_metadata','objective','pareto_assignments'])
    write_json(out/'validation_report.json',report)
    return report


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'results')
    args=parser.parse_args();print(json.dumps(validate(args.output),ensure_ascii=False,indent=2))
