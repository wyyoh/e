"""Exhaustively generate selected 2/3-trip replacement neighborhoods; MIP-limited search."""
from exact_neighborhood import *
def main():
 rng=random.Random(92600);best=from_decisions(json.loads((ROOT/'results/seed92401/best.json').read_text())['decisions']);bestm=schedule(best)
 # Exact neighborhood generation, not exhaustive coverage of the whole Q2 search space.
 scenarios=[]
 for target in ['S014','S008','S004']:
  for aux in ['S001','S006','S005']:
   targets=[i for i,p in enumerate(best) if p[0]=='B' and target in p[2]]
   auxiliaries=[i for i,p in enumerate(best) if p[0]=='C' and p[2]==(aux,)]
   for i in targets:
    for j in auxiliaries:scenarios.append((target,aux,[i,j]))
 records=[]
 for case,(s,a,ix) in enumerate(scenarios):
  # Use fixed start so index meaning stays stable; retain any best found separately.
  start=from_decisions(json.loads((ROOT/'results/seed92401/best.json').read_text())['decisions'])
  if sum(len(start[i][1]) for i in ix)>14:continue
  rec=run(case,start,ix,10,92600+case);rec['target']=s;rec['aux']=a
  m=rec.get('decoded_metrics')
  if m and feasible(m) and finite_key(m)<finite_key(bestm):
   best=from_decisions(rec['selected_decisions']);bestm=m;print('IMPROVED',json.dumps(m),flush=True)
  records.append(rec)
  (ROOT/'results/targeted_records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
  (ROOT/'results/targeted_best.json').write_text(json.dumps({'metrics':bestm,'decisions':as_decisions(best)},ensure_ascii=False,indent=2))
  print('CASE',case,s,a,len(ix),rec.get('candidate_trips'),rec['status'],None if not m else [m['hard_late_boxes'],m['makespan_s']],flush=True)
  evaluate.cache_clear();variants.cache_clear()
if __name__=='__main__':main()
