# MROF_YT_WAVE15_OBVIOUSLEVELS_REGISTRATION.md — L2 at three more obvious levels: initial balance, round numbers, equal highs and lows

**Status: FROZEN on 2026-11-01, before any validation session (on or
after 2026-09-21) or replay holdout session was read by any tool, and
before any tool computed these levels on any recorded session.**

L2 fades a failed break of a level that many traders watch: stop and
breakout orders sit just beyond it, and when the break fails and the
order flow turns, those traders are trapped. The operator asked to add
three levels that are watched for that reason and were missing:

- **IB — the initial balance**, the 09:30–10:30 ET high and low, the
  level order-flow and market-profile traders mark every morning;
- **ROUND — round numbers**, every 100 points on NQ. Studies of
  currency order books (Osler, 2003) found take-profit orders clustered
  at round numbers and stop orders just beyond them, the setting L2
  trades;
- **EQUAL — equal highs and lows**, two swing highs (or lows) at about
  the same price: a more obvious level than one swing, so more stops
  sit beyond it.

No tool has computed these levels on any session; nothing here comes
from results.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on recorded tape. No order is placed.

---

## 1. The levels

All from the run's mids (the runner's compressed mid path), per
instrument; NQ and MNQ separately.

| group | level | known from | until |
| --- | --- | --- | --- |
| **IB** | `IB_HIGH`, `IB_LOW`: the highest and lowest mid from 09:30:00 to 10:29:59 ET | 10:30:00 ET | 17:00:00 ET the same day |
| **ROUND** | every price that is a whole multiple of 100.00 points | the session's start | the session's end |
| **EQUAL** | `EQ_HIGH`, `EQ_LOW` (§1.2) | the second swing's confirmation | a 15-minute candle closing a tick beyond it, or 5 more sessions |

### 1.1 Initial balance completeness

The IB exists only when the recording covers the window: a mid at or
before 09:31:00 ET, one at or after 10:29:00 ET, and no gap longer than
120 s between consecutive mids in between (runs of the session merged
in time order). Otherwise that session has no IB.

### 1.2 Equal highs and lows

- **15-minute candles** of the mid in Eastern time, starting on the
  quarter hour.
- **Swings** are wave eleven's rule on these candles: a candle's high
  above the 2 before it and not below the 2 after it, over five
  consecutive recorded candles (lows mirrored), confirmed at the close
  of the 2nd candle after. A swing stands until a later 15-minute candle
  closes a tick or more beyond it.
- **An equal high** is born when a swing high is confirmed within
  **4 ticks (1.00 point)** of an earlier swing high that is still
  standing and was confirmed in the same session or one of the 5 before.
  Its price is the higher of the two (the more recent earlier swing if
  several match). It lasts until a 15-minute candle closes a tick beyond
  that price, or 5 more sessions. An equal high within 2 ticks of one
  already active is not added again. Lows mirrored.

## 2. The signal and the trade

**The signal** is wave eleven's WICK entry, the 10-second L2 analogue,
unchanged:

- **Break:** a 10 s grid close a tick or more beyond the level, the last
  close not at it having been on the other side.
- **Entry:** the first 10 s grid tick within 300 s of the break where
  the mid is back a tick through and that tick's aggression is against
  the break (`z_delta_s >= 1.0`). The trade fades the break.

**The test** takes **only the first signal at each level per CME
session** (each IB level, each round number, each equal level), at any
hour the level exists.

**The trade:** target 100 ticks (25 points), stop 60 ticks (15 points),
1 800 s, mid-to-mid (wave six's `path_exit`); a trade whose run ends
first is dropped. `mrofyt_costs`' round trip on every trade. **One
position at a time** within each group and instrument.

## 3. The tests (NQ; three groups, Holm over three)

Each group is judged alone, on its own trades:

| NQ trades in the group | result | verdict |
| --- | --- | --- |
| `< 30` | — | NOT ENOUGH TRADES (§4) |
| `>= 30` | mean net a trade `> 0`; its session-clustered p survives **Holm over the three groups at 0.05** (a group without a p counts as not rejected); its 95 % interval above 0; and still `> 0` with the session of the largest total net removed | **PASS** |
| `>= 30` | anything else | **NOT PROVEN**, with the reason |

MNQ is reported beside and never tested. Every WICK signal at the
group's levels (not only the first) is reported beside, not tested.

## 4. Fewer than 30 trades: results withheld

On a held-out read, a group with fewer than 30 NQ trades shows **its
trade count and number of days only**. Its win rate, points, day table
and beside rows are withheld from the screen and from the report file,
on both instruments. The verdict for that group is taken at the first
read that holds 30. No threshold is lowered and no session is dropped.

## 5. Where it is judged

- **DEV** (sessions `<= 20260918`): describes only.
- **Validation** (`--unblind`, every session `>= 20260921`, including
  every session recorded after this file): a **secondary** test. Wave
  fourteen is the primary test of these sessions; this one is judged
  beside it under its own Holm. It marks every session it reads
  `EXPOSED_PILOT_DEV` for good.
- **Replay holdout** (`--holdout`): a folder holding ONLY NinjaTrader
  Market Replay recordings of sessions **before 2026-09-01**; judged by
  the same rule, separately.

## 6. What a verdict leads to

- **PASS:** the group may be added to L2's levels only in a later
  registration judged on sessions read by nothing before it.
- **NOT PROVEN:** the group is not shown to add an edge. Nothing is
  re-tuned on these sessions.

## Explicitly NOT registered

- other IB windows (first 5, 15 or 30 minutes; the overnight range),
  IB extensions
- round numbers every 50, 25 or 10 points; ES round numbers
- other candle lengths, swing widths, tolerances or lifetimes for equal
  highs and lows; three or more equal swings as their own group
- yesterday's settlement, options levels, anchored VWAPs, monthly levels
- EARLY or CLOSE entries at these levels; every signal as a test
- any time window, filter, other target, stop or hold limit
- combining a group with the six main levels before §6
- machine-learned models of any kind
- live, paper or simulated order placement

## Implementation record — 2026-11-01

`mrofyt_obviouslevels.py`, `tests_mrofyt_obviouslevels.py`. Written
against this file before any held-out session was read by it; verified
on hand-built paths, candles and grids and on synthetic recorder-format
runs, never on market evidence.

| registered | implemented as | precision |
| --- | --- | --- |
| §1 IB | `scan`, `ib_levels` | the Eastern offset is looked up once per UTC hour (`E.et_offset_hourly`) |
| §1 ROUND | `round_levels` | only the round numbers between the session's lowest and highest grid mid (plus one step each side) are listed; no other can be broken |
| §1.2 | `scan` (15-minute candles), `swings15`, `equal_levels` | none |
| §2 | `wick_events` (wave eleven's `run_episodes`, WICK mode, on these levels only), `first_signals` | a level's first signal is per (instrument, session, level) |
| §2 trade | `score` (wave six's `path_exit`), `V.one_at_a_time` | none |
| §3 | `group_verdicts` (wave fourteen's `verdict`, then Holm) | none |
| §4–§5 | `run` (`withheld`), `text`, `record_exposure`, `record_holdout_read` | none |
