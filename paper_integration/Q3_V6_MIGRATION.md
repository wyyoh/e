# Q3 V6 main integration and migration note

Main selection is advanced to **Q3-BOTTLENECK-V6 / time**. The primary result is `5836.969929328251 s`, `68.93941621018112 kWh`, with 23 transport and 4 relay sorties. The physical model is **Q3-HOVER-COMPATIBLE-V5**.

Q1 and Q2 are unchanged. Strict Q4 is recomputed from the V6 time calendar: K=2 shortage 1, K=3 shortage 7. Old Q4 relay-copy/N-1/Pareto sensitivity results remain historical and were not recomputed for V6.

The prior Q3 `release_final/` remains in the repository as historical evidence. The authoritative current machine-readable selector is `paper_integration/FINAL_SELECTION.json`.

The complete runtime archive `q3_bottleneck_v6_full.zip` was independently validated with SHA-256 `f8efc0cb0859fe0bd39f0f23f1a18e824d3848873344ef3e7a93b11a93b257bf`, but this connector-based main update does **not** upload the 36 MB binary archive. The primary decision, schedule summaries, relay/flight/delivery records, validation summaries and strict Q4 handoff are expanded in the repository.

Old finite-domain four-relay lower bounds and old +0.50/+0.55 dB robustness claims do not transfer to V6. The V6 primary is nominal (0 dB extra loss); +0.25 dB belongs only to the separately documented robust candidate.

Manuscript prose/figures are not mechanically rewritten by this integration. Any old Q3/Q4 numbers in the LaTeX draft require a consistency pass before final submission.
