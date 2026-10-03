# MROF_YT_WAVE3_BIGMOVE_REGISTRATION.md — big-move hypotheses, registered before any run

**Status: FROZEN on 2026-10-03, before the tool was run on any recorded
session.** The operator asked for recurring order-flow events that
precede 25-point moves. This file fixes what will be looked for, how it
will be scored and how many things are being tried, so a result cannot
be chosen after it is seen.

**Registered:** 2026-10-03. **Informed by:** the wave-one pilot read of
sessions 2026-09-01 → 2026-09-18 (all labelled `EXPOSED_PILOT_DEV`) —
its feature-availability table and level census only, never a markout
at a level or pattern named here. **Judged on:** sessions from
2026-09-21 onward, which nobody has examined, at the December checkpoint.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Every test below is
read-only shadow research on recorded tape. No order is placed.

---

## 0. What this wave is and is not

Waves one and two **continue unchanged**. Nothing in this file modifies
a wave-one or wave-two threshold, level, window, feature, baseline,
detector or exit. Wave-three code lives in its own module
(`mrofyt_bigmove.py`, MROF-YT-W3-BIGMOVE-1.0) which subclasses the pilot
runner and uses only its observation hooks, exactly as wave two does;
the frozen detectors are never edited and the suite re-pins their hash.

This wave asks a different question from waves one and two. They score
a mid-price markout at fixed horizons with no stop or target (the
outcome lock). This wave scores a **path**: did price reach a fixed
target before a fixed stop inside a fixed time. That is the question
the operator asked, and it cannot be answered by a fixed-horizon
markout. The departure is stated here so it is not mistaken for an
unlocking of waves one or two:

- the path outcome is computed **only** on DEV sessions
  (`<= 20260918`) in the default mode; the tool refuses every later
  session and lists what it refused;
- the validation sessions are read once, at the checkpoint, with an
  explicit flag that announces itself and labels those sessions
  exposed permanently;
- no fill, slippage, commission or position model is applied. The
  outcome is a mid-to-mid first touch. The report says so on every
  number;
- nothing here feeds back into a wave-one or wave-two threshold.

## 1. The eight patterns

Every input is one the frozen runner already computes at the decision
instant, or is derived from them causally. "Grid" means the frozen 10 s
grid tick `te` on which the runner observes its baselines; the features
are those of the window `[te - 10 s, te)`. `z(f, v)` is the runner's
robust z-score of value `v` against the 20-session, minute-of-day
baseline of feature `f`, with its 5-prior-observation floor; `None`
disqualifies. `s` is the sign of the window's signed aggressor delta
`D`. "Level" patterns are evaluated on the frozen approach windows the
runner already produces, with the window's feature dict `f` and the
approach's direction `ad` (+1 approaching from below).

| id | name | where | conditions (all required) | direction |
| --- | --- | --- | --- | --- |
| **G1** | FLOW_SHOCK_GO | grid, any time | `z(delta10, s·D) >= 3.0`; 10 s mid response `s·r >= 4` ticks; persistence `>= 3` of 4 subwindows in direction `s` | `s` (continuation) |
| **G2** | FLOW_SHOCK_FADE | grid, any time | `z(delta10, s·D) >= 3.0`; `abs(r) <= 1` tick | `-s` (reversal) |
| **G3** | CONTROL_RUN | grid, any time | frozen control score in direction `s` `>= 2.0` on this grid tick **and** the previous one, same `s` both times | `s` (continuation) |
| **L1** | OPEN_BREAK | level windows, 09:30:00–09:59:59 ET, level in {OVERNIGHT_HIGH, OVERNIGHT_LOW, YDAY_HIGH, YDAY_LOW} | `clean_cross`; `held_5s`; `persist_agree >= 3`; `aggr_dir == ad`; `aggr_z >= 1.5` | `ad` (continuation) |
| **L2** | SWEEP_RECLAIM | level windows, level in {YDAY_HIGH, YDAY_LOW, OVERNIGHT_HIGH, OVERNIGHT_LOW, LWEEK_HIGH, LWEEK_LOW} | `returned_through_level` (crossed by `>= 1` tick, then back by `>= 1` tick); `opp_flip_z >= 1.0` | `-ad` (reversal) |
| **L3** | VWAP_SNAPBACK | level windows, (`VWAP_UPPER` with `ad == -1`) or (`VWAP_LOWER` with `ad == +1`), i.e. price outside the band coming back to it | `aggr_dir == ad`; `aggr_z >= 1.5` | `ad` (through the band toward VWAP) |
| **L4** | BREAK_RETEST | level windows, level in the L2 set | an **earlier** approach to this level in this session had `clean_cross` and `held_5s` with direction `b`; this approach has `ad == -b` (a retest from the far side); `aggr_dir == ad`; `aggr_z >= 1.5`; `progress_ticks <= 1` | `b` (continuation of the original break) |
| **D1** | TREND_1030 | the first grid tick at or after 10:30:00 ET, once per instrument per session | `CASH_OPEN_0930` known; `move = mid - CASH_OPEN_0930`, `abs(move) >= 15` points; the sum of the per-grid `D` over 09:30–10:30 has the sign of `move`; at least 4 of the six 10-minute sub-sums have that sign | sign of `move` (continuation) |

Level patterns fire at most once per approach, on the first window
that satisfies them. L4's break memory is per (instrument, session,
level) and is reset at the session roll. `ad`, `clean_cross`,
`held_5s`, `persist_agree`, `aggr_dir`, `aggr_z`, `opp_flip_z`,
`progress_ticks`, `returned_through_level` are the frozen runner's own
window fields, unchanged.

**What the first wave-one read told us, and what it did not.** The
funnel showed `aggr_z` available on 53 % of windows, `opp_flip_z` on
36 %, `control_z` on 51 %, the wall and replenishment inputs on 14 % or
less. The patterns above therefore use flow, response, persistence and
control, not walls or replenishment. The read did **not** show any
markout at these patterns, which did not exist then.

## 2. Scoring — fixed path outcome

For a fire at instant `t0` with direction `d`:

- `p0` = the last mid at or before `t0` in the same recording run
  (the pilot's own rule: never across a run boundary, never
  interpolated);
- the path is the run's mid series after `t0`, compressed to its price
  changes;
- **target** `T = 100 ticks = 25.00 points`: the first mid with
  `d·(p - p0) >= T`;
- **stop** `S ∈ {40, 60, 80} ticks = {10, 15, 20} points`: the first mid
  with `d·(p - p0) <= -S`;
- **limit** 1800 s;
- outcome, per stop: `TARGET` if the target is touched first,
  `STOP` if the stop is touched first **or on the same mid** (a tie is a
  stop), `TIMEOUT` if neither inside 1800 s (its 1800 s markout is kept),
  `UNRESOLVED` if the run ends before 1800 s with neither (excluded from
  rates, counted);
- `hit rate = TARGET / (TARGET + STOP + TIMEOUT)`;
- `expectancy (ticks, before costs) = mean over resolved events of
  (+T for TARGET, -S for STOP, the 1800 s markout for TIMEOUT)`.
  Mid-to-mid. No fill, spread, slippage or commission. It is reported
  so the hit rate is not read on its own; it is not P&L.

Also recorded per event, descriptive: maximum adverse excursion before
resolution, maximum favorable excursion, seconds to resolution.

De-duplication: the pilot's `dedup_fires` at 60 s, keyed by instrument,
session, pattern and direction. Events, not raw fires, are scored.

## 3. Baseline — hour-matched, same rule

Every grid tick on the sessions read (when the book is ready) is scored
by the same rule in **both** directions. Cells are
`(instrument, ET hour)`. A pattern's expected hit rate is the mean of
its events' cell rates; its **lift** is observed minus expected. A
seeded percentile bootstrap over the pattern's events (2 000 draws, the
pilot's seed) gives the lift's 95 % interval and a two-sided p-value.

Matching on the hour matters: the patterns cluster in cash hours, where
25-point moves are common; an unmatched baseline would flatter every
one of them.

## 4. Placebo arm — level patterns only

`--both` re-runs the whole pipeline with every level shifted by the
wave-two ARM-C rule (same seed, same magnitudes, same minimum
separation; `MROF_YT_WAVE2_REGISTRATION.md` §4.2) and reports L1–L4
on the placebo levels beside the real ones. A level pattern whose lift
survives on placebo levels is a flow pattern, not a level pattern, and
is reported as such. G1–G3 and D1 use no level and are unaffected.

## 5. Multiplicity — 24 tests, fixed now

8 patterns × 3 stops = **24 tests**. The primary instrument is NQ (the
signal source of waves one and two); MNQ is reported beside it and is
not a separate test. Holm's step-down procedure at family-wise 0.05 is
applied to the 24 p-values. A pattern-and-stop survives DEV only if it
survives Holm. Nothing else is counted as a result.

## 6. Verdict rule — at the December checkpoint, per pattern

| NQ events (dedup) | DEV | validation | verdict |
| --- | --- | --- | --- |
| `< 30` on validation | — | — | **NOT TESTED** (keep recording) |
| `>= 30` | did not survive Holm | — | not carried forward |
| `>= 30` | survived Holm at stop `S` | lift's 95 % interval includes 0 | no signal |
| `>= 30` | survived Holm at stop `S` | lift positive, interval excludes 0, placebo lift not positive | promising; proceed to a sizing and friction study, **still no live orders** |

The stop `S` carried to validation is the one that survived on DEV; if
more than one did, the smallest. It is not re-chosen on validation.

## 7. Census — diagnostic only, hypothesis-generating

On the sessions read, for every grid tick: the maximum up and down
excursion of the mid over the next 1800 s. For each of five grid
features — `z(delta10)`, `z(ofi10)`, 10 s response `r`, `z(bi3)`, and
`z(n10)` (trade count per 10 s against its own baseline) — the ticks are
split into deciles by value and the share reaching `+100` and `-100`
ticks within 1800 s is tabulated beside the overall base rate.

This table is **not** a test and produces no verdict. Any rule drawn
from it is a wave-four registration on sessions not yet recorded.

## 8. Exposure and hold-out

- **DEV (read by this wave):** every session `<= 20260918`. Already
  labelled `EXPOSED_PILOT_DEV`; this wave adds nothing to that label.
- **Validation (untouched):** every session `>= 20260921`. The tool's
  default mode **refuses** them and lists each refused session in the
  report. The checkpoint read is `--unblind`, which prints a banner,
  reads them, and writes them to the exposure ledger as exposed by this
  wave, permanently (exposure is monotone, as in the pilot).
- Waves one and two keep their own blind (`BLIND_FROM = 20260921`);
  their fixed-horizon markouts on validation sessions are not read by
  this tool in either mode.

## 9. Explicitly NOT registered

- any threshold other than those in §1 (3.0, 4 ticks, 1 tick, 2.0,
  1.5, 1.0, 15 points, 4 of 6, 3 of 4)
- any target other than 100 ticks; any stop other than 40 / 60 / 80;
  any limit other than 1800 s
- any level not named in §1
- trailing stops, break-even moves, partial exits, scaling
- machine-learned models of any kind
- a rule read off the §7 census
- additional instruments
- live, paper or simulated order placement

## 10. Implementation record

Filled in by the commit that adds `mrofyt_bigmove.py` and
`tests_mrofyt_bigmove.py`. The module is written against this file;
where the code is more precise than the text, the precision is recorded
there and does not change a threshold.
