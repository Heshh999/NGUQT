# CCHC_V1_PROTOCOL_FREEZE.md — version 1.0

Frozen 2026-08-27 UTC **before any CCHC-V1 trade outcome was generated,
opened, or summarized**. Twin: `CCHC_V1_CONFIG.json`. Provenance:
`CCHC_V1_DATA_AND_PROVENANCE_AUDIT.md` (Wave 4 S9close q=30 cell
reproduced EXACT). Cumulative burden:
`CCHC_V1_CUMULATIVE_EXPOSURE_LEDGER.csv`.

Interpretation is asymmetric. A historical failure **kills CCHC-V1
exactly as frozen** — no rescue, revision, inversion, retest, fade
fallback, or window substitution. A historical pass is **exploratory
only** and merely earns the right to face genuinely future data; it is
not validation, proof, or permission to trade. No result may be called
guaranteed to persist. **THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**

## 1. The exact frozen primary strategy
- MNQ only; one contract; max one open position; causal 1m OHLCV only;
  every eligible DEV day through **2026-08-17**; ET with the proven
  exchange calendar/DST; completed bars only; no interpolation.
- **Interval [T0,T1] = (15:30, 16:00] ET**, mechanically selected as the
  chronologically final complete 30-minute interval of the reproduced
  Wave 4 `S9close` q=30 cell (that cell contains exactly one interval
  per day; no interval returns were compared).
- **Decision bar = close stamp 930. Entry = open of stamp 931. Exit =
  open of stamp 961** (30 elapsed minutes; a genuine traded price, not
  an auction/settlement fill).
- Eligibility: stamps 930…961 all present and `em[961]−em[930] = 31`.
  **Early-close days fail automatically and are excluded; the window is
  never shifted earlier.**
- **Anchor (single, frozen, not compared): current RTH open = open of
  stamp 571 (09:30:00 print).** `D_d = close(stamp930) − RTHopen_d`.
- **Displacement gate:** `|D_d|` **strictly >** the type-7 empirical
  90th percentile of `|D_i|` over the previous ≤252 eligible sessions
  excluding day d; ≥126 prior observations required else warm-up; tie =
  no trade. No full-sample, per-side, volatility-selected, or optimized
  threshold.
- **Regime gate:** OLS with intercept `F_i = α + β·D_i` over exactly the
  previous 126 eligible sessions (all `F_i` completed no later than the
  prior eligible session); trade only if **β_d > 0**. No t-stat/p-value
  filter, no winsorizing, weighting, regularization, transformation, or
  lookback change; no substitute state variable. Retained because it was
  part of the pre-CCHC conditional-displacement theory; **LPCC's failure
  is recorded but must not tune this gate**.
- **Direction:** continuation — long if `D_d > 0`, short if `D_d < 0`,
  no trade if `D_d = 0`. Never switched to fade.
- **Stop:** `1.5 ×` trailing 60-eligible-session median of the interval
  (stamps 931–960) high−low range, ≥40 observations, rounded **up** to
  0.25, minimum one tick; stop-market; **gap-through fills at the worse
  open**, touch fills at the stop, adverse slippage applied; never
  trailed or widened. No profit target; 30-minute max hold; no carry.
- **Costs:** gross; slippage 1/2/3 ticks per side (2 = provisional base,
  3 = stress); repository base **0.87 pt**; repository **RTH stressed
  1.305 pt — BINDING** (session-appropriate, pre-existing, not chosen to
  pass); non-RTH **1.740 pt reported as a supplementary conservatism
  check** because the exit prints at 16:00. Exact-dollar/final cost gate
  **UNRESOLVED**.
- **Primary metric:** mean net points/trade under the binding stressed
  model; R = each trade's frozen stop distance. Two-sided inference;
  promotion requires the positive predicted sign. A significant negative
  result is failure, never permission to invert.

## 2. Multiplicity (cumulative, not first-idea)
Prior formal burden: MGSD-V1 458, Wave 4 90, LPCC-V1 11 → **559 formal
tests before CCHC**. CCHC adds 1 primary + 11 diagnostics.
Pre-ranked three-arm window family: (1) late premarket = LPCC-V1
**FAILED**; (2) closing half-hour = CCHC-V1 **this test**; (3) opening
drive **RESERVED/UNOPENED**. To pass, the primary must satisfy raw
**p ≤ 0.05**, local **BH q ≤ 0.05** (family size 1; no variants
manufactured), **and the fixed three-arm familywise p ≤ 0.0166667**,
which reserves equal error budget for the unopened arm. LPCC is never
dropped from the family and CCHC is never reclassified as a fresh first
test.

## 3. Inference
Day-clustered percentile bootstrap B = 10,000, seed 20260901 (one trade
per day ⇒ day = trade). Day-blocked permutation: direction-sign flips in
5-trade blocks over the executed set, 10,000 iterations, same seed;
two-sided `p = (1+#{|perm| ≥ |obs|})/(N+1)`.

## 4. Binding gates (MGSD-V1 definitions, unweakened)
(1) ≥100 effective events; (2) ≥40 unique days; (3) ≥30 per claimed
binding subgroup; (4) base PF ≥1.30; (5) stressed PF ≥1.15; (6) base EV
≥+0.10R; (7) stressed EV ≥+0.05R; (8) day-clustered 95% lower bound >0;
(9) permutation p ≤0.05; (10) BH q ≤0.05; (11) **three-arm familywise
p ≤0.0166667**; (12) ≥50% retention vs simpler controls, operationalized
before results as `EV(primary) − EV(component-free baseline) ≥
0.5·EV(primary)` with `EV(primary) > 0`; (13) no matched/residual sign
reversal; (14) same positive direction across frozen nearby definitions
(§6, only if reached); (15) positive sign in ≥70% of eligible half-year
segments (≥5 trades); (16) no domination by one trade/day/week/month/
quarter/year/direction/vol-regime; (17) survives removal of the most
influential event, best trade, best day, best month, best year;
(18) required-component survival + logical-placebo failure; (19)
material weakening under signal destruction; (20) causal executable
fills; (21) no integrity failure + deterministic reproduction. Plus one
stressed-cost profile row (38/2.00, 45/1.50, 55/1.00, 65/0.70) using
realized avg-net-win ÷ avg-net-loss, with ≥5-point break-even margin.
**Insufficient sample is a valid failure. No floor is reduced.**

## 5. Predeclared diagnostics (never candidates, never rule modifiers)
D1 no-regime ablation; D2 no-displacement ablation; D3 component-free
unconditional continuation baseline; D4 direction-reversal placebo;
D5 regime-label permutation in 5-day blocks (10,000, seed 20260902);
D6 regime date-shift −20/−10/+10/+20 eligible sessions, no wrap
(positive shifts are **non-tradable falsifications**); D7 matched
random-day control (half-year × lagged-|D| tercile); D8 randomized-
anchor placebo (RTH open resampled within calendar year, seed 20260903);
**D9 time-of-day placebo** — the identical frozen signal applied to the
predeclared adjacent non-overlapping horizon **entry open stamp 961 →
exit open stamp 991** (16:00→16:30 ET, causal, no maintenance crossing);
destruction/context only, never a fallback strategy.

## 6. Conditional stages
Parameter-stability surface (85/90/95 percentile; 63/126/252 lookback;
1.0/1.5/2.0 stop; 20/30/40 hold; ±5-minute entry boundary) and the full
MGSD institutional program (durability, walk-forward, ≥100k Monte Carlo
paths, execution stress, ruin, tail risk, DSR/PSR/PBO/SPA) run **only
after a full preliminary pass**. Otherwise both are marked
`NOT REACHED — PRELIMINARY FAILURE`; no weaker substitute is run.

## 7. Stopping rule
One primary run. No strategy search, no fallback, no rescue. The
opening-drive arm stays unopened. The buffer 2026-08-18→31 and all
partitions from 2026-09-01 remain untouched.
