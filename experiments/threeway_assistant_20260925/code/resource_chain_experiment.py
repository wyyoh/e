"""Coupled box-reconstruction across explicit aircraft/battery predecessor neighborhoods.
Model A holds resource chains; model B releases resource identities/orders for all
fixed task slots. Both use the same finite options; not global original-Q2 proofs.
"""
from __future__ import annotations
import argparse,sys,json,time,itertools,copy,math,hashlib
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[1]
def save(p,d):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def run(src,seconds=25):
 sys.path.insert(0,str(Path(src).resolve()/'upstream/primal/code'))
 import core,slot_milp,free_resource_milp,schedule_tools,export_solution,verify_solution
 plan=core.from_decisions(json.loads((Path(src)/'upstream/primal/inputs/selected_v5.json').read_text())['decisions'])
 m,sch=core.schedule(plan,True);export_solution.produce(plan,ROOT/'results/q2_baseline',label='Q2-BASE');bcheck=verify_solution.check(ROOT/'results/q2_baseline')
 assert all(x['pass'] for x in bcheck), 'baseline replay failed'
 save(ROOT/'results/q2_baseline_check.json',bcheck)
 edges=[]
 for name in ['aircraft','battery']:
  groups=defaultdict(list)
  for i,s in enumerate(sch):groups[s[name]].append(i)
  for rid,ix in groups.items():
   ix.sort(key=lambda i:(sch[i]['start_s'],i))
   for a,b in zip(ix,ix[1:]):edges.append({'from':a,'to':b,'resource_type':name,'resource_id':rid})
 save(ROOT/'inputs/resource_graph.json',{'tasks':core.as_decisions(plan),'baseline_schedule':[{k:v for k,v in r.items() if k!='task'} for r in sch],'edges':edges})
 # Predefined, no selection after viewing solver outcomes. Includes both B lanes,
 # linked predecessors and compatible A/C receivers; no change outside listed slots.
 neighborhoods=[('B_tail_energy_chain',[3,16,18,17,11,15,6]),('B_alternate_C_receiver',[2,4,17,18,10,13]),('C_battery_crosschain',[16,18,6,8,9,11,15])]
 records=[]
 for ni,(name,slots) in enumerate(neighborhoods):
  start=time.perf_counter();pool=sorted({b for i in slots for b in plan[i][1]});opts=[];stats={'physical_evaluations':0,'candidate_subsets':0}
  for i,old in enumerate(plan):
   if i not in slots:opts.append([slot_milp.option(old)]);continue
   own=set(old[1]);donor=[b for b in pool if b not in own]
   keep_sets={tuple(sorted(own-set(rem))) for nr in range(min(2,len(own))+1) for rem in itertools.combinations(sorted(own),nr)};keep_sets.add(())
   candsets={tuple(sorted(k+ex)) for k in keep_sets for na in range(3) for ex in itertools.combinations(donor,na)}
   candsets.update(plan[j][1] for j in slots);di={old:slot_milp.option(old),None:slot_milp.option(None)};t=core.T[old[0]]
   for ids in sorted(candsets,key=lambda q:(len(q),q)):
    if not ids:continue
    stats['candidate_subsets']+=1
    if sum(core.B[b]['mass_kg'] for b in ids)>t['max_payload_kg'] or sum(round(core.B[b]['volume_m3']*1000) for b in ids)>round(t['max_volume_m3']*1000):continue
    sites=sorted({core.B[b]['site'] for b in ids})
    # Explicit finite neighborhood, not a physical maximum on stops.
    if len(sites)>4:continue
    good=[]
    for route in itertools.permutations(sites):
     k=core.task(old[0],ids,route);stats['physical_evaluations']+=1;o=slot_milp.option(k)
     if o is None:continue
     def dom(a,b):return a['p']<=b['p'] and a['p']+a['c']<=b['p']+b['c'] and a['latest']>=b['latest'] and a['e']<=b['e']
     if any(dom(a,o) for a in good):continue
     good=[a for a in good if not dom(o,a)];good.append(o)
    for o in good:di[o['k']]=o
    if core.evaluate.cache_info().currsize>100000:core.evaluate.cache_clear()
   opts.append(list(di.values()))
  stats['generation_seconds']=time.perf_counter()-start;stats['option_counts']=list(map(len,opts));stats['slots']=slots;stats['pool_boxes']=[core.B[b]['id'] for b in pool]
  save(ROOT/f'inputs/chain_{ni}_options.json',{'name':name,'stats':stats,'options':[[{'decisions':None if o['k'] is None else core.as_decisions([o['k']])[0],'p':o['p'],'charge':o['c'],'energy':o['e'],'latest':o['latest']} for o in oo] for oo in opts]})
  print('CHAIN_OPTIONS',name,stats,flush=True)
  def predefined(_plan,idx,*args,**kwargs):return copy.deepcopy(opts[idx])
  slot_milp.candidate_options=predefined;free_resource_milp.candidate_options=predefined
  for model,fn in [('fixed_chains',slot_milp.solve),('released_chains',free_resource_milp.solve)]:
   out=ROOT/f'results/chains/{ni}_{model}';rec={'neighborhood':name,'model':model,'option_counts':stats['option_counts'],'generation_seconds':stats['generation_seconds'],'scope':'finite box options, fixed typed task slots, no global lower bound claim'}
   try:
    stat=fn(plan,out,seconds=seconds,seed=92520+ni);rec['solver']=stat
    if (out/'candidate.json').exists():
     dd=json.loads((out/'candidate.json').read_text());p=core.from_decisions(dd['decisions']);arr=schedule_tools.reconstruct_earliest(p,dd['arrangements']);mm,_=schedule_tools.evaluate_arrangements(p,arr)
     if mm['hard_late_boxes'] or mm['weighted_tardiness_s']>1e-6:raise ValueError('reconstructed schedule late')
     met=export_solution.produce(p,out/'replayed',label=f'Q2-CHAIN-{ni}-{model}',arrangements=arr);check=verify_solution.check(out/'replayed');assert all(x['pass'] for x in check), 'candidate replay failed'
     save(out/'replay_checks.json',check);rec['replay_summary']={'checks':len(check),'failures':sum(not x['pass'] for x in check)};rec['metrics']=met
     rec['strict_time_gain_s']=m['makespan_s']-met['makespan_s'];rec['accepted_time_improvement']=rec['strict_time_gain_s']>1e-5
    else:rec['metrics']=None
   except Exception as e:
    import traceback;traceback.print_exc();rec['error']=repr(e)
   records.append(rec);save(ROOT/'results/resource_chain_records.json',records);print('CHAIN_RECORD',rec,flush=True)
 summary={'baseline':m,'neighborhoods':len(neighborhoods),'solver_runs':len(records),'same_candidate_pool_paired':True,'time_limit_per_solve_s':seconds,'any_strict_makespan_improvement':any(r.get('accepted_time_improvement') for r in records),'errors':sum('error' in r for r in records),'scope':'coupled finite box reassignment including graph-linked tasks, typed slots fixed; no arbitrary new sorties/no repeated visits in this heuristic neighborhood; no global infeasibility conclusion','records':records}
 save(ROOT/'results/resource_chain_summary.json',summary);print('CHAIN_FINISHED',len(records),summary['any_strict_makespan_improvement'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--seconds',type=float,default=25);a=p.parse_args();run(a.source,a.seconds)
