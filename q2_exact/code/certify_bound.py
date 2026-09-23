"""Exact integer-arithmetic dual certificate for a relaxed full Q2 universe.
The certificate does NOT need floating-point solver success or MIP gap claims.
Rational lower time coefficients and repeated-item pricing cover all physical
routes, including repeat visits. Battery/deadline/energy are relaxed, not changed.
"""
import json,math,itertools,hashlib,argparse
from fractions import Fraction
from pathlib import Path
from collections import Counter
import numpy as np
from numba import njit
ROOT=Path(__file__).resolve().parents[1]
S=100000000;H=1000000

@njit(cache=True)
def metric_int(a):
 d=a.copy()
 for k in range(len(a)):
  for i in range(len(a)):
   for j in range(len(a)):
    if d[i,k]+d[k,j]<d[i,j]:d[i,j]=d[i,k]+d[k,j]
 return d

@njit(cache=True)
def min_price_int(Q,V,cost,ps,pm,pv,pcost,prep):
 n=len(cost);INF=np.int64(4000000000000000000)
 dp=np.full((Q+1,V+1,n),INF,np.int64);dp[0,0,0]=0
 best=INF
 for q in range(Q+1):
  for v in range(V+1):
   inc=np.full(n,INF,np.int64)
   for i in range(1,n):
    for j in range(n):
     if j==i:continue
     if dp[q,v,j]<INF//2:
      a=dp[q,v,j]+cost[i,j]
      if a<inc[i]:inc[i]=a
   for h in range(len(ps)):
    qn=q+pm[h];vn=v+pv[h];i=ps[h]
    if qn>Q or vn>V or inc[i]>=INF//2:continue
    a=inc[i]+pcost[h]
    if a<dp[qn,vn,i]:dp[qn,vn,i]=a
   for i in range(1,n):
    if dp[q,v,i]<INF//2:
     a=dp[q,v,i]+cost[0,i]+prep
     if a<best:best=a
 return best

def data():
 T=json.loads((ROOT/'inputs/types.json').read_text());B=json.loads((ROOT/'inputs/boxes.json').read_text());legs=json.loads((ROOT/'inputs/legs.json').read_text());N=['O01']+sorted({b['site'] for b in B});ni={s:i for i,s in enumerate(N)}
 cc=Counter((b['site'],b['mass_kg'],round(b['volume_m3']*1000)) for b in B);keys=sorted(cc);d=[cc[k] for k in keys];F=lambda x:Fraction(str(x));out=[]
 for t in T:
  tau=np.zeros((16,16),np.int64)
  for r in legs:
   exact=F(r['up_m'])/F(t['up_mps'])+F(r['distance_m'])/F(t['cruise_mps'])+F(r['down_m'])/F(t['down_mps'])
   tau[ni[r['from']],ni[r['to']]]=math.floor(exact*H)
  tau=metric_int(tau);ps=[];pm=[];pv=[];counts=[];services=[]
  Q=t['max_payload_kg'];V=round(t['max_volume_m3']*1000)
  for s in N[1:]:
   inds=[k for k,key in enumerate(keys) if key[0]==s]
   for nums in itertools.product(*[range(cc[keys[k]]+1) for k in inds]):
    m=sum(keys[k][1]*a for k,a in zip(inds,nums));v=sum(keys[k][2]*a for k,a in zip(inds,nums))
    if not m or m>Q or v>V:continue
    co=[0]*len(keys)
    for k,a in zip(inds,nums):co[k]=a
    ps.append(ni[s]);pm.append(m);pv.append(v);counts.append(co);services.append(t['handover_base_s']+(t['load_per_box_s']+t['handover_per_box_s'])*sum(nums))
  out.append((tau,np.array(ps),np.array(pm),np.array(pv),np.array(counts,np.int64),np.array(services,np.int64)))
 return T,keys,d,out

def prices(T,D,pi,lam,cuts=(),sigma=()):
 pp=np.array(pi,np.int64);vals=[]
 for t,(tau,ps,pm,pv,cnt,svc),la in zip(T,D,lam):
  scores=la*svc*H-(cnt@pp)*H;cost=la*tau
  for mask,sg in zip(cuts,sigma):
   for i in range(1,16):
    if mask&(1<<(i-1)):
     for j in range(16):
      if not j or not (mask&(1<<(j-1))):cost[i,j]-=sg*H
  maxstops=min(t['max_payload_kg']//3,round(t['max_volume_m3']*1000)//12)
  guard=(maxstops+2)*(int(cost.max())+int(np.abs(scores).max())+la*t['prep_s']*H)
  assert guard < 2**61,('integer overflow risk',guard)
  vals.append(int(min_price_int(t['max_payload_kg'],round(t['max_volume_m3']*1000),cost,ps,pm,pv,scores,la*t['prep_s']*H)))
 return vals

def run(verify_only=False,use_cuts=False):
 T,keys,d,D=data();path=ROOT/('results/rational_certificate_cuts.json' if use_cuts else 'results/rational_certificate.json')
 if not verify_only:
  a=json.loads((ROOT/('results/cg_cuts_bound.json' if use_cuts else 'results/cg_bound.json')).read_text())['numerical_certificate'];assert not any(a['mu'])
  cuts=a.get('capacity_cuts',[]) if use_cuts else [];rhs=a.get('cut_rhs',[]) if use_cuts else [];sigma=[math.floor(Fraction(str(x))*S) for x in a.get('sigma',[])] if use_cuts else []
  pi=[math.floor(Fraction(str(x))*S) for x in a['pi']];lam=[math.floor(Fraction(str(x))*S) for x in a['lambda']]
  red=prices(T,D,pi,lam,cuts,sigma);repair=max(0,(-min(red)+H-1)//H)
  pi=[p-repair for p in pi];red2=prices(T,D,pi,lam,cuts,sigma);assert min(red2)>=0
  cert={'version':1,'dual_scale':S,'time_scale':H,'demand_keys':keys,'demands':d,'capacity_cuts':cuts,'cut_rhs':rhs,'sigma_integer':sigma,'pi_integer':pi,'lambda_integer':lam,'minimum_reduced_cost_integer':red2,'repair_pi_units':repair,'lower_bound_numerator':sum(p*c for p,c in zip(pi,d))+sum(x*y for x,y in zip(rhs,sigma)),'lower_bound_denominator':S,'input_hashes':{n:hashlib.sha256((ROOT/'inputs'/n).read_bytes()).hexdigest() for n in ['boxes.json','types.json','legs.json']},'universe':'mass/volume-bounded walks; positive delivery visits; repeat classes and sites allowed; shortest-time closure allows non-delivery transits; no energy/deadlines/charging; all physical schedules map into this LOWER relaxation'}
  path.write_text(json.dumps(cert,ensure_ascii=False,indent=2))
 cert=json.loads(path.read_text());assert cert['dual_scale']==S and cert['time_scale']==H
 assert all(hashlib.sha256((ROOT/'inputs'/n).read_bytes()).hexdigest()==h for n,h in cert['input_hashes'].items())
 assert cert['demand_keys']==[list(k) for k in keys] and cert['demands']==d
 lam=cert['lambda_integer'];assert min(lam)>=0 and sum(len(t['aircraft'])*la for t,la in zip(T,lam))<=S
 cuts=cert.get('capacity_cuts',[]);rhs=cert.get('cut_rhs',[]);sigma=cert.get('sigma_integer',[])
 assert len(cuts)==len(rhs)==len(sigma) and all(v>=0 for v in sigma)
 sites=sorted({k[0] for k in keys})
 for mask,b in zip(cuts,rhs):
  selected={sites[i] for i in range(15) if mask&(1<<i)}
  mass=sum(k[1]*n for k,n in zip(keys,d) if k[0] in selected);vol=sum(k[2]*n for k,n in zip(keys,d) if k[0] in selected)
  assert b==max((mass+79)//80,(vol+249)//250)
 red=prices(T,D,cert['pi_integer'],lam,cuts,sigma);assert min(red)>=0 and red==cert['minimum_reduced_cost_integer']
 numer=sum(p*c for p,c in zip(cert['pi_integer'],d))+sum(x*y for x,y in zip(rhs,sigma));assert numer==cert['lower_bound_numerator'];lb=Fraction(numer,S)
 out={'certificate_valid':True,'arithmetic':'int64 guarded against overflow + Fraction for input rounding','lower_bound_exact_fraction':str(lb),'lower_bound_s':float(lb),'min_reduced_cost_integers':red,'fleet_dual_budget_numerator':sum(len(t['aircraft'])*la for t,la in zip(T,lam)),'fleet_dual_budget_denominator':S,'original_global_optimal_proved':False}
 (ROOT/('results/rational_certificate_cuts_verification.json' if use_cuts else 'results/rational_certificate_verification.json')).write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2));return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--verify-only',action='store_true');p.add_argument('--cuts',action='store_true');a=p.parse_args();run(a.verify_only,a.cuts)
