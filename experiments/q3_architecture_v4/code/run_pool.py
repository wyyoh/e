from pathlib import Path
import sys,json,copy,time,argparse,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'));sys.path.insert(0,str(ROOT/'code_v4'))
from precompute import load,dump
from pool_master import routekey,solve
from input_identity import fingerprint

def inherited_pool():
    ref=load(ROOT/'release_final/primary/selected.json');xyz=[tuple(s[k] for k in 'xyz') for s in ref['sites']];identity=fingerprint();known={};files=[]
    for p in sorted(ROOT.rglob('precomputed.json')):
        if 'experiments_v4' in p.parts:continue
        d=load(p)
        if d.get('extra_db',0)!=0 or d.get('input_identity')!=identity:continue
        if [tuple(s[k] for k in 'xyz') for s in d.get('sites',[])]!=xyz:continue
        if any(g is not None for g in d.get('site_groups',[])+d.get('transport_groups',[])):continue
        for i,dec in enumerate(d['decisions']):
            key=routekey(dec)
            if key in known:continue
            dem=[{'a':c['a'],'b':c['b'],'allowed':c['allowed'],'kind':c.get('kind','interval')} for c in d['compact'] if c['i']==i];known[key]=(dec,dem,{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        files.append(str(p.relative_to(ROOT)))
    return ref,known,files

def main():
    a=argparse.ArgumentParser();a.add_argument('--name',default='inherited_pool');a.add_argument('--seconds',type=float,default=180);a.add_argument('--fixed',action='store_true');a.add_argument('--slack',type=float,default=30);args=a.parse_args();ref,known,files=inherited_pool();keys=[routekey(d) for d in ref['decisions']]
    if not args.fixed:keys+=sorted(set(known)-set(keys))
    pool=[known[k][0] for k in keys];profiles=[known[k][1] for k in keys];out=ROOT/'experiments_v4'/args.name;out.mkdir(exist_ok=False,parents=True);dump(out/'pool.json',{'routes':pool,'profiles':profiles,'sites':ref['sites'],'source_caches':files,'provenance':[known[k][2] for k in keys]});print('POOL_READY',len(pool),'cache sources',len(files),flush=True);solve(pool,ref['sites'],profiles,out,seconds=args.seconds,slack=args.slack,fixed_routes=args.fixed,reference=ref)
if __name__=='__main__':main()
