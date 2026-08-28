# RMA-V1 — REALIZED MOMENT ASYMMETRY — PROTOCOL FREEZE

Frozen and committed **before any outcome is computed**.
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.

## 0. Novelty and scope discipline

Verified against the 84-row registry: no prior hypothesis in ~720 tests
has ever used **variance composition** — the split of realized variance
into downside/upside semivariance, or realized skewness of intraday
returns — as a conditioning state. All spent classes use first-moment
(direction/path) or total second-moment (size/vol) information. New
class `REALIZED_MOMENT_ASYMMETRY` (tokens: semivariance_composition,
realized_skew, variance_asymmetry_state; granularity state). Screen
decision recorded at freeze.

Deliberately excluded: everything already found or dead — and the
protected `DAY_TYPE_TAXONOMY` class (no streak/day-type variants at any
timeframe while the STREAK3DN prospective runs). The mechanism here is
intraday variance-composition reversion — informationally distinct from
the daily close-sequence object (uses magnitudes of all 1m returns, not
the sign path of daily closes; evaluated intraday at 30m cadence).

Frequency target (user directive): evaluation at every completed 30m
RTH boundary → ~8/day; decile conditioning + 60m non-overlap ≈ 4–8
signals/week.

## 1. Data

Canonical 1m grid, tradedays ≤ 2026-08-17 (exposed → exploratory
ceiling). Buffer/VALIDATION/OOS/LOCKBOX untouched.

## 2. Features (exact, causal)

At evaluation stamp `m ∈ {631, 661, 691, 721, 751, 781, 811, 841, 871}`
(each requires ≥ 150 of the trailing 180 RTH 1m returns of the same day
present; returns from contiguous minutes only):

- `RSV_m` = Σ r² over r<0 / Σ r² over all r  (downside variance share;
  0.5 = symmetric).
- `SKW_m` = standardized third moment of the window's 1m returns.

Thresholds are causal: the conditioning pool is the prior **250 days'**
feature values at all evaluation stamps (≥ 1,000 pool values required;
type-7 deciles). *TC1 correction, committed before any outcome: the
original 60-day/≥1,000 pairing was mutually infeasible (~6 evals/day);
the statistical floor is kept, the lookback extended. No outcome existed
when this was corrected — the run crashed at the first cell.*

## 3. Confirmatory cells (4, frozen directions)

One coherent mechanism — **variance-composition reversion**: variance
carried asymmetrically by one side marks forced/impatient flow on that
side, which exhausts; price drifts against the side that carried the
variance over the next hour.

| cell | condition | direction (next 60m) |
|---|---|---|
| C1 | RSV ≥ causal q90 (down-moves carried the variance) | **LONG** |
| C2 | RSV ≤ causal q10 (up-moves carried it) | **SHORT** |
| C3 | SKW ≤ causal q10 (big down-jumps) | **LONG** |
| C4 | SKW ≥ causal q90 (big up-jumps) | **SHORT** |

Non-overlap: after an event, next eligible stamp ≥ 60 min later; one
position at a time across all cells (first trigger wins, logged).

## 4. Frozen translation and management

Enter at the next 1m bar open after the evaluation stamp. Stop =
3 × ATR20(1m) at entry (race bar-by-bar, stop-first ambiguity, gap-
through at worse). Exit at the open of the bar 60 minutes after entry
(first later bar if missing; day-last close if none). Costs 0.87 base /
1.305 stressed, MNQ $2/pt, one contract. R = stop distance.

## 5. Statistics and gates (house standard)

Per cell: day-clustered bootstrap B=10,000 (seed 20260910) on stressed
mean; day-blocked sign-flip permutation P=10,000 (seed 20260911); BH
across the 4 cells (q ≤ 0.05). Gates: n≥200 · days≥60 · positive
base+stressed · PF 1.30/1.15 · EV +0.10R/+0.05R · CI LB>0 · p≤0.05 ·
q≤0.05 · ≥6/8 years positive · no >50% domination · survives best-day
and top-1% removal · +1-bar delay positive · frozen neighbors majority
positive (q85/q95 thresholds; 45m/90m exits — diagnostics only) ·
trade-quality profile table reported. **Monte Carlo (100,000 day-block
bootstrap paths, seed 20260912) runs ONLY for a cell passing every
preliminary gate — reported percentiles of terminal P&L, max drawdown,
losing streak, negative-path probability. MC can never rescue a
failure.**

Secondary descriptive module (ledgered, never promotable): the
extreme-time map — distribution of session high/low times, P(extreme
set before 10:30), split by overnight sign. 6 cells, own BH.

Full battery runs to completion; nothing added, merged or re-thresholded
after outcomes; every cell registered at close-out.
