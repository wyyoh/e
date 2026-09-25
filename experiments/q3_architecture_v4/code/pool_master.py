"""Route/site-mode set partitioning + simultaneous continuous-time resource MIP.
Backend: HiGHS bundled with SciPy (not CP-SAT). Discrete solution -> LP polish.
Finite candidate domain only; no original-problem global-optimality claim.
"""
from __future__ import annotations
import sys, json, math, copy, time
from pathlib import Path
from collections import defaultdict
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import vstack,csc_matrix
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'))
from joint_solver import Model,color_intervals
from joint_v3 import add_charge_model
from transport import T,B,BI,task,evaluate,charge_seconds
from precompute import dump,digest
from radio import R
from input_identity import fingerprint

def routekey(d):return (d['type'],tuple(sorted(d['boxes'])),tuple(d['route']))

def highs_run(m,c,seconds,logfile,start=None):
    from scipy.optimize._highspy._core import _Highs,HighsLp,HighsVarType,HighsSolution,MatrixFormat
    mat=m.matrix();lp=HighsLp();lp.num_col_=len(m.lb);lp.num_row_=len(m.lo)
    lp.col_cost_=c;lp.col_lower_=m.lb;lp.col_upper_=m.ub;lp.row_lower_=m.lo;lp.row_upper_=m.hi
    lp.a_matrix_.format_=MatrixFormat.kColwise;lp.a_matrix_.num_col_=len(m.lb);lp.a_matrix_.num_row_=len(m.lo)
    lp.a_matrix_.start_=mat.indptr.astype(np.int32);lp.a_matrix_.index_=mat.indices.astype(np.int32);lp.a_matrix_.value_=mat.data
    lp.integrality_=[HighsVarType.kInteger if b else HighsVarType.kContinuous for b in m.integrality]
    _Highs.resetGlobalScheduler(True)
    h=_Highs();h.setOptionValue('output_flag',True);h.setOptionValue('log_to_console',False);h.setOptionValue('log_file',str(logfile));h.setOptionValue('threads',1)
    h.setOptionValue('time_limit',float(seconds));h.setOptionValue('mip_rel_gap',1e-7);h.setOptionValue('mip_feasibility_tolerance',1e-7)
    passed=h.passModel(lp)
    if str(passed).endswith('kError'):raise RuntimeError(('HiGHS passModel failed',str(passed)))
    start_ok=None
    if start is not None:
        z=np.asarray(start);row=mat@z
        start_violation=max(float(np.max(np.maximum(np.array(m.lb)-z,0))),float(np.max(np.maximum(z-np.array(m.ub),0))),float(np.max(np.maximum(np.array(m.lo)-row,0))),float(np.max(np.maximum(row-np.array(m.hi),0))))
        start_ok=start_violation<=1e-5
        if start_ok:
            ss=HighsSolution();ss.col_value=z;ss.value_valid=True;h.setSolution(ss)
        else:print('MIP_START_REJECTED',start_violation,flush=True)
    tm=time.monotonic();run_status=h.run()
    if str(run_status).endswith('kError'):raise RuntimeError(('HiGHS run failed',str(run_status)))
    info=h.getInfo();solution=h.getSolution()
    status={'backend':'SciPy-bundled HiGHS '+h.version(),'model_status':str(h.getModelStatus()),'elapsed_s':time.monotonic()-tm,'objective':float(info.objective_function_value) if solution.value_valid else None,'finite_model_dual_bound':float(info.mip_dual_bound) if math.isfinite(info.mip_dual_bound) else None,'nodes':int(info.mip_node_count),'variables':len(m.lb),'constraints':len(m.lo),'mip_start_used':start_ok,'original_problem_optimality_proven':False}
    return (np.asarray(solution.col_value) if solution.value_valid and info.primal_solution_status==2 else None),status

def solve(pool,sites,profiles,out,seconds=90,upper=6341.,slack=30.,max_relays=4,fixed_routes=False,reference=None,objective='time'):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    nt,nr=len(pool),len(sites);H=float(upper);m=Model()
    ev=[evaluate(task(d['type'],[BI[b] for b in d['boxes']],d['route'])) for d in pool]
    if any(e is None for e in ev):raise ValueError('nonphysical route in pool')
    maxstart=[]
    for e in ev:
        cap=[H-e['duration']]
        for b,t in e['delivery']:
            cap.append(B[b]['expected_delivery_s']-t)
            if B[b]['hard_deadline_s'] is not None:cap.append(B[b]['hard_deadline_s']-t-slack)
        maxstart.append(min(cap))
    M=m.var('makespan',hi=H);xs=[];ss=[]
    for i,e in enumerate(ev):
        valid=maxstart[i]>=0 and all(d['allowed'] for d in profiles[i])
        x=m.var(f'x_{i}',lo=1 if fixed_routes else 0,hi=1 if valid else 0,integer=True);s=m.var(f's_{i}',hi=max(0,maxstart[i]));xs.append(x);ss.append(s)
        m.row({s:1,x:-max(0,maxstart[i])},hi=0);m.row({s:1,x:e['duration'],M:-1},hi=0)
    for box in BI:
        ids=[xs[i] for i,d in enumerate(pool) if box in d['boxes']]
        if not ids:raise ValueError(('missing box in pool',box))
        m.row({v:1 for v in ids},lo=1,hi=1)
    paths={}
    for typ,tp in T.items():
        ids=[i for i,d in enumerate(pool) if d['type']==typ]
        m.row({**{xs[i]:ev[i]['duration'] for i in ids},M:-len(tp['aircraft'])},hi=0)
        for kind,n in [('aircraft',len(tp['aircraft'])),('battery',tp['battery_count'])]:
            arcs={};sources={i:m.var(f'{kind}_src_{i}',hi=1,integer=True) for i in ids}
            dur={i:ev[i]['duration']+(ev[i]['charge'] if kind=='battery' else 0) for i in ids}
            for i in ids:
                for j in ids:
                    if i==j or set(pool[i]['boxes']) & set(pool[j]['boxes']):continue
                    if dur[i]>maxstart[j]+1e-8:continue
                    z=m.var(f'{kind}_{i}_{j}',hi=1,integer=True);arcs[i,j]=z
                    big=max(0,maxstart[i])+dur[i]
                    m.row({ss[i]:1,ss[j]:-1,z:big},hi=big-dur[i])
            for i in ids:
                inc={v:1 for (j,k),v in arcs.items() if k==i};inc[sources[i]]=1;inc[xs[i]]=-1;m.row(inc,lo=0,hi=0)
                outgoing={v:1 for (j,k),v in arcs.items() if j==i};outgoing[xs[i]]=-1;m.row(outgoing,hi=0)
            m.row({v:1 for v in sources.values()},hi=n)
            paths[typ,kind]=(sources,arcs,dur)
    use=[];rs=[];re=[];prep=[];ret=[];ene=[];chg=[];lead=[];lowbranch=[]
    power=(R['hover_kw']+R['communication_kw'])/3600
    for j,g in enumerate(sites):
        lead.append(R['prep_s']+g['out_s']+R['link_setup_s'])
        y=m.var(f'y_{j}',hi=1,integer=True);a=m.var(f'rs_{j}',hi=H);b=m.var(f're_{j}',hi=H);p=m.var(f'rp_{j}',hi=H);r=m.var(f'rr_{j}',hi=H)
        use.append(y);rs.append(a);re.append(b);prep.append(p);ret.append(r)
        m.row({p:1,a:-1,y:lead[-1]},lo=0,hi=0);m.row({r:1,b:-1,y:-g['back_s']},lo=0,hi=0)
        m.row({a:1,b:-1},hi=0);m.row({r:1,y:-H},hi=0);m.row({r:1,M:-1},hi=0)
        e=m.var(f'energy_{j}',hi=R['battery_kwh']*(1-R['reserve_pct']/100));ene.append(e)
        m.row({e:1,b:-power,a:power,y:-(g['transit_kwh']+power*R['link_setup_s'])},lo=0,hi=0)
        m.row({e:1,y:-R['battery_kwh']*(1-R['reserve_pct']/100)},hi=0)
        c=add_charge_model(m,e,y,j,R['battery_kwh'],R['charge_full_s'],R['battery_kwh']*(1-R['reserve_pct']/100));chg.append(c)
        lowbranch.append(m.names.index(f'low_soc_branch_{j}'))
    m.row({v:1 for v in use},hi=max_relays)
    if max_relays>R['component_count']:raise ValueError('Add component path cover for > initial stock jobs')
    rsrc={j:m.var(f'relay_src_{j}',hi=1,integer=True) for j in range(nr)};rarcs={}
    for i in range(nr):
        for j in range(nr):
            if i==j:continue
            z=m.var(f'relay_arc_{i}_{j}',hi=1,integer=True);rarcs[i,j]=z
            big=H+R['turnaround_s']
            m.row({ret[i]:1,use[i]:R['turnaround_s'],prep[j]:-1,z:big},hi=big)
    for j in range(nr):
        terms={z:1 for (a,b),z in rarcs.items() if b==j};terms[rsrc[j]]=1;terms[use[j]]=-1;m.row(terms,lo=0,hi=0)
        terms={z:1 for (a,b),z in rarcs.items() if a==j};terms[use[j]]=-1;m.row(terms,hi=0)
    m.row({z:1 for z in rsrc.values()},hi=len(R['aircraft']))
    cover={};demands=[]
    for i,prs in enumerate(profiles):
        for pd in prs:
            h=len(demands);d={**pd,'i':i};demands.append(d);vv=[]
            for j in d['allowed']:
                w=m.var(f'c_{h}_{j}',hi=1,integer=True);cover[h,j]=w;vv.append(w)
                m.row({w:1,use[j]:-1},hi=0)
                m.row({rs[j]:1,ss[i]:-1,w:H-d['a']},hi=H)
                big=max(0,maxstart[i])+d['b'];m.row({ss[i]:1,re[j]:-1,w:big},hi=big-d['b'])
            m.row({**{v:1 for v in vv},xs[i]:-1},lo=0,hi=0)
    for j in range(nr):m.row({use[j]:1,**{v:-1 for (h,k),v in cover.items() if k==j}},hi=0)
    initial=None
    if reference is not None:
        try:
            initial=np.zeros(len(m.lb));chosen=[];sid=[];keys={routekey(d):i for i,d in enumerate(pool)}
            for k,d in enumerate(reference['decisions']):
                i=keys[routekey(d)];initial[xs[i]]=1;initial[ss[i]]=reference['starts'][k];chosen.append(i)
            for oldj in reference['active_jobs']:
                xyz=tuple(reference['sites'][oldj][k] for k in 'xyz');j=next(j for j,g in enumerate(sites) if tuple(g[k] for k in 'xyz')==xyz and j not in sid);sid.append(j)
                initial[use[j]]=1;initial[rs[j]]=reference['relay_start'][oldj];initial[re[j]]=reference['relay_end'][oldj]
                initial[prep[j]]=initial[rs[j]]-lead[j];initial[ret[j]]=initial[re[j]]+sites[j]['back_s'];initial[ene[j]]=sites[j]['transit_kwh']+power*(initial[re[j]]-initial[rs[j]]+R['link_setup_s'])
                initial[chg[j]]=charge_seconds(1-initial[ene[j]]/R['battery_kwh'],R);initial[lowbranch[j]]=int(initial[ene[j]]>0.1*R['battery_kwh'])
            def set_chains(ids,sv,evv,sources,arcs,cap):
                labels=color_intervals([(i,sv(i),evv(i)) for i in ids],cap);gs=defaultdict(list)
                for i,k in labels.items():gs[k].append(i)
                for group in gs.values():
                    group.sort(key=sv);initial[sources[group[0]]]=1
                    for a,b in zip(group[:-1],group[1:]):initial[arcs[a,b]]=1
            for (typ,kind),(sr,ar,dur) in paths.items():
                ids=[i for i in chosen if pool[i]['type']==typ];set_chains(ids,lambda i:initial[ss[i]],lambda i:initial[ss[i]]+dur[i],sr,ar,len(T[typ]['aircraft']) if kind=='aircraft' else T[typ]['battery_count'])
            set_chains(sid,lambda j:initial[prep[j]],lambda j:initial[ret[j]]+R['turnaround_s'],rsrc,rarcs,len(R['aircraft']))
            for h,d in enumerate(demands):
                i=d['i']
                if i not in chosen:continue
                j=next(j for j in d['allowed'] if j in sid and initial[rs[j]]<=initial[ss[i]]+d['a']+1e-6 and initial[re[j]]>=initial[ss[i]]+d['b']-1e-6);initial[cover[h,j]]=1
            initial[M]=max([initial[ss[i]]+ev[i]['duration'] for i in chosen]+[initial[ret[j]] for j in sid])
        except (KeyError,StopIteration,ValueError) as e:
            print('MIP_START_UNAVAILABLE',repr(e),flush=True);initial=None
    cost=np.zeros(len(m.lb));cost[M]=1
    if objective=='energy':
        cost[M]=0;cost[ene]=1
        for i in range(nt):cost[xs[i]]=ev[i]['energy']
    print('MASTER',nt,nr,len(m.lb),len(m.lo),'seconds',seconds,flush=True)
    x,status=highs_run(m,cost,seconds,out/'highs.log',initial)
    status.update({'route_pool_size':nt,'site_job_pool_size':nr,'hard_slack_s':slack,'max_relay_sorties':max_relays,'objective_mode':objective});dump(out/'solver_status.json',status)
    print('MASTER_STATUS',status,flush=True)
    if x is None:return None,status
    lb=np.array(m.lb);ub=np.array(m.ub);inte=np.flatnonzero(m.integrality);lb[inte]=ub[inte]=np.rint(x[inte]);mat=m.matrix();lo=np.array(m.lo);hi=np.array(m.hi);eq=np.isfinite(lo)&np.isfinite(hi)&(abs(lo-hi)<1e-12);le=np.isfinite(hi)&~eq;ge=np.isfinite(lo)&~eq
    A=vstack([mat[le],-mat[ge]]).tocsc();bb=np.r_[hi[le],-lo[ge]];c1=np.zeros(len(lb));c1[M]=1
    lp=linprog(c1,A_ub=A,b_ub=bb,A_eq=mat[eq],b_eq=hi[eq],bounds=list(zip(lb,ub)),method='highs',options={'primal_feasibility_tolerance':1e-8,'dual_feasibility_tolerance':1e-8})
    if not lp.success:raise ValueError(('continuous polish infeasible',lp.message))
    ub[M]=min(ub[M],lp.fun+1e-6);c2=np.zeros(len(lb));c2[ene]=1
    lp2=linprog(c2,A_ub=A,b_ub=bb,A_eq=mat[eq],b_eq=hi[eq],bounds=list(zip(lb,ub)),method='highs',options={'primal_feasibility_tolerance':1e-8,'dual_feasibility_tolerance':1e-8})
    if not lp2.success:raise ValueError(('energy polish failed',lp2.message))
    x=lp2.x;selected=[i for i in range(nt) if x[xs[i]]>0.5];active=[j for j in range(nr) if x[use[j]]>0.5]
    fullres={'version':'Q3-POOL-JOINT-V4','input_identity':fingerprint(),'decisions':[pool[i] for i in selected],'selected_pool_indices':selected,'starts':[float(x[ss[i]]) for i in selected],'sites':sites,'active_jobs':active,'relay_start':x[rs].tolist(),'relay_end':x[re].tolist(),'relay_energy':x[ene].tolist(),'relay_charge':x[chg].tolist(),'aircraft_assign':{},'battery_assign':{},'relay_assign':{},'component_assign':{},'extra_db':0.,'site_groups':[None]*nr,'transport_groups':[None]*len(selected),'makespan_s':float(x[M]),'weighted_tardiness_s':0.,'transport_energy_kwh':sum(ev[i]['energy'] for i in selected),'relay_energy_kwh':float(sum(x[ene])),'transport_sorties':len(selected),'relay_sorties':len(active),'solver':status,'global_optimality_proved':False,'polish':{'makespan_s':float(lp.fun),'relay_energy_kwh':float(lp2.fun),'integer_decisions_fixed':True}}
    for typ,tp in T.items():
        ii=[k for k,i in enumerate(selected) if pool[i]['type']==typ]
        for kind,cap in [('aircraft',len(tp['aircraft'])),('battery',tp['battery_count'])]:
            labels=color_intervals([(k,x[ss[selected[k]]],x[ss[selected[k]]]+ev[selected[k]]['duration']+(ev[selected[k]]['charge'] if kind=='battery' else 0)) for k in ii],cap);fullres[kind+'_assign'].update({str(k):v for k,v in labels.items()})
    fullres['relay_assign']={str(k):v for k,v in color_intervals([(j,x[prep[j]],x[ret[j]]+R['turnaround_s']) for j in active],len(R['aircraft'])).items()};fullres['component_assign']={str(k):v for k,v in color_intervals([(j,x[prep[j]],x[ret[j]]+x[chg[j]]) for j in active],R['component_count']).items()}
    fullres['total_energy_kwh']=fullres['transport_energy_kwh']+fullres['relay_energy_kwh'];fullres['decision_sha256']=digest(fullres['decisions']);dump(out/'candidate.json',fullres)
    rows=[];rev={i:k for k,i in enumerate(selected)}
    for h,d in enumerate(demands):
        if d['i'] in rev:
            j=next(j for j in d['allowed'] if x[cover[h,j]]>0.5);rows.append({**d,'i':rev[d['i']],'provider_index':j})
    dump(out/'assigned_atoms.json',rows);print('POLISHED',fullres['makespan_s'],fullres['total_energy_kwh'],len(selected),active,flush=True);return fullres,status
