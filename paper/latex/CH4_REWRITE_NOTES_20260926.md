# Chapter 4 rewrite notes — 2026-09-26

## Reference writing patterns studied

The rewrite is based on the user-provided 2017 and 2025 Chinese Graduate Mathematical Modeling Competition excellent-paper collections. The closest references inspected in detail were:

- 2017 A10425002: Q1 organized as problem description/analysis -> model establishment -> model solution, with a workflow figure followed by concrete result tables and interpretation.
- 2017 A80143001: Q1 organized as model analysis -> model establishment -> model solution -> model evaluation.
- 2017 A10252401 / A10286374: Q1 first decomposes the task into explicit solution steps, then executes those steps and reports the actual route/plan tables.
- 2025 D excellent papers on low-altitude turbulence monitoring and optimal route planning: strong use of model-structure diagrams, intermediate-result figures/tables, validation, and immediate result interpretation.

These papers were used for chapter organization and competition-paper exposition only. Their formulas, numerical results, wording, and problem-specific models were not copied into this manuscript.

## Applied changes to Chapter 4

Chapter 4 now follows:

1. Problem analysis and solution roadmap
2. Safe payload model establishment
3. Safe payload solution and result interpretation
4. Indivisible-box batching model
5. Exact solution method and cross-validation
6. Formal 18-sortie solution and area-level results
7. Baseline and Pareto comparison
8. Return-reserve sensitivity analysis

## Canonical numerical sources

All Q1 numbers remain grounded in main @ 86aa4da46d7218e001d1012f804f0acece94ca60:

- problems/D/q1/results/objective_summary.json
- problems/D/q1/results/optimal_batches.csv
- problems/D/q1/results/baseline_summary.csv
- problems/D/q1/results/sensitivity_summary.json

The rewrite also corrected an earlier prose inconsistency in the baseline discussion by replacing unsupported intermediate baseline values with the canonical baseline_summary.csv values.
