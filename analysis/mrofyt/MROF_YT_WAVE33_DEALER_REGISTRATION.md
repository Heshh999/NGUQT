# MROF_YT_WAVE33_DEALER_REGISTRATION.md — when B works: the dealers' side, read from price

**Status: FROZEN on 2026-11-28, before the tool was written, before
either reading below was computed on any bar, and before any ES or RTY
bar, or any NQ bar after 2026-06-11, was read by anything.** What had
been seen beforehand is listed in §0.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on historical bars. No order is placed.

---

## 0. Where this comes from, and what was already seen

The operator asked, from 2026-11-27, which way the market goes and for
how long, and what the dealers' side has to do with it. What was found,
in the papers' own text where it could be read, and in summaries
otherwise:

- **Option dealers who are short gamma must trade with the move; long
  gamma, against it.** Baltussen, Da, Lammers and Martens (2021): in
  more than 60 futures the last half hour follows the day, and on the
  S&P 500 only on days when the dealers' gamma, known the day before,
  is negative. Barbon and Buraschi: negative gamma and a thin market go
  with intraday momentum, positive gamma with reversal. Dim, Eraker and
  Vilkov: on days with same-day expiries dealers are long gamma, and
  higher dealer gamma predicts stronger reversals of E-mini order flow.
- **B's own authors** (Zarattini, Aziz and Barbon, "Beat the Market",
  read in full): B earned more after the market had fallen over the
  last five days (a regression on the 5-day RSI as of the previous
  close, on SPY, 2007-2024, in the sample the rule was built on). Their
  reading: after a fall, dealers are more likely short gamma.
- **The dealers' positions are not on hand.** They are sold, and even
  then estimated. This file reads the dealers' side from price alone:
  after a fall, before the open; and from whether the morning's moves
  continue or give back, at noon.

**Seen beforehand:** everything in the reports of waves twenty-four and
twenty-six on NQ's ten years (B's result by halves and by year in the
account); the outside results above; wave twenty-four's C, the trade of
the first paper, failed the screen on NQ.

**Not seen:** either reading below, or B split by either, on any bar of
any market; any ES or RTY bar; any NQ bar after 2026-06-11.

## 1. Common to all

Wave twenty-four's bars, trading days, front contract, P(m), VWAP, the
daily chain and B; wave twenty-five's markets (NQ, ES, RTY), costs,
halves, the reader's refusals and the later-months window; wave
thirty-two's legs of B and its Sharpe and fall ratio, all unchanged.
A session's result x is B's net basis points of capital in B's sizing,
0 on a session without a trade, over the sessions on which B has its
bounds and its volatility.

## 2. The two readings

- **FALL** (known before the open): the product of (1 + the daily
  return) over the five trading days before the session, less 1, is
  below 0. The daily return is the chain's: a cash close over the
  previous trading day's cash close on the same contract. When any of
  the five is missing, FALL is unknown and counts as not FALL.
- **MODE** (known at 12:00): with c(k) = P(5k) − P(5k − 5) for
  k = 1 … 30, the thirty five-minute changes from 09:30 to 12:00,

      AC = Σ c(k)·c(k+1), k = 1 … 29   ÷   Σ c(k)², k = 1 … 30

  **TREND** when AC is above 0; otherwise **FIGHT** (a morning without
  a change counts as FIGHT).
- **The afternoon's AC** is the same over the 48 changes from 12:00 to
  16:00 (k = 31 … 78), reported only.

## 3. Two changes to B

- **BFALL — B after a fall:** B's rule, unchanged, on sessions with
  FALL; flat on the others.
- **BMODE — B on trend mornings:** B's rule, unchanged, to 12:00. On a
  FIGHT morning, B is flat from 12:00 (the order at 12:00 closes any
  position, paying B's cost) and takes no position after; on a TREND
  morning nothing changes.

## 4. The verdict

A change is **BETTER THAN B** when all of these hold (wave thirty-two's
bar for BL):

- it passes wave twenty-four's bar on each of NQ, ES and RTY;
- on **each of ES and RTY**, B's Sharpe is above 0, the change's Sharpe
  is **at least 5 % higher** than B's, and its fall ratio is lower than
  B's;
- in NQ's later months (2026-07-01 to 2026-11-13) it is not COLLAPSED
  (wave twenty-five's verdicts).

Otherwise it is **NOT BETTER**: B stays as it is, and no other reading,
threshold or hour is tried on these bars. **What goes on:** a change
that is better than B takes B's place in every later step **only if B
itself passes wave twenty-five**. If both are better, each goes on
alone; putting them together is a later file.

## 5. Three statements written down beforehand

Reported as HELD or NOT HELD, on each market, and "on both ES and RTY":

- **FALL HELPS:** B's mean x on FALL sessions is above its mean on the
  other sessions.
- **MODE HELPS:** B's afternoon (its legs from 12:00, wave thirty-two's
  legs) earns more on average after TREND mornings than after FIGHT
  mornings.
- **MODE PERSISTS:** the afternoon's AC is higher on average after
  TREND mornings than after FIGHT mornings, over every session with a
  complete cash day.

They lead to nothing by themselves; they say whether the describing
tool's two readings measure something.

## 6. Reported beside, never judged

- B's mean x, its standard deviation and the sessions in each of the
  four cells FALL × MODE; the share of sessions in each state; the same
  by year.
- **B's own last month:** whether B's x summed over its previous 30
  sessions is at or below 0, and B's mean x in each case (an
  independent re-run of B's source found its recent results
  mean-revert).
- The difference of the means in each statement and its Welch t.

## 7. Reads

- NQ's ten years (already read), ES and RTY (wave twenty-five's 2a
  exports), each read by this wave's own command **once**, recorded
  before any result is shown.
- NQ's later months, 2026-07-01 to 2026-11-13: BFALL, BMODE and the
  three statements, read **once** by this wave.
- Sessions from 2026-11-16 are never read.

## Explicitly NOT registered

- other windows for FALL or MODE, other thresholds, other hours; FALL
  and MODE together as a rule; sizing by either
- the dealers' positions from option data: none is on hand
- any change to B's bounds, its VWAP condition or its sizing; A
- markets other than NQ, ES and RTY; a second read of any window
- live, paper or simulated order placement

## Expected beforehand (written 2026-11-28, before anything was computed)

The readings are noisy stand-ins for positions nobody here can see, and
since same-day options took over dealers are more often long gamma,
which helps neither reading. **FALL HELPS** on both ES and RTY: about
one chance in three. **MODE HELPS** on both: about one in three. **MODE
PERSISTS** on both: about one in two, since a morning's character tends
to carry into the day. **BFALL better than B:** about one chance in
eight; flat on half the days, it needs those days to carry far more
than half of B's result. **BMODE better than B:** about one in six. The
most likely outcome: the readings describe something, and B is better
left whole.
