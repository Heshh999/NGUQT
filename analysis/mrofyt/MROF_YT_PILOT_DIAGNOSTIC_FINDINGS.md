# MROF_YT_PILOT_DIAGNOSTIC_FINDINGS.md — §8A PILOT_DIAGNOSTIC_ONLY

Produced by `mrofyt_pilot.py` (MROF-YT-PILOT-1.0) over the recordings
actually supplied. Descriptive only: no fill, stop, target, R or P&L was
computed, and no model, threshold or feature was searched.

**Classification: `PILOT_DIAGNOSTIC_COMPLETE — INSUFFICIENT_DATA_FOR_EV`.**

Every pilot stage the present data can support ran to completion. The EV
question was not opened and stays behind the State-C gate.

Reproduce:

```
python3 mrofyt_pilot.py "<capture folder>" --out pilot_report.json
python3 tests_mrofyt_pilot.py        # 18/18
```

---

## The two answers, kept separate

### 1. IS THE SYSTEM WORKING? — **YES**

| Check | Evidence |
| --- | --- |
| Manifest hash / byte / row verification | 15 runs verified byte-for-byte |
| Streams ingested end to end | 1,351,398 genuine events heap-merged in `eventSeq` order |
| Levels constructed | approach detection ran on genuine mid data |
| Decision windows completed | 293 completed 10-second windows |
| Detectors executed | all six families evaluated on every window |
| Outcome lock held | no fill, stop, target, R or P&L computed |

The recorder, the manifest chain, the streaming adapter, the auditor, the
book/tape reconstruction, the level engine, the approach state machine,
the decision-window grid and all six frozen detectors executed correctly
on real market data. Nothing in the pipeline failed.

### 2. DO ANY HYPOTHESES APPEAR PROMISING? — **`NOT_OBSERVED`**

Zero frozen signals were produced, so no hypothesis was observed either
way. This is an **absence of observation, not evidence against** any
hypothesis. No A1–A6 mechanism has been tested, supported or refuted.

These two answers are independent. A pipeline that runs correctly on
starved statistics is `WORKING` and `NOT_OBSERVED` at the same time, and
collapsing them into one answer is the error this step exists to prevent.

---

## Step 1 — data audit

29 manifests. 15 runs arrived with their bulk CSVs and **all 15 passed**:
every SHA-256, byte count and row count matched the recorder's own
manifest, identity held on every row, sequences were monotone with no
gaps, both depth sides and all three actions were present, and declared
depth (30 levels observed against a declared 10) was consistent.

14 runs are manifest-only — the bulk CSVs stayed on the capture machine,
which is the documented handoff order (`DATA_HANDOFF_V12.md` §1). The
auditor reports these as `RUN_AUDIT_FAILED / MISSING_FILE`, correctly:
it cannot verify a file it does not have. One `ORPHAN_PARTIAL`
(`…165435151-f3e484fc-R001_quality.csv.partial`) is the residue of the
crash that ended that run.

Manifest-level NQ/MNQ pairing is **excellent** — 0.991, 0.9999, 0.99999,
1.000, 1.000 window overlap across the five sessions, on 24-hour runs.
The recorder is capturing paired data properly.

Feed latency on genuine rows: NQ p50 230 ms / p95 271 ms (296,117
samples); MNQ p50 238 ms / p95 279 ms (1,055,100 samples).

## Step 2 — pipeline proof and the coverage that actually exists

This is the finding that governs everything below.

| | union coverage with verified CSVs | windows |
| --- | --- | --- |
| NQ | **162.3 s** | 3 |
| MNQ | **344.5 s** | 3 |
| NQ **and** MNQ simultaneously | **0.0 s** | — |

All CSV-backed runs are from one date, 2026-09-01, during the
duplicate-instance setup period. Concurrent duplicate recorder instances
of the same feed are collapsed into one window: they are copies, not
independent observations, and counting them separately would overstate
the evidence base by roughly 3×.

The zero is exact, not a rounding artefact. NQ's second window ends at
15:39:02.878 as MNQ's first begins; NQ's third (15:41:44–15:42:03) falls
inside MNQ's gap (15:41:43–15:42:03). **The NQ-signal / MNQ-execution
topology cannot be exercised on the supplied data at all**, because there
is not one second in which both instruments were recorded.

Meanwhile the manifest-only runs describe 18,000–83,000 second sessions.
The data that would answer the research question exists — it is on the
capture machine, not here.

## Step 3 — feature health

| feature | available | median | min | max |
| --- | --- | --- | --- | --- |
| `persist_agree` | 293/293 | 2 | 0 | 4 |
| `approaches_60s` | 293/293 | 14 | 2 | 40 |
| `retreat_ticks` | 279/293 | 4.5 | −58.5 | 48.0 |
| `progress_ticks` | 277/293 | 10.5 | −21.5 | 62.5 |
| `replenish_ratio` | 157/293 | 18.5 | 0.0 | 611.0 |
| `aggr_z` | **0**/293 | — | — | — |
| `replenish_z` | **0**/293 | — | — | — |
| `opp_flip_z` | **0**/293 | — | — | — |
| `control_z` | **0**/293 | — | — | — |
| `wall_z` | **0**/293 | — | — | — |
| `exec_vs_displayed` | **0**/293 | — | — | — |
| `post_clear_z` | **0**/293 | — | — | — |
| `resid_tail_5pct` | **0**/293 | NOT WIRED by design | | |
| `trend_dir` | **0**/293 | NOT WIRED by design | | |

Every **raw** feature computes. Every **z-scored** feature is `None`.

That split is the whole story, and it is a designed gate, not a fault.
`BaselineStore.z` returns `None` until a (feature, 5-minute-of-day)
bucket holds at least 5 prior observations, one per completed session.
With a single date there is no prior session, so no bucket can reach 5,
so no z-score exists, so no detector can arm. `exec_vs_displayed` and
`wall_z` are `None` for the consequent reason: wall qualification itself
requires `wall_z`, so no wall was ever qualified.

`replenish_ratio` reaching 611.0 is not an anomaly — it is
`depth_added / executed` where almost nothing executed at the level
during a 10-second window.

## Step 4 — level and approach census

300 approaches, 293 completed windows, 0 suppressed.

| level | approaches |
| --- | --- |
| `SESSION_VWAP` | 127 |
| `VWAP_UPPER` | 56 |
| `CASH_OPEN_0930` | 47 |
| `GLOBEX_OPEN` | 47 |
| `VWAP_LOWER` | 16 |

Never active: `YDAY_HIGH`, `YDAY_LOW`, `OVERNIGHT_HIGH`,
`OVERNIGHT_LOW`, `LWEEK_HIGH`, `LWEEK_LOW`, `PP`, `M2`, `M3`.

Only same-session levels (VWAP band, session opens) could exist. Every
prior-day and prior-week level requires a completed previous session,
and there is none. **Nine of the fourteen active levels — including the
prior-day highs and lows that the strategy is largely about — were never
even present.**

Wall state was `NO_QUALIFYING_WALL` on all 293 windows.

`ATR20` is `null` for both instruments: 12 (NQ) and 19 (MNQ) one-minute
bars exist in total, against the 20 the frozen definition needs. The
approach radius therefore fell back to its 4-tick floor throughout.

## Step 5 — A1–A6 threshold funnel

Each window is attributed to the **first** stage it fails, on the frozen
thresholds, with nothing tuned.

| family | windows | first failing stage | missing inputs | passed | fires |
| --- | --- | --- | --- | --- | --- |
| A1 | 293 | `inputs_available` ×293 | `aggr_z` 293, `replenish_z` 293, `opp_flip_z` 293, `progress_ticks` 16, `retreat_ticks` 14 | 0 | 0 |
| A2 | 293 | `inputs_available` ×293 | `wall_z` 293, `exec_vs_displayed` 293, `post_clear_z` 293, `replenish_ratio` 136 | 0 | 0 |
| A4 | 293 | `inputs_available` ×293 | `aggr_z` 293, `opp_flip_z` 293 | 0 | 0 |
| A5 | 293 | `inputs_available` ×293 | all five (`trend_dir` NOT WIRED) | 0 | 0 |
| A6 | 293 | `in_0930_0945` ×293 | — | 0 | 0 |
| A3 | 139 checks on its own 2 s vacuum grid | 0 vacuum events | — | 0 | 0 |

**Not one window was disqualified by a threshold.** Every window died at
input availability — or, for A6, at the clock: no supplied CSV covers
09:30–09:45 ET.

This matters for interpretation. A funnel that died at thresholds would
say the thresholds may be badly calibrated. A funnel that dies entirely
at availability says nothing about the thresholds at all: they were
never consulted.

## Step 6 — frozen signals and trades

**0 signals. 0 trades.** No entry, exit, fill or hold was simulated.

## Step 7 — descriptive response check

Signal population: `NO_FROZEN_SIGNALS`. All six horizons (1 s, 5 s, 10 s,
30 s, 60 s, 180 s) are therefore **empty**. No substitute population was
promoted into their place.

A separate, explicitly non-directional block records whether forward mid
data is reachable at all: it is, for 279/269/256/198/130 windows at
1/5/10/30/60 s, and for **0** windows at 180 s — no run lasts long
enough. That block carries **no directional claim**. Its unsigned drift
(median +24.5 ticks at 60 s) is one morning's move inside a five-minute
recording, an approach is not a trade, and reading it as edge would be
exactly the error this pilot is designed to avoid.

## Step 8 — matched sanity controls

`NOT_APPLICABLE`: with no signal population there is nothing to match.
Inventing a control here would fabricate a comparison. When signals
exist, the pilot's registered controls are same-bucket/same-family/
same-direction signal-absent windows, random timestamps inside the same
coverage, and sign-flipped direction.

## Step 9 — visual replay audit

Traces of the longest approaches reconstruct coherently: approach
direction, level price, per-window retreat in ticks, persistence count,
cross/return flags and wall state all move together and agree with the
mid path. Example — MNQ approach 2 to `SESSION_VWAP` at 29260.21 from
below, one completed window, retreat −5.0 ticks, `persist_agree` 3, did
not cross, returned through the level, 4 approaches to that level inside
60 s. Nothing incoherent appeared.

## Step 10 — model search

**Not performed, by instruction.** No model, threshold, feature or level
was searched, tuned or selected on these days.

---

## Two defects the genuine data exposed (both fixed, both pinned)

1. **Runner crashed on manifest-only runs.** `mrofyt_runner.py` passed
   every manifest-declared CSV path to the reader and raised
   `FileNotFoundError` on the first absent one. Since the documented
   handoff sends manifests *first*, this made the runner fail on the
   normal case. Fixed: a run missing any declared stream is now skipped
   **whole** and recorded in `skipped_runs` with the missing filenames.
   It is never partially ingested — computing features from a book or
   tape that is missing a stream would be silently wrong. Pinned by P1,
   P1b.

2. **Markout coverage test and run-boundary splice.** The first markout
   implementation required a tick to land exactly on the horizon (so it
   returned `None` for every window) and concatenated all runs of an
   instrument into one series. The second fault is the more serious one:
   concurrent duplicate instances overlap in time, so the series was not
   even monotone, and a markout could have spanned two runs and read a
   recording gap as a price move. Fixed: series are kept per run, the
   coverage test is "the run reaches the horizon", and the mark price is
   the last mid at or before it — never interpolated, never across a run
   boundary. Pinned by P2, P2b, P2c.

## Exposure

Sessions 20260901–20260905 are permanently labelled `EXPOSED_PILOT_DEV`
in `MROF_EXPOSED_PILOT_DEV_DAYS.json` (append-only). They may remain in
later DEV/training where the governing protocol permits. **They can
never become untouched prospective validation.**

No threshold, level, window, stop, target, exit, feature definition or
baseline was adjusted after seeing these days.

## Exactly what is missing

The pilot is not blocked by code. It is blocked by three specific
absences, in priority order:

1. **The bulk CSVs for the 14 manifest-only runs** —
   `…_depth.csv`, `…_quotes.csv`, `…_trades.csv`, `…_quality.csv` for
   sessions 20260902–20260905. These are the full 18,000–83,000 second
   sessions with genuine NQ/MNQ pairing. Everything in this document
   changes once they are ingested.
2. **At least six independent session-days per instrument**, so that a
   (feature, 5-minute bucket) baseline can reach five prior observations
   and z-scores begin to exist at all. Five prior sessions is the floor
   for a *single* z-score, not for evidence.
3. **Capture restarted.** The last recorded event is 2026-09-04 22:35
   UTC. Sunday's reopen, Labor Day and the sessions since are not
   recorded.

Until (1) and (2) exist, answer 2 will keep returning `NOT_OBSERVED`, and
that answer will keep being correct.

---

# Amendment 1 — MROF-YT-PILOT-1.1: event de-duplication and the primary horizon

Registered **2026-09-12**, before the data these measurements will be
read on exists. Both changes are **measurement only**. No threshold,
level, window, stop, target, exit, feature definition, baseline or
detector was touched, and the runner's raw `fires` list is byte-identical
to what 1.0 produced. Verified by the full battery: **383/383**.

## Why raw firing counts were not a signal count

`Runner._fire` records every non-zero detector return. The runner has no
position model and no consumption, so a single market event is recorded
once per qualifying window and once per coincident approach. In the
seven-session pilot the 11 raw firings were approximately **3 distinct
events**:

- six MNQ firings inside 7.4 s across approaches 3551–3559 — one event;
- approach 3307 firing twice 10 s apart — one event;
- 7 of the 11 came from MNQ, which is not a signal source under the
  NQ-signal / MNQ-execution topology.

Reporting 11 would have inflated the population ~3.7×, and — the more
serious fault — would have entered one event several times into a
median, understating its variance.

## The de-duplication rule (frozen)

Two firings belong to the same **event** when they share instrument,
session, family and direction, and the later one starts within
`EVENT_COOLDOWN_S` of the event's **first** firing.

- The default cooldown is **60 s**, matching A1's already-frozen
  `approaches_60s` lookback rather than introducing a new constant.
- Anchoring on the first firing rather than the previous one bounds
  every event at the cooldown, so a dense burst cannot chain into one
  arbitrarily long event.
- **Approach id is deliberately not part of the key.** Coincident
  approaches to nearby levels produce different ids for what is plainly
  one market event.
- Sensitivity at 10 / 60 / 300 s is reported alongside, so the choice of
  cooldown is visible rather than hidden.
- An event whose firings straddle a run rotation is flagged
  `spans_runs`, because a markout is only valid inside one run.

MNQ firings are **labelled**, never discarded: `is_signal_source` marks
NQ, and both populations are reported.

Pinned by P9, P9b, P9c, P9d, P9e, P9f, P9g, P9h.

## Markout horizons

Added **300 s, 600 s, 1800 s**; every horizon the 1.0 report carried is
retained. **300 s is primary.** Rationale, registered now: the operator's
own recorded discretionary trading averages a ~4-minute hold (longest
8 min 3 s), so 5 minutes is the horizon at which this would actually be
traded. 600 and 1800 bracket the frozen `MAX_HOLD_S = 1800` cap.

Markouts are now computed on the **event** population and reported per
family. The raw-firing markouts are retained under
`raw_fire_markouts_signed_ticks` for continuity with the 1.0 report and
are explicitly captioned as the population *not* to read.

Pinned by P9i.

## Operator friction, for the record

From the operator's NinjaTrader account report (a period of discretionary
trading, not this system): `Trade Fees & Comm. $52.78` over 58 contract
sides — **$0.91 per side, $1.82 per contract round trip**. Limit-in /
limit-out, so no spread is crossed. In points: **≈0.91 on MNQ, ≈0.09 on
NQ.**

This is recorded as context for reading markouts. It is **not** computed
by any module here, and the outcome lock is untouched: the pilot still
produces no fill, stop, target, R or P&L. Confirm the figure from the
Fills tab or the exported CSV before using it as a threshold.

---

# Amendment 2 — MROF-YT-PILOT-1.2: the validation blind

Registered **2026-09-19**. Measurement and protocol only; no threshold,
level, window, feature, baseline or detector changed, and the raw
`fires` list is still byte-identical to what 1.0 produced.

## The hole Amendment 1 and the wave-two registration created together

`MROF_YT_WAVE2_REGISTRATION.md` declares every session `>= 20260921`
untouched validation. This pilot is run weekly for recording health, it
labels every session it touches `EXPOSED_PILOT_DEV`, and it prints
markouts. `W2-A4r` is A4 exactly as it ran. So the weekly run would have
unblinded wave two's primary population one Friday at a time, and by
December there would have been no validation set left.

## What 1.2 does

- **Withholds every markout** — signal, raw, window-reference, every
  horizon — for sessions `>= BLIND_FROM = '20260921'`. Events on those
  sessions are **counted** (`blind.events_withheld`,
  `signal_source_events_withheld`, `sessions_withheld`) so accrual is
  visible. Knowing *N* does not reveal which way *N* went.
- **Labels** those sessions `VALIDATION_BLIND_MARKOUTS_WITHHELD` in the
  exposure ledger, not `EXPOSED_PILOT_DEV`. Exposure is **monotone**:
  a blind session may later be unblinded (recorded as
  `previously_blind`), an exposed one can never be re-blinded.
- **Unblinds only explicitly** — `--blind-from none` — announced loudly
  on stdout. That is the checkpoint read and it is permanent.
- **Reports a seeded percentile-bootstrap 95% interval** on every
  markout population (`ci95_median`, `ci95_mean`,
  `ci95_median_includes_zero`), which is the quantity the registered
  kill criterion reads. None below five events.
- **Carries the runner's skip reasons and book-integrity counters** in
  `step2` and the text summary — promised with the retroactive
  correction and not delivered until now.

Pinned by `P11`–`P11k`. `P11k` binds the date and label to the
registration text so the two cannot drift apart.

## What this means operationally

The weekly Friday run is now safe: run it exactly as before. The
summary will say

```
VALIDATION BLIND from 20260921: N events (M signal-source) on sessions ... -- counted, markouts WITHHELD.
```

and that line is the event-rate check. Nothing directional about those
sessions is readable until the December checkpoint is run with
`--blind-from none`.
