"""Independent accounting of global B&P bounds and integer pricing certificates.
Rechecks a complete covering cutset, not just the best node. Tiny pricing uses
an independent forward exhaustive enumeration. No global original-IP claim.
"""
from pathlib import Path
from fractions import Fraction
from collections import Counter
import json,math,time,copy,itertools,subprocess,random
import numpy as np
from elementary_cg import Engine,ROOT,OUT,save

def structural_tree(tree_dir):
 d=Path(tree_dir);tree=json.loads((d/'tree.json').read_text());summary=json.loads((d/'summary.json').read_text())
 nodes={r['id']:json.loads((d/f"node_{r['id']:04d}.json").read_text()) for r in tree['nodes']}
 opens={r[1]:r for r in tree['open']};terminal={r['id']:r for r in tree['terminal']};seen=set();checks=[]
 def eq(k,a,b):
  if a!=b:raise AssertionError((k,a,b))
  checks.append(k)
 def bounds(i):
  if i in nodes:return {(g,j):(lo,hi) for g,j,lo,hi in nodes[i]['bounds']}
  return {(g,j):(lo,hi) for g,j,lo,hi in opens[i][2]}
 def walk(i,parent=None):
  if i in seen:raise AssertionError('duplicate/cyclic tree')
  seen.add(i);n=nodes.get(i)
  if n and n['action']=='branched':
   (g,j),v=n['branch'];lo,hi=bounds(i).get((g,j),(0,80));cut=math.floor(v)
   assert lo<=cut<hi and abs(v-round(v))>1e-6
   expected=[]
   for lr in [(lo,cut),(cut+1,hi)]:
    b=bounds(i).copy();b[g,j]=lr;expected.append(b)
   eq('two exhaustive integer children',len(n['children']),2)
   for c,b in zip(n['children'],expected):
    eq('child bounds',bounds(c),b);walk(c,i)
  else:
   if i not in opens and i not in terminal:raise AssertionError(('unaccounted leaf',i))
   if n and n['action']=='pruned_by_valid_bound':assert n['certified_lb']>summary['upper_bound_s']
 walk(0)
 eq('all solved+open reached',seen,set(nodes)|set(opens))
 eq('all terminal accounted',set(terminal)<=seen,True)
 frontier=[v[0] for v in opens.values()]+[v['lb'] for v in terminal.values()]
 assert summary['lower_bound_s']<=min(frontier)+1e-7
 threshold=Fraction(math.floor(summary['lower_bound_s']*1e6)-1,10**6)
 cutset=[];splits=[]
 def compress(i):
  n=nodes.get(i)
  if n and n['certificate']:
   c=n['certificate'];v=Fraction(c['numerator'],c['denominator'])
   if v>=threshold:
    cutset.append({'id':i,'bounds':n['bounds'],'certificate':c});return
  if not n or n['action']!='branched':raise AssertionError(('no covering bound at leaf',i))
  splits.append({'id':i,'bounds':n['bounds'],'branch':n['branch'],'children':n['children']})
  for c in n['children']:compress(c)
 compress(0)
 return summary,threshold,cutset,splits,len(checks)

def check_node(en,node):
 c=node['certificate'];pi=list(map(int,c['pi_integer']));mu=list(map(int,c['mu_integer']));zz=list(map(int,c['row_duals_integer']));rows=c['rows'];bs={(g,j):(lo,hi) for g,j,lo,hi in node['bounds']}
 expected=[]
 for (g,j),(lo,hi) in sorted(bs.items()):
  if hi<80:expected.append([g,j,1,hi])
  if lo>0:expected.append([g,j,-1,-lo])
 assert rows==expected
 assert len(pi)==len(en.demand) and len(zz)==len(rows) and all(v>=0 for v in mu) and all(v<=0 for v in zz)
 den=int(c['denominator']);num=sum(int(d)*p for d,p in zip(en.demand,pi))+sum(z*r[3] for z,r in zip(zz,rows))
 assert num==c['numerator'] and sum(len(t['aircraft'])*v for t,v in zip(en.types,mu))<=den
 minima=[]
 for g in range(3):
  pg=pi.copy();constant=0
  for z,(gg,j,sgn,rhs) in zip(zz,rows):
   if g==gg:
    if j==-1:constant-=z*sgn*1000
    else:pg[j]+=z*sgn
  r,_=en.pricing(g,np.array(pg,dtype=np.int64),np.array(mu,dtype=np.int64),[],60)
  value=r['minimum_rc_integer']+constant
  assert value>=0,('negative integer reduced cost',node['id'],g,value)
  minima.append(value)
 return {'id':node['id'],'minima_after_actual_repair':minima,'numerator':num,'denominator':den}

def tiny_cpp(binary,ncases=24):
 rng=random.Random(74192);records=[]
 for idx in range(ncases):
  N=4;Q=rng.randrange(5,10);V=Q+4;budget=rng.randrange(15,45);mu=rng.randrange(1,50);prep=100;per=30;base=50
  pats=[(s,rng.randrange(1,4),rng.randrange(1,4),1,rng.randrange(-50,120)) for s in range(1,4) for _ in range(2)]
  tt=[[0 if a==b else rng.randrange(5,40) for b in range(N)] for a in range(N)]
  ee=[[[0 if a==b else rng.randrange(1,8)+(q//3) for b in range(N)] for a in range(N)] for q in range(Q+1)]
  elem=bool(idx%2);cuts=[(3,25),(6,17)] if elem and idx%3==0 else []
  best=[2**63-1];tested=[0]
  def dfs(seq,w,v):
   if seq:
    q=w;p=mu*prep;last=0;e=0;mask=0
    for j in seq:
     s,pw,pv,n,pi=pats[j];p+=mu*(tt[last][s]+base+per*n)-pi*1000;e+=ee[q][last][s];q-=pw;mask|=1<<(s-1);last=s
    p+=mu*tt[last][0];e+=ee[0][last][0]
    p-=1000*sum(reward for m,reward in cuts if mask&m)
    if e<=budget:best[0]=min(best[0],p)
    tested[0]+=1
   lastsite=pats[seq[-1]][0] if seq else 0;used={pats[j][0] for j in seq}
   for j,(s,pw,pv,n,pi) in enumerate(pats):
    if w+pw>Q or v+pv>V or s==lastsite or elem and s in used:continue
    dfs(seq+[j],w+pw,v+pv)
  dfs([],0,0)
  text=f'{Q} {V} {len(pats)} {N} {budget} {mu} {prep} {per} {base} {int(elem)} {len(cuts)}\n'
  text+='\n'.join(' '.join(map(str,p)) for p in pats)+'\n';text+='\n'.join(f'{a} {b}' for a,b in cuts)+'\n'
  text+=' '.join(str(v) for r in tt for v in r)+'\n';text+=' '.join(str(v) for ar in ee for r in ar for v in r)+'\n'
  r=subprocess.run([str(binary)],input=text,text=True,capture_output=True,check=True)
  value=int(r.stdout.split()[0]);assert value==best[0],(idx,value,best[0])
  records.append({'case':idx,'elementary':elem,'cuts':bool(cuts),'full_sequences':tested[0],'minimum_integer_rc':value})
 return records

def main():
 st=time.perf_counter();en=Engine(.001,False,0);report={'tiny_cpp':tiny_cpp(en.bin),'old_bounds':[]}
 for mode in ['trips','all']:
  d=OUT/f'bp_{mode}';s,lb,cut,splits,n=structural_tree(d)
  certs=[]
  for k,node in enumerate(cut):
   certs.append(check_node(en,node))
   if k%50==0:print(mode,k,len(cut),time.perf_counter()-st,flush=True)
  obj={'threshold_numerator':lb.numerator,'threshold_denominator':lb.denominator,'covered_lower_bound_s':float(lb),'cutset':cut,'branch_nodes':splits,'scope':s['scope'],'original_global_optimality_proved':False}
  save(OUT/f'bp_{mode}_cover_certificate.json',obj)
  report[mode]={'nodes_processed':s['processed'],'open_nodes':s['open'],'terminal_regions':s['terminal'],'tree_checks':n,'cutset_certificates_repriced':len(cut),'pricing_calls':3*len(cut),'certified_lb_s':float(lb),'repricing_details':certs}
 bad=copy.deepcopy(cut[0]);bad['certificate']['pi_integer']=[x+10**10 for x in bad['certificate']['pi_integer']]
 bad['certificate']['numerator']=sum(int(d)*p for d,p in zip(en.demand,bad['certificate']['pi_integer']))+sum(z*r[3] for z,r in zip(bad['certificate']['row_duals_integer'],bad['certificate']['rows']))
 try:check_node(en,bad);raise RuntimeError('bad dual not detected')
 except AssertionError:report['negative_forged_dual_detected']=True
 report['seconds']=time.perf_counter()-st;report['failures']=0
 save(OUT/'audit_v2.json',report);print('AUDIT COMPLETE',json.dumps({k:v for k,v in report.items() if k not in ['tiny_cpp','all','trips']}),flush=True)
if __name__=='__main__':main()
