# LPCC-V1 — RESULTS

Protocol freeze commit `f08396b1a2fdef5ebb8e000fef01723fa321813f`
(recorded per §12); engine/tests 21/21 PASS; raw output
`LPCC_RUN_OUTPUT.txt`; trades `LPCC_V1_TRADES.csv`; event snapshots
`LPCC_V1_EVENT_AUDIT.csv`; ledger `LPCC_V1_HYPOTHESIS_LEDGER.csv`.

## HEADLINE
> **LPCC-V1 HISTORICAL FEASIBILITY FAILED; HYPOTHESIS KILLED.**
> First binding failure: **G04 (base-cost PF ≥ 1.30; measured 0.857)**.
> 15 of 21 applicable gates fail. The frozen rule loses money BEFORE
> costs: gross EV −0.823 pt/trade.

## Sample
1,817 eligible days (2019-07→2026-08-17); 1,691 warm; 223 pass the
displacement gate; **127 primary trades on 127 unique days** (73 long /
54 short; 12 stop-outs / 115 time exits). Sample floors PASSED — this
is an evidential failure, not an insufficiency.

## Economics (net points/trade, n=127)
| scenario | EV | EV(R) | WR | PF |
|---|---|---|---|---|
| gross | **−0.823** | +0.012R | 48.8% | 0.93 |
| slip 1 tick/side | −1.323 | +0.001R | 48.8% | 0.89 |
| slip 2/side (prov. base) | −1.823 | −0.010R | 47.2% | 0.85 |
| slip 3/side (stress) | −2.323 | −0.021R | 47.2% | 0.81 |
| repo base 0.87 | −1.693 | −0.008R | 47.2% | 0.86 |
| **repo stressed 1.74 (binding)** | **−2.563** | −0.027R | 47.2% | **0.79** |

Stressed CI95 [−7.66, +2.49]; permutation p 0.516; BH q 0.516.
Realized payoff 0.88; break-even WR 53.1% vs actual 47.2% (**−5.8-point
margin**). Sharpe −0.37; maxDD −335 pt; longest losing streak 6.
Exact-dollar cost gate remains UNRESOLVED and moot.

## Stability
Positive in 2 of 7 years (2023 +0.5, 2025 +9.7); 2026 −17.1;
33% of half-year segments positive (gate needs 70%). No period
domination *of profits* exists because total profit is negative.

## Why it failed (from the predeclared diagnostics)
- **The regime gate is inert.** No-regime ablation: −2.22 vs primary
  −2.56 — the β>0 filter selected a slightly WORSE subset.
  Regime-label permutation p 0.563: the trailing 126-day slope carries
  no alignment information at this anchor/window. Date-shifted regimes
  (−10, −20 sessions) outperformed the true one (+4.25, +0.84) —
  exactly what a noise variable looks like.
- **The displacement gate is inert too.** Unconditional continuation
  in the window: −1.72; top-decile displacement: −2.22. Large
  premarket displacement does not continue in (08:00, 08:30].
- **The Wave 4 VR30=1.32 super-diffusion is real but not monetizable
  this way**: variance-ratio trending measures path roughness of the
  whole window, not a conditional drift harvestable from a fixed
  08:00 entry. The direction-reversal placebo also loses (−2.16):
  both directions lose after any cost because the window's conditional
  drift given the gates is ≈ 0 and the strategy pays spread/cost
  either way.

## Frozen consequences
- `LPCC_V1_FROZEN_CANDIDATE.json` = **empty**.
- Parameter stability, walk-forward, Monte Carlo, execution stress,
  risk-of-ruin: **NOT REACHED — PRELIMINARY FAILURE** (per freeze; no
  rescue surface was run).
- LPCC-V1 is dead as frozen: no rescue, revision, inversion, re-test,
  fallback fade arm, or alternative window. The Wave 4 knowledge object
  (trending windows) stands unchanged as descriptive structure.
- Buffer 2026-08-18→31 and all future partitions untouched.
