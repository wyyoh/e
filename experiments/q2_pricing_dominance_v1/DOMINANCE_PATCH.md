# Core dominance change

For cut pricing, precompute for every (used_weight, used_volume) state the cut parity bits that can still be flipped by at least one capacity-feasible future stop pattern:

```cpp
vector<int> livecut((Q+1)*(V+1),0);
for(int ww=0;ww<=Q;ww++) for(int vv=0;vv<=V;vv++){
  int m=0;
  for(int j=0;j<C;j++)
    if(ww+w[j]<=Q && vv+v[j]<=V) m |= flip[j];
  livecut[ww*(V+1)+vv]=m;
}
```

Then compare labels only on `mask & livecut[state]`.

For elementary A/B pricing, additionally precompute a live-site mask under the same remaining-capacity test and compare `visited & livesite[state]`.

The experiment does **not** remove a site/cut bit that can still be reached by any capacity-feasible continuation. It is a state-equivalence compression for pricing, not a new routing constraint.
