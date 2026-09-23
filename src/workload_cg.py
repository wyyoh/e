"""Complete-pricing lower bound for the FULL 80-box problem.
Relaxation: flight-time metric closure; no energy, charging, deadlines or
individual-machine non-overlap. Repeated service visits and over-supply within
a fractional column are allowed. These relaxations enlarge the feasible set.
The DP pricing explores ALL capacity-feasible sequences in this relaxation,
not a restricted ALNS column pool. Integer-arithmetic dual check supplies a
conservative, reproducible bound independent of an LP 'optimal' status.
"""
from pathlib import Path
from collections import Counter
import json,time,math
import numpy as np
from numba import njit
from scipy.optimize import linprog
from scipy.sparse import csc_matrix
ROOT=Path(__file__).resolve().parents[1]

@njit(cache=True)
def price(Q,V,travel,mu,prep,per,base,sites,weights,volumes,pi):
    inf=1e100;n=travel.shape[0]
    dp=np.full((Q+1,V+1,n),inf)
    parents=np.full((Q+1,V+1,n),-1,np.int16)
    items=np.full((Q+1,V+1,n),-1,np.int16)
    dp[0,0,0]=mu*prep
    for w in range(1,Q+1):
        for v in range(1,V+1):
            for j in range(len(pi)):
                if w<weights[j] or v<volumes[j]:continue
                dest=sites[j];pw=w-weights[j];pv=v-volumes[j]
                best=inf;bl=-1
                for a in range(n):
                    val=dp[pw,pv,a]
                    if val>1e90:continue
                    step=per if a==dest else per+base+travel[a,dest]
                    val+=mu*step-pi[j]
                    if val<best:best=val;bl=a
                if best<dp[w,v,dest]:
                    dp[w,v,dest]=best;parents[w,v,dest]=bl;items[w,v,dest]=j
    ends=dp.copy()
    for a in range(1,n):ends[:,:,a]+=mu*travel[a,0]
    ends[:,:,0]=inf
    return ends,parents,items

@njit(cache=True)
def int_price(Q,V,travel_ticks,mu,prep_ticks,per_ticks,base_ticks,sites,weights,volumes,pi):
    inf=np.int64(4_000_000_000_000_000_000);n=travel_ticks.shape[0]
    dp=np.full((Q+1,V+1,n),inf,np.int64);dp[0,0,0]=mu*prep_ticks
    bestall=inf
    for w in range(1,Q+1):
        for v in range(1,V+1):
            for j in range(len(pi)):
                if w<weights[j] or v<volumes[j]:continue
                dest=sites[j];pw=w-weights[j];pv=v-volumes[j];best=inf
                for a in range(n):
                    val=dp[pw,pv,a]
                    if val==inf:continue
                    step=per_ticks if a==dest else per_ticks+base_ticks+travel_ticks[a,dest]
                    val+=mu*step-pi[j]*1000
                    if val<best:best=val
                if best<dp[w,v,dest]:dp[w,v,dest]=best
            for a in range(1,n):
                if dp[w,v,a]<inf:
                    val=dp[w,v,a]+mu*travel_ticks[a,0]
                    if val<bestall:bestall=val
    return bestall

def setup():
    B=json.loads((ROOT/'data/boxes.json').read_text());types=json.loads((ROOT/'data/types.json').read_text())
    C=Counter((b['site'],b['kind'],int(b['mass_kg']),int(round(b['volume_m3']*1000))) for b in B)
    classes=sorted(C);demand=np.array([C[k] for k in classes],dtype=float)
    names=['O01']+sorted({b['site'] for b in B});nd={n:i for i,n in enumerate(names)}
    sites=np.array([nd[c[0]] for c in classes],dtype=np.int64)
    weights=np.array([c[2] for c in classes],dtype=np.int64);volumes=np.array([c[3] for c in classes],dtype=np.int64)
    legs=json.loads((ROOT/'data/legs.json').read_text());travel=[];raws=[]
    for g in types:
        a=np.zeros((16,16))
        for l in legs:a[nd[l['from']],nd[l['to']]]=l['up_m']/g['up_mps']+l['distance_m']/g['cruise_mps']+l['down_m']/g['down_mps']
        raws.append(a.copy())
        for k in range(16):a=np.minimum(a,a[:,k,None]+a[None,k,:])
        travel.append(a)
    return B,types,classes,demand,sites,weights,volumes,travel,raws

def column(g,seq,types,sites,travel,nc):
    typ=types[g];last=0;p=typ['prep_s'];a=np.zeros(nc,dtype=np.int64)
    for j in seq:
        dest=sites[j];p+=typ['load_per_box_s']+typ['handover_per_box_s']
        if dest!=last:p+=travel[g][last,dest]+typ['handover_base_s']
        last=dest;a[j]+=1
    p+=travel[g][last,0]
    return {'type':g,'counts':a,'duration':p,'sequence':list(map(int,seq))}

def main(max_iterations=250,max_seconds=300):
    B,types,classes,demand,sites,weights,volumes,travel,raws=setup();nc=len(classes)
    cols=[];seen=set();history=[]
    def add(g,seq):
        c=column(g,seq,types,sites,travel,nc)
        key=(g,tuple(c['counts']),round(c['duration'],8))
        if key in seen:return False
        seen.add(key);cols.append(c);return True
    for g in range(3):
        for j in range(nc):add(g,[j])
    # Warm columns do not limit subsequent pricing.
    for f in json.loads((ROOT/'data/incumbent_flights.json').read_text()):
        bm={b['id']:b for b in B};ids=f['box_ids'];seq=[]
        for site in f['route'][1:-1]:
            for bid in ids:
                b=bm[bid]
                if b['site']==site:seq.append(classes.index((site,b['kind'],int(b['mass_kg']),int(round(b['volume_m3']*1000)))))
        add(next(i for i,g in enumerate(types) if g['id']==f['type']),seq)
    start=time.monotonic();res=None;mins=[];stop='iteration_limit'
    for it in range(max_iterations):
        m=len(cols);ae=np.zeros((nc,m+1));au=np.zeros((3,m+1))
        for k,c in enumerate(cols):ae[:,k]=c['counts'];au[c['type'],k]=c['duration']
        au[:,-1]=[-len(g['aircraft']) for g in types]
        cost=np.zeros(m+1);cost[-1]=1
        res=linprog(cost,A_ub=csc_matrix(au),b_ub=np.zeros(3),A_eq=csc_matrix(ae),b_eq=demand,bounds=(0,None),method='highs-ds')
        if not res.success:raise RuntimeError(res.message)
        pi=res.eqlin.marginals.copy();mu=-res.ineqlin.marginals.copy();mins=[];added=0
        for g,typ in enumerate(types):
            Q=typ['max_payload_kg'];V=round(typ['max_volume_m3']*1000)
            ends,pa,ij=price(Q,V,travel[g],mu[g],typ['prep_s'],typ['load_per_box_s']+typ['handover_per_box_s'],typ['handover_base_s'],sites,weights,volumes,pi)
            flat=ends.ravel();mins.append(float(flat.min()))
            ids=np.argpartition(flat,min(60,len(flat)-1))[:60];ids=ids[np.argsort(flat[ids])]
            for ix in ids:
                if flat[ix]>=-1e-7:continue
                w,v,last=np.unravel_index(ix,ends.shape);seq=[]
                while w>0:
                    j=int(ij[w,v,last]);a=int(pa[w,v,last])
                    if j<0:raise AssertionError('broken pricing traceback')
                    seq.append(j);w-=weights[j];v-=volumes[j];last=a
                added+=add(g,list(reversed(seq)))
        row={'iteration':it,'columns':m,'restricted_lp_s':float(res.fun),'min_reduced_cost':mins,'added':int(added),'elapsed_s':time.monotonic()-start};history.append(row)
        if it%5==0 or not added:print(json.dumps(row),flush=True)
        if min(mins)>=-1e-7:stop='complete_pricing_no_negative_column';break
        if not added:stop='no_new_column_numeric';break
        if time.monotonic()-start>max_seconds:stop='time_limit';break
    # A fully checked integer dual certificate is valid even if CG did not converge.
    scale=10**6;mui=np.maximum(0,np.ceil(mu*scale)).astype(np.int64)
    pii=np.floor(pi*scale).astype(np.int64)
    tickraw=[np.floor(np.maximum(0,a*1000-1e-7)).astype(np.int64) for a in raws]
    for a in tickraw:
        for k in range(16):a[:]=np.minimum(a,a[:,k,None]+a[None,k,:])
    def checkdual(p):
        vals=[]
        for g,t in enumerate(types):
            vals.append(int(int_price(t['max_payload_kg'],round(t['max_volume_m3']*1000),tickraw[g],int(mui[g]),t['prep_s']*1000,(t['load_per_box_s']+t['handover_per_box_s'])*1000,t['handover_base_s']*1000,sites,weights,volumes,p)))
        return vals
    before=checkdual(pii);correction=max(0,(-min(before)+999)//1000);pii-=correction
    after=checkdual(pii)
    if min(after)<0:raise AssertionError('invalid dual certificate')
    den=max(scale,sum(len(t['aircraft'])*int(mui[g]) for g,t in enumerate(types)))
    numerator=sum(int(d)*int(p) for d,p in zip(demand,pii));lb=numerator/den
    ub=json.loads((ROOT/'data/incumbent_metrics.json').read_text())['makespan_s']
    cert={'dual_denominator':den,'objective_numerator':numerator,'time_tick_s':0.001,'pi_integer':pii.tolist(),'mu_integer':mui.tolist(),'minimum_integer_reduced_cost':after,'correction_integer_per_item':int(correction),'classes':[list(c) for c in classes],'demands':demand.astype(int).tolist(),'aircraft':[len(t['aircraft']) for t in types],'travel_lower_ticks':[a.tolist() for a in tickraw]}
    result={'scope':'full-80-box lower-bound relaxation; not full scheduling optimum','stop':stop,'iterations':len(history),'columns_generated':len(cols),'restricted_lp_s':float(res.fun),'pricing_minima':mins,'verified_lower_bound_s':lb,'upper_bound_s':ub,'gap_over_ub':(ub-lb)/ub,'elapsed_s':time.monotonic()-start,'global_optimality_proved':ub-lb<1e-7}
    (ROOT/'results/workload_dual_certificate.json').write_text(json.dumps(cert,ensure_ascii=False,indent=2))
    (ROOT/'results/workload_cg.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    (ROOT/'results/workload_cg_history.json').write_text(json.dumps(history,ensure_ascii=False,indent=2))
    outcols=[{'type':types[c['type']]['id'],'counts':c['counts'].tolist(),'duration_s':c['duration'],'sequence':c['sequence']} for c in cols]
    (ROOT/'results/workload_columns.json').write_text(json.dumps(outcols,ensure_ascii=False,separators=(',',':')))
    print('FINAL',json.dumps(result,ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':main()
