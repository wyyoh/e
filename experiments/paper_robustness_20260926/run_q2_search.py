"""Controlled random-search repetitions. Same initial solution and iteration budget.
The inherited ALNS source is unmodified; original physical data remain fixed.
These repetitions assess this initialization/budget, not global optimality.
"""
import sys,json,random,time,os,subprocess,csv,copy,itertools
from pathlib import Path
from functools import lru_cache
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'q2_runtime/code'))
import core,alns
OUT=ROOT/'results/q2_search';OUT.mkdir(exist_ok=True,parents=True)
def save(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def worker(seed):
 initial=json.loads((OUT/'common_initial.json').read_text());plan=core.from_decisions(initial['decisions'])
 # Caches start cold in each independent process.
 core.evaluate.cache_clear();core.variants.cache_clear()
 t=time.perf_counter();r=alns.run(plan,seed=seed,iterations=150,max_seconds=120,adaptive=True,mode='time',out=OUT/f'seed_{seed:02d}')
 r['protocol']={'common_initial': 'common_initial.json','max_iterations':150,'soft_time_cap_s':120,'wall_s':time.perf_counter()-t,'termination':'iteration_limit' if sum(r['destroy_use'].values())==150 else 'time_limit','feasible_initial_supplied':True,'not_a_from_scratch_feasibility_test':True}
 save(OUT/f'seed_{seed:02d}/run.json',r)
 # Verify every accepted final job through the independent equation implementation.
 from run_q1_q2 import task_eval,B
 checked=[]
 for d in r['decisions']:
  e=task_eval(d);assert e['physical'];checked.extend(d['boxes'])
 assert sorted(checked)==sorted(B)
 from export_solution import produce
 from verify_solution import run as verify
 f=OUT/f'seed_{seed:02d}/replay';produce(core.from_decisions(r['decisions']),f,'Q2-S')
 v=verify(f);save(OUT/f'seed_{seed:02d}/independent_validation.json',v)
 assert v.get('failed',0)==0,v
 return r

def prepare():
 p=core.from_decisions(json.loads((ROOT/'inputs/q2/decisions.json').read_text()));p=alns.canonicalize(p);rng=random.Random(1001)
 for _ in range(100):
  q=alns.local(p,rng)
  if q and alns.feasible(core.schedule(q)):p=q
 save(OUT/'common_initial.json',{'generation':'100 local proposals seed=1001, retain only zero-tardiness feasible proposals; original incumbent NOT reinserted during measured search','metrics':core.schedule(p),'decisions':core.as_decisions(p)})

def energy_worker(factor):
 original=core.evaluate
 @lru_cache(maxsize=400000)
 def changed(k):
  e=original(k)
  if e is None:return None
  e=copy.deepcopy(e);t=core.T[k[0]];energy=e['energy']*factor;soc=1-energy/t['battery_kwh']
  if soc<t['reserve_pct']/100-1e-9:return None
  e.update(energy=energy,soc=soc,charge=core.charge_seconds(soc,t));return e
 core.evaluate=changed;alns.evaluate=changed;core.variants.cache_clear()
 start=core.from_decisions(json.loads((ROOT/'inputs/q2/decisions.json').read_text()))
 # Split only jobs that exceed the perturbed energy limit; exhaustive two-way splits.
 while any(changed(k) is None for k in start):
  pos=next(i for i,k in enumerate(start) if changed(k) is None);old=start[pos];ids=old[1];candidates=[]
  for mask in range(1,1<<(len(ids)-1)):
   ia=tuple(ids[j] for j in range(len(ids)) if (mask>>j)&1);ib=tuple(x for x in ids if x not in ia)
   for ga,gb in itertools.product(core.T,repeat=2):
    for a in core.variants(ga,ia):
     for b in core.variants(gb,ib):
      for pair in [(a,b),(b,a)]:
       p=start[:pos]+list(pair)+start[pos+1:]
       if any(changed(k) is None for k in p):
        # Repair other invalid jobs in subsequent iterations; do not mistakenly
        # discard every split merely because a different original job is invalid.
        ee=[changed(x) for x in pair]
        candidates.append(((sum(e['duration'] for e in ee),sum(e['energy'] for e in ee)),p,None))
       else:
        p=alns.canonicalize(p);m=core.schedule(p)
        if m is not None:candidates.append(((m['hard_lateness_s']*1e5+m['weighted_tardiness_s']*1e3+m['makespan_s'],m['energy_kwh']),p,m))
  if not candidates:raise RuntimeError('No two-way repair found; not proof of global infeasibility')
  _,start,m=min(candidates,key=lambda x:x[0])
 out=OUT/f'energy_factor_{factor:.2f}';out.mkdir(exist_ok=True)
 save(out/'initial.json',{'decisions':core.as_decisions(start),'metrics':core.schedule(start),'method':'sequential exhaustive two-way splits of invalid jobs; local duration-energy priority while other invalid jobs remain, decoded feasible-priority score after final repair; finite ALNS refinement'})
 r=alns.run(start,seed=20260926,iterations=250,max_seconds=120,out=out)
 from run_q1_q2 import task_eval,simulate
 m,sch=core.schedule(core.from_decisions(r['decisions']),True);fl=[]
 for i,s in enumerate(sch,1):
  d=core.as_decisions([s['task']])[0];fl.append({'flight_id':f'Q2-E-{i:02d}','type':d['type'],'box_ids':d['boxes'],'route':['O01',*d['route'],'O01'],'aircraft':s['aircraft'],'battery':s['battery'],'start_s':s['start_s']})
 vv,ff,dd=simulate(energy_scale=factor,flights=fl)
 save(out/'independent_perturbed_replay.json',{'metrics':vv,'flights':ff,'deliveries':dd,'global_optimality_proven':False})
 assert vv['physical_and_hard_feasible'] and vv['zero_tardiness_feasible'],vv
 print('ENERGY_FINAL',factor,vv,flush=True)

if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='worker':worker(int(sys.argv[2]));sys.exit()
 if len(sys.argv)>1 and sys.argv[1]=='energy':energy_worker(float(sys.argv[2]));sys.exit()
 prepare();env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',PYTHONHASHSEED='0')
 # Identical iteration budgets; two separate processes at once. Per-run times retained.
 pending=list(range(1,21));active=[];finished=[]
 while pending or active:
  while pending and len(active)<2:
   seed=pending.pop(0);f=open(OUT/f'seed_{seed:02d}.log','w');p=subprocess.Popen([sys.executable,__file__,'worker',str(seed)],env=env,stdout=f,stderr=subprocess.STDOUT);active.append((seed,p,f))
  time.sleep(.5)
  for x in list(active):
   seed,p,f=x
   if p.poll() is not None:
    f.close();active.remove(x);finished.append({'seed':seed,'returncode':p.returncode});print('SEED_DONE',seed,p.returncode,flush=True)
 save(OUT/'execution_status.json',finished)
 for factor in [1.01,1.02]:
  with (OUT/f'energy_{factor}.log').open('w') as f:r=subprocess.run([sys.executable,__file__,'energy',str(factor)],env=env,stdout=f,stderr=subprocess.STDOUT)
  print('ENERGY_DONE',factor,r.returncode,flush=True)
