# Q3 current release: Q3-BOTTLENECK-V6 / time

Authoritative current result: **5836.969929328251 s**, **68.93941621018112 kWh**, 23 transport + 4 relay sorties.

Physical model: `Q3-HOVER-COMPATIBLE-V5`. Relay transit altitude is the maximum of terrain peak + 50 m, target hover altitude, and O01 work altitude; ordinary transport-flight rules are unchanged.

Primary expanded evidence: `release_v6/time/`. Historical `release_final/` is retained for audit and is no longer the selected Q3.

The full validated runtime ZIP is not stored by this connector commit; its SHA-256 is `f8efc0cb0859fe0bd39f0f23f1a18e824d3848873344ef3e7a93b11a93b257bf`.

The `time` primary is nominal (extra loss 0 dB). Old four-relay finite-domain certificates and old +0.50/+0.55 dB margins do not apply to this release. No original-problem global optimum is claimed.
