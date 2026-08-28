# MTF-V1 — FINDINGS

**Verdict: 0 of 5 confirmatory cells pass. 0 of 17 map cells survive BH.
The timeframe axis is now formally mapped and closed for price-only
signals: no exploitable structure at 5m, 15m, 30m, 60m, 240m, or daily
scale.** Freeze commit `70ba8de` (before outcomes); 23/23 engine tests;
seeds 20260830–34; DEV 2019-07-04→2026-08-17 (exposed; exploratory
ceiling). THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

## 1. B1 — the confirmed V-turn does NOT scale (the scientific headline)

| T | n events | Δturn (bp) | CI | p | E[ta\|V] in points |
|---|---:|---:|---|---:|---:|
| 1m (holdout, prior) | 848,395 | **+0.031** | [+0.015,+0.048] | **0.00005** | ~+0.075 |
| 5m | 462,564 | +0.027 | [−0.028,+0.081] | 0.330 | −0.011 |
| 15m | 152,030 | +0.039 | [−0.118,+0.197] | 0.627 | +0.248 |
| 30m | 72,515 | −0.051 | [−0.378,+0.278] | 0.779 | +0.031 |
| 60m | 32,551 | +0.142 | [−0.559,+0.828] | 0.671 | +0.270 |

The one anomaly this programme ever confirmed on an untouched holdout is
**scale-specific microstructure**: the V-turn's extra follow-through
exists at 1 minute and is statistically gone by 5 minutes. In bp the
point estimates barely grow with scale while the noise grows ~√T, so
even the best cell (60m, +0.27 pt/event) is both insignificant and below
the 0.87 pt cost. This coheres with the run-hazard map ("whatever
persistence exists is spent within two minutes"): the effect is
order-flow mechanics at the minute scale, not a fractal behavioral
pattern. **The 1m anomaly remains confirmed and remains untradeable.**

## 2. B2 — the reversion clock is not harvestable at extremes

Primary (fade |z|≥causal q90 toward VWAP, exit VWAP/212m/EOD, stop 2×):
n=1,246 over 818 days — **stressed −3.65 pt/trade**, PF 0.89, negative
in 7 of 8 years, permutation p 0.843. All four frozen neighbors
(q85/q95, 106m/318m) negative.

The mechanism autopsy is the valuable part: only **28%** of extension
events touched VWAP within 212 min, and **44% were still open at
session end** (EOD 550/1,246). The unconditional OU half-life of 106
minutes does **not** apply conditional on a large extension — extremes
are exactly the trending states where VWAP itself moves away and the
spread process decorrelates from its average behavior. The
"reversion clock" lead from ANOMALY-SCAN is hereby resolved: the clock
is real on average, **state-dependent at the tails, and not a trade.**

## 3. Module A — the multi-scale map (0/17 after BH)

- ACF: 15m lag-1 = +0.0128 [+0.0004,+0.0251] raw-significant, dies
  under BH; every other T/lag cell (5m/30m/60m/240m) includes zero.
- Daily momentum spectrum k∈{1..20}: k=1 shows a mean-reversion tilt
  (−5.4 bp, CI [−11.3, +0.02]) that just misses; nothing else close.
- Cross-scale alignment (15m×240m → next 60m): +0.22 bp, p 0.54 — noise.

NQ is martingale-flat at every bar scale from 5 minutes to 4 hours and
at 1–20 day horizons, to the resolution 7.1 years of data affords.

## 4. Disposition

- MTF-B1 scale cells (5/15/30/60m) → `DEAD_FROZEN`, new fingerprint
  class `ORDINAL_PATH_SHAPE` (the 1m parent stays what it was:
  holdout-confirmed, descriptive, sub-cost — not resurrectable as a
  trade without new information).
- MTF-B2 (+ neighbors) → `DEAD_FROZEN` under `PRICE_MEANREV_INTRADAY`
  (the dual-reading disclosure in the protocol stands; under either
  reading it is now dead on the merits as well).
- Module A map → `DESCRIPTIVE_ONLY_SPENT`.

## 5. What this closes

With this run, the exposed-price-history search space is closed on the
**timeframe axis** as well as the mechanism axis: 1m (600+ tests), 5m,
15m, 30m, 60m, 240m, daily and multi-day have all been formally tested.
The remaining sources of a second edge are unchanged and are not in this
dataset: forward validation of OFH13/OFH14 (opens 2026-09-01), and the
message-level capture programme (MLES-V1, awaiting recorder attachment).
