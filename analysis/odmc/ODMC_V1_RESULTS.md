# ODMC-V1 — RESULTS

Protocol freeze **`9072bd3d8ef244eb6b87a6c56f9e983849e526a8`** (v1.0.1
test correction `93acc65`, committed before any outcome). Provenance:
Wave 4 `S5open` q=10 cell reproduced **EXACT**. Tests **33/33 PASS**.
Raw output `ODMC_RUN_OUTPUT.txt`; trades `ODMC_V1_TRADES.csv`;
snapshots `ODMC_V1_EVENT_AUDIT.csv`; ledger `ODMC_V1_HYPOTHESIS_LEDGER.csv`.

## HEADLINE
> **ODMC-V1 HISTORICAL FEASIBILITY FAILED; HYPOTHESIS KILLED.**
> First binding failure: **G04 — base-cost PF 1.201 (< 1.30)**.
> 13 of 21 applicable gates fail. Sample floors PASSED (257 trades /
> 257 days), so this is an evidential failure, not insufficiency.

## Primary economics (n = 257 trades / 257 unique days)
| scenario | EV pt | EV R | WR | PF | payoff |
|---|---|---|---|---|---|
| gross | +3.599 | +0.084 | 56.0% | 1.272 | 1.00 |
| slip 1t/side | +3.099 | +0.075 | 55.3% | 1.231 | 1.00 |
| slip 2t/side (prov. base) | +2.599 | +0.066 | 54.1% | 1.190 | 1.01 |
| repo base 0.87 | +2.729 | +0.068 | 54.1% | 1.201 | 1.02 |
| repo RTH 1.305 | +2.294 | +0.060 | 54.1% | 1.166 | 0.99 |
| slip 3t/side | +2.099 | +0.057 | 53.7% | 1.151 | 0.99 |
| **BINDING STRESS 4t/side = 2.00** | **+1.599** | **+0.048** | **53.3%** | **1.113** | **0.98** |

**Even gross PF is only 1.272 — below the 1.30 base gate before a single
tick of cost.** Stressed CI95 **[−3.341, +6.546]** (includes zero);
permutation **p 0.5891**; local BH q 0.5891; familywise **FAIL**.
Break-even WR 50.6% vs actual 53.3% (+2.7-point margin, below the
5-point requirement). Sharpe/trade 0.039, Sortino 0.060, maxDD
**−686.0 pt** over 70 trades, longest losing streak 6, largest loss
−122.2, CVaR₅ −91.2, median MFE 24.0 / median MAE 18.5. Long 126
(+1.81) / short 131 (+1.39); 23 stop-outs / 234 time exits.
Exact-dollar cost gate UNRESOLVED.

## Stability
| year | n | EV | sum |
|---|---|---|---|
| 2020 | 51 | +2.88 | +147.0 |
| 2021 | 29 | +2.97 | +86.2 |
| 2022 | 47 | +5.34 | +251.0 |
| 2023 | 14 | +0.38 | +5.2 |
| 2024 | 43 | +6.47 | +278.2 |
| 2025 | 38 | +5.38 | +204.2 |
| **2026** | **35** | **−16.03** | **−561.0** |

2024 alone is 68% of net; **2026 destroys more than the four best years
combined**. Quarters ≥5 trades: 10 of 22 positive. Half-year segments:
57% positive (gate needs 70%). Weekday EV swings −3.02 (Fri) to +12.52
(Thu). Opening-volatility split: low-range +4.09 vs high-range −0.95 —
the effect is *absent* exactly where opening momentum should be
strongest.

## Gate table
PASS: G01 (257 events), G02 (257 days), G03, G12 retention, G13,
G17 influence, G20 causal, G21 repro.
**FAIL: G04 base PF 1.201, G05 stressed PF 1.113, G06 base EVR +0.068,
G07 stressed EVR +0.048, G08 CI includes 0, G09 perm p 0.589,
G10 BH q 0.589, G11 familywise 0.589 > 0.0166667, G15 segments 57%,
G16 domination (2024 = 68% of net), G18 placebo, G19 destruction,
Gprofile (53.3%/0.98 clears no row; margin +2.7 < 5).**

## Frozen consequences
- `ODMC_V1_FROZEN_CANDIDATE.json` = **[]**.
- **30-second arm: NOT REACHED — 1-MINUTE PARENT FAILED; NO SUB-MINUTE
  RESCUE.** No new 30s strategy was run. The prior 30s observation
  (n = 28) remains what it was: `SUB-MINUTE TEMPORAL DURABILITY:
  INSUFFICIENT DATA`.
- Parameter stability, durability, walk-forward, Monte Carlo, execution
  stress, ruin, DSR/PBO/SPA: **NOT REACHED — PRELIMINARY FAILURE.**
- ODMC-V1 is dead exactly as frozen: no rescue, inversion, revision,
  retest, fade fallback, or block substitution.
- **The three-arm pre-ranked family is now CLOSED.** No fourth fallback
  arm is authorized.
- Buffer 2026-08-18→31 and all partitions from 2026-09-01 untouched.
