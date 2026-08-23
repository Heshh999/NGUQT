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

---

# ADDENDUM — ENGINE COMPLETED AND RUN ON GENUINE 30s DATA

`analysis/ltf_exec/ltf_engine.py` is now the complete, one-command
engine; `ph2_to_ltf.py` converts the already-validated genuine 30s
history into its input format (pure reformatting — no bar created,
merged, split or interpolated).

## Correction to a previously reported check

The earlier Phase-2 report stated "0 duplicate 30s keys". **That check
was wrong** — it counted a Counter over dict keys, which is always 1.
The genuine ph2 export actually contains **45,587 duplicate rows**
across its monthly files. They were verified to be **identical
re-exports (0 conflicting values)** and are now dropped first-wins,
the same rule `cand_spec.load_merged` uses. The corrected dataset is
34,944 unique 30s bars + 17,381 1m bars over 192 days.

The engine's own integrity gate caught this (33 aggregation mismatches
→ refused to backtest). After the dedupe: **30s→1m matched 17,190,
exact 17,190, mismatch 0 — PASS.**

## Result on genuine 30s (133 canonical parents, per-parent EV)

| arm | trig | trig% | per-parent EV | vs baseline | avg entry improvement | med MAE | ff 0.25 | top-10 kept |
|---|---|---|---|---|---|---|---|---|
| **BASELINE 1m** | 133 | 100% | **+17.26** | — | — | 32.8 | — | 10/10 |
| ARM1 reclaim | 21 | 15.8% | +4.19 | **−13.07** | −32.14 | 29.8 | 40.0% | 4/10 |
| ARM2 pullback/re-expand | 36 | 27.1% | +5.25 | **−12.01** | −8.49 | 27.9 | 33.3% | 4/10 |
| ARM3 sweep+reclaim | 18 | 13.5% | −0.49 | −17.75 | −37.64 | 34.5 | 18.2% | 2/10 |
| ARM4 detect→confirm | 0 | 0% | — | — | — | — | — | 0/10 |
| ARM5 second push | 9 | 6.8% | −0.75 | −18.01 | −4.86 | 36.2 | 16.7% | 0/10 |
| ARM6 V-recovery | 28 | 21.1% | +5.75 | **−11.51** | −18.47 | 35.6 | 21.4% | 4/10 |
| ARM7 compression release | 0 | 0% | — | — | — | — | — | 0/10 |
| ARM8 FVG breakdown | 0 | 0% | — | — | — | — | — | 0/10 |

**Every 30s arm is worse than simply taking the canonical 1m entry.**
Trigger rates are 0–27%, so the arms sit out most parents — and the
parents they sit out include **6–10 of the ten largest winners** in
every case. Entry "improvement" is negative throughout (waiting costs
price, it doesn't save it: −4.86 to −37.64 pt on average). Two arms
lowered median MAE (ARM1 29.8, ARM2 27.9 vs 32.8 baseline) — a real
risk improvement that is nowhere near paying for the missed tail.
ARM4/7/8 never fired at 30s resolution.

This is the third independent confirmation, now with full per-parent
accounting across eight execution rules: **waiting for a lower-timeframe
trigger on an OFH13 parent destroys the edge by missing the winners.**

## Running it

```
python3 ph2_to_ltf.py                    # genuine 30s -> engine format
python3 ltf_engine.py inventory data     # what real data exists
python3 ltf_engine.py validate data      # aggregation gates
python3 ltf_engine.py run data           # full study, all arms
```

When Market Replay 5s/15s files arrive, drop them in the same folder
(or point the engine at the capture folder) and rerun `run` — the 15s
and 5s columns populate automatically, ARM4/ARM7 become testable, and
the aggregation gate re-verifies 5s→15s→30s→1m before any result is
produced.
