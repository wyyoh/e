from pathlib import Path
import sys,json,itertools,time
import numpy as np
from scipy.optimize import milp,LinearConstraint,Bounds
from scipy.sparse import coo_matrix

ROOT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path('problems/D/q2/evidence_v7/upstream/primal').resolve()
sys.path.insert(0,str(ROOT/'code'))
import core

D=json.load(open(ROOT.parent.parent/'results/incumbent_replay/decisions.json'))
plan=core.from_decisions(D); base,sch=core.schedule(plan,True)
last=max(range(len(sch)),key=lambda i:sch[i]['return_s']); aid=sch[last]['aircraft']
critical=[i for i,s in enumerate(sch) if s['aircraft']==aid]
last_sites=set(plan[last][2])
same_site=[i for i,k in enumerate(plan) if i not in critical and last_sites & set(k[2])]
c_late=sorted([i for i,k in enumerate(plan) if k[0]=='C'],key=lambda i:sch[i]['return_s'],reverse=True)[:2]
targets=sorted(set(critical+same_site+c_late))
union=set()
for i in targets: union.update(plan[i][1])

def options(idx,r=3,a=3):
    old=plan[idx];own=set(old[1]);donors=sorted(union-own);out={}
    for nr in range(min(r,len(own))+1):
        for rem in itertools.combinations(sorted(own),nr):
            keep=tuple(sorted(own-set(rem)))
            for na in range(a+1):
                for extra in itertools.combinations(donors,na):
                    ids=tuple(sorted(set(keep).union(extra)))
                    if not ids or len(ids)!=len(keep)+len(extra):continue
                    sites=sorted({core.B[i]['site'] for i in ids})
                    if len(sites)>4:continue
                    mass=sum(core.B[i]['mass_kg'] for i in ids);vol=sum(round(core.B[i]['volume_m3']*1000) for i in ids)
                    for g,t in core.T.items():
                        if mass>t['max_payload_kg'] or vol>round(t['max_volume_m3']*1000):continue
                        for route in itertools.permutations(sites):
                            k=core.task(g,ids,route);e=core.evaluate(k)
                            if e is None:continue
                            latest=min([core.B[b]['expected_delivery_s']-off for b,off in e['delivery']]+[e['latest']])
                            if latest>=-1e-7:out[k]=(e,latest)
    return [(k,*v) for k,v in out.items()]+[(None,None,float('inf'))]

st=time.time();flex={i:options(i) for i in targets};generation_s=time.time()-st
allopts={}
for i in range(len(plan)):
    if i in flex:allopts[i]=flex[i]
    else:
        e=core.evaluate(plan[i]);latest=min([core.B[b]['expected_delivery_s']-off for b,off in e['delivery']]+[e['latest']]);allopts[i]=[(plan[i],e,latest)]

xidx={};yidx={};nv=0
for i in range(len(plan)):
    for oi,o in enumerate(allopts[i]):xidx[i,oi]=nv;nv+=1
for i in range(len(plan)):
    for oi,o in enumerate(allopts[i]):
        if o[0] is None:continue
        for ac in core.T[o[0][0]]['aircraft']:yidx[i,oi,ac]=nv;nv+=1
Tidx=nv;nv+=1
row=[];col=[];dat=[];lb=[];ub=[]
def cons(items,L=-np.inf,U=np.inf):
    rr=len(lb);lb.append(L);ub.append(U)
    for cc,v in items:
        if v:row.append(rr);col.append(cc);dat.append(v)
for i in range(len(plan)):cons([(xidx[i,oi],1) for oi in range(len(allopts[i]))],1,1)
for b in range(len(core.B)):
    items=[]
    for i in range(len(plan)):
        for oi,o in enumerate(allopts[i]):
            if o[0] is not None and b in o[0][1]:items.append((xidx[i,oi],1))
    cons(items,1,1)
for i in range(len(plan)):
    for oi,o in enumerate(allopts[i]):
        if o[0] is None:continue
        g=o[0][0]
        cons([(yidx[i,oi,ac],1) for ac in core.T[g]['aircraft']]+[(xidx[i,oi],-1)],0,0)
for g in core.T:
    for ac in core.T[g]['aircraft']:
        items=[(Tidx,-1)]
        for i in range(len(plan)):
            for oi,o in enumerate(allopts[i]):
                if o[0] is not None and o[0][0]==g:items.append((yidx[i,oi,ac],o[1]['duration']))
        cons(items,U=0)
A=coo_matrix((dat,(row,col)),shape=(len(lb),nv)).tocsc();c=np.zeros(nv);c[Tidx]=1
lo=np.zeros(nv);hi=np.ones(nv);hi[Tidx]=1e5;integ=np.ones(nv);integ[Tidx]=0
solve0=time.time()
ans=milp(c,integrality=integ,bounds=Bounds(lo,hi),constraints=LinearConstraint(A,lb,ub),options={'time_limit':60,'mip_rel_gap':0})
solve_s=time.time()-solve0
if ans.x is None:raise RuntimeError(ans.message)
result={
 'source':'Q2-EVIDENCE-V7-FOCUSED incumbent',
 'incumbent_makespan_s':base['makespan_s'],'incumbent_energy_kwh':base['energy_kwh'],
 'critical_aircraft':aid,'critical_slots':critical,'same_final_site_slots':same_site,'late_C_slots':c_late,
 'target_slots':targets,'target_box_count':len(union),
 'neighborhood':'target slot may remove<=3 own boxes, add<=3 boxes from 23-box chain union, change A/B/C type, enumerate all service orders up to 4 unique sites; other slots fixed',
 'option_counts':{str(i):len(flex[i]) for i in targets},'total_target_options':sum(len(v) for v in flex.values()),
 'generation_s':generation_s,'milp_variables':nv,'milp_rows':len(lb),'milp_nonzeros':int(A.nnz),
 'status':ans.message,'mip_gap':float(ans.mip_gap),'mip_nodes':int(ans.mip_node_count),'solve_s':solve_s,
 'relaxed_aircraft_workload_lower_bound_s':float(ans.fun),
 'strict_improvement_possible_in_neighborhood':bool(ans.fun < base['makespan_s']-1e-7),
 'logic':'battery/time-window/ordering constraints are relaxed; therefore if even this relaxation is >= incumbent, no executable member of the defined neighborhood can improve makespan',
 'global_Q2_claim':False
}
Path('result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
