# MROF_YT_WAVE22_STRETCHFADE_REGISTRATION.md — a failed break faded back toward VWAP from a stretched price, on years of one-minute bars

**Status: FROZEN on 2026-11-17, before any minute export was read for
this question.** No tool in this repository has measured a failed break
of the six levels split by the distance from VWAP on minute bars.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on historical bars. No order is placed.

---

## 0. Where the question comes from (seen, so this is motivation and not evidence)

The one-read checkpoint (13–17 November 2026) read every recorded
session through 2026-11-13; all 55 are `EXPOSED_PILOT_DEV`. None of its
67 tests passed. Wave fourteen's headline came back NOT PROVEN: 48
trades, +1.02 points a trade.

Read afterwards from that report and from the September (DEV) report:
wave twelve's TREND filter was registered to **remove** an L2 fade taken
back toward VWAP when the price is at least `0.25 × A` from it. It
separated the trades the other way round. One position at a time, net
of costs:

| read | instrument | removed by the filter (stretched, fading toward VWAP) | kept |
| --- | --- | --- | --- |
| unseen days | NQ | 104 trades, 46.2 % won, +2.83 | 306 trades, 34.6 % won, −1.78 |
| unseen days | MNQ | 91 trades, 46.2 % won, +2.51 | 207 trades, 35.7 % won, −1.63 |
| September | MNQ | 29 trades, 48.3 % won, +2.93 | 52 trades, 34.6 % won, −1.24 |
| September | NQ | 19 trades, 47.4 % won, +4.40 | 48 trades, 52.1 % won, +5.64 |

The registered difference (kept minus removed, expected above zero) read
−3.95 on NQ (p 0.068) and −4.80 on MNQ (p 0.081) on the unseen days.

What limits this: the September NQ "kept" cell is the one L2 was chosen
from; NQ and MNQ are one market; and this is one cut among many made
after 67 tests had failed. It is a lead with a low prior. On the
recordings it yields about 13 trades a week, so they could not settle it
for months.

Earlier minute-bar studies in this repository (NQ and MNQ, 2019–2026)
lower the prior further:

- plain VWAP reversion lost (`docs/RVMR_STRAT_V1_FINDINGS.md`, B4:
  6 966 trades, −1.10 points a trade, significantly negative);
- fading a 15-minute structure break 2 ATR or more from VWAP lost in
  both its splits (`docs/NSERIES_FINDINGS.md`, N10: −3.15 and −1.66 at
  60 minutes);
- the gap between the close and VWAP closes with a median half-life of
  106 minutes (`docs/ANOMALY_SCAN_V1_FINDINGS.md`), slower than this
  trade's 30.

None of them traded a failed break of yesterday's, last week's or the
overnight high or low, which is what this file adds.

Part 16A-R on the same read: the one-minute signal **without** order
flow won 45.6 % of 57 NQ trades, wave fourteen's with order flow 41.7 %
of 48. The order flow did not add, so the question can be put to minute
bars, which hold years.

## 1. Bars

NQ one-minute exports, read exactly as part 16A-H reads them: the
context study's reader, time-stamp check and front contract; nothing
from 2026-07-01; every bar of the CME session (18:00 ET to 17:00 ET).
Each bar's volume is kept as well.

## 2. Levels and the signal

Part 16A §A2 and §A3, unchanged: yesterday's, last ISO week's and the
overnight high and low; a bar trades 2 ticks or more through a level
from one side, and that bar or one of the next 4 closes back; the signal
is that close, fading the break.

**Every signal** is used, not only the first at a level.

## 3. The stretch

At the signal bar's close `c`:

- **VWAP** = the sum of `(high + low + close) / 3 × volume` over the sum
  of `volume`, over the session's bars from 18:00 ET up to and including
  the signal bar (bars with volume only). The recordings' session VWAP
  is the same sum over trades.
- **A** = the mean full-session high-to-low range of the previous
  sessions in the read, each on its own front contract, the last 14 at
  most and **5 at least** (wave nine's measure).
- **STRETCHED:** `|c − VWAP| >= 0.25 × A` **and** the fade trades back
  toward VWAP (a short with `c` above it, a long with `c` below it).
  This is wave twelve's `classify`, the trades its TREND filter
  removed, with 0.25 unchanged.
- **REST:** every other signal that has `A` and a VWAP.
- A signal without `A` or without a VWAP is in neither group and is
  counted apart.

## 4. The trade

Part 16A §A4, unchanged: target 25 points, stop 15 points, 30 minutes
from the signal close; first touch on the following bars' highs and lows
(a bar touching both is a stop); `mrofyt_costs`' round trip on every
trade. One position at a time within STRETCHED, and separately within
REST.

## 5. The two tests (NQ), in each era

| id | question | passes when |
| --- | --- | --- |
| **ST1** | the stretched fade makes money | mean net points a trade above 0 with its 95 % interval above 0, **month-clustered**, and still above 0 without the month of the largest total net; at least 100 trades |
| **ST2** | the stretch separates | mean net of STRETCHED minus mean net of REST above 0 with its 95 % interval above 0, month-clustered over both groups at once (part 16A-R's estimator); at least 100 trades on each side |

**Holm over the two** at 0.05. PASS, or NOT PROVEN with the reason;
under 100 trades, NOT ENOUGH TRADES.

## 6. The two eras

| era | sessions | how it is read |
| --- | --- | --- |
| **NEWER** | 2019-06-01 to 2026-06-30 | without a flag |
| **OLDER** | before 2019-06-01 | `--unblind`, recorded in `MROF_MINUTE_HISTORY_EXPOSURE.json` |

Each era is a test of this rule. The rule comes from recordings of
September to November 2026, which the history never holds. The newer
years were read by this repository's earlier minute-bar studies for
other questions; none measured a failed break against the distance from
VWAP.

- **CONFIRMED:** ST1 passes in both eras.
- **ONE ERA ONLY:** the export holds fewer than 100 STRETCHED trades
  before 2019-06-01, and ST1 passes in the newer era. This is weaker and
  is reported as such.
- Anything else: the lead is dropped.

Nothing is changed between the two reads.

## 7. Beside, not tested

By year; longs and shorts apart; by level; the same split on the first
signal at each level only; REST's own result; every signal unsplit (part
16A's "every"); the number of signals without `A` or a VWAP.

## 8. What a verdict leads to

- **CONFIRMED:** a later registration on the recordings' fresh sessions
  (from 2026-11-16), with real ticks and a simulated forward test.
- **Still no live orders** in any case. Real F5 compilation and the
  genuine smoke test are user-side.

## Explicitly NOT registered

- any stretch other than `0.25 × A`; another scale (an ATR, a fixed
  number of points); the VWAP bands; a VWAP anchored anywhere else
- the first signal at a level as a test; other levels; another signal
- other targets, stops or hold limits; a limit entry
- a search over years, hours, weekdays or directions
- order flow; MNQ; anything from 2026-07-01 on
- machine-learned models of any kind
- live, paper or simulated order placement

## Implementation record — 2026-11-17

`mrofyt_stretchfade.py`, `tests_mrofyt_stretchfade.py`. Written against
this file before any minute export was read; verified on hand-built bars
and on synthetic NinjaTrader-format exports, never on market evidence.

| registered | implemented as | precision |
| --- | --- | --- |
| §1 | `VolReader`, `history_sessions` (part 16A's, with the volume and `A`) | the same sessions, bars and levels as `mrofyt_minutelevels.history_sessions` |
| §2 | `ML.signals`, `ML.session_levels` | part 16A's code |
| §3 | `rows_vwap`, `X.classify` (wave twelve's), `history_sessions` for `A` | `A` uses the sessions that have a complete cash session, in date order |
| §4 | `take` (part 16A's loop), `ML.outcome_bars`, `ML.net_points` | none |
| §5 | `ML.month_verdict`, `SMT.diff_stats`, `BM.holm` | none |
| §6 | `run`, `main`, `LG.record_history_read` | none |
