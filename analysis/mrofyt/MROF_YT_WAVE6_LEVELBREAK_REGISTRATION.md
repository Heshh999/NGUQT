# MROF_YT_WAVE6_LEVELBREAK_REGISTRATION.md — fade the failed break or follow the held one, registered before any run

**Status: FROZEN on 2026-10-26, before either tool was run on any real
data.** One idea family has support: a big level breaks; when the break
fails, fade it (wave three's L2, "break and reclaim"); when it holds,
follow it (L4, "break and retest"). The operator then asked two
questions this file answers in advance: how should the stop be set (a
fixed distance, or tight and placed by the order flow?), and does ES
confirming or denying the break tell you which side to take? Nothing
below changes waves one to five.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on recorded tape and historical bars. No order is
placed.

---

## Part A — the stops and the trapped traders, on the order-flow recordings

Module `mrofyt_levelbreak.py` (MROF-YT-W6-LEVELBREAK-1.0). It subclasses
wave three's runner, hooks only; the L2 and L4 detectors are wave
three's, unchanged.

### A1. Events

Wave three's L2 and L4 fires (§1 of its registration), de-duplicated by
the pilot's 60 s rule. Each event also carries, from its first fire:
the level price, the approach direction `ad`, the approach's **sweep
extreme** (the furthest mid toward and through the level, the runner's
own `touch`), and its **trapped volume** (§A4). The L2 trade is `-ad`
(fade); the L4 trade is the original break's direction.

### A2. Exits — fixed now

Every exit: target **100 ticks** (25 points), **1 800 s** limit,
mid-to-mid on the run's compressed mid path, never across a recording
run.

| exit | stop |
| --- | --- |
| fixed | 60 ticks (15 points) |
| STRUCTURAL | 2 ticks beyond the sweep extreme, measured from the entry mid, clamped to 12–60 ticks |
| FLOW-INVALIDATION | out at the first 10 s grid tick after entry where the aggressor delta is back in the break direction with `z >= 1.5` (the frozen `delta10` z) AND the mid is at least a tick back through the level; an 80-tick (20-point) emergency stop behind it |

A stop is valued at minus its distance, a target at plus 100, an
invalidation or a timeout at its mid.

### A3. Costs

Each trade is charged `mrofyt_costs`' round trip: $5 commission on NQ
($2 on MNQ), a tick of spread, a tick of slippage on stops.

### A4. TRAPPED volume

Aggressive contracts traded **in the break direction, a tick or more
beyond the level**, while the approach is active, summed per approach up
to the fire. The cut is the **median** trapped volume of the DEV L2
events (every event, resolved or not), per instrument, computed by the DEV run and frozen (the
`--frozen-out` file is committed before any held-out read).

### A5. The five tests (NQ; MNQ reported beside)

| id | events | exit |
| --- | --- | --- |
| T1 | L2 | fixed |
| T2 | L2 | STRUCTURAL |
| T3 | L2 | FLOW-INVALIDATION |
| T4 | L4 | fixed |
| T5 | L2 with trapped volume `>=` the cut | fixed |

Each tests the **mean net result per trade above zero**,
session-clustered (wave four's estimator), Holm over the five at 0.05.
Reported also: hit rate, gross and net points, net R (net / the trade's
risk: its stop, or 80 ticks for T3), outcome counts, per session.

| NQ trades | result | verdict |
| --- | --- | --- |
| `< 30` | — | NOT TESTED |
| `>= 30` | fails Holm, or mean net `<= 0` | no signal |
| `>= 30` | survives Holm, mean net `> 0`, 95 % interval above 0 | promising: a sizing and execution study, **still no live orders** |

### A6. Where it is judged

- **DEV** (sessions `<= 20260918`): describes, does not test — these
  days were seen before this file existed.
- **Replay holdout** (`--evaluate <frozen> --holdout`): a folder holding
  ONLY NinjaTrader Market Replay recordings of sessions **before
  2026-09-01**; the tool refuses a folder that holds any later session.
  Read once; recorded in `MROF_REPLAY_HOLDOUT_EXPOSURE.json`.
- **Validation** (`--evaluate <frozen> --unblind`, sessions `>=
  20260921`) at the December checkpoint; exposes permanently.

## Part B — ES confirmation (SMT), on minute bars

Module `mrofyt_smt.py` (MROF-YT-W6B-SMT-1.0). It reads NQ and ES
one-minute exports with `mrofyt_context`'s reader and stamp check, and
uses the context study's split: read on **2019-06-01 → 2026-06-30**
first (years earlier studies in this repository already used for other
questions), **judged on every session before 2019-06-01**, which no
study here has read. Sessions from 2026-07-01 are never read.

### B1. Events (NQ, front contract, yesterday's levels from the same contract)

- **Break:** the first cash-session bar starting 09:30–14:59 ET whose
  high is at least `0.02 × ATR14` above yesterday's cash high (low:
  mirrored). One per level per session.
- **FAILED:** among that bar and the next 14, the first close back
  inside yesterday's range; the event is that close; trade **against**
  the break.
- **HELD:** that bar and the next 14 all close beyond the level; the
  event is the 15th close; trade **with** the break.
- Neither: no event.
- **ES confirmed:** ES (its own front contract, ATR and yesterday's
  level) traded `0.02 ×` its ATR beyond its own level at any bar up to
  the NQ event bar. A session without an eligible ES day has no event.

### B2. Outcome

Stop `= max(0.05 × ATR14, 4 points)`, target `= 1.6 ×` stop, first touch
on the following one-minute bars (a bar touching both is a **stop**),
else the 15:59 close. In R (stop units), **net of 0.75 points** a round
trip.

### B3. The four tests

| id | test |
| --- | --- |
| S1 | FAILED, ES not confirming, fade: mean net R `> 0` |
| S2 | HELD, ES confirming, follow: mean net R `> 0` |
| S3 | among FAILED: mean net R (ES not confirming) − (ES confirming) `> 0` |
| S4 | among HELD: mean net R (ES confirming) − (ES not confirming) `> 0` |

Month-clustered (S3, S4: the difference of means with one cluster-robust
variance over both groups, influence-function form), Student t on `G −
1` degrees of freedom, **Holm over the four** at 0.05. S1/S2 need 60+
events; S3/S4 need 30+ in each group. PROMISING requires Holm, a
positive effect and a 95 % interval above 0.

The DEV read reports the four tests on 2019-06 → 2026-06 as a first
look; the verdict is the `--unblind` read of the years before
2019-06-01, recorded in `MROF_SMT_EXPOSURE.json`.

## Explicitly NOT registered

- any exit, stop distance, buffer, clamp, z threshold, target or limit
  other than above; trailing or partial exits
- any trapped-volume cut other than the DEV median
- choosing among T1–T3 on DEV results (all three are judged)
- any break threshold, window, 15-bar rule, stop or target for Part B
  other than above; ES tick data; any other confirming market
- combining a Part A or Part B result with a context rule (a later
  registration, on sessions neither has read)
- machine-learned models of any kind
- live, paper or simulated order placement

## Implementation record — 2026-10-26

`mrofyt_levelbreak.py`, `tests_mrofyt_levelbreak.py`, `mrofyt_smt.py`,
`tests_mrofyt_smt.py`. Written against this file before any real data
was read by them; verified on hand-built paths, grids and bars, on
planted-effect event lists and on synthetic recorder-format and
NinjaTrader-format data, never on market evidence.

| registered | implemented as | precision |
| --- | --- | --- |
| A1 | `LevelBreakRunner._w3_fire`, `level_events` | the annotation is the FIRST fire's of each de-duplicated event |
| A2 | `path_exit`, `structural_stop`, `flow_invalidation` | an outside exit applies when no stop or target came at or before its grid instant |
| A4 | `LevelBreakRunner._on_trade_event` | only ACTIVE approaches accrue; reset at the session close and wound back with an abandoned run |
| A6 | `plan()` with `--holdout` | the whole replay folder is validation; any session from 2026-09-01 stops the read |
| B1 | `find_events` | "beyond" is strict for HELD (a close ON the level is neither) |
| B3 | `mean_stats`, `diff_stats`, `tests` | none |

Synthetic tape never flips its order flow, so the frozen L2 detector
never fires on it; the suite's end-to-end checks swap in, inside the
suite only and restored afterwards, a plumbing detector (L2 without its
flow condition). The frozen detectors are never edited (hash re-pinned).
