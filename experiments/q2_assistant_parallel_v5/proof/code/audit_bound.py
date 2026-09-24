"""Independent full-domain covering certificate algebra and complete repricing.
No original problem optimality claim; source model is a route relaxation.
"""
from pathlib import Path
from fractions import Fraction
import json,math,gzip,time,copy
import numpy as np
from subset_cg import CutEngine,ROOT,OUT
from audit_core import tree_cover
def cut_cert(en,c,rows):
 pi=list(map(int,c['pi_integer']));mu=list(map(int,c['mu_integer']));zz=list(map(int,c['row_duals_integer']));pen=list(map(int,c['cut_penalties_integer']))
 assert c['rows']==[list(r) for r in rows] and c['cuts']==en.cuts
 assert all(v>=0 for v in mu+pen) and all(z<=0 for z in zz)
 for cut in en.cuts:assert len(set(cut['classes']))==len(cut['classes']) and cut['rhs']==sum(int(en.demand[j]) for j in cut['classes'])//2
 den=int(c['denominator']);num=sum(int(d)*p for d,p in zip(en.demand,pi))+sum(z*r[3] for z,r in zip(zz,rows))-sum(p*cut['rhs'] for p,cut in zip(pen,en.cuts))
 assert den>=sum(len(t['aircraft'])*m for t,m in zip(en.types,mu))
 assert num==int(c['numerator'])
 values=[]
 for g in range(3):
  pp=pi.copy();const=0
  for z,(gg,j,sgn,b) in zip(zz,rows):
   if gg==g:
    if j==-1:const-=1000*z*sgn
    else:pp[j]+=z*sgn
  # Conservative integer magnitude bound protects C++ signed 64-bit costs.
  nmax=en.types[g]['max_payload_kg']//min(en.w)
  t=en.types[g];pmax=t['prep_s']*1000+nmax*((t['load_per_box_s']+t['handover_per_box_s']+t['handover_base_s'])*1000+int(en.tt[g].max()))+int(en.tt[g].max())
  mag=mu[g]*pmax+1000*nmax*max(map(abs,pp))+1000*nmax*sum(pen)+abs(const)
  assert mag<2**63-1,('integer overflow risk',g,mag)
  r,_=en.pricing(g,np.array(pp,dtype=np.int64),np.array(mu,dtype=np.int64),np.array(pen,dtype=np.int64),seconds=90)
  val=int(r['minimum_rc_integer'])+const;assert val>=0,(g,val);values.append(val)
 return {'numerator':num,'denominator':den,'recomputed_minima_integer':values}


def create():
 target,cover,splits,summary,nseen,nb=tree_cover(OUT/'bp_cut_all')
 obj={'schema':'q2-cover-v5','threshold':[target.numerator,target.denominator],
 'cuts':json.loads((OUT/'subset_cuts.json').read_text()),
 'cover':[{'id':n['id'],'bounds':n['bounds'],'certificate':n['certificate']} for n in cover],
 'splits':splits,'source_summary':summary,'tree_regions':nseen,'tree_binary_splits':nb}
 out=ROOT/'data/cover_certificate.json.gz'
 out.write_bytes(gzip.compress(json.dumps(obj,separators=(',',':')).encode(),mtime=0))
 return obj

def verify(obj=None):
 st=time.monotonic()
 if obj is None:obj=json.loads(gzip.decompress((ROOT/'data/cover_certificate.json.gz').read_bytes()))
 target=Fraction(*obj['threshold']);leaves={n['id']:n for n in obj['cover']};splits={n['id']:n for n in obj['splits']}
 assert 0 not in leaves or not splits
 assert not(set(leaves)&set(splits)) and len(leaves)==len(obj['cover']) and len(splits)==len(obj['splits'])
 visited=set()
 def walk(i,expected):
  assert i not in visited;visited.add(i)
  n=(splits if i in splits else leaves)[i]
  actual={(g,j):(lo,hi) for g,j,lo,hi in n['bounds']};assert len(actual)==len(n['bounds']) and actual==expected
  if i in splits:
   (g,j),v=n['branch'];lo,hi=actual.get((g,j),(0,80));k=math.floor(v)
   assert lo<=k<hi and len(n['children'])==2
   for child,lr in zip(n['children'],[(lo,k),(k+1,hi)]):
    new=actual.copy();new[g,j]=lr;walk(child,new)
  else:
   c=n['certificate'];assert Fraction(int(c['numerator']),int(c['denominator']))>=target
 walk(0,{})
 assert visited==set(leaves)|set(splits)
 en=CutEngine(obj['cuts']);records=[]
 for index,n in enumerate(obj['cover']):
  rows=[]
  for g,j,lo,hi in n['bounds']:
   if hi<80:rows.append([g,j,1,hi])
   if lo>0:rows.append([g,j,-1,-lo])
  records.append({'id':n['id'],**cut_cert(en,n['certificate'],rows)})
  if index%25==0:print('REPRICED',index,len(obj['cover']),flush=True)
 bad=copy.deepcopy(obj['cover'][0]['certificate']);bad['pi_integer']=[x+10**7 for x in bad['pi_integer']]
 bad['numerator']=sum(int(d)*p for d,p in zip(en.demand,bad['pi_integer']))+sum(z*r[3] for z,r in zip(bad['row_duals_integer'],bad['rows']))-sum(p*c['rhs'] for p,c in zip(bad['cut_penalties_integer'],en.cuts))
 caught=False
 try:cut_cert(en,bad,bad['rows'])
 except AssertionError:caught=True
 assert caught
 res={'certified_lower_bound_s':float(target),'cover_certificates':len(records),'complete_pricing_calls':len(records)*3,
 'covering_tree_regions':len(visited),'original_tree_regions':obj['tree_regions'],'original_tree_binary_splits':obj['tree_binary_splits'],
 'source_processed':obj['source_summary']['processed'],'source_open':obj['source_summary']['open'],
 'original_global_optimality_proven':False,'forged_dual_rejected':caught,'failures':0,'seconds':time.monotonic()-st,'details':records}
 (OUT/'audit_v5_bound.json').write_text(json.dumps(res,indent=2)+'\n')
 print('AUDIT_V5',json.dumps({k:v for k,v in res.items() if k!='details'}),flush=True)
 return res
if __name__=='__main__':
 import sys
 verify(create() if '--create' in sys.argv else None)
