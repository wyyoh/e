# Chapter 6 rewrite notes — 2026-09-26

## Authoritative repository state

- Latest main merged into this review branch: `e9ae928621234165c50d5152382ee2861c5b750b`.
- Current Q3 release: `Q3-BOTTLENECK-V6`.
- Current Q3 physical model: `Q3-HOVER-COMPATIBLE-V5`.
- Primary path: `problems/D/q3/release_v6/time`.
- Primary joint makespan: `5836.969929328251 s`.
- Primary total energy: `68.93941621018112 kWh`.
- Current strict Q4 shortages inherited from V6/time: K=2 -> 1; K=3 -> 7.

## Excellent-paper writing patterns studied

The Chapter 6 rewrite follows the organizational patterns observed in the user-provided 2017 and 2025 Chinese Graduate Mathematical Modeling Competition excellent-paper collections:

- 2017 A-problem UAV disaster-relief papers: problem description/analysis -> solution roadmap -> model establishment -> model solution -> concrete relay deployment tables/figures.
- 2025 D-problem low-altitude turbulence / route-planning papers: system framework -> layered physical/optimization model -> algorithm -> concrete results -> validation and sensitivity/comparison.

These papers were used only for competition-paper organization and exposition. Their wording, formulas and numerical results were not copied.

## Current method change represented in the manuscript

The manuscript no longer describes the legacy restricted relay-height model as current. Relay transfer now uses

`H_R(p) = max(terrain_peak + 50 m, hover altitude z_p, O01 work altitude)`

for relay transfer flights only. Ordinary transport legs retain the original terrain-peak-plus-50-m rule. V6 then improves relay relocation, provider handoff and joint resource timing under this fixed physical model.

Chapter 6 is organized as:

1. Problem analysis and method update
2. V6 solution framework
3. Continuous communication and hover-compatible relay physics
4. Transport-relay joint scheduling model
5. Candidate relocation, joint discrete scheduling, bottleneck handoff optimization and fixed-structure continuous LP
6. Concrete V6 transport/relay plan, including all four relay positions and service windows
7. Bottleneck-chain explanation for the ~87.998 s same-model improvement
8. Continuous-interval / critical-endpoint validation, candidate comparison and evidence boundaries

## Evidence boundaries preserved

- No full-Q3 original-problem global optimality claim.
- The legacy 5755-site four-relay lower-bound certificate does not transfer to the hover-compatible candidate domain.
- The legacy +0.50/+0.55 dB robustness guarantees do not transfer to V6.
- Only the `robust025` +0.25 dB alternative is treated as a current independently verified robustness witness.
- The LP lower bound `5836.969928328251 s` proves only fixed-discrete-structure continuous-time optimality (fixed routes, real-resource order, providers and relay SOC branches).
- Validation counts establish feasibility of the saved V6 plan; they are not a substitute for global optimality.

## Provenance boundary

User-supplied external material contributed compact candidate box/type/route data and relay coordinates/heights to the V5 lineage. Accepted candidates were retimed and recomputed under the project's own AEQD/DEM/g=9.81 model and independently revalidated. The paper therefore does not claim all inherited starting layouts were independently discovered.

## Downstream synchronization

Because Q4 freezes the Q3 schedule, Q4 strict values were synchronized to the V6/time calendar. K=2 now has shortage 1 (one C-type transport UAV); K=3 remains shortage 7. Legacy relay-copy/N-1/Pareto sensitivity results were not recomputed for V6 and remain historical only.
