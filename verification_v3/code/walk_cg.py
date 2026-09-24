"""Complete pricing of a route-resource relaxation, with integer dual certificates.
NOT original schedule or global integer optimality. See docs/model_v3.md.
"""
from pathlib import Path
from collections import Counter
from fractions import Fraction
import argparse,json,time,math,itertools,subprocess,sys
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csc_matrix
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results';SCALE=10**7

def save(p,d):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False,default=lambda x:x.item() if isinstance(x,np.generic) else str(x))+'\n')

class Engine:
 def __init__(self,quantum=.001):
  self.quantum=quantum;d=ROOT/'data'
  self.B=json.loads((d/'boxes.json').read_text());self.types=json.loads((d/'types.json').read_text());legs=json.loads((d/'legs.json').read_text())
  cnt=Counter((b['site'],b['kind'],int(b['mass_kg']),round(b['volume_m3']*1000)) for b in self.B)
  self.cls=sorted(cnt);self.demand=np.array([cnt[c] for c in self.cls],dtype=np.int64)
  self.sites=np.array([int(c[0][1:]) for c in self.cls]);self.w=np.array([c[2] for c in self.cls]);self.v=np.array([c[3] for c in self.cls])
  self.tt=[];self.ee=[];self.bud=[];self.pats=[]
  self.raw_times=[];self.raw_energy=[]
  for g,t in enumerate(self.types):
   raw=np.zeros((16,16));D=raw.copy();H=raw.copy()
   for l in legs:
    a=0 if l['from']=='O01' else int(l['from'][1:]);b=0 if l['to']=='O01' else int(l['to'][1:]);D[a,b]=l['distance_m'];H[a,b]=l['up_m'];raw[a,b]=l['up_m']/t['up_mps']+l['distance_m']/t['cruise_mps']+l['down_m']/t['down_mps']
   self.raw_times.append(raw)
   tr=np.floor(np.maximum(0,raw*1000-1e-7)).astype(np.int64)
   for k in range(16):tr=np.minimum(tr,tr[:,k,None]+tr[None,k,:])
   self.tt.append(tr);er=[];raw_e=[]
   for q in range(int(t['max_payload_kg'])+1):
    L=t['empty_range_m']-(t['empty_range_m']-t['full_range_m'])*(q/t['max_payload_kg'])**1.5
    ar=t['battery_kwh']*D/L+(t['empty_mass_kg']+q)*9.81*H/(t['up_efficiency']*3600000)
    raw_e.append(ar.copy())
    # Lower ticks first, then metric closure: triangle inequality preserved in integer arithmetic.
    aint=np.floor(np.maximum(0,ar/quantum-1e-9)).astype(np.int64)
    for k in range(16):aint=np.minimum(aint,aint[:,k,None]+aint[None,k,:])
    er.append(aint)
   self.ee.append(np.array(er));self.raw_energy.append(np.array(raw_e));self.bud.append(math.ceil((1-t['reserve_pct']/100)*t['battery_kwh']/quantum-1e-10))
   ps=[]
   for s in range(1,16):
    js=[j for j in range(len(self.cls)) if self.sites[j]==s]
    for ns in itertools.product(*(range(int(self.demand[j])+1) for j in js)):
     W=sum(self.w[j]*n for j,n in zip(js,ns));V=sum(self.v[j]*n for j,n in zip(js,ns))
     if W==0 or W>t['max_payload_kg'] or V>round(t['max_volume_m3']*1000):continue
     seq=[j for j,n in zip(js,ns) for _ in range(n)];ps.append((s,int(W),int(V),len(seq),seq))
   self.pats.append(ps)
  self.static=['\n'.join([' '.join(map(str,self.tt[g].ravel())),' '.join(map(str,self.ee[g].ravel()))]) for g in range(3)]
  self.bin=ROOT/'code/resource_pricer';src=ROOT/'code/resource_pricer.cpp'
  if not self.bin.exists() or self.bin.stat().st_mtime<src.stat().st_mtime:subprocess.run(['g++','-O3','-std=c++17',str(src),'-o',str(self.bin)],check=True)
 def column(self,g,seq):
  t=self.types[g];q=int(sum(self.w[j] for j in seq));vol=int(sum(self.v[j] for j in seq))
  if q>t['max_payload_kg'] or vol>round(t['max_volume_m3']*1000) or q==0:return None
  for s,group in itertools.groupby(seq,key=lambda j:self.sites[j]):
   if any(n>self.demand[j] for j,n in Counter(group).items()):return None
  p=t['prep_s']*1000;E=0;last=0;a=np.zeros(len(self.cls),dtype=np.int64)
  for j in seq:
   b=int(self.sites[j]);p+=(t['load_per_box_s']+t['handover_per_box_s'])*1000
   if b!=last:p+=int(self.tt[g][last,b])+t['handover_base_s']*1000;E+=int(self.ee[g][q,last,b])
   q-=int(self.w[j]);a[j]+=1;last=b
  p+=int(self.tt[g][last,0]);E+=int(self.ee[g][0,last,0])
  if E>self.bud[g]:return None
  return {'g':g,'counts':a.tolist(),'p':int(p),'e':int(E),'seq':list(map(int,seq))}
 def pricing(self,g,pi,mu,seconds=60):
  t=self.types[g];mu_g=int(mu[g]);assert mu_g>=0
  h=f"{t['max_payload_kg']} {round(t['max_volume_m3']*1000)} {len(self.pats[g])} 16 {self.bud[g]} {mu_g} {t['prep_s']*1000} {(t['load_per_box_s']+t['handover_per_box_s'])*1000} {t['handover_base_s']*1000}\n"
  text='\n'.join(f'{p[0]} {p[1]} {p[2]} {p[3]} {sum(int(pi[j]) for j in p[4])}' for p in self.pats[g])+'\n'
  st=time.perf_counter();r=subprocess.run([str(self.bin)],input=h+text+self.static[g]+'\n',text=True,capture_output=True,timeout=seconds,check=True)
  ls=r.stdout.splitlines();rc,labels,count=map(int,ls[0].split());cs=[]
  for l in ls[1:]:
   vals=list(map(int,l.split()));assert len(vals[2:])==vals[1]
   seq=[j for k in vals[2:] for j in self.pats[g][k][4]];c=self.column(g,seq);assert c is not None
   calc=mu_g*c['p']-1000*sum(int(p)*n for p,n in zip(pi,c['counts']));assert calc==vals[0],(calc,vals[0]);cs.append(c)
  return {'g':g,'minimum_rc_integer':rc,'labels':labels,'seconds':time.perf_counter()-st,'status':'complete'},cs
 def seeds(self):
  cs=[]
  for g in range(3):
   for p in self.pats[g]:
    c=self.column(g,p[4])
    if c:cs.append(c)
  bm={b['id']:b for b in self.B}
  fs=json.loads((OUT/'remote_incumbent_rebuilt/flights.json').read_text())
  for f in fs:
   seq=[]
   for s in f['route'][1:-1]:
    for bid in f['box_ids']:
     b=bm[bid]
     if b['site']==s:seq.append(self.cls.index((s,b['kind'],int(b['mass_kg']),round(b['volume_m3']*1000))))
   c=self.column('ABC'.index(f['type']),seq)
   assert c is not None
   cs.append(c)
  return cs

def run(quantum=.001,seconds=300):
 en=Engine(quantum);nc=len(en.cls);cols=[];seen=set();tag=f'walk_q{quantum}'
 def add(c):
  key=c['g'],tuple(c['counts']),c['p']
  if key in seen:return False
  seen.add(key);cols.append(c);return True
 for c in en.seeds():add(c)
 start=time.perf_counter();best=None;hist=[];status='iteration_limit'
 for it in range(200):
  n=len(cols);eq=np.column_stack([np.array([c['counts'] for c in cols],float).T,np.zeros(nc)]);U=np.zeros((3,n+1))
  for k,c in enumerate(cols):U[c['g'],k]=c['p']/1000
  U[:,-1]=[-len(t['aircraft']) for t in en.types];obj=np.zeros(n+1);obj[-1]=1
  r=linprog(obj,A_ub=csc_matrix(U),b_ub=np.zeros(3),A_eq=csc_matrix(eq),b_eq=en.demand,bounds=(0,None),method='highs-ds')
  if not r.success:raise RuntimeError(r.message)
  pi=np.floor(r.eqlin.marginals*SCALE).astype(np.int64);mu=np.maximum(0,np.ceil(-r.ineqlin.marginals*SCALE)).astype(np.int64)
  added=0;recs=[]
  try:
   for g in range(3):
    rec,cs=en.pricing(g,pi,mu,max(1,seconds-(time.perf_counter()-start)));recs.append(rec)
    for c in cs:
     if int(mu[g])*c['p']-1000*sum(int(p)*a for p,a in zip(pi,c['counts']))<0:added+=add(c)
  except subprocess.TimeoutExpired:status='pricing_timeout_no_new_certificate';break
  mins=[x['minimum_rc_integer'] for x in recs];repair=max(0,(-min(mins)+999)//1000);newpi=pi-repair
  den=max(SCALE,sum(len(t['aircraft'])*int(m) for t,m in zip(en.types,mu)));num=sum(int(n)*int(p) for n,p in zip(en.demand,newpi));lb=num/den
  cert={'pi_integer':newpi.tolist(),'mu_integer':mu.tolist(),'numerator':num,'denominator':den,'pricing_minima_before_repair':mins,'uniform_repair_per_box':int(repair),'quantum_kwh':quantum,'class_order':[list(c) for c in en.cls],'lower_bound_s':lb,'scope':'repeated delivery walks, quantized optimistic energy/time, route LP, no deadlines or detailed scheduling'}
  if best is None or lb>best['lower_bound_s']:best=cert;save(OUT/f'{tag}_certificate.json',best)
  row={'it':it,'columns':n,'rmp_s':r.fun,'best_lb_s':best['lower_bound_s'],'added':added,'pricing':recs,'elapsed_s':time.perf_counter()-start};hist.append(row);print(json.dumps(row),flush=True);save(OUT/f'{tag}_history.json',hist)
  if min(mins)>=0:status='pricing_nonnegative';break
  if not added:status='no_new_column';break
  if time.perf_counter()-start>seconds:status='wall_limit';break
 save(OUT/f'{tag}_columns.json',cols)
 summary={'status':status,'quantum':quantum,'lb_s':None if best is None else best['lower_bound_s'],'columns':len(cols),'iterations':len(hist),'runtime_s':time.perf_counter()-start,'full_optimality_proven':False};save(OUT/f'{tag}_summary.json',summary);print('FINAL',json.dumps(summary),flush=True)
 return summary
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--quantum',type=float,default=.001);p.add_argument('--seconds',type=float,default=300);a=p.parse_args();run(a.quantum,a.seconds)
