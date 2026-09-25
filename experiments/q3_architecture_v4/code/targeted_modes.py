"""Generate bounded two-sortie box-transfer/swap modes, preserving real IDs.
Heuristic candidate generation, NOT complete column generation.
"""
from pathlib import Path
import sys,itertools,copy,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'));sys.path.insert(0,str(ROOT/'code_v4'))
from precompute import load,dump
from transport import variants,evaluate,BI,B,T
from pool_master import routekey,solve
from screen_sites import sampled_profiles

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--name',default='targeted_modes');ap.add_argument('--seconds',type=float,default=180);ap.add_argument('--per-pair',type=int,default=8);ap.add_argument('--sites',type=int,default=4);a=ap.parse_args();ref=load(ROOT/'release_final/primary/selected.json');pack=load(ROOT/'experiments_v4/order_modes/pool.json');routes=pack['routes'][:];seen={routekey(d) for d in routes};base=ref['decisions'];pairs=[(2,3),(2,4),(2,7),(2,13),(4,13),(6,8),(7,13),(11,19),(19,20),(10,13),(0,1),(2,22),(4,7)];stats=[]
 for i,j in pairs:
  p,q=base[i],base[j];pi=set(BI[b] for b in p['boxes']);qi=set(BI[b] for b in q['boxes']);proposal=set()
  for b in pi:
   if len(pi)>1:proposal.add((tuple(sorted(pi-{b})),tuple(sorted(qi|{b}))))
  for c in qi:
   if len(qi)>1:proposal.add((tuple(sorted(pi|{c})),tuple(sorted(qi-{c}))))
  for b in pi:
   for c in qi:proposal.add((tuple(sorted(pi-{b}|{c})),tuple(sorted(qi-{c}|{b}))))
  valid=[]
  for ids1,ids2 in proposal:
   opts=[]
   for typ,ids in [(p['type'],ids1),(q['type'],ids2)]:
    if len({B[b]['site'] for b in ids})>4:opts.append([]);continue
    vs=[k for k in variants(typ,ids) if evaluate(k)['latest']>=30];vs.sort(key=lambda k:(evaluate(k)['duration']+80*evaluate(k)['energy']));opts.append(vs[:3])
   for k1,k2 in itertools.product(*opts):
    e1,e2=evaluate(k1),evaluate(k2);score=e1['duration']+e2['duration']+80*(e1['energy']+e2['energy']);valid.append((score,k1,k2))
  valid.sort(key=lambda t:t[0]);chosen=valid[:a.per_pair];n0=len(routes)
  for _,k1,k2 in chosen:
   for typ,ids,order in [k1,k2]:
    d={'type':typ,'boxes':[B[b]['id'] for b in ids],'route':list(order)}
    if routekey(d) not in seen:seen.add(routekey(d));routes.append(d)
  stats.append({'pair':[i,j],'generated_feasible_pairs':len(valid),'kept_pairs':len(chosen),'new_patterns':len(routes)-n0})
 out=ROOT/'experiments_v4'/a.name;out.mkdir(parents=True,exist_ok=False);sites=ref['sites']
 if a.sites>4:
  other=load(ROOT/'experiments_v4/site_screen/screen_pool.json');cand=load(ROOT/'experiments_v3/relay_three/expanded_pool.json')['candidates'];sites=sites+[cand[j]['geometry'] for j in other['selected_site_sets'][0]['indices'] if tuple(cand[j]['xyz']) not in {tuple(g[k] for k in 'xyz') for g in sites}]
 print('TARGET_MODES',len(routes),stats,flush=True);profiles,st=sampled_profiles(routes,sites,20);dump(out/'pool.json',{'routes':routes,'sites':sites,'profiles':profiles,'generator':stats,'screen':st});solve(routes,sites,profiles,out/'master',seconds=a.seconds,slack=30,reference=ref)
if __name__=='__main__':main()
