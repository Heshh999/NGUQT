# V5 PHASE 0 - AUDIT OF THE V3 1-MINUTE ASSET

Run 2026-08-20, BEFORE any V5 hypothesis was declared and before any
feature->outcome relationship was examined.

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

The asset (`run151629/`, 86 monthly files) was produced by the V3 engine, not by
the V4 engines. Nothing in it is trusted on the strength of its column names. Every
forward-looking column below was independently reconstructed from raw OHLC before
being accepted.

---

## COVERAGE

| | |
|---|---|
| Bars after de-duplication | 2,503,622 |
| Span | 2019-07-04 18:25 ET -> 2026-08-17 15:16 ET |
| Duplicate timestamps | 0 |
| Time ordering | strictly monotonic |
| Session days | ~310-313 per full year |

Source rows are ~2.01 per bar because the export repeats each bar once per nearby
reference level. De-duplication is on `eventId`.

### Gaps, classified once each

| Class | Count |
|---|---|
| Daily 18:00 ET reopen | 1,477 |
| 16:15-16:30 ET maintenance halt | 491 |
| Weekend | 391 |
| **Unexplained** | **312 (0.0125% of transitions)** |
| Quiet minutes (1 < gap < 5m) | 2,416 |

Median unexplained gap is 9 minutes; none exceeds one day. The largest are real
market events, not data loss: 2020-03-16 and 2020-03-18 are the COVID limit-halt
sessions, 2022-11-06 is the DST changeover, 2025-11-27 is the Thanksgiving early
close. Quiet minutes are counted separately because NinjaTrader prints no bar when
nothing trades - absence of a bar is not absence of data.

**COVERAGE: PASS.**

---

## FORWARD COLUMNS - RECONSTRUCTED, NOT ASSUMED

`net_K` was tested against three candidate definitions across 2.5M bars:

| Candidate | K=3 | K=20 | K=80 |
|---|---|---|---|
| **`close[t+K] - close[t]`** | **100.00%** | **100.00%** | **100.00%** |
| `close[t+K] - open[t+1]` | 27.55% | 27.55% | 27.55% |
| `close[t+K] - open[t]` | 4.68% | 4.68% | 4.68% |

An exact match at 100.00% on 2.5M rows carries a second result for free: **the bar
universe reconstructed here is identical to the engine's.** A single dropped or
extra bar anywhere in seven years would have destroyed the row-shift alignment and
collapsed that rate.

`mfeLong_K` / `maeLong_K` first reconstructed at 97.65-99.15%. The residual is
fully explained by a zero-clamp:

| | K=3 | K=20 | K=80 |
|---|---|---|---|
| Clamped reconstruction exact | **100.0000%** | **100.0000%** | **100.0000%** |
| Population where raw value < 0 | 2.354% | 0.847% | 0.397% |

The clamp population exactly equals the initial shortfall at every horizon.
Established definitions:

```
net_K      = close[t+K] - close[t]
mfeLong_K  = max(0, max(high[t+1..t+K]) - close[t])
maeLong_K  = max(0, close[t] - min(low[t+1..t+K]))
```

**Consequence for P2:** the zero-clamp is lossy in exactly the direction P2 cares
about. When price runs away and never trades back through the entry, MAE is
recorded as 0, which conflates "the stop was never threatened" with "we have no
measurement of how far away price stayed." **P2 will rebuild unclamped excursions
from raw OHLC rather than use these columns.**

### End-of-history truncation

`barsObserved` is 80 everywhere except the final 80 bars, where it decays
79, 78, 77 ... 1, 0 - exactly one bar at each value. The engine ran out of future
and recorded that fact rather than fabricating a forward window.

`isWarmup` is False on all 2,503,622 bars.

**NO-LOOKAHEAD (forward columns): PASS.**

---

## FEATURE COLUMNS - TWO ARE NOT USABLE

| Column | Reconstruction | Verdict |
|---|---|---|
| `ema9`, `ema20` | recursive EMA from trailing closes, 100.00% | causal, USE |
| `ema200` | 99.98% (residual is warmup) | causal, USE |
| `atr` | **`SMA(20)` of True Range, median abs err 0.0000, corr 1.00000** | causal, USE |
| `relVolume` | closest candidate `volume / trailing SMA20`, corr 0.875, NOT exact | **definition unknown - DO NOT USE** |
| `posInSessRange` | matches neither causal (48.5%) nor lookahead (23.1%) | **DO NOT USE** |

`posInSessRange` ranges over **[-631.6, +516.9]**. A position-within-range measure
should be bounded near [0, 100]. Those values are a denominator collapsing toward
zero when the session range is small - structurally the same defect as the
`net_240m / tfAtr` blowup found in V4 analysis, where 0.078% of rows carried more
than the entire dataset's signal.

Neither column is guessed at or repaired. Both are replaced in V5 by explicitly
defined causal constructions with a guarded denominator. Neither blocks P1, which
by design conditions on nothing derived from price.

**FEATURE CAUSALITY: PASS with two columns quarantined.**

---

## THE R DENOMINATOR

The `barTo*R` grid is denominated in units of one specific stop column. Tested
against each candidate on a 200k-bar slice:

| Candidate R | matches `barToStopLong` | matches `barToLong_1R` |
|---|---|---|
| **`stopMicroSwingLong`** | **98.54%** | **98.53%** |
| `stopAtrLong` | 40.75% | 37.21% |

R is the micro-swing stop distance. Its distribution is the hazard:

| quantile | R (pt) |
|---|---|
| q0.01 | 0.00 |
| q0.25 | 2.75 |
| q0.50 | 6.50 |
| q0.95 | 36.00 |
| q1.00 | **1266.50** |

| | |
|---|---|
| R exactly 0 | 28,329 bars (1.1315%) |
| R < 0.5 pt (2 ticks) | 64,909 bars (2.5926%) |
| R > 50 pt | 58,831 bars (2.3498%) |
| R / ATR | median 1.37, q99 5.10, max 20.0 |

R spans three orders of magnitude, and on 1.13% of bars the stop sits exactly on
the entry, making every R-multiple undefined. Pooling R-multiples across this
distribution lets the smallest-R bars dominate the mean, which is the identical
failure mode that produced a retracted number in V4. Guards are declared in
`V5_PREREGISTRATION.md` before any outcome is examined.

---

## SUMMARY

| Check | Verdict |
|---|---|
| Coverage and gaps | PASS - 0.0125% unexplained, all short, several are real CME halts |
| Bar universe integrity | PASS - proven identical to the engine's by exact row-shift match |
| Forward-column definitions | PASS - reconstructed to 100.0000%, not assumed |
| End-of-history truncation | PASS - forward window decays to 0, not fabricated |
| Feature causality | PASS - EMAs and ATR exact; two columns quarantined as undefined |
| R denominator | ESTABLISHED at 98.5%, with a declared degenerate population requiring guards |
| Cost model | STILL ASSUMED (1.5 pt round turn), not measured. Unchanged from V4. |

The asset is fit for V5 research subject to the quarantines and guards above.
