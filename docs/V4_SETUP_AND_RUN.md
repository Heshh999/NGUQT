# V4 — Multi-Timeframe Market Structure + Order Flow

Two independent research captures. **Neither submits an order.** Neither contains
candle-colour classification of any kind.

V3 is closed. Its conclusion stands unchanged: *no robust V3 price-action
strategy survived*. V4 is a new programme built on different information, as the
brief's escalation ladder requires — it does not reuse, extend or contaminate the
V3 capture, and nothing in V4 shares state with it.

---

## 1. Files

Copy **all six** `.cs` files into:

```
Documents\NinjaTrader 8\bin\Custom\Strategies\
```

then press **F5** in the NinjaScript Editor to compile.

| File | What it is |
|---|---|
| `V4StructureEngine.cs` | Swing structure, HH/HL/LH/LL, structure states, the break classifier |
| `V4LocationBook.cs` | Prior day/week extremes, session high/low/open, session VWAP |
| `V4StructureResearch.cs` | The capture: events, cross-timeframe alignment, forward labels, entry probes |
| `V4OrderFlowEngine.cs` | Executed order flow + the data-quality gate |
| `MnqV4StructureResearchHost.cs` | NT8 strategy: **MnqV4StructureResearch** |
| `MnqV4OrderFlowResearchHost.cs` | NT8 strategy: **MnqV4OrderFlowResearch** |

They live in their own namespace (`…Strategies.MnqV4`) and will not collide with
the V3 files already installed.

---

## 2. Run A — the structure capture

**Strategy Analyzer → Strategy: `MnqV4StructureResearch`**

| Setting | Value |
|---|---|
| Instrument | MNQ (continuous, **Merge Back Adjusted**) |
| Bars type / Value | Minute / **1** |
| From – To | as far back as your data goes → today |
| Calculate | **On bar close** (the strategy forces this anyway) |
| Order Fill Resolution | irrelevant — no orders are placed |

Seven series are loaded automatically: Daily, 4H, 60m, 15m, 5m, 3m, 1m. You do
not add them yourself.

### Default parameters, and why

| Parameter | Default | Reason |
|---|---|---|
| Pivot confirm bars (right) | 2 | The confirmation lag. A pivot is invisible until 2 bars have closed to its right. |
| Pivot left bars | 2 | |
| Equality band (ATR) | 0.10 | A quarter-point "higher high" is noise, not structure. |
| ATR period | 20 | Everything else is measured in ATR so it survives back-adjustment. |
| Wick threshold (ATR) | 0.25 | Below this, a penetration that closes back is a wick. |
| Displacement body / close (ATR) | 1.00 / 0.35 | Both must hold for a break to count as displaced. |
| Retest band (ATR) | 0.25 | |
| Reversal distance (ATR) | 1.00 | |
| Control sample rate | 400 | 1 in 400 non-break bars per timeframe, **both directions**. |
| Capture 1-minute break events | **OFF** | *"Do not search for a 1-minute pattern simply because 1-minute data exists."* 1m is loaded because it is the label clock; making it an event source too would swamp the file on count alone. Turn it on only to test the stated 15m→1m architecture. |
| Emit from / to (ET minutes) | 0 / 1440 | Capture the whole session. **Do not pre-narrow to 09:30–11:00.** Whether that window is special is one of the questions; hard-coding it makes the answer unfalsifiable. Filter in analysis instead. |

### Output

Written to your NinjaTrader user folder (`Documents\NinjaTrader 8\`):

```
v4_structure_MNQ_v4_2021-03.csv   one row per structure break or control
v4_entries_MNQ_v4_2021-03.csv     one row per (event, entry timeframe, trigger)
```

One file per month. Rows are routed by **their own date**, not by when they were
written — events are emitted late, only once their forward horizon has elapsed.

If the entry file is too large on the first pass, untick **Write
entry-resolution file** and run the structure file alone.

---

## 3. Run B — the order-flow capture

Separate strategy, separate chart, separate file, separate verdict.

**Chart:** primary series must be **Bars type: Volumetric, 1 Minute, Ticks Per
Level 1**. The strategy reads the primary series directly.

**Strategy Analyzer → Strategy: `MnqV4OrderFlowResearch`**

### Output

```
v4_orderflow_MNQ_v4of_2021-03.csv
v4_orderflow_MNQ_v4of_AUDIT.txt      <-- read this FIRST
```

**The audit decides whether any of the rest may be used.** It reports coverage,
missing per-price levels, timestamp gaps, whether ask+bid reconciles to bar
volume, and whether the price levels sit on the instrument's tick grid, then
prints `VERDICT: PASSED` or `VERDICT: FAILED`.

If it says FAILED, that is the result. Report *"order-flow history
insufficient"*. Do not lower the thresholds until it passes.

If the chart is not volumetric, every bar is recorded as `NO_LEVELS`, the audit
fails, and the log says so explicitly.

---

## 4. Reading the structure file

Every column falls into exactly one of two blocks, and the split is the point of
the whole exercise.

**FEATURES — sealed at the close of the event bar.** Knowable before the trade.

`outcome`, `penetrationAtr`, `closeBeyondAtr`, `bodyAtr`, `relVolume`,
`tfCompression`, `tfExpansion`, `struct_1d … struct_1m`, `minsInState_*`,
`alignState`, `alignAgree/Oppose/None/Transitioning`, `archA/archB/archC`,
`dist*Atr`, `nearestLevel`, `atLocation`, `stopSwingPts`, `priorFailedBreakThisTf`.

**LABELS — filled in only from bars that arrived afterwards.** Never an input.

`net_5m … net_240m`, `mfe_*`, `mae_*`, `contMax*`, `minsToCont_*`, `retested`,
`minsToRetest`, `retestDepthPct`, `closesBeyondFirst30/60`, `failedBreak`,
`reversal`, `volExpansion`, `followState`, `minsToStop`, `minsTo_*R`.

Three of the brief's eight break outcomes — *immediately rejected*, *accepted
beyond*, *retested* — are **not** in `outcome`. They cannot be known when the
bar closes, so they live in `followState` on the label side. `outcome` carries
only the five that are properties of the break bar itself.

### Key column notes

- **Horizons are MINUTES, not bars.** A Daily break and a 15m break are measured
  on the same ruler, so they can be compared at all.
- **`locAsOfEt`** is the timestamp of the newest bar folded into the location
  book. It is always strictly earlier than `timeEt` — that is the no-lookahead
  claim, published so you can check it rather than trust it.
- **`eventKind = CONTROL`** rows are sampled bars that broke nothing, emitted in
  both directions with an identical feature and label block. Without them,
  "breaks continue X% of the time" has no denominator.
- **`isWarmup = TRUE`** rows are fully processed but outside the official
  sample. Filter them out before computing anything.

---

## 5. Reading the entry file

Join to the structure file on `eventId`.

Each parent event is priced against up to eight candidate executions: entry
timeframes {15m, 5m, 3m, 1m} × triggers {IMMEDIATE, PULLBACK_RECLAIM}, limited
to entry timeframes no coarser than the event's own.

- `probeState = TRIGGERED` — it filled. `INVALIDATED` — price closed back
  through the level before the reclaim, so the structural premise was gone.
  `EXPIRED` — never triggered inside the window.
- `minsToEntry = 0` on a same-timeframe IMMEDIATE probe means the fill is the
  break bar's own close. That is the honest price for acting on the signal.
- `netR_*`, `mfeR`, `maeR` are in R against that probe's own structural stop.
- `slipFromBreakClosePts` is what waiting for the trigger cost or saved,
  relative to the break bar close.

This is the answer to *"does execution on a lower timeframe demonstrably improve
cost-adjusted expectancy?"* — comparing entry timeframes against **the same
frozen parent event**, so any difference is execution and not a different
hypothesis.

---

## 6. Robustness runs

The brief requires any structural edge to survive nearby swing definitions,
alternative aggregation and other markets. Change **File tag** each time so runs
land in separate files.

| Run | Change | Tag |
|---|---|---|
| Base | defaults | `v4` |
| Swing −1 | Pivot confirm 1, left 1 | `v4_sw1` |
| Swing +1 | Pivot confirm 3, left 3 | `v4_sw3` |
| Equality band off | 0.00 | `v4_eq0` |
| Displacement looser | body 0.75, close 0.25 | `v4_disp_lo` |
| Displacement tighter | body 1.50, close 0.50 | `v4_disp_hi` |
| ATR 14 / ATR 30 | ATR period 14, then 30 | `v4_atr14`, `v4_atr30` |
| Cross-market | run on MES and MYM | `v4_mes`, `v4_mym` |

A finding that exists at `confirm=2` and vanishes at `confirm=1` or `confirm=3`
is fragile, whatever its t-statistic.

Cross-market runs work unchanged — the symbol is read from the instrument and
stamped on every row, and everything is measured in ATR rather than points, so
the numbers are comparable across contracts of different size. **This is
research data only. It authorises nothing, on any instrument.**

---

## 7. What this package does not do

- It does not trade, and cannot be made to. There is no order method in any V4
  file.
- It does not select a strategy. It produces the evidence a selection would have
  to be argued from.
- It does not mix order flow into the structure study. The two datasets are
  joined in analysis on (symbol, timestamp), never in code — so if order flow
  adds nothing, deleting it changes not one number in the structure results.
- It does not assume market structure is predictive. Whether a break contains
  information *before* the trade, or merely describes price *after* it, is the
  question the feature/label split exists to answer — and "it does not" remains
  a valid, reportable outcome.

**This project does not authorize live trading.**

---

## 8. Verification status

- 79 deterministic assertions in `tests/V4Tests.cs`, all passing under Mono,
  including a direct regression test against the V3 classifier defect (a bar
  that *closed* beyond a level can never be filed as a wick).
- The full repository compiles against the NT8 API stubs.
- Pure ASCII throughout.

Compiling is not correctness, and this has **not** been run inside NinjaTrader 8
yet. Nothing here should be described as runtime-verified until you have loaded
it in NT8 and read the diagnostic block it prints at the start of a run — which
names every series, its bar count, and flags any that loaded zero bars.
