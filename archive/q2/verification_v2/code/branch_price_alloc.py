"""Branch-and-price for PARTIAL INTEGRALITY lower-bound relaxation.
Branch on integer per-type trip counts and/or delivered physical item counts.
No route-integrality, box deadlines, or exact scheduling claim.
"""
import json,time,heapq,math,argparse
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csc_matrix
from elementary_cg import Engine,ROOT,OUT,save

SCALE=10**7; BIG=100000.0

def noderows(bounds):
 rows=[]
 for (g,j),(lo,hi) in sorted(bounds.items()):
  if hi<80:rows.append((g,j,1,int(hi)))
  if lo>0:rows.append((g,j,-1,-int(lo)))
 return rows

def feat(c,g,j):return (1 if j==-1 else c['counts'][j]) if c['g']==g else 0

def certify(en,pi,mu,zz,rows,seconds):
 recs=[];news=[];mods=[];constants=[]
 st=time.perf_counter()
 for g in range(3):
  pp=pi.copy();constant=0
  for z,(gg,j,sign,b) in zip(zz,rows):
   if gg!=g:continue
   if j==-1:constant-=int(z)*sign*1000
   else:pp[j]+=int(z)*sign
  rec,cs=en.pricing(g,pp,mu,[],max(1,seconds-(time.perf_counter()-st)))
  rec['minimum_rc_integer']+=constant;recs.append(rec);mods.append(pp.tolist());constants.append(constant)
  for c in cs:
   rc=int(mu[g])*c['p']-1000*sum(int(v)*n for v,n in zip(pp,c['counts']))+constant
   if rc<0:news.append(c)
 repair=max(0,(-min(r['minimum_rc_integer'] for r in recs)+999)//1000);newpi=pi-repair
 den=max(SCALE,sum(len(t['aircraft'])*int(v) for t,v in zip(en.types,mu)))
 num=sum(int(a)*int(v) for a,v in zip(en.demand,newpi))+sum(int(z)*row[3] for z,row in zip(zz,rows))
 return {'lower_bound_s':num/den,'numerator':num,'denominator':den,'pi_integer':newpi.tolist(),'mu_integer':mu.tolist(),'row_duals_integer':zz.tolist(),'rows':rows,'uniform_repair_per_box':repair,'pricing':recs},news

def choose_fraction(en,cols,x,branchmode):
 feats={}
 for c,v in zip(cols,x):
  if v<1e-9:continue
  g=c['g'];feats[g,-1]=feats.get((g,-1),0)+v
  for j,n in enumerate(c['counts']):
   if n:feats[g,j]=feats.get((g,j),0)+v*n
 opts=[]
 for key,v in feats.items():
  dist=abs(v-round(v))
  if dist<=1e-6:continue
  g,j=key
  if branchmode=='trips' and j!=-1:continue
  rank=(1 if j==-1 else 0,dist)
  opts.append((rank,key,v))
 return None if not opts else max(opts)[1:]


def main(seconds=600,maxnodes=100,branchmode='all',resume=False):
 en=Engine(.001,False,0);nc=len(en.cls);cols=[];keys=set()
 def add(c):
  key=c['g'],tuple(c['counts']),c['p']
  if key in keys:return False
  keys.add(key);cols.append(c);return True
 warm=OUT/'elementary1_cuts0_q0.001_columns.json'
 if warm.exists():
  for c in json.loads(warm.read_text()):add(en.column(c['g'],c['seq']))
 else:
  for g in range(3):
   for p in en.pats[g]:
    c=en.column(g,p[4])
    if c:add(c)
 UB=json.loads((ROOT/'data/metrics.json').read_text())['makespan_s'];start=time.perf_counter();heap=[(0.,0,{})];nextid=1;solved=[];terminal=[];bestglobal=0.;status='node_limit';nd=0
 outdir=OUT/('bp_'+branchmode);outdir.mkdir(exist_ok=True)
 previous_runtime=0.
 if resume and (outdir/'tree.json').exists():
  tree=json.loads((outdir/'tree.json').read_text());prior=json.loads((outdir/'summary.json').read_text());previous_runtime=prior.get('cumulative_seconds',prior['seconds'])
  cols=json.loads((outdir/'columns.json').read_text());keys={(c['g'],tuple(c['counts']),c['p']) for c in cols}
  solved=tree['nodes'];terminal=tree['terminal'];heap=[(lb,i,{(g,j):(lo,hi) for g,j,lo,hi in bs}) for lb,i,bs in tree['open']];heapq.heapify(heap)
  nextid=max([r['id'] for r in solved]+[h[1] for h in heap])+1;nd=len(solved);bestglobal=prior['lower_bound_s']
 
 while heap and nd<maxnodes:
  if time.perf_counter()-start>seconds:status='wall_limit';break
  inherited,nodeid,bounds=heapq.heappop(heap);rows=noderows(bounds);best=None;history=[];complete=False;last=None;node_start=time.perf_counter()
  for it in range(70):
   if time.perf_counter()-start>seconds:break
   n=len(cols);nr=len(rows)
   lowers=[k for k,row in enumerate(rows) if row[2]<0];nvar=n+1+nc+len(lowers)
   eq=np.zeros((nc,nvar));eq[:,:n]=np.array([c['counts'] for c in cols],float).T;eq[:,n+1:n+1+nc]=np.eye(nc)
   U=np.zeros((3+nr,nvar));bu=np.r_[np.zeros(3),[r[3] for r in rows]]
   for k,c in enumerate(cols):
    U[c['g'],k]=c['p']/1000
    for ri,(g,j,sign,b) in enumerate(rows):U[3+ri,k]=sign*feat(c,g,j)
   U[:3,n]=[-len(t['aircraft']) for t in en.types]
   for k,ri in enumerate(lowers):U[3+ri,n+1+nc+k]=-1
   obj=np.zeros(nvar);obj[n]=1;obj[n+1:]=BIG
   res=linprog(obj,A_eq=csc_matrix(eq),b_eq=en.demand,A_ub=csc_matrix(U),b_ub=bu,bounds=(0,None),method='highs-ds')
   if not res.success:raise RuntimeError(res.message)
   pi=np.floor(res.eqlin.marginals*SCALE).astype(np.int64);mu=np.maximum(0,np.ceil(-res.ineqlin.marginals[:3]*SCALE)).astype(np.int64);zz=-np.maximum(0,np.floor(-res.ineqlin.marginals[3:]*SCALE)).astype(np.int64)
   try:cert,cs=certify(en,pi,mu,zz,rows,max(2,seconds-(time.perf_counter()-start)))
   except Exception as exc:
    history.append({'it':it,'pricing_failed':repr(exc)});break
   if best is None or cert['lower_bound_s']>best['lower_bound_s']:best=cert
   added=sum(add(c) for c in cs);mins=[r['minimum_rc_integer'] for r in cert['pricing']]
   row={'it':it,'rmp':float(res.fun),'best_lb':best['lower_bound_s'],'columns':n,'added':added,'minrc':mins};history.append(row)
   if min(mins)>=0 or not added:
    complete=True;last={'x':res.x[:n].copy(),'ncols':n,'rmp':float(res.fun),'artificial':float(res.x[n+1:].sum())};break
   if best['lower_bound_s']>UB+1e-5:break
  lb=max(inherited,0 if best is None else best['lower_bound_s']);action='unresolved';branch=None
  if lb>UB+1e-5:
   action='pruned_by_valid_bound';terminal.append({'id':nodeid,'lb':lb,'action':action})
  elif last is not None and last['artificial']<1e-7 and complete:
   branch=choose_fraction(en,cols[:last['ncols']],last['x'],branchmode)
   if branch is None:
    action='terminal_partial_integrality';terminal.append({'id':nodeid,'lb':lb,'action':action})
   else:
    (g,j),value=branch;lo,hi=bounds.get((g,j),(0,80));left=dict(bounds);right=dict(bounds);left[g,j]=(lo,min(hi,math.floor(value)));right[g,j]=(max(lo,math.ceil(value)),hi)
    children=[]
    for child in [left,right]:
     if child[g,j][0]<=child[g,j][1]:heapq.heappush(heap,(lb,nextid,child));children.append(nextid);nextid+=1
    action='branched'
  else:
   heapq.heappush(heap,(lb,nodeid,bounds));status='unresolved_pricing'
  record={'id':nodeid,'inherited_lb':inherited,'certified_lb':lb,'bounds':[[g,j,lo,hi] for (g,j),(lo,hi) in sorted(bounds.items())],'action':action,'branch':None if branch is None else [list(branch[0]),float(branch[1])],'certificate':best,'history':history,'elapsed_node_s':time.perf_counter()-node_start}
  if action=='branched':record['children']=children
  save(outdir/f'node_{nodeid:04d}.json',record);solved.append({k:record[k] for k in ['id','certified_lb','bounds','action','branch','elapsed_node_s']});nd+=1
  lbs=[a[0] for a in heap]+[r['lb'] for r in terminal];bestglobal=max(bestglobal,min([UB]+lbs))
  progress={'processed':nd,'open':len(heap),'terminal':len(terminal),'global_lb_s':bestglobal,'ub_s':UB,'gap_over_ub':(UB-bestglobal)/UB,'latest':solved[-1],'elapsed_s':time.perf_counter()-start}
  print(json.dumps(progress),flush=True);save(outdir/'progress.json',progress)
  if action=='unresolved':break
 if not heap:status='partial_integrality_tree_closed'
 save(outdir/'columns.json',cols);save(outdir/'tree.json',{'nodes':solved,'open':[[lb,i,[[g,j,lo,hi] for (g,j),(lo,hi) in sorted(b.items())]] for lb,i,b in heap],'terminal':terminal})
 final={'status':status,'processed':nd,'open':len(heap),'terminal':len(terminal),'lower_bound_s':bestglobal,'upper_bound_s':UB,'gap_over_ub':(UB-bestglobal)/UB,'scope':'branch-and-price of integer allocation/number-of-trips relaxation; columns may remain fractional, no original scheduling certificate','original_global_optimality_proved':False,'seconds':time.perf_counter()-start,'cumulative_seconds':previous_runtime+time.perf_counter()-start};save(outdir/'summary.json',final);print('FINAL',json.dumps(final),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--seconds',type=float,default=600);p.add_argument('--nodes',type=int,default=100);p.add_argument('--branch',default='all');p.add_argument('--resume',action='store_true');a=p.parse_args();main(a.seconds,a.nodes,a.branch,a.resume)
