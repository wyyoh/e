"""Continuous fixed-plan communication stress tests and exact inventory scenarios.
Uses the hash-locked V6 geometry kernel; no time sampling is substituted for intervals.
Candidate-cell acceleration is exact pruning with unchanged prism intersection code.
"""
from pathlib import Path
from functools import lru_cache
from collections import defaultdict
import json,csv,sys,copy,time,os,math,argparse,hashlib
import numpy as np
from scipy.optimize import linprog
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results';OUT.mkdir(exist_ok=True,parents=True)
def load(p):return json.loads(Path(p).read_text())
def dump(p,d):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def csvout(p,rows):
 ks=list(dict.fromkeys(k for r in rows for k in r))
 with Path(p).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=ks);w.writeheader();w.writerows({k:(json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list,tuple)) else v) for k,v in r.items()} for r in rows)

def run(runtime):
 Q=Path(runtime).resolve()/'problems/D/q3'
 sys.path[:0]=[str(Q/'code'),str(Q/'code_v5'),str(Q/'code_v4')]
 from radio import G,THR,R
 from transport import T,B,charge_seconds
 import terrain_events as te
 from fast_geometry import enable
 enable() # exact full-array-mask equivalent pruning; kernel and constants unchanged
 from precompute import phases_for
 from export_v2 import export_verified
 from verify_v2 import verify_v2,check_physical
 from q4_audit import audit,ORDER

 # Independently reconstruct ALL partitions and resource chains for every current candidate.
 q4sc=[];q4base=[]
 for role in ['time','energy','robust025','q4_tradeoff']:
  a=audit(Q/f'release_v6/{role}/plan',OUT/f'q4/{role}/fresh_exact')
  q4base.append({'role':role,'blocks':a['blocks'],'by_group_count':a['by_group_count'],'global_pool':a['global_pool'],'interval_profiles_crosschecked':a['interval_profiles_crosschecked']})
  if role=='time':
   inv=np.array([a['inventory'][x] for x in ORDER]); scenarios=[('baseline',None,0,inv)]
   for j,res in enumerate(ORDER):
    for delta in [-1,1]:
     v=inv.copy();v[j]+=delta;scenarios.append((f'{res}_{delta:+d}',res,delta,v))
   for name,res,delta,v in scenarios:
    for k in [2,3]:
     evaluated=[]
     for row in a['all_partitions']:
      if len(row['groups'])!=k:continue
      need=np.array(row['need_vector']);gap=np.maximum(need-v,0)
      evaluated.append({'groups':row['groups'],'need_vector':need.tolist(),'gap_vector':gap.tolist(),'total_gap':int(sum(gap)),'total_need':row['total_need'],'workload_cv':row['workload_cv']})
     ranked=sorted(evaluated,key=lambda r:(r['total_gap'],r['total_need'],r['workload_cv']))
     best=ranked[0];old=a['by_group_count'][str(k)]['minimum_configuration'];fixedgap=np.maximum(np.array(old['need_vector'])-v,0)
     q4sc.append({'scenario':name,'inventory_changed_type':res,'change':delta,'K':k,'inventory_vector':v.tolist(),'best_groups':best['groups'],'best_gap_vector':best['gap_vector'],'best_total_gap':best['total_gap'],'best_total_need':best['total_need'],'best_workload_cv':best['workload_cv'],'partition_changed':best['groups']!=old['groups'],'fixed_original_partition_gap':int(sum(fixedgap)),'second_best_gap':ranked[1]['total_gap'] if len(ranked)>1 else None,'all_partitions':ranked})
 dump(OUT/'q4_inventory_full.json',q4sc);csvout(OUT/'q4_inventory_summary.csv',[{k:v for k,v in s.items() if k!='all_partitions'} for s in q4sc]);dump(OUT/'q4_all_candidates.json',q4base)
 print('Q4_COMPLETE',len(q4sc),flush=True)

 @lru_cache(maxsize=60000)
 def timeline(src,a,b,thr):
  return te.line_timeline(np.array(src),np.array(a),np.array(b),thr,False,0.)
 @lru_cache(maxsize=60000)
 def critical(src,a,b,thr):
  return te.critical_parameters(np.array(src),np.array(a),np.array(b),thr,False,0.)
 @lru_cache(maxsize=100000)
 def point(src,pt,thr):return all(x[2] for x in timeline(src,pt,pt,thr))
 def union(rows):
  result=[]
  for a,b in sorted(rows):
   if b-a<=1e-9:continue
   if result and a<=result[-1][1]+1e-9:result[-1][1]=max(b,result[-1][1])
   else:result.append([a,b])
  return result
 def fixed_check(role,extra=0.,delaymap=None):
  plan=Q/f'release_v6/{role}/plan';ph=load(plan/'all_communication_phases.json');states=load(plan/'communication_states.json');eps=load(plan/'actual_endpoint_states.json');rel=load(plan/'relays.json');rb={r['relay_id']:r for r in rel};delaymap=delaymap or {};epmap=defaultdict(list)
  for e in eps:epmap[e['phase']].append(e)
  failures=defaultdict(list);endpoint_bad=[];segments=0;epcount=0
  for s in states:
   p=ph[s['phase']];dur=p['end_s']-p['start_s'];aa=np.array([p[k+'0'] for k in 'xyz']);bb=np.array([p[k+'1'] for k in 'xyz']);a=aa+(bb-aa)*(s['start_s']-p['start_s'])/dur;b=aa+(bb-aa)*(s['end_s']-p['start_s'])/dur;dt=s['end_s']-s['start_s'];provider=s['provider']
   curves={'G01':timeline(tuple(G),tuple(a),tuple(b),THR['UG']-extra)}
   # Previous relay assignment is fixed; direct fallback is always allowed by the task.
   if provider!='G01':
    rr=rb[provider];src=tuple(rr[k] for k in 'xyz');curves[provider]=timeline(src,tuple(a),tuple(b),THR['UR']-extra)
   ev=set(critical(tuple(G),tuple(a),tuple(b),THR['UG']-extra))
   if provider!='G01':ev.update(critical(src,tuple(a),tuple(b),THR['UR']-extra))
   for c in curves.values():
    for row in c:ev.update(row[:2])
   # Include all original actual endpoints as well as new analytic loss crossings.
   for e in epmap[s['phase']]:
    if s['start_s']+1e-8<e['time_s']<s['end_s']-1e-8:ev.add((e['time_s']-s['start_s'])/dt)
   for rid in {provider}|{e['provider'] for e in epmap[s['phase']]}:
    if rid in rb:
     rr=rb[rid]
     for tm in [rr['service_start_s']+delaymap.get(rid,0.),rr['service_end_s']]:
      if s['start_s']<tm<s['end_s']:ev.add((tm-s['start_s'])/dt)
   ev=sorted(ev)
   def available_mid(u,rid):
    tm=s['start_s']+u*dt
    if next(row[2] for row in curves['G01'] if row[0]-1e-12<=u<=row[1]+1e-12):return True
    if rid=='G01':return False
    rr=rb[rid];src=tuple(rr[k] for k in 'xyz')
    return rr['service_start_s']+delaymap.get(rid,0.)-1e-8<=tm<=rr['service_end_s']+1e-8 and point(tuple(G),src,THR['RG']-extra) and next(row[2] for row in curves[rid] if row[0]-1e-12<=u<=row[1]+1e-12)
   for lo,hi in zip(ev,ev[1:]):
    if hi-lo<=1e-12:continue
    segments+=1
    if not available_mid((lo+hi)/2,provider):failures[s['flight_id']].append([s['start_s']+lo*dt,s['start_s']+hi*dt])
   for u in ev:
    tm=s['start_s']+u*dt;pt=tuple(a+(b-a)*u);epcount+=1
    old=next((e for e in epmap[s['phase']] if abs(e['time_s']-tm)<=1e-7),None);rid=old['provider'] if old else provider
    good=point(tuple(G),pt,THR['UG']-extra)
    if not good and rid in rb:
     rr=rb[rid];src=tuple(rr[k] for k in 'xyz');good=(rr['service_start_s']+delaymap.get(rid,0.)-1e-6<=tm<=rr['service_end_s']+1e-6 and point(tuple(G),src,THR['RG']-extra) and point(src,pt,THR['UR']-extra))
    if not good:endpoint_bad.append({'flight_id':s['flight_id'],'time_s':tm,'provider':rid})
  merged={f:union(rr) for f,rr in failures.items()};merged={f:v for f,v in merged.items() if v};total=sum(b-a for v in merged.values() for a,b in v);longest=max([b-a for v in merged.values() for a,b in v],default=0.)
  # Duration is summed over flights, not over wall-clock union of all concurrent flights.
  ans={'role':role,'extra_loss_db':extra,'delays_s':delaymap,'adjustment_mode':'fixed_transport_and_original_relay_provider; direct_first_fallback_only','interval_feasible':total<=1e-8,'endpoint_feasible':not endpoint_bad,'feasible':total<=1e-8 and not endpoint_bad,'scope':'continuous communication under fixed transport and original relay assignment; relay availability starts later, service end fixed; not a stochastic success probability','sum_flight_outage_s':total,'longest_single_flight_outage_s':longest,'affected_flights':sorted(set(merged)|{x['flight_id'] for x in endpoint_bad}),'failed_endpoint_checks':len(endpoint_bad),'interval_checks':segments,'endpoint_checks':epcount,'outages_by_flight':merged,'bad_endpoints':endpoint_bad[:30]}
  return ans

 loss=[]
 for role in ['time','robust025']:
  for delta in [0,.05,.10,.15,.20,.25]:
   t=time.monotonic();r=fixed_check(role,delta);loss.append(r);dump(OUT/f'q3/loss_{role}_{delta:.2f}.json',r);print('LOSS',role,delta,r['feasible'],r['sum_flight_outage_s'],'seconds',time.monotonic()-t,flush=True)
 dump(OUT/'q3_loss_grid.json',loss);csvout(OUT/'q3_loss_grid.csv',[{k:v for k,v in r.items() if k not in ['outages_by_flight','bad_endpoints']} for r in loss])
 delays=[]
 ids=[r['relay_id'] for r in load(Q/'release_v6/time/plan/relays.json')]
 for rid in ids:
  for delay in [0,1,5,10,30,60]:
   r=fixed_check('time',0.,{rid:delay});delays.append(r);dump(OUT/f'q3/delay_{rid}_{delay}.json',r);print('DELAY',rid,delay,r['sum_flight_outage_s'],flush=True)
 dump(OUT/'q3_delay_grid.json',delays);csvout(OUT/'q3_delay_grid.csv',[{k:v for k,v in r.items() if k not in ['outages_by_flight','bad_endpoints']} for r in delays])

 # Fixed-provider/fixed-resource-order continuous-time repair with exogenous deployment delay.
 ref=load(Q/'release_v6/time/selected.json');data=load(Q/'release_v6/time/precomputed.json')
 def chains(ids,assign,starts):
  gs=defaultdict(list)
  for i in ids:gs[assign[str(i)]].append(i)
  return [(a,b) for v in gs.values() for a,b in zip(sorted(v,key=lambda i:starts[i]),sorted(v,key=lambda i:starts[i])[1:])]
 def repair(rid,delay):
  ev,_=phases_for(data['decisions']);nt=len(ev);nr=len(data['sites']);n=nt+2*nr+1;mi=n-1;ri=lambda j:nt+j;re=lambda j:nt+nr+j;power=(R['hover_kw']+R['communication_kw'])/3600;guard=1e-4
  lead=[R['prep_s']+g['out_s']+R['link_setup_s'] for g in data['sites']];bounds=[];A=[];rhs=[]
  idx=ids.index(rid)
  for i,e in enumerate(ev):
   latest=min([B[b]['expected_delivery_s']-off for b,off in e['delivery']]+[B[b]['hard_deadline_s']-off for b,off in e['delivery'] if B[b]['hard_deadline_s'] is not None]);bounds.append((ref['starts'][i],latest))
  bounds += [(ref['relay_start'][j]+(delay if j==idx else 0),20000) for j in range(nr)]+[(ref['relay_end'][j],20000) for j in range(nr)]+[(0,20000)]
  def row(d,v):
   ar=np.zeros(n)
   for i,c in d.items():ar[i]+=c
   A.append(ar);rhs.append(v)
  for i,e in enumerate(ev):row({i:1,mi:-1},-e['duration'])
  Ec=[g['transit_kwh']+power*R['link_setup_s'] for g in data['sites']];alph=[];beta=[]
  for j,g in enumerate(data['sites']):
   row({ri(j):1,re(j):-1},0);row({re(j):1,mi:-1},-g['back_s']);row({re(j):power,ri(j):-power},R['battery_kwh']*.8-Ec[j])
   energy=Ec[j]+power*(ref['relay_end'][j]-ref['relay_start'][j])
   if energy>=.1*R['battery_kwh']:
    aa=R['charge_full_s']*.65/(.9*R['battery_kwh']);bb=R['charge_full_s']*(.35-.65*.1/.9);row({ri(j):power,re(j):-power},Ec[j]-.1*R['battery_kwh'])
   else:
    aa=R['charge_full_s']*3.5/R['battery_kwh'];bb=0;row({re(j):power,ri(j):-power},.1*R['battery_kwh']-Ec[j])
   alph.append(aa);beta.append(bb)
  for g in T:
   ii=[i for i,x in enumerate(data['decisions']) if x['type']==g]
   for name in ['aircraft_assign','battery_assign']:
    for i,j in chains(ii,ref[name],ref['starts']):row({i:1,j:-1},-(ev[i]['duration']+(ev[i]['charge'] if name=='battery_assign' else 0)+guard))
  rp=[ref['relay_start'][j]-lead[j] for j in range(nr)]
  for i,j in chains(list(range(nr)),ref['relay_assign'],rp):row({re(i):1,ri(j):-1},-(data['sites'][i]['back_s']+R['turnaround_s']+lead[j]+guard))
  for i,j in chains(list(range(nr)),ref['component_assign'],rp):row({re(i):1+alph[i]*power,ri(i):-alph[i]*power,ri(j):-1},-(data['sites'][i]['back_s']+lead[j]+alph[i]*Ec[i]+beta[i]+guard))
  for h,d in enumerate(data['compact']):
   i=d['i'];j=ref['cover_assignment'][str(h)];assert j in d['allowed'];row({ri(j):1,i:-1},d['a']-guard);row({i:1,re(j):-1},-d['b']-guard)
  obj=np.zeros(n);obj[mi]=1;res=linprog(obj,A_ub=A,b_ub=rhs,bounds=bounds,method='highs',options={'primal_feasibility_tolerance':1e-8,'dual_feasibility_tolerance':1e-8})
  rr={'relay_id':rid,'delay_s':delay,'adjustment_mode':'starts_and_service_ends_right_shift_only; routes,sites,resource_orders,cover_assignment,SOC_branches_fixed','solver_status':res.message,'success':bool(res.success)}
  folder=OUT/f'q3_repair/{rid}_{delay}';folder.mkdir(parents=True,exist_ok=True)
  if not res.success:dump(folder/'result.json',rr);return rr
  opt=float(res.fun);bounds[mi]=(0,opt+1e-6);obj=np.zeros(n)
  for j in range(nr):obj[re(j)]=power;obj[ri(j)]=-power
  rs=linprog(obj,A_ub=A,b_ub=rhs,bounds=bounds,method='highs',options={'primal_feasibility_tolerance':1e-8,'dual_feasibility_tolerance':1e-8});assert rs.success;z=rs.x
  sel=copy.deepcopy(ref);sel.update(starts=z[:nt].tolist(),relay_start=[float(z[ri(j)]) for j in range(nr)],relay_end=[float(z[re(j)]) for j in range(nr)],makespan_s=float(z[mi]))
  sel['relay_energy']=[Ec[j]+power*(z[re(j)]-z[ri(j)]) for j in range(nr)];sel['relay_charge']=[charge_seconds(1-e/R['battery_kwh'],R) for e in sel['relay_energy']];sel['relay_energy_kwh']=float(sum(sel['relay_energy']));sel['total_energy_kwh']=sel['relay_energy_kwh']+sel['transport_energy_kwh'];dump(folder/'selected.json',sel)
  su=export_verified(data,sel,folder/'plan',step=1,verify=False)
  vr=verify_v2(folder/'plan',step=1,intervals=True)
  rr.update(makespan_s=su['joint_makespan_s'],extra_makespan_s=su['joint_makespan_s']-ref['makespan_s'],total_energy_kwh=su['total_energy_kwh'],min_hard_slack_s=su['min_hard_slack_s'],validation_failed=vr['failed'],point_failures=vr['point_failures'],validation_pass=vr['failed']==0 and vr['point_failures']==0,lp_lower_bound_s=opt,scope='fixed structure and right-shift recovery; not original-problem optimum')
  dump(folder/'result.json',rr);return rr
 repairs=[]
 for rid in ids:
  for delay in [5,30,60]:
   try:r=repair(rid,delay)
   except Exception as ex:r={'relay_id':rid,'delay_s':delay,'error':str(ex),'success':False}
   repairs.append(r);dump(OUT/'q3_repair_summary.json',repairs);print('REPAIR',r,flush=True)
 csvout(OUT/'q3_repair_summary.csv',repairs)
 dump(OUT/'q3_q4_execution.json',{'loss_scenarios':len(loss),'delay_scenarios':len(delays),'recovery_scenarios':len(repairs),'q4_inventory_scenarios':len(q4sc),'runtime_archive_sha256':'f8efc0cb0859fe0bd39f0f23f1a18e824d3848873344ef3e7a93b11a93b257bf','complete':True})

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);a=p.parse_args();run(a.runtime)
