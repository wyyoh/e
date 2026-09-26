"""Deterministic perturbation experiments with explicit recovery permissions.
Inputs are immutable snapshots from the SHA-locked formal Q2 V7 evidence bundle.
This module does not update any formal selection file.
"""
from pathlib import Path
from functools import lru_cache
from collections import Counter,defaultdict
import json,csv,math,itertools,hashlib,copy,sys,time
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results'; OUT.mkdir(parents=True,exist_ok=True)
def load(p):return json.loads(Path(p).read_text())
def dump(p,d):
 Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def csvout(p,rows):
 if not rows:return
 ks=list(dict.fromkeys(k for r in rows for k in r))
 with Path(p).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=ks);w.writeheader();w.writerows({k:(json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict,tuple)) else v) for k,v in r.items()} for r in rows)
T={x['id']:x for x in load(ROOT/'q2_runtime/inputs/types.json')};B={x['id']:x for x in load(ROOT/'q2_runtime/inputs/boxes.json')};N={x['id']:x for x in load(ROOT/'q2_runtime/inputs/nodes.json')};G={(x['from'],x['to']):x for x in load(ROOT/'q2_runtime/inputs/legs.json')}
FL=load(ROOT/'inputs/q2/flights.json')
def charging(s,full):
 if s<0 or s>1+1e-8:return None
 return full*(.65*max(0,.9-s)/.9+.35*max(0,1-max(.9,s))/.1)
def task_eval(f,energy_scale=1.,eta_scale=1.,delay=0.,charge_scale=1.):
 """Extra delay occurs during first delivery handover; no extra hover power in the given transport model."""
 t=T[f['type']];ids=f.get('box_ids',f.get('boxes'));route=f['route'];route=route if route[0]=='O01' else ['O01',*route,'O01']
 mass=sum(B[b]['mass_kg'] for b in ids);vol=sum(B[b]['volume_m3'] for b in ids);q=mass
 now=t['prep_s']+len(ids)*t['load_per_box_s'];energy=0.;dels={};hor=0.;climb=0.
 for j,(a,b) in enumerate(zip(route[:-1],route[1:])):
  g=G[a,b];up=g['cruise_z']-N[a]['work_z'];dn=g['cruise_z']-N[b]['work_z']
  if min(up,dn)<-1e-8:raise ValueError('Height definition conflict')
  d=math.hypot(N[a]['x']-N[b]['x'],N[a]['y']-N[b]['y']);L=t['empty_range_m']-(t['empty_range_m']-t['full_range_m'])*(q/t['max_payload_kg'])**1.5
  hor+=t['battery_kwh']*d/L;climb+=(t['empty_mass_kg']+q)*9.81*up/(t['up_efficiency']*eta_scale*3600000.)
  now+=up/t['up_mps']+d/t['cruise_mps']+dn/t['down_mps']
  if b!='O01':
   drop=[x for x in ids if B[x]['site']==b];now+=t['handover_base_s']+len(drop)*t['handover_per_box_s']+(delay if j==0 else 0.)
   for x in drop:dels[x]=now
   q-=sum(B[x]['mass_kg'] for x in drop)
 assert abs(q)<1e-8
 energy=(hor+climb)*energy_scale;soc=1-energy/t['battery_kwh'];charge=charging(soc,t['charge_full_s']*charge_scale)
 return {'duration':now,'energy':energy,'soc':soc,'charge':charge,'delivery':dels,'mass':mass,'volume':vol,'physical':mass<=t['max_payload_kg']+1e-9 and vol<=t['max_volume_m3']+1e-9 and soc>=t['reserve_pct']/100-1e-9,'horizontal_energy':hor*energy_scale,'climb_energy':climb*energy_scale}
def simulate(mode='fixed_calendar',charge_scale=1.,energy_scale=1.,delay_id=None,delay=0.,flights=FL):
 values={f['flight_id']:task_eval(f,energy_scale=energy_scale,delay=delay if f['flight_id']==delay_id else 0.,charge_scale=charge_scale) for f in flights};starts={};ends={};batends={};plane_ready={};bat_ready={};output=[];deliver=[]
 for f in sorted(flights,key=lambda x:(x['start_s'],x['aircraft'],x['flight_id'])):
  i=f['flight_id'];e=values[i];st=f['start_s']
  if mode=='right_shift_repair':st=max(st,plane_ready.get(f['aircraft'],0.),bat_ready.get(f['battery'],0.))
  en=st+e['duration'];ce=en+e['charge'] if e['charge'] is not None else en+1e9
  starts[i]=st;ends[i]=en;batends[i]=ce;plane_ready[f['aircraft']]=en;bat_ready[f['battery']]=ce
  output.append({**f,'start_s':st,'return_s':en,'charge_end_s':ce,'energy_kwh':e['energy'],'return_soc':e['soc']})
  for b,off in e['delivery'].items():deliver.append({'id':b,'flight_id':i,'delivery_s':st+off,'hard_slack_s':None if B[b]['hard_deadline_s'] is None else B[b]['hard_deadline_s']-st-off,'expected_slack_s':B[b]['expected_delivery_s']-st-off})
 conflicts=[]
 for key,endkey in [('aircraft','return_s'),('battery','charge_end_s')]:
  groups=defaultdict(list)
  for f in output:groups[f[key]].append(f)
  for res,fs in groups.items():
   fs.sort(key=lambda x:(x['start_s'],x['flight_id']))
   for a,b in zip(fs,fs[1:]):
    if a[endkey]-b['start_s']>1e-6:conflicts.append({'resource':res,'previous':a['flight_id'],'next':b['flight_id'],'overlap_s':a[endkey]-b['start_s']})
 hard=[x for x in deliver if x['hard_slack_s'] is not None and x['hard_slack_s'] < -1e-6];late=[x for x in deliver if x['expected_slack_s'] < -1e-6];bad=[i for i,e in values.items() if not e['physical']]
 m={'adjustment_mode':mode,'charging_factor':charge_scale,'energy_factor':energy_scale,'delayed_task':delay_id,'delay_s':delay,'physical_and_hard_feasible':not(conflicts or hard or bad),'zero_tardiness_feasible':not(conflicts or late or hard or bad),'hard_late_boxes':len(hard),'late_boxes':len(late),'weighted_tardiness_s':sum(B[x['id']]['priority']*max(0,-x['expected_slack_s']) for x in deliver),'makespan_s':max(ends.values()),'energy_kwh':sum(e['energy'] for e in values.values()),'min_soc':min(e['soc'] for e in values.values()),'min_hard_slack_s':min(x['hard_slack_s'] for x in deliver if x['hard_slack_s'] is not None),'resource_conflicts':len(conflicts),'max_resource_overlap_s':max([c['overlap_s'] for c in conflicts],default=0.),'energy_violations':len(bad),'first_violated_constraint':('energy' if bad else 'resource_overlap' if conflicts else 'hard_deadline' if hard else 'expected_delivery' if late else ''),'first_conflict':conflicts[0] if conflicts else None}
 return m,output,deliver

def q1_solve(alpha=.2,energy_scale=1.,eta_scale=1.):
 allsel=[];pat_count=0;safe_count=0
 for site in sorted(set(b['site'] for b in B.values())):
  cats=defaultdict(list)
  for b in B.values():
   if b['site']==site:cats[(b['kind'],b['mass_kg'],round(b['volume_m3']*1000))].append(b['id'])
  catlist=sorted(cats);base=tuple(len(cats[c]) for c in catlist);patterns=[]
  for cnt in itertools.product(*(range(n+1) for n in base)):
   if not any(cnt):continue
   ids=[b for c,k in zip(catlist,cnt) for b in sorted(cats[c])[:k]]
   for g,t in T.items():
    mass=sum(B[b]['mass_kg'] for b in ids);vol=sum(B[b]['volume_m3'] for b in ids)
    if mass>t['max_payload_kg']+1e-9 or vol>t['max_volume_m3']+1e-9:continue
    pat_count+=1;e=task_eval({'type':g,'boxes':ids,'route':[site]},energy_scale=energy_scale,eta_scale=eta_scale)
    if e['soc']+1e-10<alpha:continue
    safe_count+=1;patterns.append((cnt,g,e))
  @lru_cache(None)
  def dp(rem):
   if not any(rem):return ((0,0.,0.),())
   best=None
   for ix,(c,g,e) in enumerate(patterns):
    if any(a>b for a,b in zip(c,rem)):continue
    sub=dp(tuple(b-a for a,b in zip(c,rem)))
    if sub is None:continue
    val=(sub[0][0]+1,sub[0][1]+e['energy'],sub[0][2]+e['duration'])
    # Tolerance only resolves floating-equal E labels, not a changed objective.
    if best is None or val[0]<best[0][0] or (val[0]==best[0][0] and (val[1]<best[0][1]-1e-9 or (abs(val[1]-best[0][1])<=1e-9 and val[2]<best[0][2]-1e-7))):best=(val,sub[1]+(ix,))
   return best
  sol=dp(base)
  if sol is None:return {'alpha':alpha,'energy_factor':energy_scale,'climb_efficiency_factor':eta_scale,'feasible':False,'failed_site':site,'adjustment_mode':'exact_reoptimization'},[]
  available={c:sorted(cats[c]) for c in catlist}
  for ix in sol[1]:
   cnt,g,e=patterns[ix];ids=[]
   for c,n in zip(catlist,cnt):ids+=available[c][:n];available[c]=available[c][n:]
   allsel.append({'site':site,'type':g,'boxes':ids,'mass_kg':e['mass'],'volume_m3':e['volume'],'energy_kwh':e['energy'],'duration_s':e['duration'],'return_soc':e['soc'],'counts':list(cnt)})
 return {'alpha':alpha,'energy_factor':energy_scale,'climb_efficiency_factor':eta_scale,'feasible':True,'sorties':len(allsel),'energy_kwh':sum(x['energy_kwh'] for x in allsel),'sum_work_min':sum(x['duration_s'] for x in allsel)/60,'type_counts':dict(Counter(x['type'] for x in allsel)),'count_patterns_capacity':pat_count,'count_patterns_energy_feasible':safe_count,'adjustment_mode':'exact_reoptimization'},allsel

def main():
 t0=time.time();audit=[]
 # Independent formula replay against every formal flight and box.
 m,fs,ds=simulate()
 for f,actual in zip(FL,sorted(fs,key=lambda x:x['flight_id'])):
  if f['flight_id']!=actual['flight_id']:raise ValueError('ID mismatch')
  for k in ['return_s','energy_kwh','return_soc','charge_end_s']:
   assert abs(actual[k]-f[k])<1e-7,(f['flight_id'],k,actual[k],f[k])
 reference={x['id']:x for x in load(ROOT/'inputs/q2/deliveries.json')}
 for x in ds:assert abs(x['delivery_s']-reference[x['id']]['delivery_s'])<1e-6,x
 assert m['zero_tardiness_feasible']
 dump(OUT/'q2_baseline_replay.json',{'result':m,'flights_verified':len(fs),'boxes_verified':len(ds),'independent_formulas':True})
 q2=[]
 for f in [.8,.9,1.,1.1,1.2,1.3]:
  for mode in ['fixed_calendar','right_shift_repair']:
   mm,ff,dd=simulate(mode,charge_scale=f);mm['experiment']='charging';q2.append(mm)
 for i in [f['flight_id'] for f in FL]:
  for delay in [0,15,30,60,120]:
   for mode in ['fixed_calendar','right_shift_repair']:
    mm,ff,dd=simulate(mode,delay_id=i,delay=delay);mm['experiment']='single_first_handover_delay';q2.append(mm)
 for eps in [0,.0005,.001,.0012,.0012187686,.0013,.002,.005,.01,.02]:
  for mode in ['fixed_calendar','right_shift_repair']:
   mm,ff,dd=simulate(mode,energy_scale=1+eps);mm['experiment']='uniform_energy_error';q2.append(mm)
 csvout(OUT/'q2_perturbations.csv',q2);dump(OUT/'q2_perturbations.json',q2)
 q1=[]
 for alpha in [.15,.18,.2,.22,.2308834976366333,.235,.25,.27,.28,.32,.34,.35,.353]:
  r,b=q1_solve(alpha=alpha);r['experiment']='reserve';q1.append(r);dump(OUT/f'q1_plans/reserve_{alpha:.12f}.json',b)
 for eps in [0,.01,.02,.04,.05,.1]:
  r,b=q1_solve(energy_scale=1+eps);r['experiment']='energy_error';q1.append(r);dump(OUT/f'q1_plans/energy_{eps:.3f}.json',b)
 for eta in [.8,.9,1.,1.1,1.2]:
  r,b=q1_solve(eta_scale=eta);r['experiment']='climb_efficiency';q1.append(r);dump(OUT/f'q1_plans/efficiency_{eta:.2f}.json',b)
 nominal=next(r for r in q1 if r['experiment']=='reserve' and r['alpha']==.2)
 assert nominal['sorties']==18 and abs(nominal['energy_kwh']-59.13129602205317)<1e-8
 assert abs(nominal['sum_work_min']-546.2669291485934)<1e-6
 csvout(OUT/'q1_reoptimization.csv',q1);dump(OUT/'q1_reoptimization.json',q1)
 dump(OUT/'q1_q2_execution.json',{'elapsed_s':time.time()-t0,'q1_scenarios':len(q1),'q2_scenarios':len(q2),'q1_nominal':nominal,'no_global_optimality_claim_for_perturbed_q2':True})
 print(json.dumps({'q1':len(q1),'q2':len(q2),'q1_nominal':nominal,'q2_nominal':m},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
