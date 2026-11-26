# MROF_YT_WAVE29_SPEED_REGISTRATION.md — the fastest trade a retail account can win

**Status: FROZEN on 2026-11-26, before the tool was written and before
anything below was computed on any recording.** What had been seen
beforehand is listed in §0.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on recorded tape. No order is placed.

---

## 0. The question, and what was already known

The operator asked, on 2026-11-26, for the closest thing to
high-frequency trading that a retail account can compete in, and left
the rules to this file.

Three things separate a retail account from a high-frequency firm, and
none of them can be bought here:

1. **It sees the market late.** A recorded MNQ run showed a median of
   259 ms between the exchange's time stamp and the moment the row
   reached the computer (clock synchronisation unresolved), and an order
   then needs its own time to travel. A firm in the exchange's building
   works in millionths of a second.
2. **It is at the back of every queue.** Orders at one price are filled
   in the order they arrived.
3. **It pays to trade.** About 5 dollars a round trip on NQ (0.25
   points), three times that in points on MNQ, and the spread whenever
   it crosses it.

Published work says what follows from this: what the order book
predicts lasts about two price changes (Kolm, Turiel and Westray,
2023); among fast firms the relative speed decides who earns (Baron,
Brogaard, Hagströmer and Kirilenko, 2019); limit orders at the back of
a queue lose money on average (Queuing Uncertainty of Limit Orders,
Management Science, 2023); and in the E-mini, signed volume is followed
by a small reversal over the next minutes (Federal Reserve Bank of New
York, Staff Report 917). **Below about a second a retail account cannot
win.** This file does not test that.

What is left is arithmetic. The cost of a trade is fixed; the distance
price travels grows with the square root of time. On a usual day NQ
moves, over one second, about three times the cost of a round trip;
over a minute, about twenty-five times (rough figures from its daily
range; §5 measures them). So a forecast that is far too weak to pay at
one second can pay at one minute. **The question is whether anything in
the recorded tape forecasts NQ well enough, between ten seconds and
ten minutes, to pay for a retail account's costs and delay — and, if
so, at which speed.** Fifty-five recorded sessions hold about 250,000
five-second moments, which is enough to answer it.

**Seen beforehand.** All 55 sessions are `EXPOSED_PILOT_DEV`: the
earlier waves read them for events at price levels, and wave four made
a counted search on a ten-second grid for rules that precede 25-point
moves. None of what they found survived the held-out sessions. Nothing
of this file (the panel, the forecast, the three ways to trade) had
been computed on any recording when it was frozen. NQ's spread over
whole sessions had not been measured.

## 1. The data

- **Recordings:** NQ and MNQ; the quote, trade and quality files. The
  depth files are not opened.
- **Sessions:** 2026-09-01 to 2026-11-13, and only those the exposure
  ledger marks `EXPOSED_PILOT_DEV`. Any other session is listed and
  never opened (§8 is the one exception, later, once).
- **The clock** is the moment the computer received each row.
- **The panel.** For each session, one row every **5 seconds** from
  08:00:00 to 16:15:00 New York time. A row at time t holds, for NQ:
  the best bid and ask and their sizes at t; the bid and ask at t + 0.5
  s and at t + 1.0 s; and, summed over the 5 seconds to t: the order
  flow imbalance of the best quotes (Cont, Kukanov and Stoikov),
  contracts bought and sold by aggressors and the number of such
  trades, all contracts traded and their price times size, the time
  integrals of the queue imbalance (bid size − ask size) ÷ (bid size +
  ask size) and of the spread, the seconds a quote was in force, and
  the squared one-second changes of the mid. Also the order flow
  imbalance and the signed volume of the last second alone; for the
  passive orders of §2, whether and when a join order placed at t on
  each side is filled, and the lowest and highest trade, the lowest
  bid and the highest ask from t + 0.5 s to t + 5.5 s; and a mark when
  the feed was interrupted. The same for MNQ, without the execution
  columns.
- A quote is in force for at most 10 seconds; crossed or locked quotes
  and rows the recorder marked as suppressed or disconnected are not
  quotes. The front contract of a session is the one with the most
  volume in the panel's hours.
- **A session is used** when at least 3,000 of its rows from 09:35 to
  15:55 are usable (a quote in force, no interruption in the 600
  seconds before).

## 2. What a trade costs and how it is filled

One contract. Commission **0.25 points** a round trip (NQ); the same
trades are also reported at **0.75** (MNQ).

- **Delay.** An order decided at t acts on the market as it stands at
  **t + 0.5 s**. Everything is repeated at **t + 1.0 s** (the stress).
- **Taking.** A buy is filled at the ask in force at that moment, a
  sell at the bid.
- **A join order** rests at the best bid (to buy) or best ask (to
  sell) in force at t + 0.5 s. Every contract shown there at that
  moment is ahead of it, and none of them is assumed to cancel. It is
  filled when the trades at its price by aggressors of the other side
  (or of unknown side), counted from the moment it joined, reach the
  contracts ahead plus one; or when a trade prints through its price
  and the quote confirms it (the best bid falls below a buy's price,
  the best ask rises above a sell's). It is cancelled after 10
  seconds; a fill up to 0.5 s after that still counts.
- **A deep order** rests away from the market for 5 seconds, from t +
  0.5 s to t + 5.5 s. It is filled at its price only when, in that
  time, a trade prints **through** its price and the quote confirms it
  as above. A trade at its price does not fill it.

Both passive orders are filled here less easily than in a real book,
and far less easily than in a prop firm's simulator; nothing in this
file relies on a simulator's fills.

## 3. The forecast

**Volatility.** σ(t) is the root of the mean squared one-second change
of the mid over the 600 seconds to t.

**What is forecast.** For each horizon h of **10, 30, 60, 120, 300 and
600 seconds**: the change of the mid from t to t + h, divided by σ(t)
√h, held between −5 and +5.

**From what (48 inputs, all known at t).** W is a window of seconds
ending at t.

| group | inputs |
| --- | --- |
| past moves | the mid's change over W ÷ (σ √W), W = 5, 30, 120, 600, 1800 |
| order flow imbalance | summed over W = 5, 30, 120, 600 and over the last second, each over its own usual size in the last 600 seconds |
| who is hitting | (bought − sold) ÷ (bought + sold) over W = 5, 30, 120, 600; the last second's signed volume over its usual size |
| by count | the same by number of trades, W = 30, 120, 600; and the volume figure less the count figure at W = 120 (large trades) |
| the queue | queue imbalance at t, and averaged over 5 and 30 seconds |
| the spread | in ticks at t; its 30-second average against its 600-second average |
| activity | volume a second over 30 seconds against 600; squared moves a second over 30 seconds against 600 (both in logs) |
| where price is | its place in the day's range since 09:30; its distance from the day's VWAP since 09:30; its distance from its own 600-second average |
| the micro contract | MNQ's (bought − sold) ÷ (bought + sold) over W = 5, 30, 120, 600 and by count at 120; MNQ's queue imbalance; MNQ's figure less NQ's at W = 30, 120, 600; MNQ's share of the volume over 120 seconds; MNQ's mid less NQ's |
| time of day | before 10:00; from 15:00 |
| together | the 120-second move and the 120-second hitting figure, each before 10:00 and from 15:00; the 600-second move times the squared-moves figure; the 30-second imbalance times the volume figure |

Every input is a ratio or is divided by its own recent size, and is
held between fixed bounds; none uses anything after t.

**How.** A linear forecast with a ridge penalty, one for each horizon,
**walked forward by session**: the forecast for a session is fitted on
the sessions before it only, from the 21st used session on. Inputs are
standardised on those earlier sessions. The penalty is one of 0.01,
0.1 and 1 (on the standardised scale), chosen each time by fitting on
all but the last five of the earlier sessions and taking the one that
forecasts those five best. Rows from 09:35:00 to 15:55:00 less h.

## 4. Three ways to trade it

All three hold one contract for a fixed time and close it by taking.
Entries from 09:35:00 to 15:55:00 less h.

- **T — take.** When the forecast move in points is larger than the
  spread at t plus the commission, take in its direction; close h
  seconds later. One position at a time. h = 10, 30, 60, 120, 300, 600.
- **M — join.** When the forecast move is larger than half the spread
  plus the commission, place a join order on its side; if it is not
  filled, the next may be placed 10 seconds after it. A filled order is
  held h seconds and closed by taking. One position at a time. The
  same six h.
- **D — deep.** No forecast. Every 5 seconds a buy rests k σ(t) √5
  below the mid and a sell the same distance above (never nearer than
  1 point; prices rounded away from the market), k = **2, 3, 4**. A
  filled order is held h = **30, 60, 120, 300** seconds from the end of
  its 5 seconds and closed by taking. One position a side at a time.

## 5. The map (reported, never judged)

For each horizon: the usual size of a move and of the cost; each
input's rank correlation with what followed, session by session; the
forecast's own, on sessions it was not fitted on; what the forecast's
strongest twentieth of calls went on to move. For the join order with
no forecast: how often it is filled and where the mid stood afterwards.
The spread: its average and the share of time at one tick, two, more.
The delay between the exchange's time stamp and the computer's.

## 6. The verdict on these sessions

A way to trade **qualifies** when, on the sessions its forecast was
not fitted on (D: all used sessions), with the 0.5 s delay and NQ's
commission:

- h is **60 seconds or more** (several prop firms forbid shorter
  trades as micro-scalping);
- it makes **200 trades or more**;
- its net result per session has a mean above 0 with **t of 3.0 or
  more** (the mean of the session sums over its standard error;
  sessions without a trade count 0);
- the first and the second half of those sessions are each above 0;
  and
- it is still above 0 with the 1.0 s delay.

Seventeen ways can qualify (T and M at four h, D at three k and three
h). With that bar, when nothing is there, a false pass among the
seventeen is expected in fewer than one such study in twenty. **A pass here is still not
evidence**: these sessions are exposed.

Of the ways that qualify, the one with the highest t in each of T, M
and D is **frozen**: its rule and, for T and M, the forecast fitted on
all used sessions.

When none qualifies, the answer to §0 is that nothing on the tape
pays at these speeds for a retail account, and the fastest trade worth
taking stays the kind waves twenty-four to twenty-eight study. No
variant of this wave is then tried on these sessions.

## 7. Reads

The 55 sessions are read once by this wave's command; the panel is
saved before anything is computed from it, so the tape is not read
twice. The read adds no exposure: the sessions are exposed already.

## 8. Confirmation (only if something was frozen)

- **Sessions:** every recorded session from 2026-11-16 on that exists
  when the confirmation is run; at least 20 used sessions. They have
  been read by nothing.
- **Read once**, by this wave's own command with the frozen file,
  recorded before anything is shown. Only the frozen ways are run;
  nothing is fitted or chosen.
- **A frozen way is CONFIRMED** when it makes 100 trades or more and
  its net result per session has a mean above 0 with t of 2.0 or more
  at the 0.5 s delay, and is above 0 at the 1.0 s delay. Otherwise it
  is dropped.
- A confirmed way goes to the shadow step: tracked on later sessions,
  no orders. Sizes and limits on an account are a later file.

## Explicitly NOT registered

- anything faster than the panel's 5 seconds; the depth files
- other inputs, horizons, penalties, distances, lives or delays; any
  threshold fitted to results; stops or targets
- other instruments; ES is not recorded
- a second read of these sessions for a variant; any read of sessions
  from 2026-11-16 other than §8's
- machine-learned models other than the linear forecast of §3
- live, paper or simulated order placement

## Expected beforehand (written 2026-11-26, before anything was computed)

NQ's spread is one tick most of the day. The forecast is real but
small: a rank correlation of 0.02 to 0.05 at ten seconds, under 0.01
by five minutes. **T does not qualify at any speed** (about one chance
in ten). A join order with no forecast is filled mostly when price is
about to go through it, and loses about its half-spread; **M** has
about one chance in ten. **D** is the likeliest of the three, about
one in seven. Something qualifying here: about one chance in four;
qualifying and then being confirmed: about one in eight. The most
likely outcome is a clear map showing that the costs are larger than
anything the tape forecasts, at every speed.

## Implementation record — 2026-11-26

`mrofyt_speed29.py`, `tests_mrofyt_speed29.py` (29 tests), written
after this file was frozen and before any recording was read by it;
verified on hand-built tape, on panels built in the suite with and
without a planted effect, and on recorder-format runs, never on market
evidence. Two of the tests set the code against a slow second
implementation written from this file's words alone: every column of
every row on random tapes, and the usable rows, σ, the 48 inputs and
what followed on random sessions with holes in them. Nothing above
this line was changed.

| registered | implemented as | precision |
| --- | --- | --- |
| §1 the clock, the rows | `panel_start`, `Book` | a row at t holds what the computer had received before t; a row received at exactly t belongs to the next. The one-second changes of the mid are taken between whole seconds at which a quote is in force |
| §1 quotes in force, interruptions | `Book.brk`, `SpeedRunner._stream_run` | the beginning and the end of a run, the recorder's disconnect and reconnect rows and a quote it marked suppressed or disconnected are interruptions: no quote is in force, resting orders are dropped unfilled, the row after it carries the mark. A crossed or locked quote is passed over and the quote before it stays in force for its 10 seconds |
| §1 the front contract | `build_panel` | NQ's contract with the most volume from 08:00 to 16:15; MNQ's contract of the same month, and without one the session has no micro columns (its micro inputs are 0) |
| §1 only the hours | `window_events` | each run's quote, trade and quality files are read from 07:58:55 to 16:15:12 New York with the adapter's own decoding; a run that lies wholly outside is not opened; the depth file is never opened |
| §1 a session is used | `derive` | a row is usable from 09:35:00 to 15:55:00 with a quote in force, no interruption mark in the 600 seconds before, and at least 300 one-second changes in those 600 seconds that are not all zero |
| §2 the join order | `Book.quote`, `Book.trade` | the time of a fill is counted from the moment it joined; a fill later than 10.5 seconds is none. A buy counts trades at its price by sellers or of unknown side; "prints through" is a trade below its price (above, for a sell) |
| §2 the deep order | `Book._mark`, `run_deep` | no order is placed on a side when the best price at t + 0.5 s already stands at or beyond the order's price |
| §2 the stress | `run_take`, `_close` | T: entry and exit at the quotes of t + 1.0 s. M and D: the resting order is the one §1 and §2 define, placed at t + 0.5 s; the stress repeats the closing trade at 1.0 s |
| §3 volatility and the inputs | `derive` | moves and flows over their usual size are held to ±5, logs to ±3, the spread to 8 ticks, the micro's distance to ±4 ticks. The usual size of the imbalance and of the signed volume is the root mean square of their 5-second sums over the last 600 seconds, scaled by the root of the window. The day's range and VWAP start at 09:30:00 |
| §3 what is forecast | `derive` | unknown, and left out, where the row at t + h has no quote or an interruption lies between |
| §3 the forecast | `session_sums`, `fit`, `choose`, `forecast_model` | fitted from sums of products; the penalty is added to the diagonal of the inputs' correlation matrix; an input that does not vary on the earlier sessions gets no weight; of two penalties that forecast the five sessions equally the larger is taken |
| §4 T | `run_take` | no trade without a quote at t + 0.5 s; a trade whose closing quote is missing is counted apart (`void`) and not judged; the next entry may be made at the row of the exit |
| §4 M | `run_join` | a filled order is closed at the first row at or after its fill plus h, by taking 0.5 s after that row (held between h and h + 5.5 seconds) |
| §4 D | `deep_price`, `run_deep` | the exit is h seconds after the end of the order's 5 seconds |
| §5 the map | `input_map`, `pooled`, `best_null`, `_top` | **differs from the text.** See below. Beside the best single input the report gives the t that the largest of the 48 reaches one time in twenty when each session's sign is drawn at random (1,000 draws, always the same ones): the best of 48 always looks like something |
| §5 the usual move and cost | `analyze` | the median σ times the root of h; the median spread plus the commission |
| §6 the verdict | `summarize`, `qualifies`, `analyze` | every way that qualifies is listed; the frozen file holds, for each of T, M and D, the one with the highest t (of two the same, the one listed first: the shorter hold; for D the smaller k, then the shorter hold). The halves are the first and the second half of the sessions by date |
| §6 frozen | `seal` | the frozen file carries a SHA-256 of itself; a file changed afterwards is refused |
| §7 read once, panel first | `main`, `write_panel`, `read_panel` | the panel is written before anything is computed, and the study is made from the file as read back, so the file alone gives the same report to the last digit (`--from-panel`). Prices, sizes, counts and squared moves are kept exactly, the five time integrals to the millisecond. Each report the command makes is recorded in `MROF_W29_SPEED_READS.json` |
| §8 the confirmation | `confirm`, `main` | it takes only the frozen file that the last study on record wrote; with fewer than 20 used sessions it stops with nothing saved or recorded and can be run again later; it is recorded before it is shown and refused a second time. Its report can be made again from its own saved panel with the same frozen file, which shows nothing new |

**Where the code differs from the text (§5 only, which is never
judged).** The text asks for each input's rank correlation with what
followed, session by session. On a simulated tape with nothing in it,
that figure came out clearly below zero for every input that follows
the price (its distance from the day's VWAP, its place in the day's
range, its past moves): within one session such an input and the rest
of the session's path are tied together, and an average taken session
by session inherits the tie. The code therefore centres each input on
its average over the *other* sessions, leaves what followed as it is,
and reports one correlation over all sessions together, with a t that
is the mean of the sessions' sums of products over its standard error.
On sixty simulated panels of twenty sessions with nothing in them, the
16,200 values of t had a mean of −0.02 and a standard deviation of
1.09 (a t with 19 degrees of freedom has 1.06), and 5.4 % of them lay
beyond its 5 % level. The forecast's own figure is computed the same
way; on eighteen such panels it was centred on zero. Nothing in §6 or
§8 uses the map.

**Dry runs, on simulated panels only.** With nothing planted, nothing
qualified and nothing was frozen. With a forecast planted in the flow,
T qualified at a minute and more, was frozen and was confirmed on
simulated later sessions, while the ten- and thirty-second holds could
not qualify however good, and M lost. With prints planted far beyond
the path, D qualified and was confirmed. These show that the code does
what this file says; they say nothing about the market.
