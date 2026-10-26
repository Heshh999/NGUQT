# MROF_YT_WAVE5_EXIT_REGISTRATION.md — when a winning run is ending, registered before any run

**Status: FROZEN on 2026-10-26, before the tool was run on any recorded
session.** The operator trades intraday and exits by reading the tape:
"if the trade is up 20 or 40 points and momentum seems to be dying, take
the win, whether that is 30 seconds or 30 minutes in." Every earlier
wave scored a fixed horizon or a fixed bracket and could not see that
exit. This file fixes, before anything is measured, what "in a winning
run" means, what "holding" is compared with, which eight tape signs are
tested, how each is scored, how luck is discounted, and how the
survivors are judged.

**Registered:** 2026-10-26. **Studied:** sessions `<= 20260918` only
(all labelled `EXPOSED_PILOT_DEV`). **Judged on:** sessions
`>= 20260921`, which nobody has examined, at the December checkpoint,
or on an untouched replay set if one is registered first.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only shadow research on recorded tape. No order is placed.

---

## 0. What this wave is, and the one fact that governs it

An exit cannot turn a coin-flip entry into money: under a fair price
path every exit rule has the same average, and only changes the shape
of the results. An exit is worth something only if the information it
uses **predicts** that the move is over. That is what this wave tests:
not "which exit makes a pattern look best", but "does this tape sign
predict that holding is worth less than usual".

The study does not need the waves' own entries. Every run on the tape
is a chance to ask the question, so the sample is every winning run in
the DEV sessions, whoever started it.

Waves one to four continue unchanged. The module (`mrofyt_exitstudy.py`,
MROF-YT-W5-EXIT-1.0) subclasses the wave-four runner, which subclasses
wave three's and the pilot's, and uses observation hooks only; the
frozen detectors are never edited and the suite re-pins their hash.

## 1. In a run

On every frozen 10 s grid tick `te` at which the book is ready, using
the grid mids of the same recording run over the last 30 minutes (at
least 171 of the 181 grid ticks present), for direction `d = +1`:

- `ext` = the lowest grid mid in the window, `anchor` = the latest grid
  tick at which it occurs;
- `best` = the highest grid mid from `anchor` to `te`, `t_best` = the
  earliest tick it occurs;
- **in a run** when `mid(te) - ext >= 80 ticks` (20 points) **and**
  `best - mid(te) <= 20 ticks` (within 5 points of the best).

`d = -1` is the mirror. The two cannot hold at once. `stall_s = te -
t_best`.

## 2. Holding, and the comparison

From an in-run moment, **holding** is valued by one plain reference rule
fixed now: a **10-point (40-tick) trailing stop** from the best mid
since the moment, at most **1 800 s**, mid-to-mid on the run's
compressed mid path. Value = the exit mid minus the moment's mid, in
the run's direction, in ticks. A trail crossed by a gap exits at the
mid that crossed it. If the run ends first: UNRESOLVED, excluded.

**Exiting now** is worth 0. Both choices pay one exit, so costs cancel
in the comparison; none is charged.

**Baseline:** the mean hold value over every in-run moment of the same
`(instrument, ET hour, direction)`. A sign's **lift** is the mean of
(hold value − its cell's baseline) over the sign's events. **Negative
lift = holding after the sign is worth less than holding at an ordinary
in-run moment = an exit sign.**

## 3. The eight signs, fixed

At an in-run moment in direction `d`, from the window `[te - 10 s, te)`
and the grid history of the same run. Quantile cut-points are computed
once, per instrument, on the DEV sample (in-run moments for the flow and
book signs, every grid tick for the tape-count and lot-size signs), and
frozen with the nominated signs.

| id | name | fires when |
| --- | --- | --- |
| X1 | DELTA_FADE | the last 60 s of aggressor delta (`D60`) is no longer with the run: `d · D60 <= 0` |
| X2 | TAPE_SLOW | the 10 s trade count is at most half its mean over the previous 30 grid ticks (at least 25 present) |
| X3 | ABSORPTION | with-run 10 s delta `d · D` in its top quintile **and** the 10 s mid response `d · r <= 1` tick |
| X4 | OTHER_SIDE | against-run 10 s delta `-d · D` in its top decile |
| X5 | BOOK_TURNS | against-run top-3 book imbalance `-d · BI3` in its top quintile |
| X6 | STALL | no new best for at least 120 s (`stall_s >= 120`) |
| X7 | CLIMAX | in the previous 6 grid ticks a 10 s trade count in the top 5 % of all grid ticks, the current count at most half that, and the best set within the last 60 s |
| X8 | BIG_LOT_AGAINST | the largest single trade against the run in the 10 s is in the top 1 % of the largest trade per 10 s over all grid ticks |

A sign with a missing input does not fire. The operator's own read was
asked for and not supplied; the list above is the standard order-flow
inventory, fixed here so it cannot grow after the data is seen.

## 4. Events, uncertainty and luck

- **Events:** the in-run moments where a sign fires, de-duplicated with
  an anchored **300 s** cooldown per (session, direction).
- **Uncertainty:** session-clustered standard error (wave four's
  ratio estimator), Student t on `G - 1` degrees of freedom, two-sided.
- **Luck:** Holm over the **8** NQ tests at family-wise 0.05. A test
  needs 30+ resolved events on 6+ sessions to be counted at all.
- **Status:** `EXIT SIGN` (survives, negative lift), `HOLD SIGN`
  (survives, positive lift: holding after it is better than usual),
  `NO SIGNAL`, `NOT TESTED`. NQ is primary; MNQ is reported beside it
  and is not a separate test.
- **DEV halves:** the sessions split chronologically in two; the lift
  is reported in each.

## 5. Nomination — at most three, fixed now

Eligible: p `<= 0.05`, negative lift in **both** halves (10+ events
each), 30+ events on 6+ sessions. Holm survivors first, then by t (most
negative). At most three, written out with their numeric cut-points
for NQ and MNQ and committed to the repository **before** any
validation session is read. If nothing is eligible, nothing is
nominated.

## 6. Validation

`--evaluate <nominated> --unblind` reads the validation sessions once,
applies the frozen cut-points, and scores each nominated sign as in §4
with a baseline built from the same sessions. Holm over the nominated
set.

| NQ events (validation) | result | verdict |
| --- | --- | --- |
| `< 30` | — | **NOT TESTED** (keep recording) |
| `>= 30` | fails Holm, or lift `>= 0` | no signal |
| `>= 30` | survives Holm, lift `< 0`, 95 % interval below 0 | promising: proceed to combining it with an entry, **still no live orders** |

## 7. Half-life curves — descriptive, not tests

For every wave-one family and wave-three pattern (events de-duplicated
at 60 s, as their own reports do), for in-run moments (every third, so
30 s apart) and for each sign's events: the mean mid move in the
signal's direction at 5 s, 30 s, 1, 2, 5, 10, 30 min, 1, 2 and 3 h,
minus the mean move of every grid tick of the same `(instrument, ET
hour)` in that direction. Measured inside one recording run; a horizon
the run does not reach is left out. This answers "how long does each
signal's edge last" for the operator's 5 s – 3 h range. It produces no
verdict and no rule.

## 8. Exposure

- The study reads DEV sessions only; every later session is refused and
  listed (the wave-three gate).
- `--evaluate` without `--unblind` reads DEV only and reproduces the
  study's numbers for the frozen signs.
- `--evaluate --unblind` is the checkpoint read. It announces itself
  and writes every session it reads to the exposure ledger as exposed
  by this wave, permanently.
- **Replay recordings** (NinjaTrader Market Replay of sessions before
  20260901) must be kept in a folder of their own and never passed to a
  DEV tool: every tool treats a session `<= 20260918` as DEV and would
  read it. Using them as a validation set needs its own registration
  first.

## 9. Explicitly NOT registered

- any run threshold other than 80 / 20 ticks over 30 minutes
- any reference hold other than the 10-point trail over 30 minutes;
  partial exits, scaling, break-even moves
- any sign or threshold not in §3; combinations of signs
- choosing a trail, target or holding time for a wave-one to wave-four
  pattern from the §7 curves (a later registration may do so on
  untouched sessions)
- machine-learned models of any kind
- live, paper or simulated order placement

## 10. Implementation record — 2026-10-26

`mrofyt_exitstudy.py` (MROF-YT-W5-EXIT-1.0),
`tests_mrofyt_exitstudy.py`. Written against §1–§9 before any recorded
session was read by it; the engineering verification ran on synthetic
tape and on planted-effect datasets and is asserted by the suite, never
by market evidence.

| registered | implemented as | precision |
| --- | --- | --- |
| §1 | `run_state()`: grid mids of the same run within 1 800 s of `te`, the current tick included | the anchor is the LATEST tick at the extreme, `t_best` the EARLIEST at the best |
| §2 | `trail_hold()`: forward scan of the compressed path | the trail is crossed at `>= 40` ticks from the best (1e-9 tolerance) |
| §3 | `signs_at()`, `quantile_cuts()` | quantiles are nearest-rank-below; a cut needs 20+ values |
| §4 | `sign_events()`, `sign_stats()`, `study()` | wave four's `cluster_stats`; Holm from wave three |
| §5–§6 | `nominate()`, `run_evaluate()` | none |
| §7 | `half_life()` | the pilot runner's own `markout()` (last mid at or before the horizon, never across a run) |
| §8 | the wave-three `plan()` gate; `--unblind` refused without `--evaluate` | none |
