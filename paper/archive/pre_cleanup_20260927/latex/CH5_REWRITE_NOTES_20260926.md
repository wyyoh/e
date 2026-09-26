# Chapter 5 rewrite notes — 2026-09-26

## Reference writing patterns studied

The rewrite is grounded in the user-provided 2017 and 2025 Chinese Graduate Mathematical Modeling Competition excellent-paper collections.

Most relevant patterns:

- 2017 A10425002: question 2 is organized as problem description/analysis -> model establishment -> solution steps -> concrete route/time tables -> model evaluation.
- 2017 A80143001: question 2 is organized as problem analysis -> model establishment -> result/analysis, with intermediate scheduling tables rather than only aggregate metrics.
- 2017 A10252401/A10286374: complex UAV tasks are first decomposed into explicit solution steps, then the mathematical model and actual route/timing results are presented.
- 2025 A excellent NPU scheduling papers: complex finite-resource scheduling is presented as problem analysis -> solution framework -> mathematical model -> scheduling algorithm -> concrete results -> comparison/validation.

These references were used for organization and competition-paper exposition only. Their wording, formulas, numerical results, and problem-specific models were not copied.

## Applied changes to Chapter 5

Chapter 5 now follows:

1. Problem analysis
2. Solution framework
3. Joint heterogeneous scheduling model
4. ALNS and aircraft-battery event decoder
5. Formal 23-sortie schedule and concrete aircraft/battery timetable
6. Route/Gantt/result interpretation
7. Feasibility and energy refinement
8. Fixed-B bottleneck, 22-vs-23 comparison, global bound and pricing validation

The previous order placed proof/certification evidence before the concrete schedule. The rewrite puts the actual executable plan before quality certification, matching the dominant pattern in the excellent papers.

## Canonical sources for Chapter 5

- paper_integration/FINAL_SELECTION.json
- q2_final/solution/main_23/metrics.json
- q2_final/solution/main_23/decisions.json
- q2_final/solution/main_23/actual_box_changes.json
- experiments/q2_assistant_parallel_v5/inputs/selected_incumbent.csv
- experiments/q2_assistant_parallel_v5/code/core.py
- experiments/q2_assistant_parallel_v5/code/alns.py
- experiments/q2_assistant_parallel_v5/code/verify_solution.py
- problems/D/q2/evidence_v7/README.md
- problems/D/q2/evidence_v7/RESULTS_中文说明.md

## Evidence boundaries preserved

- weighted tardiness 0 is globally optimal because it is nonnegative and a feasible solution attains 0;
- the 5693.231489 s makespan is not claimed globally optimal;
- certified interval remains [5433.956428, 5693.231490] s, UB-normalized gap 4.554093092%;
- the fixed-B 5693.231489 s lower bound applies only when the six B-task structures are frozen;
- the 22-sortie schedule is a feasibility witness, not a 22-sortie optimality result;
- 3.1201x refers only to the controlled fixed-pricing-input experiment.
