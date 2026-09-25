"""Exact pricing at each node of a partial-integrality relaxation.
Every open and terminal region is kept in the global minimum. No original-IP proof.
"""
import json,time,heapq,math,argparse
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csc_matrix
from walk_cg import Engine,ROOT,OUT,save,SCALE
BIG=100000.

def rows_of(bounds):
 rows=[]
 for (g,j),(lo,hi) in sorted(bounds.items()):
  if hi<80:rows.append((g,j,1,int(hi)))
  if lo>0:rows.append((g,j,-1,-int(lo)))
 return rows

def feature(c,g,j):return (1 if j==-1 else c['counts'][j]) if c['g']==g else 0

def certify(en,pi,mu,zz,rows,seconds):
 st=time.perf_counter();recs=[];news=[]
 for g in range(3):
  pp=pi.copy();constant=0
  for z,(gg,j,sign,b) in zip(zz,rows):
   if gg!=g:continue
   if j==-1:constant-=int(z)*sign*1000
   else:pp[j]+=int(z)*sign
  rec,cs=en.pricing(g,pp,mu,max(1,seconds-(time.perf_counter()-st)));rec['minimum_rc_integer']+=constant;recs.append(rec)
  for c in cs:
   if int(mu[g])*c['p']-1000*sum(int(v)*n for v,n in zip(pp,c['counts']))+constant<0:news.append(c)
 repair=max(0,(-min(r['minimum_rc_integer'] for r in recs)+999)//1000);newpi=pi-repair
 den=max(SCALE,sum(len(t['aircraft'])*int(v) for t,v in zip(en.types,mu)))
 num=sum(int(a)*int(v) for a,v in zip(en.demand,newpi))+sum(int(z)*row[3] for z,row in zip(zz,rows))
 return {'lower_bound_s':num/den,'numerator':num,'denominator':den,'pi_integer':newpi.tolist(),'mu_integer':mu.tolist(),'row_duals_integer':zz.tolist(),'rows':rows,'uniform_repair_per_box':repair,'pricing':recs,'quantum_kwh':en.quantum},news

def choose(cols,x,mode):
 feats={}
 for c,v in zip(cols,x):
  if v<1e-9:continue
  g=c['g'];feats[g,-1]=feats.get((g,-1),0)+v
  if mode=='all':
   for j,n in enumerate(c['counts']):
    if n:feats[g,j]=feats.get((g,j),0)+v*n
 opts=[]
 for key,v in feats.items():
  dist=abs(v-round(v))
  if dist>1e-6:opts.append(((int(key[1]==-1),dist),key,v))
 return None if not opts else max(opts)[1:]

def main(seconds=400,maxnodes=600,mode='all',resume=False):
 en=Engine(.001);nc=len(en.cls);cols=[];keys=set()
 def add(c):
  k=c['g'],tuple(c['counts']),c['p']
  if k in keys:return False
  keys.add(k);cols.append(c);return True
 for c in json.loads((OUT/'walk_q0.001_columns.json').read_text()):add(c)
 UB=json.loads((OUT/'remote_incumbent_rebuilt/metrics.json').read_text())['makespan_s']
 initial=json.loads((OUT/'walk_q0.001_certificate.json').read_text())['lower_bound_s']
 start=time.perf_counter();heap=[(initial,0,{})];nextid=1;solved=[];terminal=[];status='node_limit';out=OUT/f'bp_{mode}';out.mkdir(exist_ok=True)
 prior_seconds=0
 if resume:
  tree=json.loads((out/'tree.json').read_text());summary=json.loads((out/'summary.json').read_text());prior_seconds=summary['total_runtime_s']
  cols=json.loads((out/'columns.json').read_text());keys={(c['g'],tuple(c['counts']),c['p']) for c in cols}
  solved=tree['solved'];terminal=tree['terminal'];heap=[(lb,i,{(g,j):(lo,hi) for g,j,lo,hi in bs}) for lb,i,bs in tree['open']];heapq.heapify(heap);nextid=tree['nextid']
 while heap and len(solved)<maxnodes:
  if time.perf_counter()-start>seconds:status='wall_limit';break
  inherited,nodeid,bounds=heapq.heappop(heap);rows=rows_of(bounds);best=None;hist=[];last=None
  for it in range(100):
   if time.perf_counter()-start>seconds:break
   n=len(cols);lowers=[k for k,r in enumerate(rows) if r[2]<0];nvar=n+1+nc+len(lowers)
   eq=np.zeros((nc,nvar));eq[:,:n]=np.array([c['counts'] for c in cols],float).T;eq[:,n+1:n+1+nc]=np.eye(nc)
   U=np.zeros((3+len(rows),nvar));bu=np.r_[np.zeros(3),[r[3] for r in rows]]
   for k,c in enumerate(cols):
    U[c['g'],k]=c['p']/1000
    for ri,(g,j,sign,b) in enumerate(rows):U[3+ri,k]=sign*feature(c,g,j)
   U[:3,n]=[-len(t['aircraft']) for t in en.types]
   for k,ri in enumerate(lowers):U[3+ri,n+1+nc+k]=-1
   obj=np.zeros(nvar);obj[n]=1;obj[n+1:]=BIG
   res=linprog(obj,A_eq=csc_matrix(eq),b_eq=en.demand,A_ub=csc_matrix(U),b_ub=bu,bounds=(0,None),method='highs-ds')
   if not res.success:raise RuntimeError(res.message)
   pi=np.floor(res.eqlin.marginals*SCALE).astype(np.int64);mu=np.maximum(0,np.ceil(-res.ineqlin.marginals[:3]*SCALE)).astype(np.int64);zz=-np.maximum(0,np.floor(-res.ineqlin.marginals[3:]*SCALE)).astype(np.int64)
   try:cert,cs=certify(en,pi,mu,zz,rows,max(1,seconds-(time.perf_counter()-start)))
   except Exception as exc:hist.append({'pricing_error':repr(exc)});break
   if best is None or cert['lower_bound_s']>best['lower_bound_s']:best=cert
   added=sum(add(c) for c in cs);mins=[x['minimum_rc_integer'] for x in cert['pricing']]
   hist.append({'iteration':it,'rmp':res.fun,'best_lb':best['lower_bound_s'],'added':added,'minrc':mins})
   if min(mins)>=0 or added==0:
    last={'x':res.x[:n].copy(),'ncols':n,'artificial':float(res.x[n+1:].sum())};break
   if best['lower_bound_s']>UB+1e-6:break
  lb=max(inherited,0 if best is None else best['lower_bound_s']);branch=None;children=[]
  if lb>UB+1e-6:action='bound_prune';terminal.append({'id':nodeid,'lb':lb,'action':action})
  elif last is not None and last['artificial']<1e-7:
   branch=choose(cols[:last['ncols']],last['x'],mode)
   if branch is None:action='partial_integer_leaf';terminal.append({'id':nodeid,'lb':lb,'action':action})
   else:
    (g,j),value=branch;lo,hi=bounds.get((g,j),(0,80));mid=math.floor(value)
    for lr in [(lo,mid),(mid+1,hi)]:
     ch=dict(bounds);ch[g,j]=lr;children.append(nextid);heapq.heappush(heap,(lb,nextid,ch));nextid+=1
    action='branched'
  else:
   action='unresolved';heapq.heappush(heap,(lb,nodeid,bounds));status='pricing_or_wall_incomplete'
  record={'id':nodeid,'bounds':[[g,j,lo,hi] for (g,j),(lo,hi) in sorted(bounds.items())],'inherited_lb':inherited,'lb':lb,'action':action,'branch':None if branch is None else [list(branch[0]),float(branch[1])],'children':children,'certificate':best,'history':hist}
  save(out/f'node_{nodeid:04d}.json',record)
  if action!='unresolved':solved.append({k:record[k] for k in ['id','bounds','lb','action','branch','children']})
  lows=[h[0] for h in heap]+[r['lb'] for r in terminal];global_lb=min([UB]+lows)
  print(json.dumps({'nodes':len(solved),'open':len(heap),'terminal':len(terminal),'global_lb_s':global_lb,'ub_s':UB,'gap':(UB-global_lb)/UB,'node':nodeid,'node_lb':lb,'action':action,'columns':len(cols),'elapsed_s':time.perf_counter()-start}),flush=True)
  if action=='unresolved':break
 if not heap:status='partial_integrality_tree_closed'
 global_lb=min([UB]+[h[0] for h in heap]+[r['lb'] for r in terminal]);elapsed=time.perf_counter()-start
 save(out/'columns.json',cols);save(out/'tree.json',{'solved':solved,'open':[[lb,i,[[g,j,lo,hi] for (g,j),(lo,hi) in sorted(b.items())]] for lb,i,b in heap],'terminal':terminal,'nextid':nextid})
 report={'status':status,'lower_bound_s':global_lb,'upper_bound_s':UB,'gap':(UB-global_lb)/UB,'processed':len(solved),'open':len(heap),'terminal':len(terminal),'runtime_s':elapsed,'total_runtime_s':prior_seconds+elapsed,'branch_on':mode,'quantum_kwh':.001,'scope':'ALL original schedules mapped into repeated-walk route relaxation; only per-type counts/allocations integral. Full original integrality and schedule NOT proved.','original_global_optimality_proven':False}
 save(out/'summary.json',report);print('FINAL',json.dumps(report),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--seconds',type=float,default=400);p.add_argument('--nodes',type=int,default=600);p.add_argument('--mode',choices=['all','trips'],default='all');p.add_argument('--resume',action='store_true');a=p.parse_args();main(a.seconds,a.nodes,a.mode,a.resume)
