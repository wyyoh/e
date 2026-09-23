"""Compare C++ label pricing against exhaustive forward-route enumeration.
Random tiny nonmetric, load-dependent graphs include revisits and varied
pattern sizes. This validates code on exhaustive test cases, not real flights.
"""
from pathlib import Path
import random,subprocess,json,itertools
ROOT=Path(__file__).resolve().parents[1]
def run():
 rows=[]
 for seed in range(30):
  rng=random.Random(seed);Q=7;V=10;N=3;C=4;mu=rng.randint(1,9);prep=300;per=30;base=80;budget=30
  pats=[(1,2,3,1,rng.randint(100,500)),(1,3,4,2,rng.randint(100,500)),(2,1,2,1,rng.randint(100,500)),(2,3,4,2,rng.randint(100,500))]
  tt=[[0 if i==j else rng.randint(20,200) for j in range(N)] for i in range(N)]
  er=[[[0 if i==j else rng.randint(1,8)+q for j in range(N)] for i in range(N)] for q in range(Q+1)]
  best=[2**63-1];n=[0]
  def go(seq,w,v):
   if seq:
    q=w;e=0;p=prep;reward=0;last=0
    for j in seq:
     dst,ww,vv,nn,pp=pats[j];e+=er[q][last][dst];p+=tt[last][dst]+base+per*nn;reward+=pp*1000;q-=ww;last=dst
    e+=er[0][last][0];p+=tt[last][0]
    if e<=budget:best[0]=min(best[0],mu*p-reward);n[0]+=1
   for j,pat in enumerate(pats):
    if seq and pats[seq[-1]][0]==pat[0]:continue
    if w+pat[1]<=Q and v+pat[2]<=V:go(seq+[j],w+pat[1],v+pat[2])
  go([],0,0)
  inp=f'{Q} {V} {C} {N} {budget} {mu} {prep} {per} {base}\n'+'\n'.join(' '.join(map(str,p)) for p in pats)+'\n'+' '.join(str(x) for row in tt for x in row)+'\n'+' '.join(str(x) for mat in er for row in mat for x in row)+'\n'
  p=subprocess.run([str(ROOT/'src/pattern_pricer')],input=inp,text=True,capture_output=True,check=True)
  actual=int(p.stdout.split()[0]);ok=actual==best[0];rows.append({'seed':seed,'enumerated_feasible_sequences':n[0],'expected_rc':best[0],'cpp_rc':actual,'pass':ok})
  if not ok:raise AssertionError(rows[-1])
 (ROOT/'results/pricer_unit_tests.json').write_text(json.dumps({'tests':len(rows),'failed':sum(not r['pass'] for r in rows),'cases':rows},indent=2));print('pricing tests',len(rows),'PASS')
if __name__=='__main__':run()
