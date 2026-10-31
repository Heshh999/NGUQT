# MROF_YT_WAVE9_L2TARGETS_REGISTRATION.md — L2 without the fixed 25-point target: the next big level, or a target scaled to the day: registered before any held-out read

**Status: FROZEN on 2026-10-31, before any replay holdout or validation
session was read by any tool.** Every L2 test so far used one fixed
target, 25 points. The operator asked whether the target can come from
the market instead. Two ways had never been tried on L2:

- **NEXT LEVEL:** aim for the next big level in the trade's direction
  (wave seven tried "the next level" with the small swing levels, which
  stood too close to leave room);
- **SCALED:** a target that grows on wild days and shrinks on quiet ones,
  25 points on a typical day.

Both are registered here as rules, each judged **against the fixed 25
on the same trades**, before the sessions that judge them are read.
Wave five's exits (tape signs, a 10-point trail) and wave seven's tape
exit did not beat a fixed target on DEV; they are not repeated.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on recorded tape. No order is placed.

---

## 1. Trades

Wave eight's L2 events, unchanged: wave three's L2 fires de-duplicated by
the pilot's 60 s rule, traded against the approach, entry at the first
fire's mid, each with its test number (wave eight §2). Two sets:

- **ALL:** every L2 event (wave six's T1 trades);
- **FIRST:** test number 1 (wave eight's V1).

Every trade has the same **60-tick (15-point) stop** and the same
**1 800 s** limit as wave six's T1; only the target differs. Mid-to-mid
on the run's compressed path (wave six's `path_exit`); a trade whose run
ends before any of its three versions resolves is dropped from all
three.

## 2. The three targets

| target | rule |
| --- | --- |
| **FIXED** | 100 ticks (25 points), as before |
| **NEXT LEVEL** | among yesterday's high and low, the overnight high and low, last week's high and low and the session VWAP, as the runner holds them at the fire, the nearest one **ahead of the entry by at least 40 ticks (10 points)**; the target is **2 ticks short of it**; no cap. No such level: 100 ticks |
| **SCALED** | `100 ticks × A / A_ref`, clamped to **40–300 ticks (10–75 points)**. `A` = the mean high-to-low range of the instrument's previous recorded sessions, the last 14 at most and **5 at least** (fewer: 100 ticks). `A_ref` = the median `A` over the DEV L2 events of that instrument, computed by the DEV run and frozen |

`A` uses only sessions that closed before the trade's session; `A_ref`
uses no outcome.

## 3. Costs

`mrofyt_costs`' round trip on every trade: $5 commission on NQ ($2 on
MNQ), a tick of spread, a tick of slip on a stop.

## 4. The four tests (NQ; MNQ reported beside)

Each tests whether the target **beats the fixed 25 on the same trades**:
the per-trade difference `net(target) − net(FIXED)`, its mean above
zero, session-clustered (wave four's estimator), Student t on `G − 1`
degrees of freedom, **Holm over the four** at 0.05.

| id | trades | target against FIXED |
| --- | --- | --- |
| **N-ALL** | ALL | NEXT LEVEL |
| **S-ALL** | ALL | SCALED |
| **N-FIRST** | FIRST | NEXT LEVEL |
| **S-FIRST** | FIRST | SCALED |

| NQ trades | result | verdict |
| --- | --- | --- |
| `< 30` | — | NOT TESTED |
| `>= 30` | fails Holm, or mean difference `<= 0` | no better than 25 points |
| `>= 30` | survives Holm, mean difference `> 0`, 95 % interval above 0 | the target beats 25 points: a sizing and execution study, **still no live orders** |

Reported beside, not tested: each version's own win rate and net points
a trade; trades that fell back to 100 ticks; and, for every trade, its
**maximum favourable excursion** (MFE): the furthest the mid went in the
trade's favour before the stop or the 1 800 s limit, **not stopped at
any target**, as shares reaching 25 / 40 / 60 / 100 points.

## 5. Where it is judged

- **DEV** (sessions `<= 20260918`): describes only; computes and
  writes `A_ref` (`--frozen-out`), committed before any held-out read.
- **Replay holdout** (`--evaluate <frozen> --holdout`): a folder holding
  ONLY NinjaTrader Market Replay recordings of sessions **before
  2026-09-01**; refused if it holds any later session. Read once,
  recorded in `MROF_REPLAY_HOLDOUT_EXPOSURE.json`. Waves six to nine are
  all registered before anyone has read the replay folder.
- **Validation** (`--evaluate <frozen> --unblind`, sessions `>=
  20260921`) at the December checkpoint; it marks every session it
  reads `EXPOSED_PILOT_DEV` for good.

## Explicitly NOT registered

- any other level set (pivots, the opens, VWAP bands, swing levels), a
  distance floor other than 10 points, a buffer other than 2 ticks, a
  cap on NEXT LEVEL
- any other range measure (one-minute ATR, the overnight or cash range,
  another look-back), another reference than the DEV median, another
  clamp
- scaling the stop, trailing or partial exits, a hold limit other than
  1 800 s, the morning window or wave eight's other variants combined
  with a new target
- choosing between NEXT LEVEL and SCALED on DEV results (all four are
  judged)
- machine-learned models of any kind
- live, paper or simulated order placement

## Implementation record — 2026-10-31

`mrofyt_l2targets.py`, `tests_mrofyt_l2targets.py`. Written against
this file before any real session was read by it; verified on
hand-built paths and states and on synthetic recorder-format runs,
never on market evidence.

| registered | implemented as | precision |
| --- | --- | --- |
| §1 | `TargetRunner` (wave eight's runner), `target_events` | the levels and `A` travel with the event's first fire |
| §2 | `next_level_target`, `scaled_target`, `TargetRunner._record_range` | a session's range is the runner's own high and low of its recorded trade prices (the ones yesterday's levels come from), taken at the session close |
| §4 | `score_targets`, `mfe`, `paired_stats`, `table` | the difference is taken on net points; a trade appears in a test only when all three of its versions resolved |
| §5 | `plan()` with `--holdout` (wave six's), `record_holdout_read`, `record_exposure` | none |
