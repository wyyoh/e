# 2026-09-26 manuscript structure revision

This branch revises the competition-paper exposition without changing the frozen headline results.

## Why

The prior draft devoted substantial space to repeated discussion and evidence summaries while compressing Q2/Q3 model construction and solution mechanics into short overview subsections. The revision moves detail toward the parts directly needed to audit model and solution completeness.

## Source-grounded additions

### Q1
- box-level MILP coverage constraints;
- symmetry-compressed equivalent formulation;
- count-state DP recurrence and Pareto dominance logic.

### Q2
- task-selection / aircraft-assignment / battery-assignment / start-time variables;
- separate aircraft and battery occupation intervals;
- two-stage battery recharge function inherited from the task statement and implemented in experiments/q2_assistant_parallel_v5/code/core.py;
- deterministic resource-event decoding;
- ALNS destroy/repair and local moves documented from experiments/q2_assistant_parallel_v5/code/alns.py;
- explicit separation of search surrogate score and final lexicographic selection;
- set-partitioning / full-pricing / complementary-branch certification route consistent with Q2-EVIDENCE-V7-FOCUSED.

### Q3
- terrain blockage treated as additional propagation loss, matching task rules and the merged screening implementation;
- direct / relay service state equations;
- relay arrival, service-window, resource and energy constraints;
- separation of static candidate screening from full joint-schedule feasibility;
- continuous/critical-endpoint verification retained as the final acceptance layer.

### Q4
- indivisible task blocks explained as connected components induced by frozen transport and actual relay-service relations;
- explicit stock-surplus quantity separated from time-axis idleness.

## Deliberately unchanged
- Q1: 18 sorties; 59.131296022053 kWh; 546.266929148593 min.
- Q2: 23 sorties; 5693.231489105106 s; 66.21445957313102 kWh; certified interval [5433.956428, 5693.231490] s.
- Q3: 23 transport + 4 relay sorties; 6340.439338658365 s; 69.30853085578303 kWh.
- Q4 strict shortages: K=2 -> 2, K=3 -> 7.

## Remaining evidence gap
The main branch retains Q3 release summary and proof-scope documentation but not the full frozen relay-site / relay-window table in plain repository files. This revision therefore does not invent those coordinates or timestamps. They should be inserted only from the formally frozen companion archive before final submission.
