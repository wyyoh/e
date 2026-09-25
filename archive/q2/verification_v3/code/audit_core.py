"""Independent finite-tree coverage, exact integer repricing, and forward tiny enumeration.
Only certifies the stated lower relaxation, NOT original full IP optimality.
"""
from pathlib import Path
from fractions import Fraction
from collections import Counter
import json, math, random, itertools, subprocess, time, copy
import numpy as np
from walk_cg import Engine, ROOT, OUT, save

def tiny_tests(engines, cases=24):
 rng=random.Random(824162);records=[]
 for i in range(cases):
  N=4;Q=rng.randrange(5,10);V=Q+4;bud=rng.randrange(15,45);mu=rng.randrange(1,50);nu=rng.randrange(1,30)
  prep=100;load=20;hand=30;base=50;K=2;pen=[rng.randrange(1,30) for _ in range(K)]
  pats=[(s,rng.randrange(1,4),rng.randrange(1,4),rng.randrange(1,3),rng.randrange(-50,120),rng.randrange(2),[rng.randrange(3) for _ in range(K)]) for s in range(1,4) for _ in range(2)]
  tt=[[0 if a==b else rng.randrange(5,40) for b in range(N)] for a in range(N)]
  ee=[[[0 if a==b else rng.randrange(1,8)+q//3 for b in range(N)] for a in range(N)] for q in range(Q+1)]
  best={k:2**63-1 for k in ['plain','subset','prefix']};tested=[0]
  def visit(seq,w,v):
   if seq:
    q=w;last=0;e=0;n=sum(pats[j][3] for j in seq);clock=prep+load*n;prefix=0;pi=0;counts=[0]*K
    for j in seq:
     s,pw,pv,pn,pr,critical,cuts=pats[j];e+=ee[q][last][s];clock+=tt[last][s]+base+hand*pn
     if critical:prefix=clock
     q-=pw;last=s;pi+=pr
     for k in range(K):counts[k]+=cuts[k]
    e+=ee[0][last][0];clock+=tt[last][0];cost=mu*clock-1000*pi;tested[0]+=1
    if e<=bud:
     best['plain']=min(best['plain'],cost)
     best['subset']=min(best['subset'],cost+1000*sum(a*(c//2) for a,c in zip(pen,counts)))
     best['prefix']=min(best['prefix'],cost+nu*prefix)
   last=pats[seq[-1]][0] if seq else 0
   for j,(s,pw,pv,*_) in enumerate(pats):
    if w+pw<=Q and v+pv<=V and s!=last:visit(seq+[j],w+pw,v+pv)
  visit([],0,0)
  common=' '.join(str(x) for row in tt for x in row)+'\n'+' '.join(str(x) for ar in ee for row in ar for x in row)+'\n'
  for mode,binary in engines.items():
   if mode=='plain':
    h=f'{Q} {V} {len(pats)} {N} {bud} {mu} {prep} {load+hand} {base}\n'
    lines=''.join(' '.join(map(str,p[:5]))+'\n' for p in pats)
   elif mode=='subset':
    h=f'{Q} {V} {len(pats)} {N} {bud} {mu} {prep} {load+hand} {base} {K}\n'
    lines=''.join(' '.join(map(str,[*p[:5],*p[6]]))+'\n' for p in pats)+' '.join(map(str,pen))+'\n'
   else:
    h=f'{Q} {V} {len(pats)} {N} {bud} {mu} {nu} {prep} {load} {hand} {base}\n'
    lines=''.join(' '.join(map(str,p[:6]))+'\n' for p in pats)
   r=subprocess.run([str(binary)],input=h+lines+common,text=True,capture_output=True,check=True)
   got=int(r.stdout.split()[0]);assert got==best[mode],(i,mode,got,best[mode])
   records.append({'case':i,'mode':mode,'enumerated_sequences':tested[0],'minimum_integer_rc':got})
 return records

def check_cert(en,c,rows=None):
 pi=list(map(int,c['pi_integer']));mu=list(map(int,c['mu_integer']));den=int(c['denominator'])
 assert all(x>=0 for x in mu) and sum(len(t['aircraft'])*m for t,m in zip(en.types,mu))<=den
 num=sum(int(d)*p for d,p in zip(en.demand,pi));mins=[]
 if rows is not None:
  zz=list(map(int,c['row_duals_integer']));assert all(z<=0 for z in zz) and c['rows']==[list(r) for r in rows]
  num+=sum(z*r[3] for z,r in zip(zz,rows))
 elif 'cut_penalties_integer' in c:
  pen=list(map(int,c['cut_penalties_integer']));assert all(x>=0 for x in pen)
  for cut in c['cuts']:assert cut['rhs']==sum(int(en.demand[j]) for j in cut['classes'])//2
  num-=sum(p*cut['rhs'] for p,cut in zip(pen,c['cuts']))
 elif 'prefix_penalties_integer' in c:
  nu=list(map(int,c['prefix_penalties_integer']));assert all(x>=0 for x in nu)
  num-=sum(c['critical_due_s']*len(t['aircraft'])*v for t,v in zip(en.types,nu))
 assert num==c['numerator'],('numerator',num,c['numerator'])
 for g in range(3):
  args=[g,np.array(pi,dtype=np.int64),np.array(mu,dtype=np.int64)];const=0
  if rows is not None:
   pg=pi.copy()
   for z,(gg,j,sgn,rhs) in zip(zz,rows):
    if gg==g:
     if j==-1:const-=1000*z*sgn
     else:pg[j]+=z*sgn
   args[1]=np.array(pg,dtype=np.int64)
  elif 'cut_penalties_integer' in c:args.append(np.array(pen,dtype=np.int64))
  elif 'prefix_penalties_integer' in c:args.append(np.array(nu,dtype=np.int64))
  r,_=en.pricing(*args,seconds=60);v=int(r['minimum_rc_integer'])+const;assert v>=0,('negative_rc',g,v);mins.append(v)
 return {'lower_bound_s':float(Fraction(num,den)),'numerator':num,'denominator':den,'recomputed_minima_integer':mins}

def tree_cover(path):
 tree=json.loads((path/'tree.json').read_text());summary=json.loads((path/'summary.json').read_text())
 nodes={n['id']:json.loads((path/f"node_{n['id']:04d}.json").read_text()) for n in tree['solved']}
 opens={n[1]:n for n in tree['open']};terminal={n['id']:n for n in tree['terminal']};seen=set();branches=[]
 def bs(i):return {(g,j):(lo,hi) for g,j,lo,hi in (nodes[i]['bounds'] if i in nodes else opens[i][2])}
 def walk(i):
  assert i not in seen,('cyclic_or_duplicate',i);seen.add(i);n=nodes.get(i)
  if n and n['action']=='branched':
   (g,j),v=n['branch'];low,high=bs(i).get((g,j),(0,80));k=math.floor(v)
   assert low<=k<high and len(n['children'])==2
   for child,lr in zip(n['children'],[(low,k),(k+1,high)]):
    expected=bs(i).copy();expected[g,j]=lr;assert bs(child)==expected
    walk(child)
   branches.append(i)
  else:assert i in opens or i in terminal,('unaccounted_region',i)
 walk(0);assert seen==set(nodes)|set(opens) and set(terminal)<=seen
 frontier=[a[0] for a in opens.values()]+[a['lb'] for a in terminal.values()]
 assert summary['lower_bound_s']<=min(frontier)+1e-7
 target=Fraction(math.floor(summary['lower_bound_s']*1e6)-1,10**6);cover=[];splits=[]
 def compress(i):
  n=nodes.get(i)
  if n and n.get('certificate'):
   c=n['certificate']
   if Fraction(c['numerator'],c['denominator'])>=target:cover.append(n);return
  assert n and n['action']=='branched',('no_certificate_to_cover',i)
  splits.append({k:n[k] for k in ['id','bounds','branch','children']})
  for child in n['children']:compress(child)
 compress(0)
 return target,cover,splits,summary,len(seen),len(branches)

def main():
 st=time.perf_counter();en=Engine();report={'tiny_pricing':tiny_tests({'plain':en.bin}),'certificates':{}}
 report['certificates']['root']=check_cert(en,json.loads((OUT/'walk_q0.001_certificate.json').read_text()))
 target,cover,splits,summary,nseen,nb=tree_cover(OUT/'bp_all');repriced=[]
 for k,n in enumerate(cover):
  rows=[]
  for g,j,lo,hi in n['bounds']:
   if hi<80:rows.append([g,j,1,hi])
   if lo>0:rows.append([g,j,-1,-lo])
  repriced.append({'id':n['id'],**check_cert(en,n['certificate'],rows)})
  if k%50==0:print('REPRICE',k,len(cover),flush=True)
 bad=copy.deepcopy(json.loads((OUT/'walk_q0.001_certificate.json').read_text()));bad['pi_integer']=[int(x)+10**7 for x in bad['pi_integer']];bad['numerator']=sum(int(d)*v for d,v in zip(en.demand,bad['pi_integer']))
 rejected=False
 try:check_cert(en,bad)
 except AssertionError:rejected=True
 assert rejected
 report.update({'tree':{'nodes_reachable':nseen,'binary_splits':nb,'cutset_certificates_repriced':len(cover),'pricing_calls':3*len(cover),'published_lower_bound_s':float(target),'repricing':repriced},'negative_forged_dual_detected':True,'failures':0,'elapsed_s':time.perf_counter()-st})
 save(OUT/'audit_core.json',report);print('CORE AUDIT COMPLETE',float(target),flush=True)
if __name__=='__main__':main()
