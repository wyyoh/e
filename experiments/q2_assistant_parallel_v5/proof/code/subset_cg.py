"""Add valid rank-1 Chvatal-Gomory subset-row cuts to the route LP.
All pricing is complete integer DP, with repeated visits allowed.
"""
from walk_cg import *

class CutEngine(Engine):
 def __init__(self,cuts,quantum=.001):
  super().__init__(quantum);self.cuts=cuts
  self.bin=ROOT/'code/cut_pricer';src=ROOT/'code/cut_pricer.cpp'
  if not self.bin.exists() or self.bin.stat().st_mtime<src.stat().st_mtime:subprocess.run(['g++','-O3','-std=c++17',str(src),'-o',str(self.bin)],check=True)
 def features(self,c):return [sum(c['counts'][j] for j in cut['classes'])//2 for cut in self.cuts]
 def pricing(self,g,pi,mu,pen,seconds=60):
  t=self.types[g];K=len(self.cuts)
  h=f"{t['max_payload_kg']} {round(t['max_volume_m3']*1000)} {len(self.pats[g])} 16 {self.bud[g]} {int(mu[g])} {t['prep_s']*1000} {(t['load_per_box_s']+t['handover_per_box_s'])*1000} {t['handover_base_s']*1000} {K}\n"
  text=''
  for p in self.pats[g]:
   n=Counter(p[4]);cs=[sum(n[j] for j in c['classes']) for c in self.cuts]
   text+=' '.join(map(str,[p[0],p[1],p[2],p[3],sum(int(pi[j]) for j in p[4]),*cs]))+'\n'
  text+=' '.join(map(str,pen))+'\n'
  st=time.perf_counter();r=subprocess.run([str(self.bin)],input=h+text+self.static[g]+'\n',text=True,capture_output=True,timeout=seconds,check=True)
  ls=r.stdout.splitlines();rc,labels,count=map(int,ls[0].split());cols=[]
  for line in ls[1:]:
   vals=list(map(int,line.split()));seq=[j for k in vals[2:] for j in self.pats[g][k][4]];c=self.column(g,seq);assert c is not None
   calc=int(mu[g])*c['p']-1000*sum(int(p)*n for p,n in zip(pi,c['counts']))+1000*sum(int(p)*n for p,n in zip(pen,self.features(c)))
   assert calc==vals[0],(calc,vals[0]);cols.append(c)
  return {'g':g,'minimum_rc_integer':rc,'labels':labels,'seconds':time.perf_counter()-st,'status':'complete'},cols

def pick_cuts(en,cols,x,excluded,count):
 active=[(c,float(v)) for c,v in zip(cols,x) if v>1e-8];opts=[]
 # Exhaustive rank-one rows over one to three aggregate item classes.
 for size in [1,2,3]:
  for js in itertools.combinations(range(len(en.cls)),size):
   if js in excluded:continue
   demand=sum(en.demand[j] for j in js)
   if demand%2==0:continue
   rhs=int(demand)//2;lhs=sum(sum(c['counts'][j] for j in js)//2*v for c,v in active)
   if lhs>rhs+1e-6:opts.append((lhs-rhs,js,rhs))
 opts.sort(reverse=True);picked=[]
 for viol,js,rhs in opts:
  # A selection policy only; unselected valid cuts remain absent from the relaxation.
  if any(set(js)&set(c['classes']) for c in picked):continue
  picked.append({'classes':list(js),'rhs':rhs,'separation_violation':viol})
  if len(picked)==count:break
 return picked

def run_cut(maxcuts=5,seconds=360,quantum=.001):
 cols=json.loads((OUT/'walk_q0.001_columns.json').read_text());en=CutEngine([],quantum)
 cols=[en.column(c['g'],c['seq']) for c in cols];cols=[c for c in cols if c is not None]
 keys={(c['g'],tuple(c['counts']),c['p']) for c in cols};nc=len(en.cls);start=time.perf_counter();hist=[];best=None;status='wall_limit'
 for it in range(150):
  n=len(cols);K=len(en.cuts);eq=np.column_stack([np.array([c['counts'] for c in cols],float).T,np.zeros(nc)]);U=np.zeros((3+K,n+1))
  for k,c in enumerate(cols):U[c['g'],k]=c['p']/1000;U[3:,k]=en.features(c)
  U[:3,-1]=[-len(t['aircraft']) for t in en.types];obj=np.r_[np.zeros(n),1.]
  r=linprog(obj,A_eq=csc_matrix(eq),b_eq=en.demand,A_ub=csc_matrix(U),b_ub=np.r_[np.zeros(3),[c['rhs'] for c in en.cuts]],bounds=(0,None),method='highs-ds')
  if not r.success:raise RuntimeError(r.message)
  pi=np.floor(r.eqlin.marginals*SCALE).astype(np.int64);mu=np.maximum(0,np.ceil(-r.ineqlin.marginals[:3]*SCALE)).astype(np.int64);pen=np.maximum(0,np.ceil(-r.ineqlin.marginals[3:]*SCALE)).astype(np.int64)
  added=0;recs=[]
  try:
   for g in range(3):
    rec,cs=en.pricing(g,pi,mu,pen,max(1,seconds-(time.perf_counter()-start)));recs.append(rec)
    for c in cs:
     key=c['g'],tuple(c['counts']),c['p']
     rc=int(mu[g])*c['p']-1000*sum(int(v)*a for v,a in zip(pi,c['counts']))+1000*sum(int(v)*a for v,a in zip(pen,en.features(c)))
     if rc<0 and key not in keys:cols.append(c);keys.add(key);added+=1
  except subprocess.TimeoutExpired:status='pricing_timeout';break
  mins=[z['minimum_rc_integer'] for z in recs];fix=max(0,(-min(mins)+999)//1000);newpi=pi-fix
  den=max(SCALE,sum(len(t['aircraft'])*int(m) for t,m in zip(en.types,mu)));num=sum(int(a)*int(p) for a,p in zip(en.demand,newpi))-sum(int(p)*c['rhs'] for p,c in zip(pen,en.cuts))
  cert={'lower_bound_s':num/den,'numerator':num,'denominator':den,'pi_integer':newpi.tolist(),'mu_integer':mu.tolist(),'cut_penalties_integer':pen.tolist(),'cuts':en.cuts.copy(),'quantum_kwh':quantum,'uniform_repair_per_box':fix,'pricing':recs,'scope':'valid integer-route inequalities, relaxed master and complete repeated-walk pricing'}
  if best is None or cert['lower_bound_s']>best['lower_bound_s']:best=cert;save(OUT/'subset_certificate.json',best)
  row={'it':it,'columns':n,'cuts':len(en.cuts),'rmp_s':r.fun,'best_lb_s':best['lower_bound_s'],'added':added,'pricing':recs,'elapsed_s':time.perf_counter()-start};hist.append(row);print(json.dumps(row),flush=True)
  if min(mins)>=0 or added==0:
   more=pick_cuts(en,cols[:n],r.x[:n],{tuple(c['classes']) for c in en.cuts},maxcuts-len(en.cuts)) if len(en.cuts)<maxcuts else []
   if not more:status='pricing_complete_cut_limit';break
   en.cuts+=more;print('ADD CUTS',more,flush=True)
  if time.perf_counter()-start>seconds:break
 save(OUT/'subset_history.json',hist);save(OUT/'subset_columns.json',cols);save(OUT/'subset_cuts.json',en.cuts)
 s={'lower_bound_s':best['lower_bound_s'] if best else None,'cuts':len(en.cuts),'columns':len(cols),'status':status,'runtime_s':time.perf_counter()-start,'global_optimality_proven':False};save(OUT/'subset_summary.json',s);print('FINAL',json.dumps(s),flush=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--seconds',type=float,default=360);ap.add_argument('--cuts',type=int,default=5);ap.add_argument('--quantum',type=float,default=.001);a=ap.parse_args();run_cut(a.cuts,a.seconds,a.quantum)
