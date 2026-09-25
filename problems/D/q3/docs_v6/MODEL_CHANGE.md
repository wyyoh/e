# Explicit model change and causal scope

## Old restricted relay domain
The legacy relay geometry used `H = terrain_peak + 50` and rejected a hover target above H; candidate generation also clipped hover AGL to that plane.

## Hover-compatible relay transfer model
Only for relay transfer flights:
\[
H_R(p)=\max\{\max_{c\in\mathcal C(O01,p)}Z(c)+50,\ z_p,\ z_{O01}\}.
\]
This preserves terrain clearance and makes the transfer altitude compatible with the hover endpoint. All outgoing/return climb/descent, horizontal flight, setup, hover and charging are recomputed. Hover AGL remains in (0,300]. Ordinary transport legs are unchanged.

The substantial V5 improvement therefore changed the relay candidate domain and cannot be presented as a pure solver improvement. V6 keeps this physical model fixed and improves relay placement/service handoff and joint resource timing.

No original-problem global optimum is claimed. Full interval and endpoint verification is required for accepted candidates; sampling is only a screening device.
