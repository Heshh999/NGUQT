# LTF-EXEC-BACKTEST-V1 — 5s/15s execution research

**Status: CAPTURE REQUIRED.** Genuine 5-second and 15-second history
does not exist anywhere in this project. Nothing was interpolated. The
capture module, the deterministic backtester, and all nine execution
arms are built, frozen and pipeline-verified — awaiting genuine Market
Replay capture data. OFH13_PROSPECTIVE_V1 untouched.

## Phase 1 — data inventory (final)

Searched every data directory (ofnew, of2, of1, of3, ofx, aud, ph2,
V4LAB, repo) by filename and by in-file timeframe field:

| timeframe | verdict | detail |
|---|---|---|
| **5s** | **NOT AVAILABLE** | no file, any period |
| **15s** | **NOT AVAILABLE** | no file, any period |
| **30s** | **AVAILABLE (limited)** | ph2 capture: 2025-09→2026-05, 192 days, 34,944 non-warmup bars, ~09:30–11:00 ET, OHLCV only — no bid/ask, no delta |
| tick / T&S | **NOT AVAILABLE** | — |

`analysis/ltf_exec/data_audit.csv` holds the machine-readable audit.

## Phase 2 — 30s genuineness PROVEN

Timestamp convention: **CLOSE-STAMPED** (a 1m bar at t aggregates the
30s bars stamped t−30s and t). Validation on the 9 in-window months:

- 2×30s → 1m: **17,190 matched minutes, 17,190 exact OHLC (100%), 0
  mismatches**, 191 missing pairs (session edges), 0 duplicates
- volume agreement within 1 contract: 17,189 / 17,190
- ph2's own 1m rows vs canonical capture 1m: **17,381 / 17,381 exact**

## Phase 3 — Market Replay capture module (built, compile-verified)

`src/MnqV41LtfCaptureHost.cs` — new NT8 strategy, submits no orders:

- primary series = **1m Volumetric** (HARD FAIL otherwise); runs the
  frozen `V41FrozenCandidateEngine` so parent state is exact
- `AddDataSeries(Second,30/15/5)` — NinjaTrader closes genuine bars;
  each is written as it closes
- row schema: `timestampET, instrument, contract, timeframe, OHLCV,
  bidVolume, askVolume, delta, deltaPercent` (delta columns written
  **only** for the Volumetric 1m rows — standard Second series carry no
  bid/ask and the columns stay EMPTY, per the data rule), plus frozen
  parent state: `parentCandidate, parentEventId, parentDirection,
  parentAvailableTime, parentEntryTime, parentEntryPrice, parentATR,
  fvgLow, fvgHigh, structuralInvalidation, parentStillValid,
  engineVersion`
- parent = latest eligible canonical OFH13 event; validity = ≤30 min
  from entry and no 1m far-side close
- one file per capture day: `V41_ltf/V41_LTF_MNQ_YYYYMMDD.csv`

**To capture:** paste `MnqV41LtfCaptureHost.cs` in (keep everything
already installed), F5, then on a Playback connection put it on an MNQ
1m **Volumetric** chart and replay full RTH days — the more days the
better; each session yields ~4,680 5s rows + 1,560 15s + 780 30s + 390
1m. Send back the `V41_ltf` folder.

## Phases 4–17 — backtester (built, frozen, pipeline-verified)

`analysis/ltf_exec/ltf_backtest.py`:

- `validate <dir>`: 5s→15s, 15s→1m, 5s→1m exact-aggregation gates — **no
  backtesting until they pass**
- `run <dir>`: canonical OFH13 parents regenerated from frozen
  `cand_spec` (133 on the current history — reproduction gate inside),
  then all nine arms with **per-parent accounting: one row per
  parent × arm, triggered or not**, no LTF bar before
  `parentAvailableTime`, arm windows bounded by parent validity
- arm rules frozen as specified (ARM0 canonical baseline; ARM1 15s
  reclaim; ARM2 15s pullback/re-expansion; ARM3 5s sweep+reclaim; ARM4
  5s detect → 15s confirm; ARM5 15s second push; ARM6 15s V-recovery
  (50% arm); ARM7 15s compression 30/60/90 s → 5s release; ARM8 15s
  FVG-breakdown reclaim). Order-flow-microstructure variants (5s/15s
  delta) return **FUTURE CAPTURE REQUIRED** — 1m delta is never
  inherited onto a specific LTF bar.
- outputs: `per_parent.csv` now; the remaining CSVs
  (timeframe_comparison, missed_winners, favorable_first,
  stop_geometry, slippage_latency, daily_results) are produced by the
  same run once genuine 5s/15s rows exist.

Pipeline verification (this run): 133 parents × 9 arms = 1,197
deterministic rows; ARM0 scored; every 5s/15s arm honestly reports
`INSUFFICIENT DATA — genuine bars absent`.

## The 30s column — already measured (genuine data, two prior studies)

| study | parents | per-parent EV 1m | per-parent EV 30s | entry price |
|---|---|---|---|---|
| OFH13-30S (V4.2) | 57 | +19.87 | +20.77 | median **1.50 pt worse** |
| H-NEW12 (V4.2-B) | 100 | +22.62 | +21.11 | median **1.75 pt worse** |

Genuine 30s execution on the strongest parent was a wash both times:
always earlier, slightly worse price, EV within noise.

## Final answers

- **DO WE HAVE GENUINE HISTORICAL 5s DATA? NO.**
- **DO WE HAVE GENUINE HISTORICAL 15s DATA? NO.**
- **DID MARKET REPLAY PRODUCE GENUINE 5s/15s DATA? NOT YET** — the
  capture module is built and compile-verified; the replay run is the
  user's next action.
- **DID 15s / 5s IMPROVE PARENT ECONOMICS? NOT YET TESTABLE** (no
  genuine data; the honest prior from two genuine 30s studies is
  "no material improvement").
- **WHICH TIMEFRAME WAS BEST?** On measured evidence so far: **NO
  MATERIAL DIFFERENCE** between 1m and 30s; 15s/5s unmeasured.
- **AFTER MISSED WINNERS, SLIPPAGE, LATENCY — IS LTF ENTRY BETTER?
  INCONCLUSIVE** pending capture; at 30s the answer was NO.

Sample-size rule stands: Replay capture of N days yields roughly
N×(parents/day ≈ 0.5) OFH13 parents in-window — several weeks of
replayed days are needed before any 5s/15s claim can exceed the
"very low sample" label. That expectation is set now, before data.
