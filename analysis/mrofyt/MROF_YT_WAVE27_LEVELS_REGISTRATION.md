# MROF_YT_WAVE27_LEVELS_REGISTRATION.md — every key level, every way of trading it, counted

**Status: FROZEN on 2026-11-26, before any of the rules below was
computed on any data.** What had been seen beforehand is listed in §0.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on historical bars. No order is placed.

---

## 0. Where this comes from, and what was already seen

The operator asked, on 2026-11-26, for the widest possible search:
every idea that quant research, trading books, forums and well-known
futures traders offer for NQ, ES, QQQ and SPY, with key levels and
swing highs and lows in particular, and trades lasting from about 15
minutes to 3 hours.

Testing many ideas and keeping what looks good produces lucky winners in
proportion to the number tested. This file therefore fixes, before
anything is computed: **every strategy that will be run (877), the 181
hypotheses they are counted as, half of the weeks locked away unread,
and the rule by which a hypothesis is confirmed on them.**

The public ideas collected on 2026-11-26 (appendix) reduce, almost
without exception, to one sentence: *price reaches a level, and then
either goes through or turns back.* They differ in the level, in which
of the two they expect, in whether they wait for a retest, and in the
time of day. This wave runs all of those combinations instead of a
chosen few.

**Seen beforehand on NQ's ten years of minute bars (2016-01 to
2026-06-11):** the fifteen rules of wave twenty-four (A, B and E
passed; ten failed); part 16A, waves twenty-two and twenty-three (the
failed break of yesterday's, last week's and the overnight high and low
faded on one-minute bars lost, also when taken from a stretched VWAP;
two VWAP-zone rules and the overnight value area's accepted break
failed); A's three changes and the prop account of wave twenty-six.
**None of the 877 strategies below has been computed on any bar.** That
breakouts from the open (A, B) passed the screen and fades at daily
levels lost is known, and shaped which side of each event is called its
"own" direction; both directions are tested and counted.

## 1. Not tested here, because it was already judged on these bars

Wave twenty-four fixed that no variant of a failed rule is tried on
these bars. Not in this wave, in any form:

| judged before | so not here |
| --- | --- |
| D, the VWAP trend; wave twenty-three's VWAP zones | VWAP as a level, in any event |
| O5, big half-hour moves continue or fade; Q2, a shock gives part back | momentum or reversal from the size of a recent move; news-time shocks |
| C, the last half hour follows the day | any entry from 15:30 |
| O1, O4, Q4: the night and the day against or with each other | gap fades, gap continuations, the night's direction |
| Q1, Q3, Q5: half-hour, turn-of-month and month-end seasonality | any calendar rule |
| part 16A and wave twenty-two: the failed break of yesterday's, last week's and the overnight high and low, faded | the rejection and the failed breakout at those three (the break and its retest there are new) |
| wave twenty-three: the overnight value area | value-area levels |

## 2. Bars, sessions, the grid

- **Bars, front contract, eligible sessions, the daily chain, A, B, E:**
  wave twenty-four's. **Reader, markets, costs:** wave twenty-five's
  (NQ: 0.50 points a round trip; no stop is used in this wave).
- **The grid:** one-minute bars of the session's front contract from
  18:00 ET the evening before to 16:00. A minute without a bar carries
  the last close, with no range and no volume. P(t) is the last close
  before clock time t.
- **A usable session** is eligible by wave twenty-four and has s, the
  standard deviation of the 14 daily returns before it (B's own).
  Overnight families need, besides, a bar in the first hour and 600 of
  the 930 minutes from 18:00 to 09:30 with a bar.
- **The unit R.** A trade's result is its signed move minus the cost,
  over the entry price, **divided by s**: a share of a normal day's
  move. This is risk-sized trading: the same risk on a quiet and on a
  wild day.

## 3. The levels

Each level is a price fixed before the bar that tests it.

| group | levels | first bar that may test it |
| --- | --- | --- |
| PDX | yesterday's cash-session high and low (same contract) | 09:30 |
| ONX | the overnight high and low, 18:00–09:30 | 09:30 |
| PWX | last ISO week's high and low (same contract, weekday sessions, whole sessions) | 09:30 |
| PDC | yesterday's cash close (same contract) | 09:30 |
| OPN | today's open, P(09:30) | 10:00 |
| OR15 | the high and low of 09:30–09:45 | 09:45 |
| IB60 | the high and low of 09:30–10:30 | 10:30 |
| AMX | the high and low of 09:30–12:00 | 12:00 |
| HRX | at each of 10:00, 11:00, …, 15:00: the high and low of the 60 minutes before | that hour |
| RND | every multiple of 100 index points | 09:30 |
| SW5 | swing highs and lows of 5-minute bars from 09:30: a bar's high above the three highs before it and not below the three after (lows alike) | the bar after the third bar following it |
| SW15 | the same on 15-minute bars | likewise |
| ASIA | the high and low of 18:00–02:00 | 02:00 |
| EUR | the high and low of 02:00–08:00 | 08:00 |

## 4. The events, and each one's own direction

A level is in one of three states. Bars are judged at their close;
"before" is the close of the bar before.

- **Untested.** The first bar that reaches it — from below: its high at
  or above the level with the price before below it; from above
  likewise — is either a **break (BRK)**, when it closes beyond the
  level, or a **rejection (REJ)**, when it does not. After a rejection
  the level is finished for the session.
- **Broken.** The first later bar that comes back to the level is
  either a **retest (RET)**, when it closes on the side the break went
  to, or a **failed breakout (FBK)**, when it does not. Then the level
  is finished.

| event | its own direction | the public idea |
| --- | --- | --- |
| BRK | with the break | breakout, break of structure |
| REJ | away from the level | rejection, liquidity sweep, double top |
| RET | with the break | break and retest |
| FBK | against the break | failed breakout, fake-out, trap |

**SQZ, the squeeze.** At a bar from 10:00: W = the highest high minus
the lowest low of the 30 bars before it; contracted when W is below half
the median W at that minute over the 14 previous usable sessions. A
close above that high (below that low) while contracted is a BRK, own
direction with it; once a side a session.

## 5. Families, strategies, hypotheses

- **A family** = group × event × entry window. Windows by the entry
  bar's start: **AM** 09:30–11:29, **PM** 11:30–15:29; ASIA events are
  entered 02:00–07:59, EUR events 08:00–09:29.
- **Entry** at the close of the event's bar. **Exit** H minutes later
  (cash-session families no later than 16:00). H = 15, 30, 60, 120, 180
  (ASIA: 30, 60, 120, 180; EUR: 15, 30, 60). **A strategy** = a family ×
  H × a direction; it holds one trade at a time (an event while it is in
  a trade is passed over).
- **A hypothesis** = a family in one direction: the equal-weight mean
  of its strategies' daily results. Its **mirror** (every trade
  reversed, paying the same costs) is another hypothesis.

| groups | events | windows | families |
| --- | --- | --- | --- |
| PDX, ONX, PWX | BRK, RET | AM, PM | 12 |
| PDC, OPN, OR15, IB60, HRX, RND, SW5, SW15 | BRK, REJ, RET, FBK | AM, PM | 64 |
| AMX | BRK, REJ, RET, FBK | PM | 4 |
| SQZ | BRK | AM, PM | 2 |
| ASIA | BRK, REJ, RET, FBK | 02:00–08:00 | 4 |
| EUR | BRK, REJ, RET, FBK | 08:00–09:30 | 4 |

90 families; 438 strategies and their 438 mirrors; 180 hypotheses.

**EPROP, E for a prop account** (one more strategy and hypothesis, no
mirror). E's own signal on the daily chain, unchanged (bought at a
close with IBS below 0.1, sold at the first close with IBS above 0.9).
A prop account must be flat over the daily break, so instead of holding
from close to close EPROP is long **each session from the day after the
buy to the day of the sell**, from the first bar's close after 18:00
(within the first hour) to P(16:00), paying a round trip a session. Its
daily result is that return minus the cost, minus the mean such return
of all usable discovery sessions, in R.

**In all: 877 strategies, 181 hypotheses.**

## 6. Half of the weeks are locked away

Every ISO week is **discovery** or **lockbox**, fixed by its label:
lockbox when the first eight hex digits of SHA-256 of `YYYY-Www` are an
odd number. Stage 1 computes nothing on a lockbox session; a lockbox
session's bars serve only as history (yesterday's levels, the 14-day
medians).

## 7. The statistics

For a hypothesis, on the usable sessions of a set (a session without a
trade counts 0):

- **raw** = its mean daily result in R;
- **what A and B already earn is taken out:** its daily result is
  regressed on A's and B's daily results (each one contract, no sizing,
  in R) over the discovery sessions; alpha = the daily result minus
  those two slopes times A's and B's. A copy of A or B has no alpha;
- **t** = the mean of alpha's weekly sums over its standard error, the
  weeks of the set as the observations; p one-sided from Student's t.

## 8. The two stages, and what follows

**Stage 1, discovery weeks.** A hypothesis goes forward when its
strategies average 150 trades or more, its raw mean is above 0, at
least 60 % of its strategies have a raw mean above 0, and t ≥ 2.5. At
most the twelve with the highest t go forward. With no edge anywhere,
about one of the 181 would reach t ≥ 2.5 by luck.

**Stage 2, lockbox weeks, read once.** For those forwarded, with stage
1's slopes: Benjamini–Hochberg at 10 % over their one-sided p. A
hypothesis is **CONFIRMED** when it is rejected there and its raw mean
on the lockbox is above 0. Of those confirmed, one in ten at most is
expected to be luck.

**After stage 2, each read once and fixed in its own file first:** ES
and RTY on the same weeks; NQ's months from 2026-07-01 to 2026-11-13;
then the sessions from 2026-11-16, tracked without orders. Sizing,
stops and combining what is confirmed come after confirmation, never
before.

A hypothesis that is not confirmed is dropped; no variant of it is tried
on these bars.

## Explicitly NOT registered

- any level, event, window, hold, threshold or direction other than
  §3–§5; choosing among a family's strategies
- any rule of §1
- stops, targets, sizing other than R, filters by volume, volatility,
  trend or weekday
- other markets and cross-market rules (a later wave, once ES and RTY
  are read)
- options, order flow, machine-learned models
- a second read of the lockbox weeks
- live, paper or simulated order placement

## Appendix — the public ideas collected on 2026-11-26, and where each went

| idea, and where it is told | in this wave as | or |
| --- | --- | --- |
| Opening range breakout, 5 minutes (Zarattini and Aziz) | | A, wave twenty-four: passed the screen. An independent replication on five index CFDs finds the gross result and nothing after CFD costs: the reason §2c of wave twenty-five measures the cost |
| ORB on busy opens; the stop from the day's range (Zarattini, Barbon, Aziz) | | A1, A2: wave twenty-six |
| Noise-area intraday momentum (Zarattini, Aziz, Barbon) | | B: passed the screen |
| VWAP trend (Zarattini and Aziz); VWAP bounce, VWAP reclaim, VWAP bands | | D and wave twenty-three: failed, §1 |
| Opening range of 15, 30, 60 minutes; initial balance break and extension (Crabel; Dalton's market profile; the IB statistics pages) | OR15, IB60: BRK, REJ, RET, FBK | |
| The morning range broken in the afternoon ("noon curve") | AMX | |
| The previous hour's high and low, hourly sweeps (the NQ statistics pages) | HRX | |
| Yesterday's high and low; the overnight high and low; last week's | PDX, ONX, PWX: BRK, RET | their fade: part 16A, lost, §1 |
| Gap fill: the return to yesterday's close | PDC | the gap itself: Q4, O4, §1 |
| The open as support and resistance later in the day | OPN | |
| Round numbers, psychological levels (barrier studies on indices) | RND | |
| Break of structure, change of character (ICT, "smart money concepts") | SW5, SW15: BRK | |
| Liquidity sweep, stop hunt, turtle soup (ICT; Raschke and Connors) | SW5, SW15, HRX, OR15, IB60, AMX, ASIA, EUR: REJ | at daily levels: part 16A, §1 |
| Break and retest | every group: RET | |
| Failed breakout, fake-out, bull and bear trap | FBK | at daily levels: part 16A, §1 |
| Double top and bottom, equal highs and lows | SW5, SW15: REJ | |
| Squeeze, narrow range, volatility contraction (Carter's squeeze; Crabel's NR) | SQZ | |
| London breakout, Asian range (forex and gold sites) | ASIA, EUR | |
| Buy weakness, sell strength over days (IBS; Connors' RSI-2) | EPROP | E: passed the screen |
| Overnight drift, close-to-open and open-to-close reversal (Lou, Polk, Skouras; NY Fed) | | O1, Q4: failed, §1 |
| Last-half-hour momentum; intraday momentum everywhere (Gao et al.; Baltussen et al.) | | C: failed, §1 |
| Big moves continue in busy hours, reverse in quiet ones; liquidity shocks | | O5, Q2: failed, §1 |
| Half-hour, weekday, turn-of-month, month-end seasonality | | Q1, Q3, Q5: failed, §1 |
| Fair value gaps, order blocks, premium and discount (ICT) | | not here: each needs choices no source fixes; a later wave may define them |
| Dealer gamma, 0DTE flows (vendors; one thesis finds no added forecast power) | | needs options data |
| Order flow, footprint, absorption | | waves two to twenty-one: 67 tests on the recordings, none passed |
| Pairs and lead–lag between NQ, ES and RTY; relative strength | | a later wave, when ES and RTY are read |
| Fibonacci retracements, moving-average crosses, candle patterns alone | | not here: no level fixed before the bar, or a recent-move rule (§1) |

## Implementation record — 2026-11-26

`mrofyt_levels27.py`, `tests_mrofyt_levels27.py` (14 tests), written
against this file before any of its strategies was computed on any bar;
verified on hand-built sessions and a synthetic export, never on market
evidence.

| registered | implemented as | precision |
| --- | --- | --- |
| §2 the grid | `grid_of`, `sessions` | minute i of the grid is 18:00 + i; a session without a bar at 18:00 starts with its first close; the suite checks the cash session against wave twenty-four's bar for bar |
| §2 usable, s | `daily_vol`, `sessions` | s is `rule_b`'s own; ONX's two levels need the same overnight bars as the overnight families |
| §3 levels | `rth_levels`, `swings`, `on_signals`, `week_ranges` | last week's range is the previous ISO week's, on the session's contract; the 10:00 hour level uses 09:00–10:00; round hundreds are listed from the session's own range, which changes no event |
| §4 events | `machine` | a bar whose close is exactly on the level has not closed beyond it; when the close before is exactly on the level there is no test on that bar |
| §4 the squeeze | `widths`, `sqz_signals` | the median of 14 is the mean of the 7th and 8th |
| §5 strategies | `day_results`, `family_of` | entry at the close of the event's bar, exit at P(entry + H); two events of one family on one bar: the first listed is taken |
| §5 EPROP | `eprop_sessions`, `series` | the session's first bar must lie before 19:00; the mean session is taken over the discovery sessions and used in both stages |
| §6 the split | `week_label`, `is_lockbox`, `compute` | stage 1 skips a lockbox session before any signal is computed; only its 30-bar ranges enter the squeeze's history |
| §7 statistics | `slopes`, `weekly_t`, `assess` | A is `trade_a`'s result at one contract, B is `day_b`'s, both over s; weeks without a usable session are no observations |
| §8 stages | `stage1`, `stage2`, `main` | ties in t by name; the lockbox command runs stage 1 again itself, so the forwarded list cannot be handed in; the lockbox read is written to `MROF_MINUTE_HISTORY_EXPOSURE.json` before any result is shown, and refused a second time |

**Expected beforehand (written 2026-11-26, before any of it was
computed).** Most of the 181 will show nothing. Breaks and retests of
the opening ranges, the hour and the morning range will make money
before A and B are taken out and little after, because they are the
same trend-following bet. Rejections at swings and at the hour's high
and low will lose by about their costs, as the fades of part 16A did.
EPROP is the likeliest to go forward, since E was strong and unrelated
to A and B, though paying a round trip a session and missing 16:00 to
18:00 will cost it. In all: nought to three forwarded, about one chance
in three of none; of those forwarded, nought or one confirmed on the
lockbox.
