# Sub-Minute Execution Study: OFH6 + Liquidity Sweep + Reclaim

**Date:** 2026-08-21
**Script:** `analysis/v41/ofsub_run.py` (all parameters declared in its
header before the first run). Full console output: scratchpad
`ofsub_out.txt`.
**Scope:** execution timing ONLY. The 1m ordinary-reclaim exploratory
result (+18.3 pt, ratio 1.407) is already-seen; nothing here confirms
that edge, and this study's own DEV/IR split (below) actively cautions
against it. INTERNAL HISTORICAL RESEARCH. No live trading is authorized.

---

## 1. Sub-minute data audit

| timeframe | exists | coverage | notes |
|---|---|---|---|
| 30s | **YES** | 2025-09-01 .. 2026-05-29; within the OF overlap 2025-11..2026-05: **147 days, complete 182-slot grid every day**, 09:30:00-11:00:30 ET, close-stamped | V3 phase-2 capture (`ph2/V3_30s_*.csv`). OHLCV only - **no bid/ask** at 30s. Zero duplicate-timestamp conflicts. |
| 15s | NO | - | never captured |
| 10s | NO | - | never captured |
| 5s | NO | - | never captured |
| tick | NO | - | never captured |

Integrity checks performed: 30s->1m aggregation exact on 1,800/1,800
tested minutes (proves close-stamping); price basis identical to the
order-flow capture on 3,726/3,726 matched 1m closes (zero offset - same
back-adjusted continuous, levels transfer exactly). Timezone ET, same
session template. Missing relative to the OF window: **2026-06, 07, 08**
and everything outside 09:30-11:00 ET. No sub-minute bars were
fabricated, interpolated, or inferred from 1m OHLC anywhere.

## 2. Frozen parent event

Frozen-OFH6 context active (life 30 min; activating signal strictly
before the sweep; no opposite signal intervening) + first-breach sweep of
the live SW3 / SW15 / PDL level - identical machinery to `ofht_spec`.
Sweep moment = close of the first breaching **30s** bar (earliest causal
observation, located inside the 1m breach bar). Parent eligible only when
[sweep, sweep+5min] lies fully inside 30s coverage - a time/data
criterion, never an outcome criterion.

## 3. Causality audit

The parent freezes at the 30s breach observation. Each arm then searches
its own completed bars independently: the 1m arm sees only completed 1m
closes, the 30s arm only completed 30s closes. No arm conditions on the
other arm's outcome, and no entry uses any future bar. The 0.5-ATR
adverse-close void (preserved from the existing 1m definition) is
evaluated on 1m closes for both arms; a 30s entry stands only if it
completes before the void moment. Forward geometry runs on the hybrid
path (30s bars to 11:00:30, then 1m bars), the SAME hierarchy for both
arms; races resolving both levels inside one bar are AMBIGUOUS and
reported, never resolved by assumption.

## 4-5. Parents and trigger rates

**67 eligible parents** (27 long, 40 short; of 216 context sweeps on
covered days - the rest fell outside the 09:30-11:00 window or the
coverage rule). Triggers: **both 48, 30s-only 5, 1m-only 0, neither 14**.
The 30s arm never misses a 1m confirmation (trigger rate 79% vs 72%) -
its extra 5 triggers were reclaims the 1m close never confirmed.

## 6-8. Entry timing, price, and risk

| | 1m arm | 30s arm |
|---|---|---|
| latency from sweep (med / mean) | 30s / 44s | **0s / 19s** |
| risk to sweep-extreme stop, median | 18.00 pt (72 t, 0.70 ATR) | **14.50 pt (58 t, 0.65 ATR)** |
| risk, mean | 18.97 | 16.59 |

Paired (n=48, same parent): entry-price improvement mean **+1.54 pt**,
median 0.00, p75 +2.75, p90 +7.50; 58% enter earlier, 21% at a worse
price; day-clustered bootstrap **95% CI [+0.17, +2.96] - excludes zero**.
Paired risk delta mean -2.03 pt, median 0.00. The medians are zero
because in roughly half the pairs the 30s trigger IS the full-minute
bar; the improvement lives entirely in the half where the half-bar
reclaims first.

## 9-10. Path geometry from each arm's actual entry

| horizon | 1m ratio | 30s ratio |
|---|---|---|
| 5m | 0.849 | 0.929 |
| 15m | 1.264 | 1.257 |
| 30m | 1.333 | 1.374 |
| 60m | 1.610 | 1.599 |

ATR favourable-first (1.0 ATR): 43.8% vs 47.2% - both below 50%, within
noise of each other at this n. R-first with the sweep stop: 1R 44.4% vs
45.8%; 1.5R 26.1% vs **35.3%**; 2R 23.9% vs **32.7%** - the multi-R
gains are mechanical consequences of the smaller R, not of a better
path. **Absolute geometry is unchanged by execution timeframe.**

## 11. False early reclaims

Re-break of the sweep extreme within 30s/1m/2m/3m/5m:
1m arm 25/38/46/52/65%; 30s arm 26/36/47/57/66%. **Identical.** The
earlier trigger does NOT buy price at the cost of confirmation. (Both
arms' 65% five-minute re-break rate is why the sweep-extreme stop fails
below.)

## 12. Paired outcome deltas

MAE60 mean -1.41 (med 0.00); MFE60 mean +1.27 (med 0.00); net60 mean
+0.95, **95% CI [-2.96, +4.65] - includes zero**. Execution timeframe
does not change the trade's outcome.

## 13-15. DEV / IR, months, sides

Both arms: DEV net60 ~+27..+35, IR **~-6**. The parent thesis itself
did not replicate inside this morning-window subset - a further caution
against reading the already-seen +18.3 exploratory number as an edge.
Months: positive 2025-11..2026-03, negative 2026-04/05, both arms alike.
30s-only extra triggers: 4 long / 1 short. Concentration (30s arm): top
2 trades = +460 of +807 total.

## 16. Cost sensitivity

Base 0.87 / +1 tick / +2 ticks shifts every mean by exactly the added
cost; the 30s-vs-1m comparison is unchanged. But note the paired price
gain (+1.54 mean) is about the size of 1.5 ticks - real-world slippage
on a faster trigger could consume most of it.

## 17. Stop family (after raw geometry, as required)

| stop | 1m arm | 30s arm |
|---|---|---|
| sweep-extreme | -0.59, win 17% | +0.00, win 15% |
| 1.0 ATR | +8.28, win 23% | +7.99, win 25% |
| 1.5 ATR | +15.44, win 40% | +12.35, win 38% |

The conceptually motivated sweep-extreme stop is destroyed by the 65%
five-minute re-break rate: the thesis "the sweep failed" does not stop
the market revisiting the extreme. Wider stops just re-expose the
symmetric path.

## 18. Fixed-R grid

**Not run.** Declared gate was geometry improvement; absolute geometry
did not improve, so a target grid would only re-measure the parent
drift.

## 19-20. Verdicts

| timeframe | verdict |
|---|---|
| 30s | **MODEST EXECUTION IMPROVEMENT** |
| 15s | **INSUFFICIENT DATA** |
| 10s | **INSUFFICIENT DATA** |
| 5s | **INSUFFICIENT DATA** |

**DID SUB-MINUTE EXECUTION CONVERT THE OFH6 + LIQUIDITY-SWEEP THESIS
INTO A MEANINGFULLY BETTER ENTRY THAN THE 1M RECLAIM?**

# NO

The 30s reclaim delivers a real but small execution gain - entry
+1.54 pt mean (CI excludes zero), median risk 18.0 -> 14.5 pt (-19%),
median 30 seconds earlier, five extra valid triggers, no loss of
confirmation quality. But it does not change what the trade IS: MFE/MAE,
favourable-first, false-reclaim rate and net expectancy are statistically
indistinguishable (paired net60 CI includes zero), the medians of every
paired delta are exactly zero, and the mean gain is roughly the size of
the extra slippage a faster trigger invites. If the parent thesis were
ever validated, the simplest timeframe capturing what improvement exists
is **30s** - and nothing in this data justifies going lower.

### What must be collected before the missing arms can ever run

1. 15s / 10s / 5s and tick (or Time&Sales) series for MNQ on the SAME
   back-adjusted continuous, exported alongside a 1m series in the same
   host so the price basis is provably identical (the existing
   `MnqTwoStrategies.cs` already declares Second-30/15/10/5 and Tick-1
   series - the collection path exists in the repo).
2. Extension of the 30s capture to 2026-06 onward and, ideally, beyond
   the 09:30-11:00 ET window.
3. Provider tick-history depth must be verified in NT8 (Tools ->
   Historical Data) before promising any backfill; if history does not
   reach back, sub-minute data can only accumulate forward - which also
   makes it prospective.
