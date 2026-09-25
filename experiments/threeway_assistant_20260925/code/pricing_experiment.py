from __future__ import annotations
import argparse,sys,json,time,subprocess,hashlib,random,statistics,itertools
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def save(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def one(binary,text):
 t=time.perf_counter();r=subprocess.run([str(binary)],input=text,text=True,capture_output=True,check=True,timeout=45)
 h=list(map(int,r.stdout.splitlines()[0].split()));return {'minimum_rc':h[0],'labels':h[1],'seconds':time.perf_counter()-t},r

def micro():
 out=[]
 for seed in range(24):
  rng=random.Random(71200+seed);Q=8;V=10;C=5;N=4;BUD=25;K=2;mu=rng.randint(0,3);prep=2;per=1;base=2
  pats=[(rng.randrange(1,N),rng.randrange(1,4),rng.randrange(1,4),1,rng.randrange(-2,22),[rng.randrange(3) for _ in range(K)]) for _ in range(C)]
  pen=[rng.randrange(9) for _ in range(K)];tt=[[0 if a==b else rng.randrange(1,5) for b in range(N)] for a in range(N)]
  e0=[[0 if a==b else rng.randrange(1,4) for b in range(N)] for a in range(N)];ee=[[[e0[a][b]+q//3 if a!=b else 0 for b in range(N)] for a in range(N)] for q in range(Q+1)]
  for kind in ['cut_pricer','elementary_pricer','memory_pricer']:
   elem=kind!='cut_pricer';bits=[0,1,2,0];terminal=[0,0,0,-1000*rng.randrange(-5,6)];allowed=[1,1,1,int(seed%2==0)]
   header=f'{Q} {V} {C} {N} {BUD} {mu} {prep} {per} {base} {K}'
   if kind=='memory_pricer':header+=' 2 14'
   text=header+'\n'+'\n'.join(' '.join(map(str,[s,w,v,n,p,*cn])) for s,w,v,n,p,cn in pats)+'\n'+' '.join(map(str,pen))+'\n'
   if kind=='memory_pricer':text+=' '.join(map(str,bits))+'\n'+'\n'.join(f'{t} {a}' for t,a in zip(terminal,allowed))+'\n'
   text+=' '.join(str(v) for r in tt for v in r)+'\n'+' '.join(str(v) for mat in ee for row in mat for v in row)+'\n'
   best=[2**63-1]
   def dfs(w,v,a,e,c,par,vis,mem):
    if a and e+ee[w][0][a]<=BUD and (kind!='memory_pricer' or allowed[mem]):best[0]=min(best[0],c+mu*tt[0][a]+(terminal[mem] if kind=='memory_pricer' else 0))
    for b,ww,vv,nn,pp,cn in pats:
     if w+ww>Q or v+vv>V or b==a or (elem and vis&(1<<b)):continue
     ne=e+ee[w][b][a]
     if ne>BUD:continue
     nm=mem|bits[b]
     if kind=='memory_pricer' and not allowed[nm]:continue
     nc=c+mu*(per*nn+base+tt[b][a])-1000*pp+sum(1000*pen[k]*((cn[k]+((par>>k)&1))//2) for k in range(K))
     np=par
     for k in range(K):
      if cn[k]%2:np^=1<<k
     dfs(w+ww,v+vv,b,ne,nc,np,vis|(1<<b),nm)
   dfs(0,0,0,0,mu*prep,0,0,0)
   b,_=one(ROOT/'code/bin'/f'{kind}_baseline',text);a,_=one(ROOT/'code/bin'/f'{kind}_accelerated',text)
   assert b['minimum_rc']==a['minimum_rc']==best[0],(seed,kind,b,a,best)
   out.append({'seed':seed,'kernel':kind,'brute_min_rc':best[0],'baseline':b,'accelerated':a})
 save(ROOT/'results/pricing_micro.json',{'cases':len(out),'failures':0,'records':out})
 print('MICRO_PASS',len(out),flush=True)

def real(src,nodes=8,repeats=3):
 src=Path(src).resolve();sys.path.insert(0,str(src/'code'));import audit_pair
 cover=json.loads((src/'results/final_certificate.json').read_text());audit_pair.check_cover(cover)
 valid=[n for n in cover['cutset'] if n.get('certificate') and not n['certificate'].get('ks')]
 # Fixed quantiles of certificate list, plus smallest lower bound; no selection by measured speed.
 ids=sorted(set([int(i) for i in __import__('numpy').linspace(0,len(valid)-1,nodes-1)]+[min(range(len(valid)),key=lambda i:valid[i]['certificate']['lower_bound_s'])]))
 selected=[valid[i] for i in ids];save(ROOT/'inputs/selected_certificate_nodes.json',selected)
 original=subprocess.run;captured=[];cache={}
 def wrapper(args,*aa,**kw):
  nm=Path(args[0]).name
  if nm in ['cut_pricer','elementary_pricer','memory_pricer']:
   inp=kw['input'];ix=len(captured);p=ROOT/'inputs/pricing_payloads'/f'{ix:03d}_{nm}.txt';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(inp)
   tt=time.perf_counter();r=original([str(ROOT/'code/bin'/f'{nm}_baseline')],*aa,**kw);head=list(map(int,r.stdout.splitlines()[0].split()))
   captured.append({'case':ix,'kernel':nm,'path':str(p.relative_to(ROOT)),'input_sha256':hashlib.sha256(inp.encode()).hexdigest(),'source_node':current[0],'original_rc':head[0],'original_labels':head[1],'first_seconds':time.perf_counter()-tt})
   return r
  return original(args,*aa,**kw)
 current=[None];subprocess.run=wrapper
 try:
  for node in selected:
   current[0]=node['id'];audit_pair.audit_certificate(node,45,True,cache);print('CAPTURE',node['id'],len(captured),flush=True)
 finally:subprocess.run=original
 save(ROOT/'inputs/pricing_cases.json',captured)
 records=[];rng=random.Random(92501)
 for x in captured:
  inp=(ROOT/x['path']).read_text();runs={'baseline':[],'accelerated':[]}
  for rep in range(repeats):
   order=['baseline','accelerated'];rng.shuffle(order)
   for mode in order:
    a,_=one(ROOT/'code/bin'/f"{x['kernel']}_{mode}",inp)
    assert a['minimum_rc']==x['original_rc'],(x,a)
    runs[mode].append(a)
  b=statistics.median(r['seconds'] for r in runs['baseline']);a=statistics.median(r['seconds'] for r in runs['accelerated'])
  records.append({**x,'baseline_median_s':b,'accelerated_median_s':a,'speedup':b/a,'accelerated_labels':runs['accelerated'][0]['labels'],'runs':runs})
  save(ROOT/'results/pricing_benchmark.json',{'scope':'selected fixed V7 dual/cap/cut inputs, not entire global search','nodes':len(selected),'repeats':repeats,'records':records,'failures':0})
  print('BENCH',x['case'],x['kernel'],round(b/a,3),flush=True)
 totalb=sum(r['baseline_median_s'] for r in records);totala=sum(r['accelerated_median_s'] for r in records)
 summary={'cases':len(records),'nodes':len(selected),'repeats':repeats,'failures':0,'baseline_sum_median_s':totalb,'accelerated_sum_median_s':totala,'aggregate_speedup':totalb/totala,'baseline_labels':sum(x['original_labels'] for x in records),'accelerated_labels':sum(x['accelerated_labels'] for x in records),'global_bound_changed':False,'scope':'kernel benchmark only; same full input problem per case; final min reduced costs exact equal; global V7 bound retained'}
 save(ROOT/'results/pricing_summary.json',summary);print('PRICING_SUMMARY',summary,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--nodes',type=int,default=8);p.add_argument('--repeats',type=int,default=3);a=p.parse_args();micro();real(a.source,a.nodes,a.repeats)
