"""Recheck the integer reduced-cost certificate using exhaustive C++ pricing.
Also checks coefficient generation and every published incumbent column.
The bound is for the relaxation; it is not a formal-real-arithmetic flight proof.
"""
from pathlib import Path
from collections import Counter
import json,itertools,subprocess,math
import numpy as np
from workload_cg import setup
ROOT=Path(__file__).resolve().parents[1]

def verify(tag='patterns_0p001'):
 cert=json.loads((ROOT/'results'/f'energy_certificate_{tag}.json').read_text())['certificate']
 lpath=ROOT/'results'/f'energy_lattice_{tag}.npz';lattice=np.load(lpath) if lpath.exists() else None
 tt=lattice['travel'] if lattice is not None else [];energies=[lattice['energyA'],lattice['energyB'],lattice['energyC']] if lattice is not None else [];budgets=lattice['budgets'] if lattice is not None else []
 B,types,classes,demand,sites,weights,volumes,travel,raws=setup();pi=cert['pi_integer'];mu=cert['mu_integer'];den=cert['denominator'];tests=[]
 def ck(n,b,detail=''):tests.append({'check':n,'pass':bool(b),'detail':str(detail)})
 ck('positive_denominator',den>0);ck('T_dual_constraint',sum(len(t['aircraft'])*mu[g] for g,t in enumerate(types))<=den)
 ck('objective_numerator',sum(int(d)*p for d,p in zip(demand,pi))==cert['numerator'])
 # Reconstruct rational lower coefficient arrays from the source graph.
 names=['O01']+sorted({b['site'] for b in B});nd={s:i for i,s in enumerate(names)};geo=json.loads((ROOT/'data/legs.json').read_text());N=16
 for g,t in enumerate(types):
  a=np.floor(np.maximum(0,raws[g]*1000-1e-7)).astype(np.int64)
  for k in range(N):a=np.minimum(a,a[:,k,None]+a[None,k,:])
  if lattice is None:tt.append(a);budgets.append(math.ceil((1-t['reserve_pct']/100)*t['battery_kwh']/cert['quantum_kwh']-1e-10))
  ck('travel_minorant_'+t['id'],np.array_equal(a,tt[g]))
  er=[]
  for q in range(t['max_payload_kg']+1):
   mat=np.zeros((16,16));L=t['empty_range_m']-(t['empty_range_m']-t['full_range_m'])*(q/t['max_payload_kg'])**1.5
   for l in geo:mat[nd[l['from']],nd[l['to']]]=t['battery_kwh']*l['distance_m']/L+(t['empty_mass_kg']+q)*9.81*l['up_m']/(t['up_efficiency']*3600000)
   for k in range(N):mat=np.minimum(mat,mat[:,k,None]+mat[None,k,:])
   er.append(np.floor(np.maximum(0,mat/cert['quantum_kwh']-1e-9)).astype(np.int64))
  if lattice is None:energies.append(np.array(er))
  ck('energy_minorant_'+t['id'],np.array_equal(np.array(er),energies[g]))
  pats=[]
  for dest in range(1,N):
   js=[j for j in range(len(classes)) if sites[j]==dest]
   for cnt in itertools.product(*(range(int(demand[j])+1) for j in js)):
    w=sum(weights[j]*n for j,n in zip(js,cnt));v=sum(volumes[j]*n for j,n in zip(js,cnt));num=sum(cnt)
    if 0<w<=t['max_payload_kg'] and v<=round(t['max_volume_m3']*1000):pats.append((dest,w,v,num,sum(pi[j]*n for j,n in zip(js,cnt))))
  head=f"{t['max_payload_kg']} {round(t['max_volume_m3']*1000)} {len(pats)} 16 {budgets[g]} {mu[g]} {t['prep_s']*1000} {(t['load_per_box_s']+t['handover_per_box_s'])*1000} {t['handover_base_s']*1000}\n"
  payload=head+'\n'.join(' '.join(map(str,x)) for x in pats)+'\n'+' '.join(map(str,tt[g].ravel()))+'\n'+' '.join(map(str,energies[g].ravel()))+'\n'
  out=subprocess.run([str(ROOT/'src/pattern_pricer')],input=payload,text=True,capture_output=True,check=True,timeout=120)
  rc=int(out.stdout.split()[0]);ck('all_columns_nonnegative_'+t['id'],rc>=0,f'integer minimum={rc}')
 num=cert['numerator'];result={'checks':len(tests),'failed':sum(not t['pass'] for t in tests),'lower_bound_s':num/den,'numerator':num,'denominator':den,'details':tests}
 (ROOT/'results/certificate_verification.json').write_text(json.dumps(result,indent=2))
 return result
if __name__=='__main__':print(json.dumps(verify(),indent=2))
