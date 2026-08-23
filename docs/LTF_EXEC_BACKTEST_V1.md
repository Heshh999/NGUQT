# LTF-EXEC-BACKTEST-V1 — 5s/15s execution research

**Status: CAPTURED, UNDER-SAMPLED.** Genuine 5s/15s/30s bars now exist
for 2026-06-02 → 2026-08-21, 70 days (see ADDENDUM 3 at the end — the
addenda supersede the "NOT AVAILABLE" verdicts below, which were true
when written). Nothing was ever interpolated. Coverage is **28 of 132
canonical parents**; no arm survives family correction (best BH q =
1.000). OFH13_PROSPECTIVE_V1 untouched.

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

- primary series = 1m; when it is **Volumetric** the frozen
  `V41FrozenCandidateEngine` runs and every row carries exact parent
  state. A non-Volumetric primary no longer aborts the run — capturing
  5s/15s bars needs no order-flow data at all, so the strategy prints a
  diagnostic, leaves the parent columns EMPTY and keeps capturing.
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
- one file per **ET calendar day**: `V41_ltf/V41_LTF_MNQ_YYYYMMDD.csv`.
  The writer rolls on the date, so a multi-day replay produces one file
  per day rather than piling every day into the first day's file;
  re-replaying a day appends to that day's file.
- progress print every 30 minutes of replayed time with running
  per-timeframe counts, and a shutdown summary (`1m / 30s / 15s / 5s`
  bar counts, day files, output folder, and a warning if a Second
  series produced 0 bars — which means the feed had no tick data for
  that period)

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

---

# ADDENDUM 2 — GENUINE 5s / 15s DATA CAPTURED (2026-08-02 → 2026-08-21)

The capture host ran to completion in Strategy Analyzer against
downloaded tick data. **Genuine 5-second and 15-second MNQ bars now
exist in this project for the first time.** Nothing was interpolated.

## What arrived

| series | bars | days | genuineness probe (share closing on :00) |
|---|---|---|---|
| 1m | 20,698 | 18 | — (chart primary) |
| 30s | 41,397 | 18 | 50.0% measured vs 50.0% expected → GENUINE |
| 15s | 82,796 | 18 | 25.0% measured vs 25.0% expected → GENUINE |
| 5s | 248,008 | 18 | 8.3% measured vs 8.3% expected → GENUINE |

A minute-built fake would have scored 100% on all three. Ratios are
exact: 248,008 / 20,698 = 11.98 ≈ 12.

## Aggregation gates

```
5s  -> 15s   matched 82424  exact 82424  mismatch 0   PASS
15s -> 30s   matched 41397  exact 41397  mismatch 0   PASS
30s -> 1m    matched 20697  exact 20695  mismatch 2   PASS (2 quarantined)
15s -> 1m    matched 20697  exact 20695  mismatch 2   PASS (2 quarantined)
5s  -> 1m    matched 20360  exact 20358  mismatch 2   PASS (2 quarantined)
```

The two mismatches are `2026-08-07 16:00` and `2026-08-14 16:00`,
differing by **1 and 2 contracts of volume** — one or two trades
assigned to the far side of a bar boundary in the 1m series but not the
30s series. Diagnosis: 13 of the 15 16:00 minutes in the sample match
exactly, including one Friday, so this is not a session-close rule.

**No tolerance was introduced.** The gate stays exact; those minutes are
QUARANTINED — excluded from the study entirely (36 LTF bars dropped) —
and more than `QUARANTINE_MAX = 10` isolated mismatches, or more than
0.1% of matched minutes, remains a hard FAIL. The 33-mismatch duplicate
defect that this gate caught earlier would still fail today.

## Aggregation-denominator defect found and fixed

The first run reported every arm losing to baseline by ~17 points. That
was wrong. Per-parent EV divided by all 133 canonical parents while only
9 had LTF coverage, so 124 data gaps were scored as the arm declining to
trade. `noFillReason = NO_LTF_BARS_IN_WINDOW` appeared on 2,992 of 3,591
rows. Baseline and arms are now both restricted to covered parents, and
ARM0 (the 1m baseline, which needs no LTF bar) no longer votes on
coverage.

## Result — PIPELINE DEMONSTRATION, NOT A FINDING

Coverage: **9 of 133 canonical parents** (5s), 8 (15s/30s), all IR.
Baseline per-parent EV on those 9 is **−4.67** — a losing stretch.

| arm | tf | trig | perParEV | vs base |
|---|---|---|---|---|
| BASELINE | 5s | 9 | −4.67 | — |
| ARM2_PULLBACK_REEXPAND | 5s | 9 | +17.93 | **+22.60** |
| ARM3_SWEEP_RECLAIM | 5s | 4 | +7.42 | +12.09 |
| ARM5_SECOND_PUSH | 5s | 4 | +7.00 | +11.68 |
| ARM2_PULLBACK_REEXPAND | 30s | 5 | +17.23 | +17.48 |

**These numbers must not be acted on.** n = 9 on a stretch where the
baseline lost money. The same ARM2 rule, measured on all 133 parents
with genuine 30s bars, **lost to baseline by 12.01 points**. A sign flip
between n=133 and n=9 is what noise looks like, not what an edge looks
like. ARM4 and ARM7 became mechanically testable for the first time and
fired 3 and 1 times respectively.

The capture pipeline is proven end to end: NinjaTrader → genuine 5s/15s
bars → probe → aggregation gates → quarantine → per-parent backtest.
What it lacks is sample. 18 replayed days bought 9 parents; the 133
canonical parents span 108 days from 2025-08-19 to 2026-08-19 and need
roughly a year of tick data across five contract months.

---

# ADDENDUM 3 — MERGED CAPTURE 2026-06-02 → 2026-08-21 (70 days)

| series | bars | genuineness probe |
|---|---|---|
| 1m | 79,513 | — |
| 30s | 159,044 | 50.0% on :00 vs 50.0% expected → GENUINE |
| 15s | 318,072 | 25.0% vs 25.0% → GENUINE |
| 5s | 952,811 | 8.3% vs 8.3% → GENUINE |

## Data quality — the strongest validation in this project

**Captured 1m vs the frozen canonical history: ~95,000 of ~95,000
minutes match EXACTLY, across all 70 days**, including the pre-roll June
period. There is no contract-roll artifact: the MNQ 09-26 tick series
NinjaTrader served for early June agrees with the canonical series bar
for bar. (2026-08-20/21 show no overlap — they are past
`FREEZE_DATA_END = 2026-08-19`, as intended.)

```
5s  -> 15s   matched 316800  exact 316800  mismatch  0   PASS
15s -> 30s   matched 159026  exact 159026  mismatch  0   PASS
30s -> 1m    matched  79510  exact  79500  mismatch 10   PASS (10 quarantined, cap 39)
15s -> 1m    matched  79494  exact  79484  mismatch 10   PASS (10 quarantined, cap 39)
5s  -> 1m    matched  78540  exact  78530  mismatch 10   PASS (10 quarantined, cap 39)
```

## Three engine defects the larger capture exposed

**1. No dedupe on re-captured days.** The capture host appends, so
re-running an overlapping range wrote 2026-08-02 twice (13,669 lines vs
6,833). The loader concatenated both copies; the aggregation gate would
have *skipped* the doubled groups rather than failed on them — a silent
hole. Now first-wins on `(timeframe, timestamp)`, with any *conflicting*
duplicate aborting the run outright. Result: **6,474 duplicates dropped,
0 conflicting**, and the deduped totals match NinjaTrader's own counters
exactly (159,044 / 318,072 / 952,811).

**2. Absolute quarantine cap did not scale.** `QUARANTINE_MAX = 10`
would fail a clean capture purely for being large. Now rate-based:
`max(10, 0.05% of matched)`. A clean capture runs ~0.013%; the
33-mismatch duplicate defect this gate caught earlier is 0.19% and still
fails.

**3. Bar-level quarantine was not enough.** Correcting the earlier
report: the 10 mismatches are **not** all the benign 1–2 contract
boundary artifact seen in ADDENDUM 2. Several are material source
disagreements on fast, high-volume minutes — `2026-06-09 11:37` differs
by **7,087 contracts**, `2026-07-17 12:22` by 12 points of high. The
likely cause is that the 1m series is built from the provider's MINUTE
records while the Second series are built from TICK records, and the two
disagree on violent minutes. Where such a minute falls inside a parent's
60-minute window, the arm and the baseline would be scored on different
price paths, so **the whole parent is now excluded**, not just two bars.
One parent (`OFH13-20260717121200-+1`) was dropped on this rule.

## Result — still NOT A FINDING

Coverage **28 of 132** parents (up from 9). Every parent day inside the
captured range has a capture file — coverage of that window is complete;
the limit is simply that only 29 canonical parents fall in 70 days.

Baseline per-parent EV on the covered set is positive (+6.26 to +9.54
depending on timeframe) and **most arms beat it** — the opposite sign to
the 133-parent genuine-30s study. Day-clustered sign-flip test over all
24 arm × timeframe cells:

| arm | tf | n | mean Δ | p | BH q |
|---|---|---|---|---|---|
| ARM2_PULLBACK_REEXPAND | 30s | 23 | +11.38 | 0.102 | **1.000** |
| ARM3_SWEEP_RECLAIM | 5s | 28 | +9.76 | 0.406 | 1.000 |
| ARM2_PULLBACK_REEXPAND | 5s | 28 | +9.56 | 0.378 | 1.000 |
| ARM3_SWEEP_RECLAIM | 15s | 24 | +8.96 | 0.348 | 1.000 |
| ARM6_V_RECOVERY | 15s | 24 | +8.22 | 0.374 | 1.000 |

**Nothing survives. Best uncorrected p = 0.102; every BH q = 1.000.**
The sign flip between the n=133 30s study and this n=28 window is what
noise looks like across 24 simultaneous comparisons, not an edge. No arm
is promoted. OFH13_PROSPECTIVE_V1 remains untouched and unchallenged.

To reach the full 133 parents the capture needs roughly a year of tick
data across five contract months (MNQ 09-25, 12-25, 03-26, 06-26,
09-26). 70 days bought 29 parents; the rate is ~0.41 parents per
captured day.
