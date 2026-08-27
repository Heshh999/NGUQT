# CCHC-V1 — DIAGNOSTICS (predeclared; never candidates)

Binding stressed cost 1.305 pt RT. Seeds: bootstrap/perm 20260901,
regime-permutation 20260902, matched/anchor 20260903.

| test | n | EV | reading |
|---|---|---|---|
| **PRIMARY** | 98 | **+15.335** | 3 binding gates fail |
| D1 no-regime ablation | 226 | +2.438 | regime gate does concentrate return… |
| D2 no-displacement ablation | 676 | −0.369 | β>0 alone is worthless |
| D3 component-free baseline | 1,639 | −0.797 | unconditional closing continuation loses |
| D4 direction-reversal placebo | 98 | −12.078 | direction is doing real work on these days |
| D5 regime-label permutation (10k) | null +2.276 | **p 0.0211** | labels carry information |
| **D6 shift −20** | 116 | **+16.753** | **beats the true regime** |
| **D6 shift −10** | 106 | **+19.789** | **beats the true regime** |
| D6 shift +10 (non-tradable) | 104 | +7.495 | falsification only |
| D6 shift +20 (non-tradable) | 94 | +4.261 | falsification only |
| **D7 matched random-day control** | 98 | **+10.932** | **most of the edge is period, not event** |
| D8 randomized-anchor placebo (200) | null −5.352 | p 0.0050 | anchor matters |
| D9 time-of-day placebo (16:00→16:30) | 62 | −4.228 | effect does not extend past the interval |

## What the diagnostics actually establish
Two of them are decisive, and they cut against the candidate:

1. **D6 date-shift.** Regime labels taken from **10 and 20 eligible
   sessions earlier** produce **higher** stressed EV (+19.79, +16.75)
   than the true, correctly-aligned labels (+15.34). A genuinely
   predictive alignment would degrade under shifting. What survives
   shifting is a slowly-varying *volatility-regime* state: any nearby
   version of it selects the same 2020/2022 clusters.

2. **D7 matched random-day control.** Non-event days matched on
   half-year × lagged-|D| tercile earn **+10.93** — roughly 71% of the
   primary's +15.34. So the event selection itself contributes only
   ≈ +4.4 pt; the rest is *when* the strategy is active, not *what* it
   selects. The frozen retention gate G12 compares against the
   component-free baseline D3 (−0.797) and therefore passes, but D7 is
   the more informative control and it says most of the apparent edge
   is period concentration.

D4 (−12.08 reversed) and D8 (p 0.005) confirm the days themselves are
directionally non-random — but D1 (+2.44 across all 226 displacement
days) shows that without the regime gate the same event type earns
almost nothing, and the regime gate's own timing is not specific (D6).
D9 shows the effect does not survive into the adjacent 16:00→16:30
horizon, consistent with an interval-local volatility phenomenon.

Influence: drop-most-influential +12.37; drop-best-trade +12.37;
drop-best-month (2020-03) +8.04; drop-best-year (2020) +9.52.
All remain positive — the failure is not one print, it is the
concentration of the whole sample into two crisis years.
