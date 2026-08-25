# ES-NQ-DATA-V1 — CROSS-MARKET DATA AUDIT

# **ES-NQ-DATA-V1 NOT READY — reason: INSUFFICIENT ES COVERAGE**

> **Superseded 2026-08-26 by the ES pilot.** The original verdict was
> NO ES DATA. Genuine ES history has now arrived and is **certified
> clean** — the pilot passed every technical gate. The blocker is no
> longer quality; it is **span**: 42 session days against 7.1 years of
> NQ (**1.86%** of the history). See ADDENDUM at the end.

No hypothesis was run. Nothing was fabricated, substituted, or
forward-filled. What *could* be built without ES was built and verified:
the NQ side is fully audited, and the synchronization loader is written
and self-tested so that synchronization is a proven step when genuine ES
history arrives.

---

# 1. NQ history audited (source of truth)

**Path:** `scratchpad/rvmr_1m/rvmr_1m_{2019..2026}.csv` — the RVMR-certified
extract of the Phase-0-audited V3 asset (`scratchpad/run151629`, 86 monthly
files).

| property | value |
|---|---|
| bars | **2,503,622** |
| span | **2019-07-04 18:25 → 2026-08-17 15:16 ET** |
| interval | 1 minute |
| OHLC / volume | present, complete |
| unique timestamps | 2,503,622 — **0 duplicates**, strictly monotonic |
| OHLC validity | **0 invalid** (all `low ≤ open,close ≤ high`) |
| volume | **0 negative, 0 zero-volume** bars |
| timezone | US/Eastern, DST-consistent (sole anomaly 2022-11-06, classified in Phase 0) |
| session | ETH + RTH; maintenance break 17:00–18:00 ET |
| **bar stamping** | **CLOSE-STAMPED — proven, not inferred (§2)** |
| contract construction | **continuous, no roll discontinuity (§3)** |
| instrument | MNQ (micro), continuous |
| known exclusions | 312 unexplained gaps (0.0125% of transitions, median 9 min, all classified in Phase 0 — COVID limit halts, DST changeover, holiday early closes) |
| known quarantines | `relVolume` and `posInSessRange` quarantined as undefined (Phase 0); neither is used here |

## 2. Bar-stamp proof (empirical, per directive — not from naming)

MNQ's maintenance break is 17:00–18:00 ET. Stamp census over the full
history:

| stamp | days present |
|---|---|
| 16:59 | 1,765 |
| **17:00** | **1,769** |
| 17:01 | **0** |
| 17:59 | **0** |
| 18:00 | **0** |
| **18:01** | **1,831** |

A close-stamped bar covering `[16:59, 17:00)` stamps **17:00**; the first
bar after the reopen covers `[18:00, 18:01)` and stamps **18:01**. An
open-stamped series would instead show 16:59 as the last stamp and 18:00
as the first. **Conclusion: CLOSE-STAMPED**, confirming independently
what the capture schema's `f_barCloseEt` field name asserts.

*Convention note recorded for cross-market work:* the frozen
`V4SessionMap` treats stamps 09:30–16:00 as RTH, which under close
stamping covers `[09:29, 16:00)`. This is the established convention and
the ES side must match it exactly rather than being "corrected".

## 3. Roll audit (NQ)

Overnight reopen gap `|open(18:01) − close(17:00)|`, 1,761 transitions,
roll windows = 2nd Thursday of Mar/Jun/Sep/Dec ± 2 days:

| set | n | median | p90 | max |
|---|---|---|---|---|
| roll-window days | 81 | **4.50 pt** (0.024%) | 22.50 | 115.50 |
| non-roll days | 1,680 | **3.75 pt** (0.022%) | 29.25 | 360.00 |

Ratio of medians **1.20×**, and non-roll p90 (29.25) *exceeds* roll p90
(22.50). A stitched **unadjusted** series would show a systematic
roll-day jump of the NQ calendar spread (tens of points); none is
present. **No roll discontinuity in the NQ series.** The largest gaps are
Sunday reopens, not rolls.

---

# 2. ES history found: **NONE**

The directive requires the search be complete before declaring absence.
It now is:

| search | result |
|---|---|
| filenames (ES / MES / SPX / SP500 / emini / e-mini) across all 46 data directories | **0 matches** |
| **inside all 135 uploaded archives** (zip member listings) | **0 matches** |
| **exhaustive price sweep — all 882 CSVs, 545 with a price column** | **0 files with any close below 8,000.** ES trades ~2,000–7,000; every file in this project sits in **10,948 – 31,052** |
| **every distinct symbol/instrument/contract value in the project** | exactly two: **`MNQ`** (318,147 rows) and **`MNQ SEP26`** (70,671 rows) |
| repository source (`src/`, `analysis/`, `docs/`) | no ES instrument reference |

**Classification: INSUFFICIENT DATA — absent, not limited.**

Nothing was substituted (no SPY, SPX, QQQ, YM, RTY), nothing synthesized,
no order flow inferred from OHLCV.

# 3–4. Target range and actual overlap

| | |
|---|---|
| **TARGET START** | **2019-07-04** |
| **TARGET END** | **2026-08-17** (extend to present at capture time) |
| eligible NQ timestamps | 2,503,622 |
| eligible ES timestamps | **0** |
| **matched** | **0** — match 0.00% |

Steps 5–15 of the directive (contract map validation, ES roll audit, ES
session audit, ES duplicate audit, synchronization table, coverage
report, correlation sanity, relative-strength availability) are **not
performable**: they are two-market procedures and one market does not
exist. The machinery for all of them is built and verified below.

---

# 5. Synchronization loader — built and SELF-TESTED

`analysis/xmarket/es_nq_data_spec.py` (`ES-NQ-DATA-V1`, loader 1.0,
contract map `CMAP-1`).

Emits per matched row: `timestampEt, sessionDate, nq/es OHLCV,
nqAvailableTime, esAvailableTime, crossMarketAvailableTime, nqContract,
esContract, qualityFlags`, plus causal prep fields (`atr`, `z1/z3/z5`,
`relStrength1/3/5`). **No trading labels, no thresholds, no signals** —
the XMARKET normalization is frozen in its own pre-registration, not
here.

Guarantees, each verified by self-test against a controlled in-memory
fixture derived from real NQ bars (never written to any data directory,
never used as a market):

| # | invariant | result |
|---|---|---|
| 1 | identical copy → all MATCHED, zero *_ONLY | **PASS** |
| 2 | ES shifted +1 min → **no fuzzy join** (132 NQ_ONLY / 132 ES_ONLY) | **PASS** |
| 3 | ES with holes → NQ_ONLY rises, rows drop 6,000→4,000, **no forward fill** | **PASS** |
| 4 | roll-window quarantine fires | PASS (no roll window in the test slice) |
| 5 | identical duplicate deduped; **conflicting duplicate FAILS CLOSED** | **PASS** |
| 6 | `crossMarketAvailableTime = max(nq, es)` on every emitted row | **PASS** |

**Causal design:** a close-stamped bar is available exactly at its stamp
and never earlier; a cross-market field exists only when **both** bars
are complete. Roll windows are quarantined for **both** markets, so a
roll in either can never manufacture divergence, lead/lag, or false
confirmation.

# 6. Integrity / versioning

Every artifact carries `SPEC_VERSION`, `LOADER_VERSION`,
`CONTRACT_MAP_VERSION`, source-file hashes (`sha16`), row counts, and the
generation commit. NQ source hash set is recorded at build time.

---

# What is needed — ES acquisition plan

**Instrument: ES** (E-mini S&P 500), not MES. Both track identically in
price; ES has deeper liquidity and longer clean history in NinjaTrader.
MES is acceptable and would also cover the full window (it launched
2019-05, before the NQ data starts) — but **do not mix ES and MES across
years.** Pick one family for the entire period.

**Resolution: 1-minute OHLCV only.** No tick, no 5s/15s/30s, no order
flow. Coverage beats resolution in this phase, and sub-minute
synchronization is a separate later study only if XMARKET-V1 survives.
This keeps the download small.

**Session template:** the same one that produced the NQ series (ETH,
CME US Index Futures), so the 17:00–18:00 break and the close-stamp
convention match.

### Contract map — 29 quarterly contracts cover the target range

`ES 09-19, 12-19` · `03-20, 06-20, 09-20, 12-20` · `03-21 … 12-21` ·
`03-22 … 12-22` · `03-23 … 12-23` · `03-24 … 12-24` · `03-25 … 12-25` ·
`03-26, 06-26, 09-26`

**You should not need to download these individually.** The NQ series
shows *no roll discontinuity*, which means it was produced as a
continuous/merged series — so ES should be produced the same way, with
NinjaTrader handling contracts via the instrument's merge policy. The
contract map above exists so the roll audit can be run on the result,
not as a shopping list.

### Operational checklist

**Do a one-month pilot first — do not start a seven-year download.**

1. **Tools → Historical Data → Download** — Instrument `ES`, Interval
   **Minute**, Value **1**, range `06/01/2026 → 08/17/2026`.
   *(Do not tick Tick. Do not tick Day.)*
2. **New → Strategy Analyzer → Backtest**, ES **1 Minute**, same range,
   `Max bars look back = Infinite`, session template as above.
3. Run a 1-minute capture and send me the folder.

**Then I validate the pilot against NQ** — stamp convention (the 17:00 /
18:01 signature), session boundaries, gap structure, duplicate
behaviour, and same-minute match rate — and confirm the full-range
download will synchronize *before* you spend hours on it. If the pilot
mismatches, we fix the export settings on one month instead of seven
years.

4. Only after the pilot passes: repeat step 1 with
   `07/04/2019 → present` and step 2 over the same range.

**One thing I need from you:** my existing `MnqV41LtfCaptureHost` also
adds 30s/15s/5s series, which would force an ES *tick* download. Say the
word and I'll strip it to a 1-minute-only ES variant — small, quick, no
tick data required. I have not built it pre-emptively because the ES/MES
choice and the capture-vs-export route are genuinely yours to make.

**Known risk to flag now:** whether your data provider serves ES 1-minute
history back to 2019 is a provider question, not a NinjaTrader one. The
pilot will not reveal that — so when you run step 4, check the **Loaded**
panel's Begin date for ES before assuming full coverage. If the provider
only goes back a few years, that shortens the overlap and we report the
reduced coverage honestly rather than padding it.

---

# Readiness gate

| # | condition | result |
|---|---|---|
| 1 | NQ source audited | **PASS** |
| 2 | ES source audited | **PASS** (audited; it is empty) |
| 3 | sufficient overlap | **FAIL — 0 matched rows** |
| 4 | contract mapping documented | PASS (NQ audited; ES map specified) |
| 5 | roll artifacts controlled | PASS on NQ; quarantine built and tested |
| 6 | timestamp convention established | **PASS — CLOSE-STAMPED, proven** |
| 7 | session alignment established | PASS on NQ; ES pending |
| 8 | missing data not fabricated | **PASS** |
| 9 | synchronized dataset deterministic | PASS (loader self-tested) |
| 10 | causal available-time fields correct | **PASS** |
| 11 | correlation sanity checks | not performable (needs two markets) |
| 12 | source hashes / versioning | **PASS** |

**Ten of twelve pass. The two that fail both fail for one reason: there
is no ES data.**

# **ES-NQ-DATA-V1 NOT READY — NO ES DATA**

**Exact minimal action:** download ES 1-Minute history for
`06/01/2026 → 08/17/2026`, export/capture it, and send the folder. That
single pilot month is all that is needed to unblock validation; the
seven-year pull follows once the pilot's stamps and sessions are proven
to match NQ.

**XMARKET-V1 remains not started.** OFH13_PROSPECTIVE_V1, RVMR-V1 and
all frozen infrastructure are untouched.
**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**

---

# ADDENDUM — ES PILOT RECEIVED AND CERTIFIED (2026-06-30 → 2026-08-17)

**Genuine ES history now exists in this project for the first time.**
Instrument `ES`, contract `ES SEP26`, 43 day files, closes **7,324.50 –
7,837.75** — unambiguously ES, against NQ's ~30–31k in the same era.

## Quality — flawless

| check | ES pilot |
|---|---|
| 1m bars | **46,612** over 42 session days |
| duplicate rows | **0** |
| **conflicting** duplicates | **0** |
| OHLC invalid | **0** |
| negative / zero volume | **0 / 0** |
| span | 2026-06-30 18:02 → 2026-08-17 16:59 ET |

## Bar-stamp proof on ES — identical convention to NQ

Same maintenance-break test used on NQ:

| stamp | ES days | NQ days |
|---|---|---|
| 17:00 | **32** | 1,769 |
| 17:01 | 0 | 0 |
| 17:59 | 0 | 0 |
| 18:00 | 0 | 0 |
| 18:01 | **33** | 1,831 |

**ES is CLOSE-STAMPED, exactly like NQ.** No timestamp transformation is
required — the two series are directly comparable as delivered. This was
the single largest risk to the whole cross-market programme and it is
now retired.

## Synchronization — within the pilot window

| | |
|---|---|
| NQ bars in window | 46,575 |
| ES bars in window | 46,612 |
| **MATCHED** | **46,509** |
| match % of NQ in window | **99.86%** |
| match % of ES | **99.78%** |
| ES_ONLY | 103 — **all after 2026-08-17 15:16**, where the NQ research history simply ends |
| NQ_ONLY | 66 — scattered minutes ES did not trade; correctly left absent, never filled |
| ROLL_QUARANTINED | 0 (no quarterly roll window inside the pilot span) |

## Descriptive correlation sanity — PASS

| horizon | corr |
|---|---|
| normalized 1m return | **+0.8672** (n 46,455) |
| normalized 3m return | **+0.8835** |
| normalized 5m return | **+0.8888** |
| daily return | **+0.8783** (42 days) |

Strongly positive at every horizon, no sign flip, rising with horizon
exactly as two indices of the same economy should. **No synchronization
failure.** (Descriptive only — not an edge test, and no signal was
derived from it.)

## Loader defect found by the real pilot — fixed

The LTF capture schema packs **1m / 30s / 15s / 5s rows into one file
under identical column names**. The loader read them all as bars, so a
5-second row landing on a minute boundary *conflicted* with the 1-minute
bar and the loader **failed closed on perfectly good data**. A
`timeframe == '1m'` filter now applies wherever that column exists.
Fail-closed behaved correctly; the bug was that it was reading rows it
should never have considered. Self-test re-run: **PASS**.

## Coverage — the one thing still missing

| | |
|---|---|
| NQ research history | 2019-07-04 → 2026-08-17, **2,503,622 bars, ~7.1 years** |
| ES overlap | 2026-06-30 → 2026-08-17, **46,509 matched bars, 42 session days** |
| **overlap as a fraction of NQ history** | **1.86%** |

**Classification: LIMITED.** Per the directive's own standard —
"do not declare XMARKET data ready merely because *one year* overlaps" —
42 session days does not qualify, and no pass threshold is invented
after the fact. Gate 3 (*sufficient overlap*) fails; **11 of 12 gates
now pass.**

## What the pilot achieved

Everything it was designed to. Stamp convention, session alignment,
duplicate behaviour, OHLC validity, synchronization mechanics and
correlation sanity are all now **proven on real data** rather than
assumed. The full-history download is de-risked: we know it will
synchronize.

## Remaining action — the full pull, 1-minute only

The pilot captured 30s/15s/5s as well, which means it required an ES
**tick** download and produced 94 MB for seven weeks. At that rate seven
years is roughly 5 GB, and provider tick history rarely reaches 2019.

**`src/V41Bar1mCaptureHost.cs` (new, compile-verified) removes that
blocker:** it adds **no** secondary series, so it runs on **Minute data
alone** — no tick download at any point. Its output schema is byte-
identical to the LTF files, so the loader reads it unchanged.

1. **Tools → Historical Data → Download** — Instrument `ES`, Interval
   **Minute**, Value **1**, range `07/04/2019 → present`. **Do not tick
   Tick.**
2. **Check the Loaded panel's Begin date for ES before running.** How
   far back the provider actually serves is a provider question; if it
   stops at, say, 2022, we report the reduced overlap honestly.
3. **Strategy Analyzer → Backtest**, ES **1 Minute**, same range,
   `Max bars look back = Infinite`, strategy `V41Bar1mCaptureHost`,
   Output folder `C:\V41`, File tag `ES`.
4. Send the `V41_bar1m` folder. Then re-run
   `es_nq_data_spec.py build --es <folder>`; every gate above re-runs
   automatically on the longer span.

**Verdict: ES-NQ-DATA-V1 NOT READY — INSUFFICIENT ES COVERAGE.**
The exact minimal action is step 1–4 above. XMARKET-V1 remains not
started; its pre-registration remains frozen at `36aaa28`, written
before any ES bar existed.
