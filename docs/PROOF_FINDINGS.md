# PRO-OF-V1 — RESULTS (professional order-flow family)

Pre-registered in `docs/PROOF_PREREGISTRATION.md` before any outcome.
Track A: M = 8 tested on existing data. Track B: 7 concepts that our
data cannot represent — capture specs below, zero historical claims.
Frozen shelf untouched. All Track-A rules EXPLORATORY-DERIVED.

**Headline: NO ROBUST ORDER-FLOW EDGE FOUND IN CURRENT BAR-LEVEL DATA.
Zero of eight survived. The most coherent near-miss is stop-run
resolution (H3), and the overall pattern is consistent with the
professional concepts living at a finer resolution than a 1-minute
summary preserves.**

## 1–3. Data audit / testability

As pre-registered: bar-level volumetrics, developing profile, swings,
prior-day/session levels, 30s OHLCV (morning window) — available.
**Footprint ladders, tick/T&S, MBP/MBO depth, DOM snapshots,
add/cancel/modify, icebergs, queue data, synchronized ES — NOT
AVAILABLE.** Therefore: auction acceptance/rejection, stop runs,
headfakes, participation pullbacks, profile transitions and
extreme-flow reactions were testable now (H1–H8, with H7's LVN an
explicitly declared PROXY); iceberg/reloading, pull/stack, book sweeps,
tape speed, event-volume CVD, ES→NQ lead/lag and DOM aggregation were
not, and were not faked.

## 4–11. Definitions & results (60 m horizon)

Definitions exactly as pre-registered; DEV freezes: balance cut 5.283,
extreme-flow cut 1293; Q_BD75/CD margins reused.

| study | n | mean | med | MFE/MAE | ff | verdict driver |
|---|---|---|---|---|---|---|
| H1 breakout FULL | 860 | +3.43 | +4.38 | 0.97 | 47.1% | ablation monotone in mean but geometry < control; IR −5.26; **top trade = 108% of total** |
| H2 headfake FULL | 1102 | −1.10 | −1.87 | 0.97 | 49.8% | ablation degrades monotonically from the bare-excursion arm |
| H3 ACCEPTED (continuation) | 976 | +1.56 | +2.13 | 1.04 | 52.9% | ≈ control |
| **H3 REJECTED (reversal)** | 476 | +5.30 | **−0.37** | **1.21** | **56.4%** | best cell in family — see below |
| H4 CONTRACTED pullback | 179 | +7.19 | +6.13 | 1.04 | 47.2% | control separation real (+8.29) but U-partition R 0.80 / ff 38% |
| H5 extreme bar ACC / REJ | 707/515 | −0.05 / −3.96 | | 0.98 / 1.00 | 48% | reaction ≠ information; the bar itself is −7.74 (drift after climax, both ways ~flat) |
| H6 VA-edge ACCEPTANCE | 730 | +6.38 | +8.63 | 1.04 | 49.4% | IR −1.41; no ordering edge; U/DEV carried the mean |
| H6 VA-edge REJECTION | 894 | −2.39 | −5.87 | 0.87 | 46.5% | refuted |
| H7 LVN proxy | 740 | −1.30 | +2.63 | 0.93 | 48.8% | ≤ non-LVN control (PROXY ONLY) |
| H8 divergence CONT vs FADE | 460 ea | −5.35 / +3.61 | | 1.08 / 0.93 | 51.5 / 48.5% | absorption-continuation **worse** than the fade it was meant to replace; both ≈ 0 |

H8-STRUCT (divergence + structure failure): n = 17, mean +22.19 —
fragile extreme, not pursued.

## 12–22. Battery on the four candidate cells

Matched controls (direction · hour · ATR quintile · partition),
partitions, direction splits, tails, sign-flip p, day-clustered CI:

| cell | ΔR vs ctl | Δff | Δmean | U→DEV→IR | p | CI | BH q(8) |
|---|---|---|---|---|---|---|---|
| H1 FULL | −0.03 | −3.2 | +5.97 | +7.8 / +10.7 / **−5.3** | 0.087 | [−2.9, +10.0] | 0.226 |
| H3 REJECTED | **+0.24** | **+5.0** | +7.29 | +4.0 / +9.4 / +1.5 | 0.113 | [−4.6, +15.7] | 0.226 |
| H4 CONTRACTED | +0.06 | −2.4 | +8.29 | +2.7 / +5.1 / +13.5 | 0.090 | [−4.8, +19.3] | 0.226 |
| H6 ACCEPTANCE | +0.05 | −1.2 | +6.45 | +9.6 / +11.8 / **−1.4** | 0.036 | [−0.9, +14.2] | 0.226 |

Every CI spans (or grazes) zero; every BH q is 0.226. Tail
concentration disqualifies the means: H1 108%, H3 64%, H6 63% of total
P&L in the top 1% of trades. H4 is the cleanest on tails (28%) and has
the wrong-side U partition. **No cell passes the pre-declared survivor
gate**, so no management analysis was run (deliverable 23: not
applicable — nothing survived).

### What H3 nonetheless established

The two-arm question — do accepted and rejected stop runs have
different forward distributions? — got a **qualified yes**: at 15m
extremes, rejected runs show the family's only geometry-plus-ordering
signature (R 1.21, ff 56.4%, and the *ordering holds on IR at 59.1%*),
while accepted runs sit at control level. But the median is negative,
the mean is tail-carried, and the same construction at 3m extremes
shows nothing (R 1.00, ff 49.3%) — level quality matters, sample halves.
This is the concept most worth re-testing with better data.

## 24–31. Track-B capture specifications (frozen; nothing tested)

Common to all: every record stamped with exchange timestamp (ms or
better), ET conversion, session, instrument, engine version + hash.
NinjaTrader source: `MarketDepth` events (MBP) via
`OnMarketDepth` and `OnMarketData` (last/bid/ask/volume per trade);
true MBO is NOT available through standard NT8 — stated, not worked
around.

- **H9 iceberg/reloading:** per price level: executed volume at touch,
  displayed size before/after each trade, replenishment count within
  500 ms, cumulative executed-vs-displayed ratio. Event row whenever
  executed ≥ 3× initially displayed at one price while best bid/offer
  holds. Needs `OnMarketData` (Last) + `OnMarketDepth` deltas.
- **H10 pull/stack:** 1-second snapshots of the top 5 levels each side:
  size, adds, cancels (depth deltas classified by side/level), plus
  near-touch depth ratio. Event = one side's near-touch depth halving /
  doubling within 10 s without transacting.
- **H11 sweep + replenishment:** trade prints grouped into aggressor
  sequences (same side, ≤250 ms gaps); record levels consumed, size,
  duration; then 5 s of post-sweep depth deltas on the swept side.
- **H12 tape speed:** rolling 1 s / 5 s trade counts, contracts/s,
  levels/s, plus the H10 snapshot at known levels (prior-day H/L,
  session H/L, 15m swings — computed causally in-engine).
- **H13 event/volume bars:** raw time & sales (price, size, aggressor
  side, ms timestamp) is sufficient; equal-volume bars (pre-declared
  sizes 500 / 1,000 / 2,000 contracts) built offline.
- **H14 ES→NQ:** an identical Volumetric 1m + (if enabled) depth
  capture running on ES in the same session, same clock; offline
  alignment at 1 s. Requires an ES data subscription — flagged.
- **H15 DOM aggregation:** no new fields; an offline transform of the
  H10 snapshots at 1 / 4 / 8-tick aggregation. Spec: identical features
  computed per aggregation; compare signal stability and false-signal
  rate.

**Recommended NT8 additions (one capture host, one file family):**
per-trade T&S stream (ms, price, size, aggressor), 1 s top-5 MBP
snapshots + deltas, per-level executed/displayed at touch, and the
existing 1m Volumetric context for continuity. That single set makes
H9–H13 and H15 testable; H14 additionally needs the ES twin.

## 32. Ranking (testable eight)

1. H3 stop-run resolution (rejected arm) — only geometry+ordering
   signature, ordering survives IR; fails on median/tails/q.
2. H4 participation-contraction pullback — honest control separation,
   cleanest tails, wrong-side U partition.
3. H6 acceptance — mean without ordering; dies on IR.
4. H1 acceptance — monotone ablation, single-trade mean, IR negative.
5. H5 — reaction adds nothing; the extreme bar itself is mild poison
   (−7.74) in both directions.
6. H2, H7, H8 — refuted or at control.

## 33. Mechanism synthesis

Across 8 tests: **acceptance/continuation framings beat their reversal
mirrors in means but never in ordering; reversal framings only show
ordering at swept 15m extremes.** The one repeated positive note is the
same one the whole programme keeps finding: something real happens
around *higher-timeframe liquidity extremes after a violent excursion
fails* — G4 (frozen shelf), G4-FVG (V4.2 survivor), and now H3-REJECTED
all touch it — and bar-level data keeps being too coarse to convert it
into a tradable entry with acceptable tails.

## Final answers

**DID ANY AUCTION/ORDER-FLOW CONCEPT SHOW A REPEATABLE ADVANTAGE IN THE
CURRENT HISTORICAL DATA? — NO.** (H3-REJECTED is a lead, not an
advantage: q = 0.226, negative median, tail-carried mean.)

**IS THE FAILURE CONSISTENT WITH BAR-LEVEL AGGREGATION BEING TOO COARSE
FOR HOW DOM/ORDER-FLOW TRADERS ACTUALLY TRADE? — YES.** Three
independent signs: (1) every concept that *requires* intra-minute
resolution (replenishment, pulling, sweeps, tape speed) was untestable
outright; (2) the concepts that were testable degraded exactly where
1-minute summaries lose the most (ordering within the bar — our
AMBIGUOUS counts spike at the interesting events); (3) the one
mechanism with a stable ordering signal (H3) is precisely the one whose
defining moment — what happens in the seconds after stops trigger — a
1m bar averages away. Consistency is not proof: it is also consistent
with there being no edge at any resolution.

**WHICH SHOULD WE PRIORITIZE NEXT? — STOP-RUN RESOLUTION**, captured
properly (the H11/H12 fields around known extremes), with
ICEBERG/RELOADING second. Per the pre-registration: the recommendation
is Track-B capture, **not** variant generation on bar data.

No survivor frozen. Verdicts: H1 NO INCREMENTAL VALUE · H2 NO
INCREMENTAL VALUE · H3 **INTERESTING MECHANISM — NEEDS MORE DATA** ·
H4 INTERESTING MECHANISM — NEEDS MORE DATA · H5 NO INCREMENTAL VALUE ·
H6 DIRECTIONAL DRIFT ONLY · H7 NO INCREMENTAL VALUE (PROXY) · H8 NO
INCREMENTAL VALUE · H9–H15 **CAPTURE REQUIRED — NOT HISTORICALLY
TESTABLE**.
