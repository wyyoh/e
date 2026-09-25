"""Time-aware site selection from inherited candidates. Screen is NOT certification."""
from pathlib import Path
import sys,time,argparse,copy
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import csr_matrix,vstack
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'));sys.path.insert(0,str(ROOT/'code_v4'))
from precompute import load,dump,phases_for
from radio import G,THR,R
from pool_master import routekey,solve
from run_pool import inherited_pool

def choose_sites(max_sets=14):
    ref,known,src=inherited_pool()
    pool=load(ROOT/'experiments_v3/relay_three/expanded_pool.json')['candidates']
    mat=np.load(ROOT/'experiments_v3/relay_three/certified_matrix.npz');cov=mat['coverage'];pts=mat['points'];xyz=mat['positions']
    assert np.array_equal(xyz,np.array([c['xyz'] for c in pool]))
    n=len(pool);prices=np.array([c['geometry']['out_s']+c['geometry']['back_s'] for c in pool]);rng=np.random.default_rng(447)
    reps={}
    for i,row in enumerate(cov):
        if not row.any():continue
        key=np.packbits(row).tobytes()
        if key not in reps or prices[i]<prices[reps[key]]:reps[key]=i
    ids=list(reps.values());C=csr_matrix(cov[ids].T.astype(float));C=vstack([C,np.ones((1,len(ids)))]).tocsc();lb=np.r_[np.ones(len(pts)),4];ub=np.r_[np.full(len(pts),np.inf),4]
    chosen=set();sets=[]
    for k in range(max_sets):
        cost=prices[ids]*(rng.uniform(.80,1.20,len(ids)) if k else 1.)
        if k>3:cost=cost+(rng.uniform(-100,100,len(pts))@cov[ids].T)
        r=milp(cost,integrality=np.ones(len(ids)),bounds=Bounds(0,1),constraints=LinearConstraint(C,lb,ub),options={'time_limit':4,'mip_rel_gap':.005})
        if r.x is None:continue
        js=[ids[t] for t,v in enumerate(r.x) if v>.5];chosen.update(js);sets.append({'indices':js,'objective':float(r.fun),'status':int(r.status)})
        row=np.zeros(len(ids));row[np.flatnonzero(r.x>.5)]=1;C=vstack([C,csr_matrix(row[None,:])]).tocsc();lb=np.r_[lb,-np.inf];ub=np.r_[ub,3]
    site_geos=[];seen=set()
    for g in ref['sites']:
        key=tuple(g[v] for v in 'xyz');seen.add(key);site_geos.append(g)
    for i in sorted(chosen):
        g=pool[i]['geometry'];key=tuple(g[v] for v in 'xyz')
        if key not in seen:seen.add(key);site_geos.append(g)
    print('SELECTED_SITES',len(site_geos),len(sets),flush=True)
    return ref,known,site_geos,sets

def sampled_profiles(routes,sites,step=30):
    from point_fast_v3 import margins
    ev,ph=phases_for(routes);points=[];meta=[]
    for p in ph:
        a=np.array([p[k+'0'] for k in 'xyz']);b=np.array([p[k+'1'] for k in 'xyz']);dt=p['end_s']-p['start_s']
        tt=np.linspace(0,1,max(2,int(np.ceil(dt/step))+1)) if np.linalg.norm(b-a)>1e-9 else np.array([0.,1.])
        for t in tt:points.append(a+(b-a)*t);meta.append((p['i'],p['start_s']+dt*t))
    points=np.array(points);uniq,rev=np.unique(points,axis=0,return_inverse=True);direct=margins(uniq,G,THR['UG'])>=-1e-10
    back=[];acc=[]
    for j,g in enumerate(sites):
        s=np.array([g[k] for k in 'xyz']);bk=bool(margins(s[None,:],G,THR['RG'])[0]>=-1e-10);back.append(bk);acc.append((margins(uniq,s,THR['UR'])>=-1e-10)&bk)
        if j%10==0:print('POINT_SCREEN',j,'/',len(sites),'unique',len(uniq),flush=True)
    A=np.array(acc).T;profiles=[[] for _ in routes]
    for idx,(i,t) in enumerate(meta):
        k=rev[idx]
        if direct[k]:continue
        allow=np.flatnonzero(A[k]).tolist();profiles[i].append({'a':float(t),'b':float(t),'allowed':allow,'kind':'screen_point'})
    for i,rows in enumerate(profiles):
        compact=[]
        for d in sorted(rows,key=lambda a:(a['a'],a['b'])):
            if compact and d['allowed']==compact[-1]['allowed'] and d['a']-compact[-1]['b']<=step+1e-5:compact[-1]['b']=d['b']
            else:compact.append(d.copy())
        profiles[i]=compact
    return profiles,{'screen_step_s':step,'screen_point_count':len(points),'unique_point_count':len(uniq),'whole_time_certified':False,'backhaul':back}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--name',default='site_screen');ap.add_argument('--sets',type=int,default=12);ap.add_argument('--seconds',type=float,default=150);ap.add_argument('--fixed',action='store_true');ap.add_argument('--slack',type=float,default=30);ap.add_argument('--resume',action='store_true');a=ap.parse_args();out=ROOT/'experiments_v4'/a.name;out.mkdir(parents=True,exist_ok=True)
    if a.resume:pack=load(out/'screen_pool.json');ref=load(ROOT/'release_final/primary/selected.json');routes=pack['routes'];sites=pack['sites'];profiles=pack['profiles']
    else:
        ref,known,sites,sets=choose_sites(a.sets);keys=[routekey(d) for d in ref['decisions']]
        if not a.fixed:keys+=sorted(set(known)-set(keys))
        routes=[known[k][0] for k in keys];profiles,st=sampled_profiles(routes,sites,30);dump(out/'screen_pool.json',{'routes':routes,'sites':sites,'profiles':profiles,'screen':st,'selected_site_sets':sets})
    solve(routes,sites,profiles,out/'master',seconds=a.seconds,slack=a.slack,fixed_routes=a.fixed,reference=ref)
if __name__=='__main__':main()
