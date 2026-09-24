"""Exact count-state DP, independent of the binary box-level MILP formulation."""
from dataclasses import dataclass
from functools import lru_cache
from model.physics import ENERGY_TOL,TIME_TOL


@dataclass(frozen=True)
class Label:
    n: int=0
    e: float=0.
    t: float=0.
    path: tuple=()

    def plus(self,p):
        return Label(self.n+1,self.e+p.energy,self.t+p.time,self.path+(p.id,))

    def combine(self,b):
        return Label(self.n+b.n,self.e+b.e,self.t+b.t,self.path+b.path)

    def record(self):
        return dict(sorties=self.n,energy_kwh=self.e,time_s=self.t,time_min=self.t/60,pattern_ids=self.path)


def equivalent(a,b):
    return a.n==b.n and abs(a.e-b.e)<=ENERGY_TOL and abs(a.t-b.t)<=TIME_TOL


def dominates(a,b):
    weak=a.n<=b.n and a.e<=b.e+ENERGY_TOL and a.t<=b.t+TIME_TOL
    strict=a.n<b.n or a.e<b.e-ENERGY_TOL or a.t<b.t-TIME_TOL
    return weak and strict


def prune(labels):
    front=[]
    for a in sorted(labels,key=lambda l:(l.n,l.e,l.t,l.path)):
        if any(equivalent(b,a) or dominates(b,a) for b in front):continue
        front=[b for b in front if not dominates(a,b)]
        front.append(a)
    return sorted(front,key=lambda l:(l.n,l.e,l.t,l.path))


def scalar_dp(demand,patterns,objective='lex'):
    key=(lambda l:(l.n,l.e,l.t,l.path)) if objective=='lex' else (lambda l:(l.t,l.n,l.e,l.path))
    by_kind=[[p for p in patterns if p.counts[k]>0] for k in range(len(demand))]
    @lru_cache(None)
    def visit(state):
        if not any(state):return Label()
        k=next(k for k,n in enumerate(state) if n)
        best=None
        for p in by_kind[k]:
            rest=tuple(n-c for n,c in zip(state,p.counts))
            if min(rest)<0:continue
            tail=visit(rest)
            if tail is None:continue
            candidate=tail.plus(p)
            if best is None or key(candidate)<key(best):best=candidate
        return best
    return visit(tuple(demand))


def pareto_dp(demand,patterns):
    by_kind=[[p for p in patterns if p.counts[k]>0] for k in range(len(demand))]
    @lru_cache(None)
    def visit(state):
        if not any(state):return (Label(),)
        k=next(k for k,n in enumerate(state) if n)
        candidates=[]
        for p in by_kind[k]:
            rest=tuple(n-c for n,c in zip(state,p.counts))
            if min(rest)>=0:
                candidates.extend(tail.plus(p) for tail in visit(rest))
        return tuple(prune(candidates))
    return list(visit(tuple(demand)))


def global_pareto(fronts):
    frontier=[Label()]
    for area,local in sorted(fronts.items()):
        frontier=prune(a.combine(b) for a in frontier for b in local)
    return frontier
