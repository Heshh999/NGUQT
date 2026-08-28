# RMA-V1 — REALIZED MOMENT ASYMMETRY — FINDINGS

Protocol frozen at 7407f12 before any outcome. Two pre-outcome
infrastructure corrections (TC1 pool feasibility, 17aa5c7; q7 helper
reference, 5b38c87) — both crashes before any statistic existed,
documented and committed before rerun. Confirmatory output verified
byte-identical across the reruns.

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

## Verdict

**0 / 4 confirmatory cells pass. Variance-composition reversion does
not exist on MNQ at the 60-minute horizon.** Monte Carlo was not run:
the protocol states "Monte Carlo … runs ONLY for a cell passing every
preliminary gate — MC can never rescue a failure," and no cell passed
any of the profitability gates.

Scope of evidence: 10,736 feature evaluations over 1,831 DEV days
(2019-07-04 → 2026-08-17), ~2,500 executed simulated trades across the
four cells — a genuinely high-frequency test (4–8 signals/week per
cell), exactly the frequency band the directive asked for.

## Confirmatory results (stressed 1.305 pt costs, next 60m)

| cell | condition → direction | n | stressed/trade | perm p | BH q |
|---|---|---|---|---|---|
| C1 | RSV ≥ q90 → LONG | 626 | −3.086 pt | 0.8230 | 0.8786 |
| C2 | RSV ≤ q10 → SHORT | 646 | −2.015 pt | 0.6448 | 0.8786 |
| C3 | SKW ≤ q10 → LONG | 585 | **+0.551 pt** | 0.1706 | 0.6823 |
| C4 | SKW ≥ q90 → SHORT | 645 | −3.934 pt | 0.8786 | 0.8786 |

Three of four cells are negative even **gross** (before any costs).
The lone positive, C3 (buy after a window dominated by large down-
jumps), is honestly described as: positive but insignificant, and
regime-dominated. Its year decomposition is 2020 +0.71, 2021 +0.16,
**2022 +10.11**, 2023 −1.67, 2024 +0.21, 2025 +0.23, **2026 −9.07**:
one bear-market year supplies essentially all the profit and the
current year gives most of it back. CI [−3.24, +4.59] straddles zero
widely; p 0.17 is nowhere near the 0.05 gate even before BH. PF 1.03
stressed, EV −0.03 R — fails PF, EV, CI, p, q, and domination gates
simultaneously.

Diagnostics are consistent with a null: every neighbor threshold
(q85/q95) is negative for C1/C4; +1-bar delay leaves C3 at +0.09
(signal has no persistence); C3's exit ladder (+0.41 at 45m, +0.55 at
60m, +0.98 at 90m) is the drift signature of holding longer in a
long-biased instrument, not a reversion clock.

## Mechanism autopsy

The hypothesis was that variance carried asymmetrically by one side
(downside semivariance share, or large signed jumps) marks forced flow
that exhausts. The data say the opposite or nothing:

- **RSV cells (C1/C2) are backwards-or-dead in both directions.**
  Down-side-dominated variance does not mark a low (C1 long loses
  −3.1), and up-side-dominated variance does not mark a top (C2 short
  loses −2.0). Whatever information the semivariance split carries is
  worth less than one spread.
- **Up-jump fading (C4) is the worst cell** (−3.9 stressed, gross
  −2.6): fighting upside jumps in an uptrending index is negative
  before costs. This mirrors every prior fade-the-up-move failure.
- **Down-jump fading (C3) is the only economically sane residue** — it
  aligns with the long drift and with the known 1m V-turn direction —
  but at 30m-cadence/60m-horizon scale it is indistinguishable from
  noise plus 2022.

This was the first use of second/third-moment *composition* (rather
than total variance) as a conditioning state in ~720 registered tests.
The class is now spent: intraday moment-asymmetry states at this
granularity are informationally empty after costs.

## Descriptive extreme-time map (ledgered, never promotable)

- P(session high set in first RTH hour) = 0.371; P(session low in
  first hour) = **0.450**; P(high in last hour) = 0.286; P(low in last
  hour) = 0.188.
- Conditional on overnight gap: gap-up days put the low in the first
  hour 44.2% of the time; gap-down days put the high in the first hour
  35.8% of the time.

Reading: extremes cluster massively at the open (a uniform clock would
give ~17% per hour for the first hour vs the observed 37–45%), and the
**low** is the extreme most often set early — consistent with the
instrument's long drift (buy-the-open-dip resolves upward more often
than not). This is a map, not a strategy: it conditions on nothing
tradeable beyond time-of-day (a spent class, CALENDAR_TOD), and no
directional cell was tested or may be derived from it retroactively.

## Registry actions

- `RMA-MOMENT-CELLS` → DEAD_FROZEN, new fingerprint class
  `REALIZED_MOMENT_ASYMMETRY` (added to CLASS_DEF).
- `RMA-EXTREME-MAP` → DESCRIPTIVE_ONLY_SPENT under the existing
  `PRICE_ONLY_MAP` class.
- Fingerprints regenerated; closure tests re-run.

## Reproduction

`python3 analysis/rma/rma_run.py` (77–97 s). Seeds 20260910/20260911
frozen in protocol; output `RMA_RUN_OUTPUT.txt`; raw statistics
`RMA_V1_RAW.json`. Confirmatory block reproduced byte-identically on
consecutive runs.
