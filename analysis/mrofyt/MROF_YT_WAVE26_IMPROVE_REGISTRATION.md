# MROF_YT_WAVE26_IMPROVE_REGISTRATION.md — three changes to A, and A and B on a prop account

**Status: FROZEN on 2026-11-26, before any of the rules below was
computed on any data, and before any ES or RTY bar, or any NQ bar after
2026-06-11, was read.** What had been seen beforehand is listed in §0.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on historical bars. No order is placed.

---

## 0. Where this comes from, and what was already seen

Wave twenty-four's screen passed A (the 5-minute opening range
breakout) and B (out of the noise area); wave twenty-five takes them,
unchanged, to ES, RTY, NQ's later months and the recordings' costs. The
operator asked, on 2026-11-26, whether A and B can be improved. This
file fixes the only changes that will be tried, before the data that
can judge them is read: three changes to A, and the sizing and risk
rules that would run A and B on a $150,000 prop-firm account.

**Seen beforehand, on the ten years of NQ (2016-01 to 2026-06-11), with
the rules of wave twenty-four unchanged:** everything in wave
twenty-four's report; and, worked out for the operator on 2026-11-25,
each rule's trades, wins, losses and result by year in points for one
contract, its average win and loss, its longest run of losses (A 29
trades, B 11 days), and its largest fall from a peak with one contract
(A 1,507 points, B 1,845; since 2023 A 1,376, B 1,845). **The dollar
budgets of §3 were chosen knowing those falls**, so §3 is a plan checked
on bars it was fitted to, not a test.

**Not seen:** any of A1, A2, A3 or the sizing of §3 on any bar; any ES
or RTY bar; any NQ bar after 2026-06-11.

## 1. Common to all

Wave twenty-four's bars, trading days, front contract, P(m), VWAP, the
daily chain, A and B; wave twenty-five's markets, costs, halves, the
reader's refusals and the later-months window, all unchanged. A and B
are wave twenty-four's own functions; a change below alters only what
it names.

## 2. Three changes to A

Each is a separate try. Nothing else of A changes: the direction (the
sign of P(09:35) − O), the entry at P(09:35), the 10 R target, the first
touch on the following bars (a bar touching both is a stop), the exit at
P(16:00), the costs and the source's sizing, leverage =
min(1 % / (R / entry), 4), with R as each change defines it.

**A1 — busy opens only** (Zarattini, Barbon and Aziz, "A Profitable Day
Trading Strategy for the U.S. Equity Market": the breakout on "stocks in
play"). V5 = the volume of the session's first five one-minute bars
(09:30–09:35). A trades only when V5 is **above** the mean V5 of the 14
previous eligible sessions; no trade until there are 14.

**A2 — a stop from the normal day** (the same paper). D = the mean of
the cash-session high minus low over the 14 previous trading days of the
daily chain. R = 0.10 × D (at least one tick, else no trade); the stop
at entry − d × R. No trade until there are 14.

**A3 — out when B is against it.** At each of B's times, 10:00 to
15:30, before that bar's stop and target are checked: when B's own rule
at that time would be short under a long A, or long under a short A, A
is closed at P(m) and pays the round trip of a close (0.50 on NQ). B's
bounds are B's own; on a session where B has none (its first 14, or no
14-day volatility), A3 is A.

**The bar for a change.** On each of NQ (the ten years: a screen, as in
wave twenty-four), ES and RTY (wave twenty-five's 2a): wave
twenty-four's bar, in the source's sizing. Then, **better than A**: the
mean result per eligible session (a session without a trade counts 0)
higher than unchanged A's on **both ES and RTY**. In NQ's later months
(2026-07-01 to 2026-11-13) it must not be COLLAPSED (wave twenty-five's
verdicts).

A change that passes the bar but is not better than A is an alternative,
not an improvement: A stays as it is. A change that fails is dropped,
and no variant of it is tried on these data. If more than one is better
than A, the one with the higher mean result per session on ES and RTY
together goes on. **A change can go on only if A itself passes wave
twenty-five.**

## 3. A and B on a $150,000 prop account (NQ, in micros)

This is not a test of an edge. It fixes how A and B would be sized and
stopped on a prop account, and checks on the ten years of NQ whether
that would have lasted. It uses A and B unchanged.

- **Contract:** MNQ, 2 dollars a point. **Costs:** 1.50 dollars of
  commission and one tick of spread a round trip (1.00 point), one tick
  more on a stop (1.25); each contract bought or sold half a round trip.
- **A's size** (item 1 of the reply: the source's 1 % risk, scaled):
  micros = floor(150 / (R × 2)), at least 1, at most 15. About 150
  dollars at risk a trade.
- **B's size (item 4, by volatility):** micros = round(500 / (s × O ×
  2)), at least 1, at most 15; s = B's own 14-day standard deviation of
  daily returns, O the session's open. About 500 dollars for a day's
  normal move, whatever the price level.
- **The account (item 6):** 150,000 dollars; it **fails** when its
  value at any minute close falls 4,500 dollars below its highest
  end-of-day value. After a failure a new account starts the next
  trading day. A and B trade on it together; each counts its own
  result. E is not on it: it holds overnight, which prop accounts do not
  allow.
- **The daily loss stop (item 5):** once the day's result (closed and
  open, at a minute close) reaches −1,000 dollars, everything is closed
  at that minute's close and nothing more is traded that day.
- **Reported:** the result, the failures and the largest fall from a
  peak, by year and in all, without and with the daily stop.

**What follows from it (fixed now):**

- **More than one failure in the ten years:** both budgets are halved
  (75 and 250 dollars) for the third step.
- **The daily stop** is kept for the third step when it lowers the
  number of failures or the largest fall, and costs at most 10 % of the
  total result; otherwise it is left off.

## 4. Reads

- NQ's ten years (already read), ES and RTY (wave twenty-five's 2a
  exports), read by this wave's own command, each **once**.
- NQ's later months, 2026-07-01 to 2026-11-13: A1, A2 and A3 read
  **once** by this wave, recorded before any result is shown. The
  operator may make it in the same sitting as wave twenty-five's own
  read.
- Sessions from 2026-11-16 are never read.

## Explicitly NOT registered

- any other change to A or B: thresholds, times, targets, stops,
  filters, holds
- other budgets, contract caps, drawdown limits or stop levels than
  §3's, unless §3's own halving rule applies
- order flow as a filter (55 recorded days are too few to judge it)
- E on the prop account
- machine-learned models of any kind
- live, paper or simulated order placement

## Implementation record

`mrofyt_improve26.py`, `tests_mrofyt_improve26.py`, written against
this file before any of its rules was computed on any bar.
