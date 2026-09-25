"""Independent feasible-upper-bound verifier, not importing optimization code.
Recomputes all route legs, unloads, complete handovers, energy and charge from
raw numeric inputs. First-stage zero lateness and original hard deadlines must
both hold. Verification tolerances are explicit; no integer-time stretching.
"""
from pathlib import Path
from collections import Counter,defaultdict
import json,math,argparse
ROOT=Path(__file__).resolve().parents[1]

def verify(path):
    dat=json.loads((ROOT/'data/instance.json').read_text());B={r[0]:dict(zip(dat['box_fields'],r)) for r in dat['boxes']};types={g['id']:g for g in dat['types']};nodes={n['id']:n for n in dat['nodes']};geo={}
    for a,b,d,h in dat['legs']:geo[a,b]=geo[b,a]=(d,h)
    inp=json.loads(Path(path).read_text());jobs=inp['flights'] if isinstance(inp,dict) else inp
    checks=[];perair=defaultdict(list);perbat=defaultdict(list);en=[];ends=[];slacks=[];dels=[];norm=[]
    def check(k,b,detail=''):checks.append({'check':k,'pass':bool(b),'detail':detail})
    check('exact_box_coverage',Counter(x for j in jobs for x in j['box_ids'])==Counter(B.keys()))
    check('unique_jobs',len({j['flight_id'] for j in jobs})==len(jobs))
    for job in jobs:
      typ=job['type'] if isinstance(job['type'],str) else 'ABC'[job['type']];t=types[typ];fid=job['flight_id'];ids=job['box_ids'];route=job['route']
      if route[0]!='O01':route=['O01']+route+['O01']
      check(fid+'.aircraft',job['aircraft'] in t['aircraft']);check(fid+'.battery',job['battery'] in {f'{typ}-BAT{k+1:02d}' for k in range(t['battery_count'])})
      check(fid+'.route',route[0]==route[-1]=='O01' and set(route[1:-1])=={B[i]['site'] for i in ids} and len(route[1:-1])==len(set(route[1:-1])))
      q=sum(B[i]['mass_kg'] for i in ids);vl=sum(round(B[i]['volume_m3']*1000) for i in ids)
      check(fid+'.capacity',q<=t['max_payload_kg'] and vl<=round(t['max_volume_m3']*1000))
      st=job['start_s'];check(fid+'.start',math.isfinite(st) and st>=-1e-7)
      now=st+t['prep_s']+len(ids)*t['load_per_box_s'];energy_wh=0.
      for a,b in zip(route[:-1],route[1:]):
       d,z=geo[a,b];H=z+50;up=H-nodes[a]['work_z'];dn=H-nodes[b]['work_z']
       check(fid+'.clearance',up>=-1e-9 and dn>=-1e-9)
       L=t['empty_range_m']-(t['empty_range_m']-t['full_range_m'])*(q/t['max_payload_kg'])**1.5
       power=t['battery_kwh']*3600000*t['cruise_mps']/L
       energy_wh+=power*(d/t['cruise_mps'])/3600+(t['empty_mass_kg']+q)*9.81*up/(t['up_efficiency']*3600)
       now+=up/t['up_mps']+d/t['cruise_mps']+dn/t['down_mps']
       if b!='O01':
        drop=[i for i in ids if B[i]['site']==b];now+=t['handover_base_s']+len(drop)*t['handover_per_box_s']
        for i in drop:
         rb=B[i];check(i+'.zero_tardiness',now<=rb['expected_delivery_s']+1e-6)
         hard=[]
         if rb['kind']=='医疗物资':hard.append(rb['expected_delivery_s'])
         if rb['first_batch']=='是':hard.append(rb['first_deadline_s'])
         if hard:check(i+'.hard_deadline',now<=min(hard)+1e-6);slacks.append(min(hard)-now)
         dels.append({'box_id':i,'flight_id':fid,'delivery_s':now,'expected_s':rb['expected_delivery_s']})
        q-=sum(B[i]['mass_kg'] for i in drop)
      soc=1-energy_wh/(1000*t['battery_kwh']);check(fid+'.reserve',soc>=t['reserve_pct']/100-1e-9);check(fid+'.empty_return',q==0)
      chg=max(0,.9-soc)*(.65*t['charge_full_s']/.9)+(1-max(.9,soc))*(.35*t['charge_full_s']/.1)
      if 'return_s' in job:check(fid+'.return_binding',abs(job['return_s']-now)<=1e-6)
      if 'energy_kwh' in job:check(fid+'.energy_binding',abs(job['energy_kwh']-energy_wh/1000)<=1e-7)
      perair[job['aircraft']].append((st,now,fid));perbat[job['battery']].append((st,now+chg,fid));en.append(energy_wh/1000);ends.append(now)
      norm.append(dict(flight_id=fid,type=typ,aircraft=job['aircraft'],battery=job['battery'],box_ids=ids,route=route,start_s=st,return_s=now,energy_kwh=energy_wh/1000,return_soc=soc,charge_duration_s=chg,charge_end_s=now+chg))
    for category,groups in [('aircraft',perair),('battery',perbat)]:
      for rid,xs in groups.items():
       xs.sort()
       for l,r in zip(xs,xs[1:]):check(category+'.'+rid+'.nonoverlap',l[1]<=r[0]+1e-6,str((l,r)))
    metrics={'makespan_s':max(ends),'energy_kwh':sum(en),'sorties':len(jobs),'weighted_tardiness_s':sum(B[d['box_id']]['priority']*max(0,d['delivery_s']-B[d['box_id']]['expected_delivery_s']) for d in dels),'min_hard_slack_s':min(slacks),'min_return_soc':min(j['return_soc'] for j in norm),'used_aircraft':len(perair),'used_batteries':len(perbat)}
    if isinstance(inp,dict) and 'claimed_makespan_s' in inp:check('claimed_bound_matches',abs(inp['claimed_makespan_s']-metrics['makespan_s'])<1e-6)
    result={'checked_file':Path(path).name,'checks':len(checks),'failed':sum(not c['pass'] for c in checks),'failures':[c for c in checks if not c['pass']],'metrics':metrics}
    return result,norm,dels
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('path',nargs='?',default=str(ROOT/'data/baseline.json'));p.add_argument('--output',default='baseline_independent');a=p.parse_args()
 r,j,d=verify(a.path)
 for name,obj in [(a.output,r),(a.output+'_flights',j),(a.output+'_deliveries',d)]:
  (ROOT/'results'/f'{name}.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2))
 print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(bool(r['failed']))
