"""Complete integer pricing of an elementary METRIC/MONOTONE RELAXATION.
Original routes are projected by first-visit consolidation only after removing
box deadlines and detailed scheduling. This is NOT a ban on original revisits.
"""
from pathlib import Path
from collections import Counter
from fractions import Fraction
import argparse,json,time,math,itertools,subprocess
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csc_matrix
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results'

def save(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

def setup(quantum=.001):
 B=json.loads((ROOT/'data/boxes.json').read_text());types=json.loads((ROOT/'data/types.json').read_text());legs=json.loads((ROOT/'data/legs.json').read_text())
 cls=sorted(Counter((b['site'],b['kind'],int(b['mass_kg']),round(b['volume_m3']*1000)) for b in B));cnt=Counter((b['site'],b['kind'],int(b['mass_kg']),round(b['volume_m3']*1000)) for b in B)
 demand=np.array([cnt[c] for c in cls],dtype=np.int64);sites=np.array([int(c[0][1:]) for c in cls]);w=np.array([c[2] for c in cls]);v=np.array([c[3] for c in cls]);tt=[];ee=[];bud=[];raws=[]
 for t in types:
  raw=np.zeros((16,16));D=np.zeros((16,16));H=np.zeros((16,16))
  for l in legs:
   a=0 if l['from']=='O01' else int(l['from'][1:]);b=0 if l['to']=='O01' else int(l['to'][1:]);D[a,b]=l['distance_m'];H[a,b]=l['up_m'];raw[a,b]=l['up_m']/t['up_mps']+l['distance_m']/t['cruise_mps']+l['down_m']/t['down_mps']
  raws.append(raw)
  tr=np.floor(np.maximum(0,raw*1000-1e-7)).astype(np.int64)
  for k in range(16):tr=np.minimum(tr,tr[:,k,None]+tr[None,k,:])
  tt.append(tr);er=[]
  for q in range(t['max_payload_kg']+1):
   L=t['empty_range_m']-(t['empty_range_m']-t['full_range_m'])*(q/t['max_payload_kg'])**1.5
   ar=t['battery_kwh']*D/L+(t['empty_mass_kg']+q)*9.81*H/(t['up_efficiency']*3600000)
   for k in range(16):ar=np.minimum(ar,ar[:,k,None]+ar[None,k,:])
   er.append(np.floor(np.maximum(0,ar/quantum-1e-9)).astype(np.int64))
  ee.append(np.array(er));bud.append(math.ceil((1-t['reserve_pct']/100)*t['battery_kwh']/quantum-1e-10))
 pats=[]
 for t in types:
  ps=[]
  for s in range(1,16):
   js=[j for j in range(len(cls)) if sites[j]==s]
   for ns in itertools.product(*(range(int(demand[j])+1) for j in js)):
    W=sum(w[j]*n for j,n in zip(js,ns));V=sum(v[j]*n for j,n in zip(js,ns))
    if W==0 or W>t['max_payload_kg'] or V>round(t['max_volume_m3']*1000):continue
    seq=[j for j,n in zip(js,ns) for _ in range(n)];ps.append((s,int(W),int(V),len(seq),seq))
  pats.append(ps)
 return B,types,cls,demand,sites,w,v,tt,ee,bud,pats

class Engine:
 def __init__(self,quantum=.001,elementary=True,level=0):
  self.quantum=quantum;self.elem=elementary
  self.B,self.types,self.cls,self.demand,self.sites,self.w,self.v,self.tt,self.ee,self.bud,self.pats=setup(quantum)
  self.cuts=[]
  for size in range(1,level+1):
   for ns in itertools.combinations(range(1,16),size):
    W=sum(int(d*n) for d,n,s in zip(self.demand,self.w,self.sites) if s in ns);V=sum(int(d*n) for d,n,s in zip(self.demand,self.v,self.sites) if s in ns)
    rhs=max(math.ceil(W/80),math.ceil(V/250))
    if size==1 or rhs>1:self.cuts.append({'nodes':list(ns),'mask':sum(1<<(s-1) for s in ns),'rhs':rhs})
  self.static=['\n'.join([' '.join(map(str,self.tt[g].ravel())),' '.join(map(str,self.ee[g].ravel()))]) for g in range(3)]
  self.bin=ROOT/'code/resource_pricer';src=ROOT/'code/resource_pricer.cpp'
  if not self.bin.exists() or self.bin.stat().st_mtime<src.stat().st_mtime:subprocess.run(['g++','-O3','-std=c++17',str(src),'-o',str(self.bin)],check=True)
 def column(self,g,seq):
  t=self.types[g];q=int(sum(self.w[j] for j in seq));vol=int(sum(self.v[j] for j in seq))
  if q>t['max_payload_kg'] or vol>round(t['max_volume_m3']*1000) or q==0:return None
  order=[s for s,_ in itertools.groupby(self.sites[j] for j in seq)]
  if self.elem and len(set(order))!=len(order):return None
  for s,group in itertools.groupby(seq,key=lambda j:self.sites[j]):
   if any(n>self.demand[j] for j,n in Counter(group).items()):return None
  p=t['prep_s']*1000;E=0;last=0;a=np.zeros(len(self.cls),dtype=np.int64)
  for j in seq:
   b=int(self.sites[j]);p+=(t['load_per_box_s']+t['handover_per_box_s'])*1000
   if b!=last:p+=int(self.tt[g][last,b])+t['handover_base_s']*1000;E+=int(self.ee[g][q,last,b])
   q-=int(self.w[j]);a[j]+=1;last=b
  p+=int(self.tt[g][last,0]);E+=int(self.ee[g][0,last,0])
  if E>self.bud[g]:return None
  mask=sum(1<<(s-1) for s in set(order))
  return {'g':g,'counts':a.tolist(),'p':p,'e':E,'seq':list(map(int,seq)),'hits':[int(bool(mask&c['mask'])) for c in self.cuts]}
 def pricing(self,g,pi,mu,rho,seconds=60):
  t=self.types[g]
  h=f"{t['max_payload_kg']} {round(t['max_volume_m3']*1000)} {len(self.pats[g])} 16 {self.bud[g]} {int(mu[g])} {t['prep_s']*1000} {(t['load_per_box_s']+t['handover_per_box_s'])*1000} {t['handover_base_s']*1000} {int(self.elem)} {len(self.cuts)}\n"
  lines='\n'.join(f'{p[0]} {p[1]} {p[2]} {p[3]} {sum(int(pi[j]) for j in p[4])}' for p in self.pats[g])+'\n'
  lines+='\n'.join(f"{c['mask']} {int(v)}" for c,v in zip(self.cuts,rho))+'\n'
  st=time.perf_counter();r=subprocess.run([str(self.bin)],input=h+lines+self.static[g]+'\n',text=True,capture_output=True,timeout=seconds,check=True)
  ls=r.stdout.splitlines();rc,labels,count=map(int,ls[0].split());cs=[]
  for l in ls[1:]:
   vals=list(map(int,l.split()));seq=[j for k in vals[2:] for j in self.pats[g][k][4]];c=self.column(g,seq)
   assert c is not None
   calc=int(mu[g])*c['p']-1000*sum(int(p)*n for p,n in zip(pi,c['counts']))-1000*sum(int(p)*n for p,n in zip(rho,c['hits']))
   assert calc==vals[0],(calc,vals[0]);cs.append(c)
  return {'g':g,'minimum_rc_integer':rc,'labels':labels,'seconds':time.perf_counter()-st,'status':'complete'},cs

def run(quantum=.001,elem=True,level=0,maxit=100,seconds=300):
 en=Engine(quantum,elem,level);nc=len(en.cls);cols=[];seen=set();tag=f"elementary{int(elem)}_cuts{level}_q{quantum}";scale=10**7
 def add(c):
  if c is None:return False
  k=(c['g'],tuple(c['counts']),c['p'],tuple(c['hits']))
  if k in seen:return False
  seen.add(k);cols.append(c);return True
 for g in range(3):
  for p in en.pats[g]:add(en.column(g,p[4]))
 fs=json.loads((ROOT/'data/flights.json').read_text());bm={b['id']:b for b in en.B}
 for f in fs:
  seq=[]
  for s in f['route'][1:-1]:
   for bid in f['box_ids']:
    b=bm[bid]
    if b['site']==s:seq.append(en.cls.index((s,b['kind'],int(b['mass_kg']),round(b['volume_m3']*1000))))
  add(en.column('ABC'.index(f['type']),seq))
 # Previous L0 output can warm the stronger problem, never bounds its scope.
 if level>0:
  p=OUT/f'elementary1_cuts0_q{quantum}_columns.json'
  if p.exists():
   for c in json.loads(p.read_text()):add(en.column(c['g'],c['seq']))
 start=time.perf_counter();best=None;hist=[];status='iteration_limit';last_duals=None
 for it in range(maxit):
  n=len(cols);A=np.column_stack([np.array([c['counts'] for c in cols],float).T,np.zeros(nc)]);U=np.zeros((3+len(en.cuts),n+1));ub=np.r_[np.zeros(3),-np.array([c['rhs'] for c in en.cuts])]
  for k,c in enumerate(cols):U[c['g'],k]=c['p']/1000;U[3:,k]=-np.array(c['hits'])
  U[:3,-1]=[-len(t['aircraft']) for t in en.types];obj=np.zeros(n+1);obj[-1]=1
  r=linprog(obj,A_ub=csc_matrix(U),b_ub=ub,A_eq=csc_matrix(A),b_eq=en.demand,bounds=(0,None),method='highs-ds')
  if not r.success:raise RuntimeError(r.message)
  pi=np.floor(r.eqlin.marginals*scale).astype(np.int64);mu=np.maximum(0,np.ceil(-r.ineqlin.marginals[:3]*scale)).astype(np.int64)
  rho=np.maximum(0,np.floor(-r.ineqlin.marginals[3:]*scale)).astype(np.int64)
  added=0;recs=[]
  try:
   for g in range(3):
    rec,cs=en.pricing(g,pi,mu,rho,max(2,seconds-(time.perf_counter()-start)));recs.append(rec)
    for c in cs:
     calc=int(mu[g])*c['p']-1000*sum(int(p)*n for p,n in zip(pi,c['counts']))-1000*sum(int(p)*n for p,n in zip(rho,c['hits']))
     if calc<0:added+=add(c)
  except subprocess.TimeoutExpired:status='pricing_timeout_no_new_certificate';break
  mins=[x['minimum_rc_integer'] for x in recs];correction=max(0,(-min(mins)+999)//1000);newpi=pi-correction
  den=max(scale,sum(len(t['aircraft'])*int(m) for t,m in zip(en.types,mu)))
  num=sum(int(n)*int(p) for n,p in zip(en.demand,newpi))+sum(c['rhs']*int(p) for c,p in zip(en.cuts,rho));lb=num/den
  cert={'pi_integer':newpi.tolist(),'mu_integer':mu.tolist(),'rho_integer':rho.tolist(),'numerator':num,'denominator':den,'pricing_minima_before_repair':mins,'correction_per_box':int(correction),'quantum_kwh':quantum,'elementary_relaxation':elem,'cut_level':level,'cuts':en.cuts,'class_order':[list(c) for c in en.cls],'lower_bound_s':lb}
  if best is None or lb>best['lower_bound_s']:best=cert;save(OUT/f'{tag}_certificate.json',best)
  row={'it':it,'cols':n,'rmp_s':float(r.fun),'best_lb_s':best['lower_bound_s'],'added':added,'pricing':recs,'elapsed_s':time.perf_counter()-start};hist.append(row);print(json.dumps(row),flush=True);save(OUT/f'{tag}_history.json',hist)
  if min(mins)>=0:status='complete_integer_pricing_nonnegative';break
  if not added:status='no_new_column';break
  if time.perf_counter()-start>seconds:status='wall_limit';break
 save(OUT/f'{tag}_columns.json',cols)
 summary={'scope':'valid relaxation with first-visit projection, no detailed scheduling/deadlines','elementary':elem,'level':level,'quantum':quantum,'status':status,'lb_s':None if best is None else best['lower_bound_s'],'iterations':len(hist),'columns':len(cols),'time_s':time.perf_counter()-start,'original_global_optimality_proved':False};save(OUT/f'{tag}_summary.json',summary);print('FINAL',json.dumps(summary),flush=True)
 return summary
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--quantum',type=float,default=.001);p.add_argument('--repeat',action='store_true');p.add_argument('--level',type=int,default=0);p.add_argument('--seconds',type=float,default=300);a=p.parse_args();run(a.quantum,not a.repeat,a.level,seconds=a.seconds)
