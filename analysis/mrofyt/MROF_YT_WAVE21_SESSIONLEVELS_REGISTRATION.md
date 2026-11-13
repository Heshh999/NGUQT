# MROF_YT_WAVE21_SESSIONLEVELS_REGISTRATION.md — the Psy levels, the Tokyo and London ranges, the ADR lines

**Status: FROZEN on 2026-11-13, before any result from a validation
session (on or after 2026-09-21) or a replay holdout session existed.**

What is disclosed about the held-out sessions at this date:

- Two one-read checkpoint runs with `--unblind` were started (7 and
  8 November) and stopped before they finished. They wrote no report and
  no ledger entry, and no outcome from them was seen by anyone.
- The operator watches the market every day. While the Traders Reality
  Psy levels were being matched (Amendment 45), a chart of early
  November was seen and the operator read the chart's Psy-Hi and Psy-Lo
  of the weeks of 2 and 9 November (four prices). No rule below was
  chosen from any of it.

The operator trades with the Traders Reality indicator and asked for
three of its level kinds that no wave has tested: the weekly Psy high
and low, the Tokyo and London session ranges, and the ADR lines. None
of them was computed on any session, DEV included, before this file was
frozen.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on recorded tape. No order is placed.

---

## 1. The levels

Per instrument, NQ and MNQ separately. A **window** high or low is the
highest or lowest **trade** price in the window, from the trades the
runner hands to wave thirteen's profile (the indicator draws its lines
from the chart's highs and lows, which are trades).

| group | levels | window | known |
| --- | --- | --- | --- |
| **PSYC** | `PSYC_HI`, `PSYC_LO` | Monday 00:00:00–07:59:59 **GMT** | from the window's end to Friday 17:00 ET |
| **PSYH** | `PSYH_HI`, `PSYH_LO` | Sunday 22:00:00 – Monday 05:59:59 **ET** | from the window's end to Friday 17:00 ET |
| **ASIA** | `TOKYO_HIGH`, `TOKYO_LOW` | 00:00:00–05:59:59 **GMT** every day (the indicator's Tokyo session) | from the window's end to 17:00 ET that session |
| **LONDON** | `LONDON_HIGH`, `LONDON_LOW` | 08:00:00 **London time** to 09:29:59 ET | 09:30 ET to 17:00 ET that session |
| **ADR** | `ADR_HIGH`, `ADR_LOW` | moving, §1.3 | the whole session |

### 1.1 Why two Psy groups

The indicator's forex Psy calculation (`Traders_Reality_Lib`,
`calcPsyLevels`) takes the highest high and lowest low while
`time('240', '0000-0800:2', "GMT")` is in session. Its source does not
settle whether that is the chart's own candles inside Monday
00:00–08:00 GMT (**PSYC**: 19:00–03:00 ET in winter, 20:00–04:00 in
summer) or the 4-hour candles it names whose open falls there (**PSYH**:
the CME candles opening 22:00 and 02:00 ET). Both are registered as
they stand. `mrofyt_psycheck.py` identifies, from the chart's own
numbers and after the read, which of the two is the operator's line;
that is a fact about the indicator, read from no outcome.

### 1.2 Completeness of a window

The first trade within **120 s** of the window's start, the last within
120 s of its end, and no gap between consecutive trades longer than
**600 s**; otherwise that window gives no level. London time is GMT, or
GMT+1 from the last Sunday of March 01:00 GMT to the last Sunday of
October 01:00 GMT.

### 1.3 The ADR lines

At every 10 s grid record of a session:

- `A` = wave nine's measure, the mean high-to-low range of the
  instrument's previous recorded sessions, the last 14 at most and **5
  at least** (fewer: no ADR lines that session). It stands in for the
  indicator's 14-day average true range.
- `ADR_HIGH = (the session's lowest mid so far) + A`;
  `ADR_LOW = (the session's highest mid so far) − A`, from 18:00 ET.

These are the indicator's Hi-ADR and Lo-ADR while the day's range is
under the average; once it is over, this wave keeps the same formula.

## 2. The signal and the trade (five tests)

Wave fifteen §2, unchanged, at these levels only:

- **Signal:** wave eleven's WICK entry: a 10 s grid close a tick or more
  beyond the level, the last close not at it having been on the other
  side; entry at the first 10 s tick within 300 s where the mid is back
  a tick through and that tick's aggression is against the break
  (`z_delta_s >= 1.0`). The trade fades the break. The ADR lines are
  read on each grid record, as wave eleven reads VWAP.
- **Taken:** only the first signal at each level per CME session (a Psy
  level, which lasts the week, once per session).
- **Trade:** target 100 ticks (25 points), stop 60 ticks (15 points),
  1 800 s, mid-to-mid (wave six's `path_exit`), `mrofyt_costs`' round
  trip; one position at a time within each group and instrument.

| id | group |
| --- | --- |
| **PSYC** | the Psy levels, clock window |
| **PSYH** | the Psy levels, 4-hour-candle window |
| **ASIA** | the Tokyo session high and low |
| **LONDON** | the London high and low up to the New York open |
| **ADR** | the ADR lines |

## 3. Verdicts (NQ; MNQ described beside, never tested)

Wave fourteen's verdict on each group's own trades: 30 or more trades;
mean net per trade above 0 with its session-clustered 95 % interval
above 0; still above 0 without the session of the largest total.
**Holm over the five** at 0.05. **PASS**, or **NOT PROVEN** with the
reason; under 30, **NOT ENOUGH TRADES**.

Beside, not tested: every signal of each group, and the counts of
levels built.

## 4. Withholding and where it is judged

- A held-out read shows the count only for any group with fewer than 30
  NQ trades. A Psy group has two levels a week, so it is expected to be
  under 30 in this read and to show its count only.
- **DEV:** describes. **Validation** (`--unblind`): **secondary** tests,
  part of the one-read checkpoint from V47 on. **Replay holdout:**
  separately.
- Wave fourteen stays the headline. Five tests are added to a read that
  already holds about sixty-two; a pass here is a lead.

## 5. What a verdict leads to

A PASS admits that group to a later registration judged on sessions
read by nothing before it. Of PSYC and PSYH, only the one
`mrofyt_psycheck.py` matches to the chart is carried forward as "the Psy
levels"; the other is recorded and dropped.

## Explicitly NOT registered

- the crypto Psy calculation (Saturday night); the Psy lines while they
  are still forming; last week's Psy lines on the Sunday evening before
  the new window
- the Sydney, Hong Kong, New York, Frankfurt and Brinks boxes; the
  London range after 09:30 ET; session opening ranges
- the indicator's ADR from the daily open, its 50 % ADR lines, AWR, AMR,
  RD and RW; a true-range average
- further pivots (R2, S2, R3, S3, M0, M1, M4, M5), the daily open, the
  EMAs and their cloud, vector candle zones
- the EARLY or CLOSE entries at these levels; a second signal at a level
- any other target, stop or hold limit
- machine-learned models of any kind
- live, paper or simulated order placement

## Implementation record — 2026-11-13

`mrofyt_sessionlevels.py`, `tests_mrofyt_sessionlevels.py`. Written
against this file before any held-out result existed; verified on
hand-built trades, grids and paths and on synthetic recorder-format
runs, never on market evidence.

| registered | implemented as | precision |
| --- | --- | --- |
| §1, §1.1 | `SessionLevelsRunner` (wave twenty's runner, hooks only), `window_levels` | a window belongs to the CME session of its trades; its start and end are fixed from its first trade |
| §1.2 | `complete`, `uk_offset` | none |
| §1.3 | `adr_grid` | the session's lowest and highest mid so far come from the compressed mid paths of the session's runs up to each grid record |
| §2 | `OL.wick_events`, `adr_events` (wave eleven's `run_episodes`, the two lines carried in a grid record's level slots), `OL.first_signals`, `OL.score`, `V.one_at_a_time` | wave fifteen's code |
| §3 | `FS.verdict`, `PL.apply_holm` | none |
| §4 | `run`, `text`, the ledgers | none |
