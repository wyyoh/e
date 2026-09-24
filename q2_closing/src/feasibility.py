"""Two bounded closing checks: fixed-box type reassignment and 22 flights.
The 22-flight test has NO incumbent makespan cap: feasibility != improvement.
"""
from common import *
from physics import Model,partition_bound
from search import workload_master,internal_check
from schedule import schedule
from replay import verify
import itertools,math

def main():
    d=inputs();m=Model(d);baseline=load(ROOT/'results/baseline_incumbent.json');jobs=baseline['flights'];cap=baseline['claimed_makespan_s']
    if load(ROOT/'logs/search_summary.json')['improved']:
        print('Stop condition already met; no additional search.');return
    pool=[m.job(g,j['box_ids'],j['route'],j['flight_id']) for j in jobs for g in d['types']]
    pool=[j for j in pool if j['feasible']]
    candidate,_,log=workload_master(pool,[],d['types'],cap-1e-5,23,10,[])
    save(ROOT/'results/fixed_routes_type_reassignment.json',dict(patterns=len(pool),solver=log,has_potential_improvement=candidate is not None,scope='all three types on each of the unchanged 23 box sets and routes; workload necessary condition'))
    # Exact union of the two same-area B trips into one C trip. Explore this
    # explicit local 22-flight candidate, without claiming a full space search.
    attempts=[]
    for left,right in itertools.combinations(jobs,2):
        if left['type']!='B' or right['type']!='B' or left['route']!=right['route']:continue
        merged=m.job('C',left['box_ids']+right['box_ids'],left['route'],'FEAS22-MERGED')
        if not merged['feasible']:
            attempts.append(dict(removed=[left['flight_id'],right['flight_id']],failures=merged['failures']));continue
        selected=[j for j in jobs if j not in (left,right)]+[merged]
        # finite 3-hour horizon for this primal search, not a theorem about 22.
        plan,slog=schedule(selected,d['types'],10800,seed=20260924,trials=100000)
        attempt=dict(removed=[left['flight_id'],right['flight_id']],partition_bound=partition_bound(selected,d['types']),schedule=slog)
        if plan is not None:
            internal=internal_check(plan,m);result,*_=verify(plan);attempt['independent_replay']=result
            if result['failed']==0:
                out=dict(flights=plan,claimed_makespan_s=result['metrics']['makespan_s'],metrics=result['metrics'],internal_validation=internal,independent_validation=result)
                save(ROOT/'results/feasible_22_incumbent.json',out)
                save(ROOT/'results/feasibility_22_sorties.json',dict(status='verified_feasible',proven_infeasible=False,globally_optimal=False,metrics=result['metrics'],removed=[left['flight_id'],right['flight_id']],replacement=merged,independent_validation=result,improves_current_upper_bound=result['metrics']['makespan_s']<cap-1e-7,scope='constructive 22-flight feasibility witness; no minimal-makespan claim',earlier_improvement_capped_search=load(ROOT/'results/feasibility_22_sorties.json')))
                print('22-flight feasible',result['metrics'],flush=True)
                if result['metrics']['makespan_s']<cap-1e-7:save(ROOT/'results/best_incumbent.json',out)
                return
        attempts.append(attempt)
    save(ROOT/'results/feasibility_22_sorties.json',dict(status='search_failed_to_find_feasible',proven_infeasible=False,globally_optimal=False,attempts=attempts,scope='same-area B+B to C merge, limited scheduling heuristic'))
if __name__=='__main__':main()
