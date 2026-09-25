import json,random
from math import comb
from pathlib import Path

ranked=json.loads(Path('problems/D/q3/experiments_v3/robust_spatial/ranked_candidates.json').read_text())
N=len(ranked);good=sum(c['sampled_minimum_margin_db']>=0.5 for c in ranked)
rng=random.Random(20260925);sample=rng.sample(ranked,6)
print(json.dumps({
 'candidate_pool':N,
 'screen_pass_count':good,
 'screen_pass_fraction':good/N,
 'random_hit_probability':{str(k):1-comb(N-good,k)/comb(N,k) for k in (1,3,5,10)},
 'uniform_six':[{'xyz':c['xyz'],'score':c['sampled_minimum_margin_db'],'pass':c['sampled_minimum_margin_db']>=.5} for c in sample]
},indent=2))
