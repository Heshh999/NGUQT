# NT8 PROSPECTIVE RESEARCH ENGINE — frozen candidates in NinjaTrader 8

**Status: PARITY PASS — READY FOR PLAYBACK.** Both halves are now
evidenced: off-platform logic parity (§10–§12) **and** the in-platform
HISTORICAL_PARITY run on a real NinjaTrader Volumetric feed (§10a),
which reproduced the research capture with zero feature mismatches.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. The host submits no
orders in this version; every order path is DRY-RUN. It must NEVER be
labeled ready for live trading.**

Final question — *did the NinjaTrader implementation reproduce the
canonical frozen Python candidates without changing their rules?* —
**YES.** The exact C# classes the NT8 host runs
(`V41FrozenCandidateEngine`, `V41Management`) reproduced the canonical
Python event-for-event and field-for-field off-platform (§10–§12), and
NinjaTrader 8 itself — reading its own Volumetric bars, on the user's
machine, over 356,874 bars — then emitted the identical event stream
(§10a). Streaming behaviour under a live-style feed remains to be shown;
that is the Playback gate.

---

## 1. Source audit — what was read, what wins

Read before any code was written, per "THE ACTUAL FROZEN CODE WINS":

| frozen source | role |
|---|---|
| `analysis/v41/cand_spec.py` | canonical candidate definitions (hash-locked) |
| `analysis/v41/prospective.py` | canonical management + scorer (hash-locked) |
| `analysis/v41/FROZEN_HASHES.txt` | hash registry |
| `docs/PROSPECTIVE_REGISTRY.md` | frozen versions, D-list, failure conditions |
| `analysis/v41/ofh6_spec.py`, `ofht_spec.py` | historical originals (cross-check only) |

Where a docstring/header disagreed with the executed code, the executed
code was ported and the disagreement stays in the D-table (§4). No rule
was re-derived, re-tuned, or "improved".

## 2. Frozen rule table (as implemented, constants in `V41Frozen`)

| rule | frozen value |
|---|---|
| OFH6 signal | 15-bar consecutive-minute sum of `ofBarDelta`; abs ≥ **3380**; dir = sign |
| signal gate | RTH, `minutesFromRthOpen ≥ 30`, `minutesToRthClose ≥ 90`, ATR valid, fwd-90 consecutive |
| cooldown | 30 min between OFH6 signals (frozen tmin arithmetic — see D8) |
| signal life | 30 min (G1 window, FVG window, ctx life) |
| horizon | 60 min management window |
| cost | 0.87 pt round trip; MNQ $2/pt/contract |
| OFH13/OFH14 | first FVG / first IFVG after signal, first touch of the zone, mitigation per `_mitigate` (D3) |
| G3 | 20-min delay re-entry (D6: R = 1.0 × ATR entry bar) |
| G4 | 0.5-ATR trend attack, 3-bar window, adverse checked before favorable (D4: market at close) |
| G1 | limit at signal close − dir × 0.5 × ATR(signal bar), 30-min validity, every window bar entry_ok (D5, D7) |
| event id | `CAND-yyyyMMddHHmmss-±1` — identical in Python and C# |

## 3. Management (verbatim from the registry, verified against `prospective.py`)

| version | arm | stop | target | time exit |
|---|---|---|---|---|
| OFH13_PROSPECTIVE_V1 (**PRIMARY**) | A | 1.5 × ATR | none | 60 min |
| OFH14_PROSPECTIVE_V1 | A | STRUCT (zone-derived) | none | 60 min |
| G4 / G3 | — | SIGNAL-ONLY (no managed arm) | — | — |
| G1 | B only | `G1_ADOPTED = False`; diagnostic B-arm on OFH13/G4/OFH14 parents, logged separately | | |

No trailing stop, no break-even move, no partials, no EMA exits — none
exist in the frozen registry, so none exist in the engine.

## 4. Spec ≠ code discrepancies — preserved, NOT fixed

D1–D7 are inherited from `docs/PROSPECTIVE_REGISTRY.md` §2 and are all
replicated verbatim in C#. This phase added one:

| id | discrepancy |
|---|---|
| **D8** | The frozen `tmin` index (`cand_spec.py:130`) counts every month as 44,640 min (31 days) but a year as 527,040 min (366 days) ⇒ **non-monotonic across the year boundary**: Jan 1–5 index *below* late December (Jan 6 00:00 == Dec 31 00:00). The OFH6 cooldown check `tmin − last < 30` therefore stays true after a late-December signal deep into early January, suppressing signals. Verified empirically: canonical signal 2025-12-30 10:59 (tmin 1,067,835,539) suppresses would-be signals 2026-01-02 10:00/10:41/11:12/11:52 and 2026-01-05 10:45 (diffs −4379…−14 min); Python's first post-boundary signal is 2026-01-05 13:17 (diff +138). The first C# build used true minutes-since-epoch and fired **exactly those 5 extra signals** (+15 cascaded events) — the parity harness caught it. Fix: `V41InBar.TminOf` now replicates the frozen arithmetic verbatim and documents this. |

Changing any D would create a NEW candidate version that cannot inherit
the validation evidence. The engine replicates them all.

## 5. Prospective start-date audit

`FREEZE_DATA_END = '2026-08-19'` (frozen in `prospective.py`): a day is
prospective iff `day > 2026-08-19`. The alternative 2026-09-01 cutoff
was reconciled in the previous phase: the frozen cutoff is kept — it is
already strictly clean (no frozen-era data after it), and 2026-09-01
would only be a stricter subset. The NT8 host and recorder use the same
`day > 2026-08-19` test (`V41Frozen.FreezeDataEnd`); it was **not**
silently changed.

## 6. Architecture — reuse, no forks

New code is exactly two files; everything else is the existing V4.1
infrastructure the user already runs:

| piece | file | new? |
|---|---|---|
| pure frozen engine + management | `src/V41FrozenCandidateEngine.cs` | NEW |
| NT8 strategy host + recorder | `src/MnqV41ProspectiveResearchHost.cs` | NEW |
| Volumetric per-price reader | `src/MnqV4OrderFlowResearchHost.cs` (`V4VolumetricReader`) | reused |
| ATR(20) (Wilder, V4.1 semantics) | `src/V4StructureEngine.cs` (`V4Atr`) | reused |
| RTH session map | `src/V4Shared.cs` (`V4SessionMap`) | reused |
| off-platform parity driver | `tests/ProspectiveParityDriver.cs` | NEW (not installed in NT8) |
| parity comparator | `analysis/v41/compare_nt8_parity.py` | NEW (research side) |

The engine is a plain class with no NinjaTrader references, so the SAME
compiled logic runs in the off-platform driver and inside NT8. Each
candidate keeps independent state (pending lists `pG1/pG3/pG4/pFvg`,
per-candidate cooldowns) — nothing is shared or merged. NO
super-strategy exists.

`BarDelta` = Σ(ask volume) − Σ(bid volume) across the Volumetric bar's
price levels, identical to the V4.1 feature `f_ofBarDelta` the frozen
Python was trained on. `Calculate.OnBarClose`;
`IsInstantiatedOnEachOptimizationIteration = false`; ghost-instance
guard via `dataWasLoaded`.

## 7. Causality audit

Per-bar order inside `V41FrozenCandidateEngine.OnBar` (documented at the
method):

1. resolve fwd-eligibility of OLD events/signals whose +60/+90 windows
   just completed;
2. detect a NEW OFH6 signal on this bar (so a same-bar opposite signal
   voids fills — matching the batch semantics);
3. advance pendings created on EARLIER bars (consecutive-minute
   `NextTmin` chains; a gap kills the pending exactly as the Python
   consec test does);
4. spawn pendings for the new signal; detect a G4 attack on this bar.

Nothing reads a future bar. The one thing the frozen Python does that a
causal engine cannot — filtering populations on 60/90 min of FUTURE
bar-existence (the Q-FWD quirk) — is handled by *emit now, finalize at
+60/+90*: events/signals carry `FwdResolved/Eligible` flags and the
recorder reports divergence counters. On this history: 3 divergent
signals, 7 divergent events — every one adjacent to a data gap or the
capture end, none anywhere else, exactly as documented.

## 8. Warm-up audit

Longest lookback wins: ATR(20) = 20 bars; dsum15 = 15; disp5 = 5;
FVG pattern = 3 ⇒ **20 one-minute bars** of genuine Volumetric history
before the first signal can qualify. The host prints this in the startup
diagnostic and emits nothing while ATR is NaN. Additionally the OFH6
gate itself (`minutesFromRthOpen ≥ 30`) means no signal can occur in the
first 30 RTH minutes, which dominates the 20-bar warm-up on every
session after the first.

## 9. Startup diagnostics (printed AND written to `V41_PROSPECTIVE_DIAG_*.txt`)

Instrument, "SUBMITS NO ORDERS" banner, Volumetric-read check (bid/ask
available), ET time zone resolution, mode, orders flag, engine version,
all four frozen hashes, prospective cutoff, candidate/management table,
warm-up statement, and a PASS / **HARD FAIL** verdict. If the primary
series is not Volumetric (bid/ask volumes unreadable), the host prints
`HARD FAIL: order-flow candidates cannot run on OHLCV proxies`, sets
`aborted`, and processes nothing further. There is no OHLCV fallback.

## 10. Parity harness + results (off-platform, full history)

`tests/ProspectiveParityDriver.cs` replicates `cand_spec.load_merged()`
exactly (new capture ≤ 2025-11-01, old capture > 2025-11-01, unparsable
OHLC/ATR rows dropped, ordinal sort by et, first-wins dedupe), feeds the
engine, and exports `nt8_signals.csv`, `nt8_events.csv`,
`nt8_trades.csv`. `analysis/v41/compare_nt8_parity.py` diffs those
against the canonical Python with zero fuzzy matching.

Run of record (355,455 bars, 2025-08-18 18:21 → 2026-08-19 16:59):

| stream | python | nt8 | MATCHED | MISSING | EXTRA | FIELD_MISMATCH |
|---|---|---|---|---|---|---|
| OFH6 signals | 952 | 952 eligible (955 raw) | **952** | 0 | 0 | — |
| OFH13 (**PRIMARY**) | 133 | 133 | **133** | 0 | 0 | 0 |
| OFH14 | 462 | 462 | **462** | 0 | 0 | 0 |
| G4 | 218 | 218 | **218** | 0 | 0 | 0 |
| G3 | 477 | 477 | **477** | 0 | 0 | 0 |
| G1 | 845 | 846 | **845** | 0 | 1 | 0 |

The single G1 EXTRA (`G1-20260320100400--1`) is individually attributed:
its parent signal sits before a data gap that breaks the fwd-90 window
(`PARENT_FWD90_GAP` + `PARENT_SIGNAL_GAP_DIVERGENT`) — the documented
Q-FWD population quirk, impossible for a causal engine to pre-know and
flagged by the engine itself via `ParentSignalDivergent`. Membership and
direction tolerance is otherwise **zero** and met. Fields compared at
1e-9 (entryPx, R, atr, zone lo/hi/mid, depth, flow): 0 mismatches.

**PARITY VERDICT: PASS** (`compare_nt8_parity.py`, report archived in the
scratch `parity_out/parity_report.txt`).

## 10a. IN-PLATFORM parity run (NinjaTrader 8, real Volumetric feed)

Run by the user in NT8, `Mode = HISTORICAL_PARITY`, MNQ Volumetric
1-minute, engine `V41-PROSPECTIVE-ENGINE-1.0`. Startup diagnostic
`PASS` (volumetric read TRUE, bid/ask TRUE, **0 no-level bars** across
356,874 bars), window 2025-08-18 18:02 → 2026-08-20 16:59 — one session
and 19 minutes wider than the research capture.

Compared with `analysis/v41/compare_nt8_host.py` (host export schema),
scoped to the overlapping capture window:

**Diff A — NT8 platform run vs canonical frozen Python**

| candidate | python | nt8 | MATCHED | MISSING | EXTRA | FIELD_BAD |
|---|---|---|---|---|---|---|
| OFH13 (**PRIMARY**) | 133 | 133 | **133** | 0 | 0 | 0 |
| OFH14 | 462 | 462 | **462** | 0 | 0 | 0 |
| G4 | 218 | 218 | **218** | 0 | 0 | 0 |
| G3 | 477 | 477 | **477** | 0 | 0 | 0 |
| G1 | 845 | 846 | **845** | 0 | 1* | 0 |

*the same single `PARENT_FWD90_GAP` event as the off-platform run.
Management: **1,190 rows, 0 mismatches**. Four further events fall on
2026-08-20, outside the capture window — expected, NT8 had a newer bar.

**Diff B — NT8 platform run vs off-platform driver** (same engine, one
fed by NT8's Volumetric reconstruction, one by the capture CSVs):

```
emitted events: driver 2143   nt8 (in-window) 2143   shared 2143
driver-only 0    nt8-only 0    feature mismatches 0
```

Entry prices and ATR agree to the export precision on all 2,143 events.
NinjaTrader's own Volumetric feed reproduces the research capture's
features exactly; no feed-side divergence exists to explain away.

### Recorder defect found and fixed by this run

The host writes each event row at **emit** time, so `fwdEligible` was
`PENDING` on all 2,147 rows and `parentSignalDivergent` `FALSE` on all
of them — both resolve 60/90 bars later. Harmless for the parity diff
(eligibility was recomputed), but it would have shipped an unusable
population column into the prospective ledger. Fixed in engine
**1.0.1**: `V41Event.SigEt` provenance field plus a
`V41_PARITY_RESOLUTION_MNQ.csv` / `V41_PROSPECTIVE_RESOLUTION_*.csv`
written at run end carrying the finalized flags keyed by `eventId`.
1.0.1 is a **recording-only** change — no rule, threshold, gate or
management behaviour differs — and the full off-platform parity gate was
re-run after it with byte-identical results.

**Verified on-platform.** The user re-ran HISTORICAL_PARITY on 1.0.1
(diagnostic PASS, same 356,874 bars). Every event and trade row is
identical to the 1.0 run apart from the `engineVersion` stamp, and the
comparator returns the same PASS with the resolution file supplying
eligibility instead of the recompute fallback. The resolution file
carries 2,147 rows: 2,140 `fwdEligible=TRUE`, **7 FALSE** — exactly the
audit's Q-FWD divergent-event count — and eligible-by-candidate
(G1 847, G3 477, OFH14 463, G4 220, OFH13 133) matches the audit
line-for-line.

`sigEt` is blank on all 221 G4 rows, and that is **correct**: G4
qualifies against the signal *context* (`CtxOkAt` — any same-direction
signal live within 30 min), not against one identified parent, so no
single originating signal exists to name. A blank `sigEt` on G4 is
therefore expected and must not be read as a missing value; a
consequence is that G4 rows always report
`parentSignalDivergent=FALSE`.

## 11. Management parity

For every eligible OFH13/OFH14 event, the driver scored the A-arm
(`V41Management.Score` vs `prospective.score_one`) and the diagnostic
G1 B-arm (`V41Management.G1Fill` vs `prospective.g1_fill`), including
stop placement, intrabar stop fills at the stop price, TIME exits at
close of entry+60, MFE/MAE, held minutes and exit reasons:
**1,190 rows compared, 0 mismatches** (net/exitPx/held at 1e-6;
NO_FILL/fill-price agreement at 1e-9).

## 12. Manual spot check

`docs/NT8_PARITY_SPOT_CHECK.txt` — 30 events stratified across all five
candidates × direction × month, every exported field printed side by
side plus the full managed A-arm outcome where applicable:
**PASS, 0 mismatched fields.**

## 13. Hash / version audit

`V41Frozen` carries `EngineVersion = "V41-PROSPECTIVE-ENGINE-1.0.1"` and
the four frozen hashes (`cand_spec 9bea8f1cafc2b6ea`,
`ofh6_spec e8145b7c493029de`, `ofht_spec 272d7bca6402b6d2`,
`ofht_cache 376ce829086b5224`), all printed at startup and stamped into
every event/trade row. On the research side `prospective.py` still
aborts if any frozen file drifts. Any change to
`V41FrozenCandidateEngine.cs` rules requires a version bump and re-runs
the parity gate from scratch.

## 14. Prospective output (NT8 records, Python scores)

In `Mode = PROSPECTIVE_LOG`, for days strictly after 2026-08-19 the host
writes monthly files under the output folder:

- `V41_PROSPECTIVE_EVENTS_YYYY-MM.csv` — schema: `candidateId, version,
  eventId, timestampET, direction, entryTime, entryPrice, atr,
  stopPrice, targetPrice, timeExitMin, parentEt, fvgHigh, fvgLow,
  fvgMid, depth, flow, reasonQualified, fwdEligible,
  parentSignalDivergent, engineVersion, candSpecHash, ofh6Hash`
- `V41_PROSPECTIVE_TRADES_YYYY-MM.csv` — schema: `candidateId, version,
  eventId, arm, timestampET, direction, entryPrice, stopPts, exitReason,
  exitPrice, heldMin, netPts, netUsd, R, mfe, mae, ratio, ff05, ff1,
  ff2, fillAssumption, noFillReason, month, isoWeek, engineVersion`
- `V41_PROSPECTIVE_RESOLUTION_*.csv` — `eventId, candidateId,
  timestampET, sigEt, fwdEligible, parentSignalDivergent, engineVersion`.
  Written at run end. **This is the column the population filter joins
  on** — the event rows themselves say `PENDING` because they are written
  the moment the event fires (see §10a).
- `V41_PROSPECTIVE_DIAG_*.txt` / `V41_PROSPECTIVE_AUDIT_*.txt` —
  startup diagnostic, bar counts, first/last ET, no-levels bars, Q-FWD
  divergence counters.

These rows are the raw material for the frozen Python prospective scorer
(`analysis/v41/prospective.py`), which owns the ledger
(`docs/prospective_ledger.csv`), the pre-declared failure conditions and
the 20/50/100-trade checkpoints. **NT8 records; Python scores.** The
NT8 side never computes verdicts.

## 15. Beginner handoff — exact steps

### A. Install (once)

1. Close NinjaTrader 8.
2. Copy these two files from the repo's `src/` folder into
   `Documents\NinjaTrader 8\bin\Custom\Strategies\`:
   - `V41FrozenCandidateEngine.cs`
   - `MnqV41ProspectiveResearchHost.cs`
   Keep ALL previously installed V4.1 `.cs` files in place — the host
   reuses `V4VolumetricReader`, `V4Atr`, and `V4SessionMap` from them.
3. Start NinjaTrader 8, open a NinjaScript editor (New →
   NinjaScript Editor), press **F5** to compile. It must say 0 errors.

### B. HISTORICAL PARITY RUN (do this first — it is the platform gate)

1. New → Chart → **MNQ** (current front contract, e.g. MNQ 09-26 —
   MNQ ONLY, never NQ), Data Series type **Volumetric**, base period
   **1 Minute**, delta type Bid/Ask (ticks / level 1).
   Load "days to load" covering the capture period you want to compare.
2. Right-click chart → Strategies → add **MnqV41ProspectiveResearchHost**.
3. Parameters: `Mode (PARITY or PROSPECTIVE)` = `HISTORICAL_PARITY`;
   `Output folder` = default (Documents\...\V41Prospective) or any
   folder you like; leave `Enable Sim101 orders` = **False**.
4. Enable the strategy. It processes historical bars, prints the
   startup diagnostic to the NinjaScript Output window (New →
   NinjaScript Output), and writes `V41_PARITY_EVENTS_*.csv`,
   `V41_PARITY_TRADES_*.csv`, plus DIAG/AUDIT txt files to the output
   folder. If it prints **HARD FAIL — primary series is not
   Volumetric**, the chart's data series is wrong; fix step 1.
5. Send those files back into the research environment. We run
   `analysis/v41/compare_nt8_parity.py` on them; the verdict must be
   **PASS** before anything else happens.

### C. PLAYBACK GATE (after B passes)

1. Connect to the **Playback** connection (Connections → Playback),
   download/replay a Market Replay day that overlaps the capture.
2. Same chart + strategy setup as B, `Mode = HISTORICAL_PARITY`.
3. Replay at any speed. The engine must emit the same events for the
   replayed period as the historical run (same files, same comparator).
   This proves the streaming path (live-style bar building) matches the
   historical path.

### D. SIM101 GATE (only after B and C pass)

`Enable Sim101 orders` exists but this version deliberately submits
NOTHING — order wiring is deferred until the parity and Playback gates
are green. Even when a later version arms it: the flag defaults to
False, refuses any account whose name does not contain "Sim101", and
fails closed. Live order submission is not implemented anywhere, and
this project does not authorize adding it.

### E. Prospective logging (ongoing)

After B/C pass: run the same chart + strategy with
`Mode = PROSPECTIVE_LOG` each day/week. Upload the
`V41_PROSPECTIVE_*` files; the frozen Python scorer appends to the
ledger and checks the pre-declared failure conditions at 20/50/100
trades. Do not edit any parameter between runs — the configuration IS
the frozen version.

## 16. Stopping rule status

Allowed labels: PARITY PASS — READY FOR PLAYBACK · PARITY FAIL ·
PLAYBACK PASS · SIM101 PASS. (READY FOR LIVE TRADING is not an allowed
label for this project.)

Current: **PARITY PASS — READY FOR PLAYBACK** — evidenced both
off-platform (§10–§12) and in-platform on a real NT8 Volumetric feed
(§10a). Next action is §15-C, the Playback gate. Not ready for live
trading; this project does not authorize live trading.
