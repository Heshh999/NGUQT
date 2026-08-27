# CCHC-V1 — RESULTS

Protocol freeze commit **`5133c5114a236d29e6fff412325b6fddcf87d179`**.
Provenance: Wave 4 `S9close` q=30 cell reproduced **EXACT**. Tests
28/28 PASS. Raw output `CCHC_RUN_OUTPUT.txt`; trades
`CCHC_V1_TRADES.csv`; per-day snapshots `CCHC_V1_EVENT_AUDIT.csv`;
diagnostics ledger `CCHC_V1_HYPOTHESIS_LEDGER.csv`.

## HEADLINE
> **CCHC-V1 HISTORICAL FEASIBILITY FAILED; HYPOTHESIS KILLED.**
> First binding failure: **G01 — 98 effective independent events
> (< 100 floor)**. Also failed: **G11** three-arm familywise
> (p 0.0243 > 0.0166667) and **G16** period domination (2020 alone =
> 60.7% of net profit; 2020+2022 = 100.9%).
>
> This one looked good on the surface — and that is exactly why the
> frozen gates exist. The gross numbers are the most attractive in the
> programme; the structure underneath them is not a tradable edge.

## Primary economics (n = 98 trades / 98 unique days)
| scenario | EV pt | EV R | WR | PF | payoff |
|---|---|---|---|---|---|
| gross | +16.640 | +0.303 | 61.2% | 1.802 | 1.14 |
| slip 1 tick/side | +16.140 | +0.297 | 61.2% | 1.771 | 1.12 |
| slip 2/side (prov. base) | +15.640 | +0.291 | 61.2% | 1.740 | 1.10 |
| slip 3/side (stress) | +15.140 | +0.285 | 61.2% | 1.710 | 1.08 |
| repo base 0.87 | +15.770 | +0.293 | 61.2% | 1.748 | 1.11 |
| **repo RTH stressed 1.305 (BINDING)** | **+15.335** | **+0.288** | **61.2%** | **1.722** | **1.09** |
| non-RTH 1.740 (supplementary) | +14.900 | +0.282 | 61.2% | 1.696 | 1.07 |

Stressed CI95 **[+0.710, +30.766]** (barely clears zero); permutation
**p = 0.0243**; local BH q = 0.0243; **three-arm familywise: FAIL**.
Break-even WR 47.8% vs actual 61.2% (+13.4-point margin). Sharpe/trade
0.203, Sortino 0.373, maxDD −312.5 pt over 20 trades, longest losing
streak 4, largest loss −144.6, CVaR₅ −140.3, median MFE 47.6 /
median MAE 30.8. Long 45 (+17.6) / short 53 (+13.4); 15 stop-outs /
83 time exits. Exact-dollar cost gate remains UNRESOLVED.

## Why it fails — the trade distribution is the whole story
| year | eligible | warm | displacement-gate | regime β>0 | **trades** |
|---|---|---|---|---|---|
| 2019 | 121 | 0 | 0 | 0 | **0** |
| 2020 | 248 | 243 | 54 | 141 | **36** |
| 2021 | 251 | 251 | 24 | 2 | **0** |
| 2022 | 250 | 250 | 45 | 197 | **39** |
| 2023 | 248 | 248 | 12 | 84 | **2** |
| 2024 | 249 | 249 | 36 | 36 | **4** |
| 2025 | 246 | 246 | 29 | 185 | **17** |
| 2026 | 154 | 154 | 26 | 32 | **0** |

**76.5% of trades and 100.9% of net profit come from 2020 and 2022** —
the COVID crash and the 2022 bear market. Three of eight calendar years
produce **zero** trades; only 27 of ~85 DEV months trade at all. The
single best month (2020-03, 12 trades) carries so much weight that
removing it drops EV from +15.34 to +8.04, and removing 2020 drops it
to +9.52. The strategy is a high-volatility-regime artifact wearing a
conditional-continuation costume.

## Stability (reported without selecting favorable subgroups)
Quarters with ≥5 trades: 6 of 7 positive. Half-year segments ≥5 trades:
3 of 4 positive (75%, passes G15). Weekday EV ranges +59.0 (Mon, n 15)
to −0.6 (Fri, n 21). Volatility split: low-range days +24.2 (n 49) vs
high-range +6.5 (n 49). 2023 −18.2 (n 2), 2025 −4.4 (n 17) — the two
most recent years with meaningful samples are flat-to-negative.

## Gate table
PASS: G02 days, G03, G04 base PF 1.748, G05 stressed PF 1.722,
G06 base EVR +0.293, G07 stressed EVR +0.288, G08 CI>0, G09 perm ≤.05,
G10 BH q ≤.05, G12 retention, G13 no sign flip, G15 segments,
G17 influence, G18 placebo, G19 destruction, G20 causal, G21 repro,
Gprofile (61.2% / 1.09 clears the Balanced row 55%/1.00 with margin).
**FAIL: G01 (98 < 100), G11 (0.0243 > 0.0166667), G16 (2020 = 60.7%
of net).**

## Frozen consequences
- `CCHC_V1_FROZEN_CANDIDATE.json` = **[]** (empty).
- Parameter stability, five-year durability, walk-forward, Monte Carlo,
  execution stress, ruin, DSR/PBO/SPA: **NOT REACHED — PRELIMINARY
  FAILURE.** No rescue surface was run and no weaker substitute
  attempted.
- CCHC-V1 is dead exactly as frozen: no rescue, revision, inversion,
  retest, closing-fade fallback, threshold change, or window
  substitution. Sample insufficiency (98 vs 100) is a valid failure and
  the floor was not reduced.
- The Wave 4 `VR30 = 1.27` closing cell stands unchanged as descriptive
  structure; it is not a strategy result.
- The **opening-drive arm remains RESERVED and UNOPENED**; its error
  budget is intact (this is precisely why the 0.0166667 familywise
  threshold existed, and CCHC did not clear it).
- Buffer 2026-08-18→31 and all partitions from 2026-09-01 untouched.
