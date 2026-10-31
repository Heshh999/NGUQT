# MROF_YT_WAVE10_CLOSERECLAIM_REGISTRATION.md — break and reclaim on candle closes at the big levels, filtered by the order flow: registered before any held-out read

**Status: FROZEN on 2026-10-31, before any replay holdout or validation
session was read by any tool.** L2 (wave three) fades a failed test of a
big daily level within seconds of the order flow flipping: on a candle
chart, a wick. The operator asked for the same principle on candle
closes: a one-minute candle **closes through** the level (the break is
accepted for a moment), price stays beyond it for up to five minutes,
a candle **closes back** inside, and the order flow must confirm the
reclaim. It is registered here as its own test, with L2 reported beside
it from the same read, before the sessions that judge it are read.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on recorded tape. No order is placed.

---

## 1. Levels and candles

- **Levels:** wave three's six range levels as the runner holds them:
  yesterday's high and low, the overnight high and low (known from
  09:30 ET), last week's high and low. Read at each candle's close from
  the 10 s grid record that ends at that close.
- **Candles:** one-minute candles of the recording run's mid path; a
  candle's **close** is the last mid before the minute ends (a minute
  with no change closes where the one before did). A minute whose close
  has no grid record (the book not ready) is skipped. Nothing is ever
  spliced across two runs.
- **Side:** a close is **above** a level when it is at least 1 tick
  above it, **below** when at least 1 tick below, otherwise **at** it.

## 2. The event

- **Break:** a close on one side of a level when the last close that
  was not *at* the level was on the other side. Its direction `b` is the
  side it closed on (+1 above).
- **Reclaim:** within the **5 one-minute candles** after the break
  candle, a close back on the original side. The first such close ends
  the episode. With none, the break **held** and the episode ends with
  no trade (a later close back is a new break the other way).
- **Order-flow filter at the reclaim close:** both of
  - the reclaim candle's net aggressive delta (the sum of its six 10 s
    grid ticks) is in the reclaim direction (`-b`), and
  - the 10 s grid tick ending at the close shows aggression in the
    reclaim direction with the frozen side-signed z `z_delta_s >= 1.0`.
- **Trade:** at the reclaim close, against the break (`-b`), entry at
  that mid. Any hour.
- **Test number:** break episodes are counted per instrument, session
  and level, in order; the **first test** is the first break of that
  level in the session.

## 3. Exit and costs

Wave six's T1 exit, unchanged: target 100 ticks (25 points), stop 60
ticks (15 points), 1 800 s, mid-to-mid on the run's path (`path_exit`);
a trade whose run ends first is dropped. `mrofyt_costs`' round trip:
$5 commission on NQ ($2 on MNQ), a tick of spread, a tick of slip on a
stop.

## 4. The two tests (NQ; MNQ reported beside)

| id | trades |
| --- | --- |
| **C1** | every reclaim that passes the order-flow filter |
| **C2** | the same, first test of the level only |

Each tests the **mean net result per trade above zero**,
session-clustered (wave four's estimator), Student t on `G − 1`
degrees of freedom, **Holm over the two** at 0.05. Every event counts,
as in waves six and eight; one position at a time is reported beside.

| NQ trades | result | verdict |
| --- | --- | --- |
| `< 30` | — | NOT TESTED |
| `>= 30` | fails Holm, or mean net `<= 0` | no signal |
| `>= 30` | survives Holm, mean net `> 0`, 95 % interval above 0 | promising: a sizing and execution study, **still no live orders** |

Reported beside from the same read, not tested: every reclaim **without**
the filter (all, and first test), and L2 itself (wave eight's V0 and
V1), so the filter's effect and the candle-close version against the
wick version can be read on the same days.

## 5. Where it is judged

- **DEV** (sessions `<= 20260918`): describes only. Nothing is frozen
  from it: every setting is in this file.
- **Replay holdout** (`--holdout`): a folder holding ONLY NinjaTrader
  Market Replay recordings of sessions **before 2026-09-01**; refused if
  it holds any later session. Recorded in
  `MROF_REPLAY_HOLDOUT_EXPOSURE.json`.
- **Validation** (`--unblind`, sessions `>= 20260921`); it marks every
  session it reads `EXPOSED_PILOT_DEV` for good.

## Explicitly NOT registered

- any other candle length, break distance, reclaim window, filter
  measure, z threshold or flow window; a filter on the break candle
- any other level set (VWAP, pivots, the opens, swing levels)
- any other stop, target or hold limit; a structural stop; a trailing
  or partial exit; the morning window or wave nine's targets combined
  with this event
- trading the held break (that is wave six's L4 and wave seven's HELD)
- choosing between C1 and C2 on DEV results (both are judged)
- machine-learned models of any kind
- live, paper or simulated order placement

## Implementation record — 2026-10-31

`mrofyt_closereclaim.py`, `tests_mrofyt_closereclaim.py`. Written
against this file before any real session was read by it; verified on
hand-built candles and grids and on synthetic recorder-format runs,
never on market evidence.

| registered | implemented as | precision |
| --- | --- | --- |
| §1 | `CloseRunner` (wave nine's runner) puts the six levels on every grid record; `minute_closes`, `side` | candles cover every minute from a run's first mid to its last |
| §2 | `episodes`, `flow_ok` | the five candles are counted in clock minutes; a skipped minute still counts |
| §3–§4 | `score_close`, `table` | the L2 rows come from wave eight's functions on the same runner |
| §5 | `plan()` with `--holdout` (wave six's), `record_holdout_read`, `record_exposure` | none |
