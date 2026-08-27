# LPCC_V1_PROTOCOL_FREEZE.md

Frozen 2026-08-27 UTC **before any LPCC-V1 trade outcome was generated,
opened, or summarized**. Machine-readable twin: `LPCC_V1_CONFIG.json`.
Provenance: `LPCC_V1_DATA_AND_PROVENANCE_AUDIT.md` (Wave 4 VR30 cell
reproduced EXACT). Interpretation is asymmetric: historical failure
kills LPCC-V1 as frozen (no rescue, revision, inversion, or retest);
historical pass is exploratory only and merely permits future-data
testing. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

## The exact frozen primary strategy
- Instrument MNQ; one contract; one position max; causal 1m OHLCV only;
  DEV universe = all eligible days through 2026-08-17; ET with
  exchange-calendar sessions; completed bars only; no interpolation.
- Interval: T0=08:00, T1=08:30 ET (recovered first VR-cell window).
  Decision bar = completed 08:00-stamped bar. Entry = open of the
  08:01-stamped bar. Exit = open of the 08:31-stamped bar (30 elapsed
  minutes). One event per eligible day; no scanning; no re-entry.
- Eligibility (day d): stamps 08:00 through 08:31 all present and
  em-contiguous (32 consecutive stamps); previous completed RTH close
  exists on the proven session calendar.
- Anchor: previous completed RTH close only (no substitutes, no
  comparisons). Displacement D_d = close(08:00 bar, day d) − prevRTHclose.
- Displacement gate: |D_d| STRICTLY > lagged empirical 90th percentile
  of {|D_i|} over the previous 252 eligible days (exclusive of d);
  ≥126 prior eligible observations required else warm-up; quantile =
  numpy.quantile linear interpolation (type-7), documented; tie = no
  trade. No full-sample percentile; no per-side thresholds.
- Regime gate: OLS with intercept F_i = α + β·D_i over the previous 126
  eligible days exclusively (F_i = open(08:31,i) − open(08:01,i), raw
  window move, completed before d). Trade only if β_d > 0. No t-stat
  requirement, no winsorizing, no weighting, no alternative state
  variable.
- Direction: continuation — long if D_d > 0, short if D_d < 0, no trade
  if D_d = 0.
- Stop: 1.5 × trailing 60-eligible-session median of the exact-interval
  high–low range (≥40 obs required), rounded UP to the 0.25 tick, min 1
  tick; stop-market; gap-through fills at the worse bar open;
  touch fills at stop; adverse slippage per cost scenario; never
  trailed or widened. No target; 30-minute max hold; no overnight.
- Costs reported: gross; slippage 1/2/3 ticks per side (2/side =
  provisional slippage base, 3/side = slippage stress); repository
  frozen base 0.87 pt RT; repository frozen premarket stressed
  **1.740 pt RT — the binding stressed-cost model for all gates**
  (at least as conservative as MGSD premarket treatment). Exact-dollar
  cost gate UNRESOLVED (no authenticated commissions; none invented).
- Primary metric: mean net points/trade under the 1.740 stressed model;
  R = per-trade frozen stop distance. Two-sided inference; promotion
  requires the positive predicted sign.

## Inference (frozen)
- Day-clustered percentile bootstrap, B = 10,000, seed 20260829.
- Day-blocked permutation for the primary: direction-sign permutation in
  5-trading-day blocks over the executed-trade set, 10,000 iterations,
  seed 20260829; p = (1+#{|perm mean| ≥ |obs mean|})/(N+1) two-sided.
- BH family: ONE primary candidate (q = p); every other formal test is
  ledgered in `LPCC_V1_HYPOTHESIS_LEDGER.csv` as a diagnostic, never a
  candidate.

## Gates (MGSD-V1 definitions, unweakened)
(1) ≥100 effective events; (2) ≥40 unique days; (3) ≥30 per claimed
binding subgroup; (4) base PF ≥ 1.30; (5) stressed PF ≥ 1.15; (6) base
EV ≥ +0.10R; (7) stressed EV ≥ +0.05R; (8) day-clustered 95% lower
bound of stressed EV > 0; (9) permutation p ≤ 0.05; (10) BH q ≤ 0.05;
(11) ≥50% retention vs simpler controls — operationalized BEFORE
results as: stressed EV(primary) − stressed EV(component-free baseline)
≥ 0.5 × stressed EV(primary), AND primary ≥ each ablation arm is
reported; (12) no sign reversal in matched/residual constructions;
(13) neighbor agreement (§stability surface, only if reached); (14)
positive sign in ≥70% of eligible half-year segments (≥5 trades);
(15) no single trade/day/week/month/year/direction/vol-regime
domination (>50% of net profit with >2 periods); (16) survives removal
of most influential event, best trade, best day, best month, best year;
(17) ablation/placebo survival; (18) signal destruction materially
weakens; (19) causal executable fills; (20) no integrity failure;
(21) deterministic reproduction. Plus one §profile row (38/2.0, 45/1.5,
55/1.0, 65/0.7) at stressed cost, with ≥5-point break-even margin.
**Insufficient sample is a valid failure. No floor is reduced.**

## Predeclared diagnostics (never candidates)
D1 no-regime ablation; D2 no-displacement ablation; D3 component-free
unconditional continuation baseline; D4 direction-reversal placebo;
D5 regime-label permutation in 5-day blocks (10,000, seed 20260830);
D6 date-shift of the regime series by −20/−10/+10/+20 eligible sessions
(no wrap; positive shifts labeled non-tradable falsifications);
D7 random-day control matched on calendar half-year × lagged-|D|
tercile; D8 randomized-anchor placebo (prior close resampled within
calendar year, 5-day-block-aware, seed 20260831).

## Stability surface and institutional program
Run ONLY after a full preliminary pass, exactly as §8/§9 of the task
(85/90/95 percentile; 63/126/252 lookback; 1.0/1.5/2.0 stop; 20/30/40
hold; ±5-minute window start; then the unchanged MGSD robustness
program). If any binding preliminary gate fails: `NOT REACHED`.

## Stopping rule
One primary run. No parameter search. No fallback. A failure ends
LPCC-V1 permanently; the buffer 2026-08-18→31 and all future partitions
stay untouched.
