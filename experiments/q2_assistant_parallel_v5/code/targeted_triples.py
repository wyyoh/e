"""3-route neighborhood explores larger regrouping, preserving all physical rules."""
from exact_neighborhood import *
def main():
 rng=random.Random(92900);start=from_decisions(json.loads((ROOT/'results/seed92401/best.json').read_text())['decisions']);best=start;bestm=schedule(best)
 bs=[i for i,p in enumerate(start) if p[0]=='B'];cs=[i for i,p in enumerate(start) if p[0]=='C'];aa=[i for i,p in enumerate(start) if p[0]=='A']
 cand=[]
 for i in bs:
  for j in cs:
   for k in aa:
    ix=[i,j,k];n=sum(len(start[t][1]) for t in ix);sites=set(s for t in ix for s in start[t][2])
    if n<=13 and len(sites)<=4:cand.append(ix)
 rng.shuffle(cand);records=[]
 for case,ix in enumerate(cand[:20]):
  rec=run(case,start,ix,8,92900+case);m=rec.get('decoded_metrics')
  if m:
   p=from_decisions(rec['selected_decisions'])
   # Separate post-processing can exchange identical physical boxes with different deadlines.
   for k in range(2):p=optimize_order(canonicalize(p),rng,4000)
   m=schedule(p);rec['after_deadline_reassignment']=m
   if feasible(m) and finite_key(m)<finite_key(bestm):
    best=p;bestm=m;print('IMPROVED',json.dumps(m),flush=True)
  records.append(rec)
  (ROOT/'results/triple_records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
  (ROOT/'results/triple_best.json').write_text(json.dumps({'metrics':bestm,'decisions':as_decisions(best)},ensure_ascii=False,indent=2))
  print('CASE',case,ix,rec.get('candidate_trips'),rec['status'],None if not m else [m['hard_late_boxes'],m['late_boxes'],m['makespan_s']],flush=True)
  evaluate.cache_clear();variants.cache_clear()
if __name__=='__main__':main()
