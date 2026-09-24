# Q2 assistant parallel experiment V5

Base commit: `97187484cdf90ee3f90e194679ce231e97c0baa2`.
Branch: `research/q2-assistant-parallel-v5`.

The user is optimizing with Codex concurrently. This work only adds files under `experiments/q2_assistant_parallel_v5/`. Do not update main, other research branches, official templates, or Q1/Q3/Q4. No merge is requested in this session.

Input baseline: the conversation attachment `D题_第二问全局验证V4_代码证书与23架次方案.zip`. V4's claimed baseline is 23 sorties, 5693.231489105107 s, 66.225670196 kWh; its retained lower bound is 5414.564006 s. These are baseline claims to be checked, not new results.

Planned scope: improve actual Q2 routes/batches and exact-resource schedules; independently verify any incumbent; preserve the global lower-bound scope. A restricted-neighborhood optimum must not be called an original-problem global optimum. Results and commands will be added after execution.

Integration later: compare identical input hashes, zero tardiness feasibility, then (makespan, energy, sorties). Lower bounds may be maximized only when valid for the same original problem and workflow. Keep source attribution and do not overwrite Codex's work.
