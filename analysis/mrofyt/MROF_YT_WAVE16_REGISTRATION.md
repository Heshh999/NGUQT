# MROF_YT_WAVE16_REGISTRATION.md — L2's levels on years of minute bars, a limit entry for L2, and intraday momentum

**Status: FROZEN on 2026-11-02, before any tool computed any part of it
on any data: no minute export has been read for these questions, no
validation session (on or after 2026-09-21) or replay holdout session
has been read by any tool, and the years before 2019-06-01 have been
read by no study in this repository.**

After fifteen waves the operator asked for the three ideas that follow
from what was learned:

- L2 at the six big levels made money on DEV, but the recordings hold
  about nine usable sessions. **16A** tests the same levels without
  order flow on years of NQ minute bars, and on the recordings measures
  what the order flow adds.
- Costs take 2–3 ticks of every trade. **16B** tests a resting limit
  entry against entering at the signal.
- **16C** is an independent, published effect (Gao, Han, Li and Zhou,
  "Market intraday momentum", Journal of Financial Economics, 2018: on
  the S&P 500 ETF, the return from the previous close to 10:00 ET
  predicts the return of the last half hour), tested on NQ minute bars.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on recorded tape and exported bars. No order is
placed.

---

## Part 16A — L2's levels without order flow

### A1. Bars

- **History:** NQ one-minute exports, read exactly as the context study
  reads them: the same reader, stamp check and front contract, and
  nothing from 2026-07-01. Every bar of the CME session (18:00 ET to
  17:00 ET) is kept.
- **Recordings:** one-minute bars of each recording run's mid (high,
  low and last mid of each clock minute, the mid in force at the
  minute's start included).

### A2. Levels (as the runner defines them)

| level | history | recordings |
| --- | --- | --- |
| `YDAY_HIGH`, `YDAY_LOW` | the previous session's full-session high and low, same contract; that session's cash session complete | the runner's own (wave ten's copy on each grid record) |
| `LWEEK_HIGH`, `LWEEK_LOW` | high and low of every session of the same contract in the ISO week before the session's ISO week | the runner's own |
| `OVERNIGHT_HIGH`, `OVERNIGHT_LOW` | the session's bars from 18:00 to 09:29 ET; known from the 09:30 bar | the runner's own |

### A3. The signal (no order flow)

Per level and session, bars in time order. A close's **side** is +1 a
tick or more above the level, −1 a tick or more below, 0 otherwise
(wave ten's rule).

- **Break:** price on one side (its last non-zero close), a bar trades
  **2 ticks or more through** to the other side.
- **Failed break:** that bar or one of the next 4 **closes back** on the
  original side. The signal is that close, fading the break.
- **Held:** 5 bars without that close give no signal, and the side
  becomes the last non-zero close.

Only **the first signal at each level per session** is taken, at any
hour the level exists. One position at a time.

### A4. The trade

Target 25 points, stop 15 points, 30 minutes, from the signal close.

- **History:** first touch on the following bars' highs and lows (a bar
  touching both is a stop). Otherwise the close of the last bar that
  starts within the 30 minutes (TIMEOUT). Dropped if the session's bars
  end first.
- **Recordings:** wave six's `path_exit` on the mid path from the end of
  the signal minute.
- **Costs:** `mrofyt_costs`' round trip on every trade.

### A5. The tests

- **16A-H (history, NQ).** Mean net points a trade above 0 with its
  95 % interval above 0, **month-clustered**, and still above 0 with the
  month of the largest total net removed; at least 100 trades. Anything
  else with 100 trades is NOT PROVEN, with the reason.
  - **Describe:** sessions 2019-06-01 to 2026-06-30.
  - **Judge:** every session before 2019-06-01, read once (`--unblind`),
    recorded in `MROF_MINUTE_HISTORY_EXPOSURE.json`.
  - Every signal (not only the first) and the result by year are
    reported beside.
- **16A-R (recordings, NQ).** **Wave fourteen's L2 first signals (with
  order flow) minus this rule (without), on the same sessions:** the
  difference in mean net a trade, session-clustered (wave six B's
  influence-function estimator), above 0 with its 95 % interval above 0,
  each side with at least 30 trades.
  - Secondary to wave fourteen.
  - A held-out read with fewer than 30 on either side withholds every
    result (wave fourteen's §5).
  - DEV describes.

## Part 16B — a limit entry for L2

- **Signals:** wave fourteen's (the first L2 signal at each level per
  session), every one; NQ tested, MNQ beside.
- **MARKET** (the reference): wave fourteen's trade, entered at the
  signal mid.
- **LIM2 / LIM4:** at the signal, a limit order **2 ticks / 4 ticks
  better** than the signal mid (above it for a short, below for a long),
  live for **60 s**.
  - **Fill:** it fills only when the mid trades **a full tick through**
    the limit price within those 60 s. That is conservative: every order
    ahead in the queue is assumed to fill first.
  - **Trade:** the fill is at the limit price, at that moment. Then the
    same bracket (25 / 15 / 30 minutes), measured from the limit price on
    the mid path.
  - **Unfilled:** no trade, 0 points.
  - **Costs:** as for MARKET; no spread saving is credited.
- **Improvement:** each signal's limit result (0 if unfilled) minus its
  MARKET result, net points. A signal either version leaves unresolved
  is dropped from both.
- **Test (NQ):** mean improvement above 0 with its 95 % interval above
  0, session-clustered, **Holm over LIM2 and LIM4** at 0.05; at least 30
  signals.
  - Beside: the fill rate, the winners missed by not filling, and the
    mean on filled signals.
  - A held-out read with fewer than 30 signals withholds every result.

## Part 16C — intraday momentum

- **Data:** NQ minute exports as in A1, sessions whose cash session is
  complete (the context study's rule), with the previous session of the
  same contract complete.
- **Signal:** `r` = the close of the 09:59 bar (the 10:00 ET price)
  minus the previous session's cash close (its 15:59 bar). Long when
  `r > 0`, short when `r < 0`, no trade at 0.
- **Trade:** enter at the close of the 15:29 bar, exit at the close of
  the 15:59 bar (15:30 to 16:00 ET). No stop, no target. A day without
  those bars has no trade.
- **Net:** `mrofyt_costs`' round trip (no stop slip).
- **Test (NQ):** mean net points a day above 0 with its 95 % interval
  above 0, **month-clustered**, and still above 0 with the month of the
  largest total net removed; at least 250 days.
  - **Describe:** 2019-06-01 to 2026-06-30.
  - **Judge:** before 2019-06-01, read once (`--unblind`), recorded in
    `MROF_MINUTE_HISTORY_EXPOSURE.json`.
  - Beside: by year, and longs and shorts apart.
- The published sample (1993–2013, an ETF, not NQ) overlaps the judged
  years. Those years are untouched by this repository, not by the
  literature.

## What a verdict leads to

- **16A-H PASS:** L2's levels carry an edge without order flow over
  years, so the recordings only have to show what order flow adds.
- **16A-R PASS:** the order flow adds to it.
- **16B PASS:** the limit entry replaces the market entry in a later
  registration, judged on sessions read by nothing before it.
- **16C PASS:** a second, independent strategy for a sizing and
  execution study.
- **Still no live orders** in any case. Real F5 compilation and the
  genuine smoke test are user-side.

## Explicitly NOT registered

- **16A:** other break or close-back distances, windows or levels; ES;
  an RTH-only version; a combination with order-flow filters other than
  wave fourteen's.
- **16B:** other offsets, lifetimes or fill rules; a limit at the
  level; partial fills; queue modelling; crediting the spread saved.
- **16C:** the 15:00–15:30 half hour as a signal; volatility or event-day
  filters; other entry or exit times; stops or targets; ES.
- Machine-learned models of any kind.
- Live, paper or simulated order placement.

## Implementation record — 2026-11-02

`mrofyt_minutelevels.py`, `mrofyt_limitentry.py`,
`mrofyt_intradaymom.py` and one suite each. Written against this file
before any of it was computed on any data; verified on hand-built bars,
paths and grids, synthetic NinjaTrader-format exports and synthetic
recorder-format runs, never on market evidence.

| registered | implemented as | precision |
| --- | --- | --- |
| A1 | `FullDayAgg` / `FullReader` (the context study's reader), `minute_bars` | a minute with no new mid is flat at the mid in force |
| A2 | `history_sessions` | the context study's eligible sessions: a complete cash session with 14 earlier sessions in the same read (its ATR rule), so the first 14 sessions of each read are not traded |
| A3 | `signals`, `first_per_level` | none |
| A4 | `outcome_bars`, `LB.path_exit` | none |
| A5 | `month_verdict`, `run_history`, `run_recordings` (`SMT.diff_stats` by session) | none |
| 16B | `limit_result`, `run` | none |
| 16C | `MomDayAgg`, `momentum_days`, `run` | the same eligible sessions as A2 (14 earlier sessions in the read) |
