# ODMC_V1_PROTOCOL_FREEZE.md — version 1.0

Frozen 2026-08-27 UTC **before any ODMC-V1 trade outcome was generated,
opened, or summarized**. Twin: `ODMC_V1_CONFIG.json`. Provenance:
`ODMC_V1_DATA_AND_PROVENANCE_AUDIT.md` (Wave 4 `S5open` q=10 cell
reproduced EXACT; 30s observation lineage reproduced). Cumulative
burden: `ODMC_V1_CUMULATIVE_EXPOSURE_LEDGER.csv`.

Interpretation is asymmetric. Failure **kills ODMC-V1 exactly as
frozen** — no rescue, inversion, revision, retest, fade fallback, or
block substitution. A pass is **exploratory only** and merely earns the
right to face genuinely future data. No result may be called guaranteed
to persist. **This is the third and final arm; the three-arm family
closes after this run regardless of outcome. THIS PROJECT DOES NOT
AUTHORIZE LIVE TRADING.**

## 1. The exact frozen primary strategy
- MNQ only; one contract; **max one ODMC position per day**; canonical
  causal 1m OHLCV only; every eligible DEV day through **2026-08-17**;
  ET with the proven exchange calendar/DST; completed bars only; strict
  contiguity across the whole block; no interpolation. **No day is
  excluded for being volatile, news/FOMC/CPI/NFP, holiday-adjacent,
  gapping, or historically losing** — only exchange-calendar
  unavailability of the exact block excludes a day.
- **Block [T0,T10] = [09:30, 09:40) ET** (stamps 571–580), the
  mechanically selected earliest complete block of the reproduced cell.
  **T5 = 09:35.** Split once, exactly in half.
- Mapping (frozen, tested): `P0` = **open of stamp 571** (09:30:00);
  signal half = completed stamps **571–575**; `P5` = **close of stamp
  575** (09:35:00); decision after 575 completes; **entry = open of
  stamp 576** (09:35:00 print); trade half = stamps **576–580**;
  **exit = open of stamp 581** (09:40:00 print). Eligibility requires
  stamps 571…581 present with `em[581] − em[571] = 10`.
- **Impulse `M_d = close(575) − open(571)`**, MNQ points. The block's
  starting traded open is the **only** anchor. No premarket, previous
  close, VWAP, overnight midpoint, or anchor comparison.
- **Magnitude gate:** `|M_d|` **strictly >** the type-7 empirical 90th
  percentile of `|M_i|` over the previous ≤252 eligible sessions
  excluding day d; ≥126 prior observations required else warm-up;
  **tie or `M_d = 0` ⇒ no trade**. No full-sample distribution, no
  per-side thresholds, no volatility-scaled or alternative percentile.
- **Direction: continuation of the first-half impulse** — long if
  `M_d > 0`, short if `M_d < 0`. Never flipped to reversal.
- **NO regime gate.** Explicitly excluded: field slope (the failed
  LPCC/CCHC construction), trailing VR, yearly/volatility/trend state,
  EMA, VWAP, gap, news.
- **Stop:** `1.5 ×` trailing 60-eligible-session median high−low range
  of the **trade half (stamps 576–580)**, ≥40 observations, rounded
  **up** to 0.25, minimum one tick; stop-market; **gap-through fills at
  the worse open**, touch fills at the stop, adverse slippage applied;
  never trailed, tightened, or widened. **No profit target**; five-minute
  max hold; no exposure beyond the block; no overnight.
- **Costs:** gross; slippage **1/2/3/4 ticks per side**; repository base
  **0.87 pt** (base-cost gates); repository RTH stressed 1.305 (reported);
  **BINDING STRESS = 4 ticks/side = 2.00 pt round turn** — the
  repository has **no opening-specific stress model**, so the frozen
  fallback applies and the most conservative opening treatment binds.
  Exact-dollar/commission gates **UNRESOLVED**.
- **Primary metric:** mean net points/trade under the **2.00 pt binding
  stress**; R = each trade's frozen stop distance. Two-sided inference;
  promotion requires the positive predicted sign. A significant negative
  result is failure, never permission to invert.

## 2. Cumulative multiplicity and the final familywise decision
Prior formal burden: **571 tests** (MGSD-V1 458, Wave 4 90, LPCC-V1 11,
CCHC-V1 12). ODMC adds 1 primary + 10 diagnostics. Pre-ranked three-arm
family: (1) LPCC-V1 **FAILED** (p 0.5160); (2) CCHC-V1 **FAILED**
(p 0.0243); (3) ODMC-V1 **this test**. To pass statistical promotion
ODMC must satisfy raw **p ≤ 0.05**, local **BH q ≤ 0.05** (family size
1; no variants manufactured), **and the reserved familywise
p ≤ 0.0166667**. A final BH across all three primary arms is reported
with LPCC and CCHC retained exactly as failed. No arm is removed, ODMC
is not reclassified, and **no fourth fallback arm is authorized**.

## 3. Inference
Day-clustered percentile bootstrap B = 10,000, seed 20260904 (one trade
per day ⇒ day = trade). Day-blocked permutation: **impulse-sign
permutation in 5-day blocks**, 10,000 iterations, same seed; two-sided
`p = (1+#{|perm| ≥ |obs|})/(N+1)`.

## 4. Binding gates (MGSD-V1, unweakened)
(1) ≥100 effective events; (2) ≥40 unique days; (3) ≥30 per claimed
binding subgroup; (4) base PF ≥1.30; (5) stressed PF ≥1.15; (6) base EV
≥+0.10R; (7) stressed EV ≥+0.05R; (8) day-clustered 95% lower bound >0;
(9) permutation p ≤0.05; (10) BH q ≤0.05; (11) **familywise
p ≤0.0166667**; (12) ≥50% effect retention after simpler controls,
operationalized before results as `EV(primary) − EV(D9 unconditional
opening-drift baseline, direction-matched) ≥ 0.5·EV(primary)` with
`EV(primary) > 0`, **and** `EV(primary) − EV(D7 matched non-event
control) ≥ 0.5·EV(primary)`; (13) no matched/residual sign reversal;
(14) same positive direction across frozen neighbors (§6, if reached);
(15) positive sign in ≥70% of eligible half-year segments (≥5 trades);
(16) no domination by one trade/day/week/month/quarter/year/direction/
volatility regime (>50% of net); (17) survives removal of the most
influential event, best trade, best day, best month, best year;
(18) required-component survival + logical-placebo failure; (19)
material weakening under signal destruction; (20) causal executable
fills; (21) no integrity failure + deterministic reproduction. Plus one
stressed-cost profile row (38/2.00, 45/1.50, 55/1.00, 65/0.70) using
realized avg-net-win ÷ avg-net-loss, with ≥5-point break-even margin.
**Sample floors are not reduced if the top-decile gate yields <100
events. Costs are not lowered because the hold is short.**

## 5. Predeclared diagnostics (never candidates, never rule modifiers)
D1 no-magnitude-gate ablation (all nonzero impulses); D2 below-threshold
control (|M| ≤ threshold, reported separately, never promoted);
D3 direction-reversal placebo; D4 impulse-sign destruction in 5-day
blocks (10,000, seed 20260905, magnitudes and dates preserved);
D5 random-day pairing (event-day impulse × another eligible day's
second half, within calendar year, block-aware, seed 20260906);
D6 date-shift of the qualifying event series −20/−10/+10/+20 eligible
sessions, no wrap (**positive shifts are non-tradable falsifications**);
D7 matched non-event control (calendar half-year × opening-gap-magnitude
tercile × first-half-range tercile); D8 adjacent-block placebo (identical
5/5 construction on the immediately following block, stamps 581–590,
time-of-day specificity only); D9 unconditional opening-drift baseline
(constant long and constant short through stamps 576–580 on all eligible
days); D10 residualization of the aligned second-half return on causal
first-half range, opening gap, lagged volatility, weekday, and year
indicators (controls fixed in advance, never selected by significance).

## 6. Conditional stages
The **restricted 30-second arm (§9 of the task)** runs **only** if the
1-minute primary passes every preliminary gate; otherwise it is marked
`NOT REACHED — 1-MINUTE PARENT FAILED; NO SUB-MINUTE RESCUE.` and no
new 30s strategy is run. If reached it may only describe execution
refinement on overlapping genuine dates, cannot alter parent events, and
is labelled `SUB-MINUTE TEMPORAL DURABILITY: INSUFFICIENT DATA`
regardless of result. The parameter-stability surface (85/90/95
percentile; 4-6 / **5-5** / 6-4 split; 1.0/1.5/2.0 stop; 3/5/7 hold;
block start ∓1 minute) and the full MGSD institutional program run
**only after a full preliminary pass**; otherwise both are
`NOT REACHED — PRELIMINARY FAILURE` with no weaker substitute.

## 7. Stopping rule
One primary run. No opening-strategy search, no fallback, no rescue.
**The three-arm family closes after this run.** The buffer 2026-08-18→31
and all partitions from 2026-09-01 remain untouched.
