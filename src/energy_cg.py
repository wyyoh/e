"""Stronger complete-pricing lower bound with a downward-rounded energy lattice.
Safe relaxation, not full Branch-Price-and-Check. Each visit may repeat.
Both time and load-dependent energy use shortest-path minorants of raw arcs.
No all-different visited mask or timing/charging exclusion is claimed.
"""
from pathlib import Path
import json,time,math,subprocess
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csc_matrix
from workload_cg import setup
ROOT=Path(__file__).resolve().parents[1]

def main(quantum_kwh=0.01,iterations=100,wall_s=240):
 B,types,classes,demand,sites,weights,volumes,travel,raws=setup();nc=len(classes);N=16;scale=10**6
 names=['O01']+sorted({b['site'] for b in B});nd={s:i for i,s in enumerate(names)}
 geo=json.loads((ROOT/'data/legs.json').read_text());tt=[];ee=[];bud=[]
 for g,t in enumerate(types):
  a=np.floor(np.maximum(0,raws[g]*1000-1e-7)).astype(np.int64)
  for k in range(N):a[:]=np.minimum(a,a[:,k,None]+a[None,k,:])
  tt.append(a)
  er=[]
  for q in range(t['max_payload_kg']+1):
   ar=np.zeros((N,N));Rg=t['empty_range_m']-(t['empty_range_m']-t['full_range_m'])*(q/t['max_payload_kg'])**1.5
   for l in geo:
    ar[nd[l['from']],nd[l['to']]]=t['battery_kwh']*l['distance_m']/Rg+(t['empty_mass_kg']+q)*9.81*l['up_m']/(t['up_efficiency']*3600000)
   # Minorant allows intermediate waypoints and ignores their service times.
   for k in range(N):ar=np.minimum(ar,ar[:,k,None]+ar[None,k,:])
   er.append(np.floor(np.maximum(0,ar/quantum_kwh-1e-9)).astype(np.int64))
  ee.append(np.array(er));bud.append(math.ceil((1-t['reserve_pct']/100)*t['battery_kwh']/quantum_kwh-1e-10))
 def col(g,seq):
  t=types[g];p=t['prep_s']*1000;last=0;cnt=np.zeros(nc,dtype=int);q=sum(int(weights[j]) for j in seq);E=0
  if q>t['max_payload_kg'] or sum(int(volumes[j]) for j in seq)>round(t['max_volume_m3']*1000):return None
  # Process consecutive deliveries jointly: preceding arc carries every box.
  for j in seq:
   dest=int(sites[j]);p+=(t['load_per_box_s']+t['handover_per_box_s'])*1000
   if dest!=last:p+=tt[g][last,dest]+t['handover_base_s']*1000;E+=ee[g][q,last,dest]
   q-=int(weights[j]);cnt[j]+=1;last=dest
  p+=tt[g][last,0];E+=ee[g][0,last,0]
  if E>bud[g]:return None
  return (g,tuple(map(int,cnt)),int(p),int(E),tuple(map(int,seq)))
 cols=[];seen=set()
 def add(g,seq):
  c=col(g,seq)
  if c is None:return False
  key=c[:3]
  if key in seen:return False
  cols.append(c);seen.add(key);return True
 for g in range(3):
  for j in range(nc):add(g,[j])
 for c in json.loads((ROOT/'results/workload_columns.json').read_text()):add('ABC'.index(c['type']),c['sequence'])
 static=[]
 for g,t in enumerate(types):
  static.append('\n'.join([' '.join(map(str,tt[g].ravel())),' '.join(map(str,ee[g].ravel()))]))
 def pricing(g,pii,mui,timeout):
  t=types[g];head=f"{t['max_payload_kg']} {round(t['max_volume_m3']*1000)} {nc} {N} {bud[g]} {int(mui[g])} {t['prep_s']*1000} {(t['load_per_box_s']+t['handover_per_box_s'])*1000} {t['handover_base_s']*1000}\n"
  lines='\n'.join(f'{sites[j]} {weights[j]} {volumes[j]} {int(pii[j])}' for j in range(nc))
  p=subprocess.run([str(ROOT/'src/energy_pricer')],input=head+lines+'\n'+static[g]+'\n',text=True,capture_output=True,timeout=timeout,check=True)
  data=p.stdout.splitlines();rc,labels,count=map(int,data[0].split());seqs=[]
  for line in data[1:]:a=list(map(int,line.split()));seqs.append(a[2:])
  return rc,labels,seqs
 start=time.monotonic();hist=[];bestcert=None;stop='iteration_limit'
 for it in range(iterations):
  m=len(cols);A=np.zeros((nc,m+1));U=np.zeros((3,m+1))
  for k,c in enumerate(cols):A[:,k]=c[1];U[c[0],k]=c[2]/1000
  U[:,-1]=[-len(t['aircraft']) for t in types];cost=np.zeros(m+1);cost[-1]=1
  r=linprog(cost,A_ub=csc_matrix(U),b_ub=np.zeros(3),A_eq=csc_matrix(A),b_eq=demand,bounds=(0,None),method='highs-ds')
  if not r.success:raise RuntimeError(r.message)
  pii=np.floor(r.eqlin.marginals*scale).astype(np.int64);mui=np.maximum(0,np.ceil(-r.ineqlin.marginals*scale)).astype(np.int64)
  mins=[];labels=[];added=0
  try:
   for g in range(3):
    rc,l,seqs=pricing(g,pii,mui,max(5,wall_s-(time.monotonic()-start)));mins.append(rc);labels.append(l)
    for seq in seqs:
     c=col(g,seq)
     if c is None:raise AssertionError('traceback not energy feasible in relaxation')
     calc=int(mui[g])*c[2]-sum(int(pii[j])*1000*c[1][j] for j in range(nc))
     if calc<0:added+=add(g,seq)
  except subprocess.TimeoutExpired:
   stop='pricing_time_limit';break
  correction=max(0,(-min(mins)+999)//1000);pnew=pii-correction
  # Each column has >=1 box, hence shifting EVERY pi down by correction
  # raises every reduced cost by >=correction*1000, with an exact certificate.
  den=max(scale,sum(len(t['aircraft'])*int(mui[g]) for g,t in enumerate(types)))
  num=sum(int(demand[j])*int(pnew[j]) for j in range(nc));lb=num/den
  cert={'iteration':it,'denominator':den,'numerator':num,'pi_integer':pnew.tolist(),'mu_integer':mui.tolist(),'original_minimum_reduced_cost':mins,'uniform_correction_integer':int(correction),'certified_minima_lower_bounds':[int(x+correction*1000) for x in mins],'quantum_kwh':quantum_kwh}
  if bestcert is None or lb>bestcert['lower_bound_s']:bestcert={'lower_bound_s':lb,'certificate':cert}
  row={'iteration':it,'columns':m,'restricted_lp_s':float(r.fun),'verified_lb_s':lb,'pricing_minima':mins,'labels':labels,'added':int(added),'elapsed_s':time.monotonic()-start};hist.append(row);print(json.dumps(row),flush=True)
  if min(mins)>=0:stop='complete_integer_pricing_nonnegative';break
  if not added:stop='no_new_column_rounding_gap';break
  if time.monotonic()-start>wall_s:stop='wall_limit';break
 ub=json.loads((ROOT/'data/incumbent_metrics.json').read_text())['makespan_s']
 result={'scope':'global lower-bound relaxation (energy minorants, repeated visits/items, no scheduling/deadlines)','energy_quantum_kwh':quantum_kwh,'stop':stop,'iterations':len(hist),'columns_generated':len(cols),'upper_bound_s':ub,'verified_lower_bound_s':None if bestcert is None else bestcert['lower_bound_s'],'global_optimality_proved':False,'elapsed_s':time.monotonic()-start}
 if bestcert:result['gap_over_ub']=(ub-bestcert['lower_bound_s'])/ub
 tag=str(quantum_kwh).replace('.','p')
 for fn,data in [(f'energy_cg_{tag}',result),(f'energy_history_{tag}',hist),(f'energy_certificate_{tag}',bestcert),(f'energy_columns_{tag}',[{'type':c[0],'counts':c[1],'duration_ticks':c[2],'energy_units':c[3],'sequence':c[4]} for c in cols])]:
  (ROOT/'results'/f'{fn}.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')))
 np.savez_compressed(ROOT/'results'/f'energy_lattice_{tag}.npz',travel=np.array(tt),energyA=ee[0],energyB=ee[1],energyC=ee[2],budgets=np.array(bud))
 print('FINAL',json.dumps(result,indent=2),flush=True)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--quantum',type=float,default=.01);p.add_argument('--seconds',type=float,default=240);a=p.parse_args();main(a.quantum,wall_s=a.seconds)
