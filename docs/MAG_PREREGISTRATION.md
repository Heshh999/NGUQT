# MAG-AUC-V1 — PRE-REGISTRATION (FROZEN BEFORE RESULTS)

**Declared family size M = 15.** M does not shrink for any reason,
including a hypothesis voided by specification error.

Committed before any outcome, return, or P&L was computed. The only
numbers computed before this freeze are **gate-variable distributions on
the U partition** (documented below): frequency calibration, never
performance. No forward label was evaluated first.

## Canonical reproduction — PASS (required before research)

| object | got | expected |
|---|---|---|
| bars | 355,455 | 355,455 |
| OFH6 signals | 952 | 952 |
| OFH13 | 133 | 133 |
| OFH14 | 462 | 462 |
| G4 | 218 | 218 |
| G3 | 477 | 477 |
| G1 | 845 | 845 |

## Data audit

| item | class | note |
|---|---|---|
| 1m OHLCV | **AVAILABLE** | 355,455 bars, 315 days, 2025-08-18 → 2026-08-19 |
| bid / ask volume | **AVAILABLE** | 100% coverage |
| bar delta, delta % | **AVAILABLE** | 100% |
| cumulative delta | **AVAILABLE** | `ofCumDelta`, session-running |
| rolling delta | **CAUSALLY DERIVABLE** | `dsum15` 98.9%, or rolled from bar delta |
| **per-bar delta range** | **NOT AVAILABLE** | `ofMinDelta`/`ofMaxDelta` are SESSION-running cumulative extremes — verified constant across consecutive bars. **Not fabricated, not used.** |
| total volume, volume per tick | **AVAILABLE** | 100% / 99.999% |
| imbalance & stacked counts (3x) | **AVAILABLE** | 100% |
| ATR | **AVAILABLE** | 100% |
| **VWAP** | **PROXY ONLY** | no tick VWAP; typical-price×volume accumulation is derivable and is labelled a proxy wherever used |
| developing POC / VAH / VAL | **AVAILABLE** | 100%, `profileReady` flag present |
| causal balance / range | **CAUSALLY DERIVABLE** | see BALANCE below |
| overnight high / low / midpoint | **CAUSALLY DERIVABLE** | 18:00 → 09:29 ET bars |
| overnight VWAP | **PROXY ONLY** | same limitation as VWAP |
| RTH opening range | **CAUSALLY DERIVABLE** | `minutesFromRthOpen` |
| 3m / 15m structure | **CAUSALLY DERIVABLE** | `red_lib.build_swings` |
| prior-day high / low | **CAUSALLY DERIVABLE** | `red_lib.prior_day_levels` |
| 30s data | **AVAILABLE (partial)** | 192 days ph2 + 70 days capture |
| 15s / 5s data | **AVAILABLE (partial)** | 70 days, 2026-06-02 → 2026-08-21 only |

---

## FROZEN MAG_SCORE

Strictly causal; **contains no directional information of any kind.**

```
a = |ofBarDelta|                          / trailingMean(·, 1440)
b = ofTotalVolume                         / trailingMean(·, 1440)
c = buyImbalanceCount_3x
    + sellImbalanceCount_3x               / trailingMean(·, 1440)

MAG_SCORE = (a + b + c) / 3
```

The 1440-bar (one full day) trailing mean **excludes the current bar**
from its own normaliser. Imbalance counts are **summed**, so buy/sell
sign cancels by construction.

**Bar range is deliberately EXCLUDED from the primary score.** MAG-H3
asks whether MAG_SCORE predicts *future* absolute movement; putting the
current bar's range into the score would make that partly a
volatility-persistence tautology. Range appears only as a diagnostic.

**Declared diagnostics (exactly two, as permitted):**
- `MAG_ALT_VOL` = `b` alone (participation only)
- `MAG_ALT_RNG` = trailing-normalised bar range — **the skeptical
  benchmark.** If MAG_SCORE cannot beat plain volatility persistence at
  predicting future movement, it adds nothing and must be reported as
  adding nothing.

**Buckets — terciles measured on the U partition ONLY, applied
unchanged to DEV and IR** (no look-ahead):

```
LOW    MAG_SCORE <  1.270
MEDIUM 1.270 .. 2.335
HIGH   MAG_SCORE >  2.335
```

## FROZEN BALANCE and COMPRESSION

```
BALANCE(j)  = high/low envelope of the 30 minutes ending at j
ratio(j)    = (bal_hi - bal_lo) / (ATR_1m * sqrt(30))
```

The `sqrt(n)` term is the random-walk scaling that makes an *n*-minute
range commensurable with a *1*-minute ATR. **BRK-H2 died because it
compared a 5-minute range to an unscaled 1-minute ATR and required the
range to be a third of it — impossible by construction.** This is the
corrected, dimensionally coherent form and it is registered as a **NEW
hypothesis (BAL-H1/H2), not a silent repair of BRK-H2.**

Attainability verified on U before freezing (distribution only, no
outcomes): ratio ranges **0.460 → 2.434**, median 0.943.

```
QUIET BALANCE  ratio <= 0.784      (U p25; a FREQUENCY calibration,
                                    admits 4,439 of 17,754 U bars)
```

## FROZEN ACCEPTANCE / REJECTION — one primary each, no search

```
ACCEPTANCE  two consecutive completed 1m closes beyond the balance edge
REJECTION   >= 1 completed close beyond the edge, then a completed close
            back INSIDE the balance, within 5 bars of the first breach
```

No 1/2/3/4/5-close sweep is run. These are the primaries and the only
ones scored.

## FROZEN PRICE EFFICIENCY (ASYM-H2)

```
EFF(j) = |close_j - close_{j-5}| / sum(range over those 5 bars)
```
Net movement over path length — dimensionless, sign-free in the
denominator. Direction, where needed, is the **sign of the numerator**
(price), never delta. U terciles: **LOW < 0.119, HIGH > 0.264.**

## FROZEN OVERNIGHT DEFINITIONS

Overnight session = bars 18:00 ET (day D−1) → 09:29 ET (day D).
`ON_HI`, `ON_LO`, `ON_MID = (HI+LO)/2`, `ON_VWAP` = **proxy**
(typical-price × volume accumulation). RTH open = first bar ≥ 09:30.
Opening interval = 09:30–09:44 inclusive.

## FROZEN MANAGEMENT (all directional cells)

The frozen OFH13 management, verbatim: **1.5 ATR stop, no target,
60-minute time exit, 0.87 pt round-trip cost.** No management search
happens unless a cell first shows credible raw geometry — and then only
the broad grid the directive permits.

---

## The fifteen

**MAG-H3 (RUN FIRST, gates the rest).** Does MAG_SCORE predict future
*absolute* movement? Buckets LOW/MED/HIGH × horizons 5/10/15/30/60 →
|return|, true range, MFE+MAE, realised variance. Spearman + broad
quantile monotonicity + matched controls. **No direction, no P&L.**
Compared head-to-head against MAG_ALT_RNG and MAG_ALT_VOL. If magnitude
does not replicate, every downstream MAG cell is read skeptically.

**MAG-DIR-H1.** Balance at j; HIGH mag at j; price closes beyond an edge
within 10 bars; ACCEPTANCE; enter in the **price-selected** direction.
Order-flow sign is never consulted. Controls: breakout alone; HIGH mag
alone; mag+breakout without acceptance; **breakout+acceptance without
mag** (the primary comparison); FULL.

**MAG-DIR-H2.** Same parent, opposite resolution: HIGH mag, breakout,
then REJECTION → enter back toward the interior. Measures distance
outside, time outside, volume outside, |delta| outside, re-entry speed,
rotation depth. Controls: breakout only; re-entry only; mag+re-entry;
FULL.

**MAG-OFH13-H1.** Offline diagnostic on the 133 canonical events.
MAG_SCORE at entry → LOW/MED/HIGH → N, WR, PF, mean/median R, MFE, MAE,
MFE/MAE, favourable-first, average winner, tail contribution. Looking
for monotonicity. **OFH13_PROSPECTIVE_V1 IS NOT FILTERED OR MODIFIED.**

**OVN-H2.** Overnight extension ≥ 1.0 ATR from ON_VWAP(proxy) → RTH
re-entry through ON_VWAP within 60 RTH minutes → trade the reversion.
Controls: extension only; re-entry only; extension+re-entry.

**OVN-H3.** Strong overnight move ≥ 1.0 ATR → RTH opens beyond the ON
extreme → ACCEPTANCE in the opening interval → trade continuation.
Direct comparison with OVN-H2 answers whether the RTH auction decides
continuation vs reversion.

**OVN-H4.** ON_HI/ON_LO frozen at 09:29 → RTH trades beyond → completed
reclaim within 5 bars → trade the reclaim. Controls: touch; sweep only;
sweep+reclaim; **sweep+reclaim+HIGH mag**.

**OPEN-H1.** Opening drive |close(09:44) − open(09:30)| ≥ 1.0 ATR, held
beyond the overnight extreme, origin not reclaimed within 30 min →
continuation on a completed new extreme. Direction from **price drive**,
never delta sign; magnitude is a quality condition only.

**OPEN-H2.** Large opening drive + HIGH mag → new extreme → stall →
rapid recovery of **50% (arm A)** or **100% (arm B)** of the impulse
within 60 RTH minutes → trade the V.

**BAL-H1.** QUIET balance (ratio ≤ 0.784) → HIGH mag shock within 10
bars → breakout → ACCEPTANCE → enter price-selected direction.

**BAL-H2.** Same parent → breakout → failure to accept → completed
return inside → fade toward the interior. Compared directly with BAL-H1.

**RANGE-H1.** Regime persistence. After HIGH mag, realised range over
+3/+5/+10/+15/+30 min vs matched MEDIUM/LOW. Does the state mark a
persistent regime or one big bar? **Diagnostic only — no strategy change
is made here.**

**RANGE-H2.** Meta-interaction: magnitude bucket × strategy type
(OFH13, accepted-breakout, rejected-breakout) with **no rule changed and
no threshold re-optimised per regime.**

**ASYM-H1.** At extreme |delta|: arm A follow delta sign; arm B follow
price direction; arm C price direction only when |delta| extreme; arm D
price direction unconditional. Does absolute intensity improve a
price-direction model?

**ASYM-H2 (high priority).** STATE A = HIGH activity + HIGH efficiency →
continuation in the price direction. STATE B = HIGH activity + LOW
efficiency → rejection/mean-reversion. Compared against raw delta sign,
raw activity, and price momentum alone.

---

## Statistics and gates

Per-event accounting; non-triggering parents count as 0 where a
denominator exists. Day-clustered bootstrap CI (20,000), sign-flip-by-day
or matched-control permutation as appropriate to the claim (a
non-directional claim never uses a sign-flip null), **BH at M = 15**,
plus family-wise (Holm) reported alongside.

Reported for every cell: N, frequency, returns at 5/10/15/30/60, median,
MFE, MAE, MFE/MAE, favourable-first at all five pairs with **AMBIGUOUS
never guessed**, absolute movement, long/short separately, U/DEV/IR
separately, largest winner, largest loser, top 1%, top 5%, mean excluding
top 1%.

### Promotion gate — ALL EIGHT required, each printed explicitly

1. economic expectancy positive
2. **the signal itself is profitable — not merely "less bad than control"**
3. U/DEV/IR sign behaviour reasonably stable
4. not dominated by the top 5% tail
5. matched-control advantage exists
6. raw geometry credible
7. sample size adequate
8. no control-construction artifact

### Control-construction audit — mandatory

After BRK-H1, every control set is audited for time-of-day, ATR, volume,
range, trend, distance from other signals and session state against its
signal set. A control that differs materially is reported as such,
because a bad control manufactures significance from a losing signal.

## Standing rules

Every survivor is **EXPLORATORY-DERIVED** — this batch runs on
already-spent history. No prospective result is used for discovery.
OFH13/OFH14/G4/G3/G1, `prospective.py`, `PROSPECTIVE_REGISTRY.md`, the
NT8 host and the live ledger are **not modified**. Void hypotheses are
not retuned. M is not shrunk. **THIS PROJECT DOES NOT AUTHORIZE LIVE
TRADING.**
