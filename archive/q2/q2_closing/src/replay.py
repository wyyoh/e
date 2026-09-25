"""Independent replay from original XLSX and freshly reconstructed DEM table.
Does not import the optimizer, its job evaluator or its scheduling decoder.
"""
from common import ROOT,load,save,table
from raw_audit import spreadsheet_inputs
from collections import Counter,defaultdict
import csv,math,argparse

def verify(plan):
    data=spreadsheet_inputs();boxes=data['boxes'];types=data['types'];nodes=data['nodes'];geo={}
    with (ROOT/'results/raw_geometry.csv').open(encoding='utf-8',newline='') as f:
        for r in csv.DictReader(f):geo[r['origin'],r['destination']]=geo[r['destination'],r['origin']]=(float(r['distance_m']),float(r['max_dem_m']))
    jobs=plan['flights'] if isinstance(plan,dict) else plan;checks=[];failures=[]
    def ck(name,yes):
        checks.append(name)
        if not yes:failures.append(name)
    ck('80 original boxes exactly once',Counter(b for j in jobs for b in j['box_ids'])==Counter(boxes.keys()))
    ck('unique flight identifiers',len({j['flight_id'] for j in jobs})==len(jobs))
    ac=defaultdict(list);ba=defaultdict(list);delivery=[];flights=[];legs=[];phases=[]
    for j in jobs:
        fid=j['flight_id'];t=types[j['type']];ids=j['box_ids'];route=j['route']
        if route[0]!='O01':route=['O01']+route+['O01']
        ck(fid+' route endpoints',route[0]==route[-1]=='O01')
        ck(fid+' route delivery sites',set(route[1:-1])=={boxes[b]['site'] for b in ids})
        ck(fid+' route no duplicate delivery',len(set(route[1:-1]))==len(route)-2)
        ck(fid+' aircraft type',j['aircraft'] in t['aircraft']);ck(fid+' battery type',j['battery'] in [f"{j['type']}-BAT{k+1:02d}" for k in range(t['battery_count'])])
        q=sum(boxes[b]['mass_kg'] for b in ids);volume=sum(round(boxes[b]['volume_m3']*1000) for b in ids)/1000
        ck(fid+' mass',q<=t['max_payload_kg']);ck(fid+' volume',volume<=t['max_volume_m3']+1e-12)
        start=j['start_s'];ck(fid+' nonnegative start',math.isfinite(start) and start>=-1e-7)
        now=start;energy_j=0.;prep=t['prep_s']+len(ids)*t['load_per_box_s']
        phases.append(dict(flight_id=fid,kind='prepare_load',start_s=now,end_s=now+prep));now+=prep;takeoff=now
        for k,(a,b) in enumerate(zip(route,route[1:])):
            dist,z=geo[a,b];up=z+50-nodes[a]['work_z'];down=z+50-nodes[b]['work_z']
            ck(fid+f' leg{k} heights',up>=0 and down>=0)
            if b=='O01':ck(fid+' empty return departure',q==0)
            length=t['empty_range_m']-(t['empty_range_m']-t['full_range_m'])*math.sqrt((q/t['max_payload_kg'])**3)
            # Reconstruct Joules through calibrated cruise power and flight time.
            watts=t['battery_kwh']*3600000*t['cruise_mps']/length
            cruise=dist/t['cruise_mps'];climb=(t['empty_mass_kg']+q)*9.81*up/t['up_efficiency']
            e=watts*cruise+climb;energy_j+=e;begin=now
            for kind,dt in [('climb',up/t['up_mps']),('cruise',cruise),('descent',down/t['down_mps'])]:
                phases.append(dict(flight_id=fid,leg=k,kind=kind,start_s=now,end_s=now+dt));now+=dt
            legs.append(dict(flight_id=fid,leg=k,origin=a,destination=b,payload_kg=q,distance_m=dist,max_dem_m=z,up_m=up,down_m=down,departure_s=begin,arrival_s=now,energy_kwh=e/3600000))
            if b!='O01':
                drops=[bid for bid in ids if boxes[bid]['site']==b];hand=t['handover_base_s']+len(drops)*t['handover_per_box_s']
                phases.append(dict(flight_id=fid,leg=k,kind='handover',start_s=now,end_s=now+hand));now+=hand
                for bid in drops:
                    box=boxes[bid];hard=box['hard_deadline_s'];late=max(0,now-box['expected_delivery_s'])
                    ck(bid+' zero weighted lateness',late<=1e-7)
                    if hard is not None:ck(bid+' hard deadline',now<=hard+1e-7)
                    delivery.append(dict(box_id=bid,service_area=b,flight_id=fid,aircraft=j['aircraft'],battery=j['battery'],delivery_s=now,expected_delivery_s=box['expected_delivery_s'],hard_deadline_s=hard,hard_slack_s=hard-now if hard is not None else None,expected_slack_s=box['expected_delivery_s']-now,weighted_tardiness_s=box['priority']*late))
                q-=sum(boxes[bid]['mass_kg'] for bid in drops)
        energy=energy_j/3600000;soc=1-energy/t['battery_kwh'];ck(fid+' final empty',q==0)
        ck(fid+' reserve',soc>=t['reserve_pct']/100-1e-10)
        # Integral over both constant charging-rate intervals, independently coded.
        fast=max(0,min(.9,1)-soc)*t['charge_full_s']*.65/.9
        slow=(1-max(.9,soc))*t['charge_full_s']*.35/.1
        charge=fast+slow
        for name,actual in [('energy_kwh',energy),('return_s',now),('return_soc',soc),('takeoff_s',takeoff),('charge_end_s',now+charge),('duration_s',now-start),('volume_m3',volume)]:
            if name in j:ck(fid+' binding '+name,math.isfinite(j[name]) and abs(j[name]-actual)<(1e-7 if name.endswith('_s') else 1e-9))
        ac[j['aircraft']].append((start,now,fid));ba[j['battery']].append((start,now+charge,fid))
        flights.append(dict(flight_id=fid,type=j['type'],aircraft=j['aircraft'],battery=j['battery'],route=route,box_ids=ids,start_s=start,takeoff_s=takeoff,return_s=now,charge_end_s=now+charge,charge_s=charge,energy_kwh=energy,return_soc=soc,work_s=now-start))
    for kind,groups in [('aircraft',ac),('battery',ba)]:
        for rid,chain in groups.items():
            chain.sort()
            for a,b in zip(chain,chain[1:]):ck(kind+' '+rid+' '+a[2]+' before '+b[2],a[1]<=b[0]+1e-7)
    metrics=dict(makespan_s=max(f['return_s'] for f in flights),energy_kwh=sum(f['energy_kwh'] for f in flights),sorties=len(flights),type_sorties=dict(Counter(f['type'] for f in flights)),weighted_tardiness_s=sum(b['weighted_tardiness_s'] for b in delivery),late_boxes=sum(b['expected_slack_s'] < -1e-7 for b in delivery),minimum_hard_deadline_slack_s=min(b['hard_slack_s'] for b in delivery if b['hard_slack_s'] is not None),minimum_expected_deadline_slack_s=min(b['expected_slack_s'] for b in delivery),minimum_return_soc=min(f['return_soc'] for f in flights),used_aircraft=len(ac),used_batteries=len(ba))
    if isinstance(plan,dict) and 'claimed_makespan_s' in plan:ck('claimed makespan',abs(plan['claimed_makespan_s']-metrics['makespan_s'])<1e-7)
    return dict(checks=len(checks),failed=len(failures),failures=failures,metrics=metrics),flights,delivery,legs,phases

def main():
    p=argparse.ArgumentParser();p.add_argument('name',nargs='?',default='baseline');a=p.parse_args()
    result,flights,delivery,legs,phases=verify(load(ROOT/f'results/{a.name}_incumbent.json'))
    save(ROOT/f'results/{a.name}_replay.json',result)
    for suffix,rows in [('replayed_flights',flights),('box_assignment',delivery),('replayed_legs',legs),('phases',phases)]:save(ROOT/f'results/{a.name}_{suffix}.json',rows)
    table(ROOT/f'results/{a.name}_deadline_slack.csv',delivery)
    print(result);assert result['failed']==0
if __name__=='__main__':main()
