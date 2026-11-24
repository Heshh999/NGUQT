# MROF_YT_WAVE24_SCREEN15_REGISTRATION.md — fifteen ideas, screened on ten years of NQ minute bars

**Status: FROZEN on 2026-11-24, before any of the fifteen rules below was
computed on any data.** What had been seen beforehand is listed in §0.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on historical bars. No order is placed.

**This is a screen, not a test.** The ten years have been read before
(waves sixteen, twenty-two and twenty-three, and the exploration of
2026-11-22 to 24). A rule that passes here has earned a look at the
recorded order flow; it has proven nothing.

---

## 0. Where this comes from, and what was already seen

After waves twenty-two and twenty-three failed on these bars, the
operator set a funnel:

1. fifteen ideas written down as exact rules (this file);
2. each screened on the ten years of minute bars;
3. survivors checked with order flow on the 55 recorded sessions already
   used (`EXPOSED_PILOT_DEV`);
4. what survives that is judged on recorded sessions nothing has read
   (from 2026-11-16).

The fifteen: five of our own from the ten years (O1–O5), five public
trading ideas with written rules (A–E), five from quantitative research
(Q1–Q5).

**Already seen on these bars, so not independent of them:**

- O1: the night after the largest fifth of drops in the last 30 minutes
  gained +18.8 bp on average, against −5.1 bp after the largest fifth of
  rises (fifths cut on the whole sample); the same in 8 of 11 years; in
  2016–2020 and 2021–2026 apart (+18.2 and +16.9 bp).
- The overnight gain by hour; the size of each half hour of the cash
  session and its mean drift (largest t 2.0, at 14:30); random entries
  with a 25 / 15 bracket (−0.98 points a trade in 2020–2026).
- The eight tests of waves sixteen, twenty-two and twenty-three, all
  NOT PROVEN.

Nothing else in §3 had been computed on any data when this file was
frozen.

**Sources.** The rules of A–E and Q1–Q5 follow the published
descriptions as far as they could be read from this environment (search
summaries of the papers; the full texts were not reachable). Each rule
is stated in full below; where it departs from its source, or the source
left a choice open, the choice is fixed here.

## 1. Data and common definitions

- **Bars:** the NQ one-minute exports received on 2026-11-22 (43
  contract files, NQ 03-16 to NQ 12-26; NQ 09-26 absent), read by wave
  twenty-two's reader (`mrofyt_stretchfade.history_sessions`): the front
  contract of each session, sessions with a complete cash session, 14
  earlier sessions and yesterday complete on the same contract
  ("eligible"). Nothing from 2026-07-01 on.
- **Halves:** **H1** = sessions to 2020-12-31; **H2** = sessions from
  2021-01-01.
- **P(t)** = the price at clock time t (ET) = the close of the one-minute
  bar that ends at t. A minute without a bar carries the last close,
  with no range and no volume.
- **O** = the open = the close of the last bar before 09:30 (within the
  hour before; otherwise the session is not used).
- **PC** = yesterday's close = the same contract's last cash close of
  the previous session.
- **VWAP** = Σ((high + low + close) / 3 × volume) / Σ(volume) from 09:30
  to t.
- **Trailing statistics** use earlier eligible sessions only; a rule
  does not trade until its history exists.
- **A trading day** = a session with a cash session in the bars,
  complete or not (a half day counts).
- **The daily chain** (rules holding over more than one session): a
  trading day's return is its cash close over the previous trading
  day's cash close **on the same contract**; a trade that crosses a day
  without such a return is dropped and counted.
- **Costs** (`mrofyt_costs`, NQ): 0.50 points a round trip, 0.75 when
  the exit is a stop; a rule that changes position many times pays 0.25
  points for each contract bought or sold.
- **Unit:** net basis points of the entry price. A and B are also given
  in their source's own position sizing, and are judged in it.

## 2. The pass bar

A rule **passes the screen** when, in **each** half:

- it has at least 30 trades (or trading days, for B and D);
- its mean net result is above 0; and
- it is still above 0 without the calendar month of its largest total.

**Long-only rules (O1, E, Q3)** are judged on what they add to being
long anyway: from each trade is subtracted the half's average return of
the same kind of holding (the average night for O1; the average session
times the sessions held for E and Q3).

Beside, not part of the bar: the month-clustered 95 % interval over both
halves together (`month_verdict`); a pass whose interval is above 0 is
marked **strong**.

Thirteen rules are judged (O2 is a benchmark and O3 cannot be screened).
A rule without any edge, before costs, passes this bar by luck roughly
one time in seven, so one or two false passes among thirteen would be
ordinary. That is why a pass only earns the next step.

## 3. The fifteen

### Our own, from the ten years

**O1 — after selling into the close, the night rebounds.**
x = ln(P(16:00) / P(15:30)). When x is at or below the 20th percentile
of x over the 100 previous eligible sessions: long from P(16:00) to the
next session's O (which must be eligible). Long-only (§2).

**O2 — how far the next half hour moves (benchmark, no pass or fail).**
For each of the 13 half hours of the cash session, y = ln(range /
starting price). F1 = the mean of y in that half hour over the 14
previous sessions. F2 = F1 plus today's previous half hour's surprise
(its y minus its F1; the first half hour uses F1). Reported: the share
of the variance of y each explains, per half. Order flow has to beat F2
in step 3.

**O3 — sweeps carry information.** Needs each trade's aggressor and the
book. **Not screened;** it goes to step 3 as it is.

**O4 — the first 15 minutes decide a big overnight move.**
g = ln(O / PC). When |g| is at least the mean |g| of the 20 previous
sessions: d = the sign of ln(P(09:45) / O); in at P(09:45), out at
P(10:30). Beside: with and against the overnight move.

**O5 — breakouts in busy hours, fades in quiet hours.**
At T, r = ln(P(T) / P(T − 30 min)) and m = the mean |r| at T over the 14
previous sessions. When |r| ≥ 1.5 × m: at T in {10:00, 10:30, 15:00,
15:30} trade with r; at T in {12:00, 12:30, 13:00, 13:30} trade against
it; in at P(T), out at P(T + 30 min). Beside: the two parts.

### Public trading ideas

**A — the 5-minute opening range breakout** (Zarattini and Aziz, "Can
Day Trading Really Be Profitable?").
d = the sign of P(09:35) − O; none at 0. In at P(09:35). Stop at the low
(long) or high (short) of 09:30–09:35; R = the distance to it, at least
one tick. Target at 10 R. First touch on the following bars (a bar
touching both is a stop); otherwise out at P(16:00). **Sized as the
source:** leverage = min(1 % / (R / entry), 4).

**B — out of the noise area** (Zarattini, Aziz and Barbon, "Beat the
Market").
σ(m) = the mean of |P(m) / O − 1| over the 14 previous sessions, for
each minute m. Upper = max(O, PC) × (1 + σ(m)); lower = min(O, PC) ×
(1 − σ(m)). At each of 10:00, 10:30, …, 15:30: long when P is above both
the upper bound and VWAP; short when below both the lower bound and
VWAP; otherwise flat. Flat at P(16:00). **Sized as the source:**
leverage = min(2 % / s, 4), s = the standard deviation of the last 14
daily returns. One result a day, on days with a trade.

**C — the last half hour follows the day** (Baltussen, Da, Lammers and
Martens, "Hedging Demand and Market Intraday Momentum").
d = the sign of P(15:30) / PC − 1; in at P(15:30), out at P(16:00).

**D — the VWAP trend** (Zarattini and Aziz, "VWAP: The Holy Grail for
Day Trading Systems").
At each minute from 09:31 to 15:59: long when P is above VWAP, short
when below, unchanged when equal. Flat at P(16:00). One result a day.

**E — buy weakness at the close** (the IBS rule published for QQQ).
IBS = (close − low) / (high − low) of the cash session. Flat and IBS
below 0.1: buy at the close. Long and IBS above 0.9: sell at the close.
Daily chain. Long-only (§2).

### From quantitative research

**Q1 — the same half hour as on earlier days** (Heston, Korajczyk and
Sadka, "Intraday Patterns in the Cross-Section of Stock Returns").
For each of the 13 half hours: s = the mean of that half hour's return
over the 20 previous sessions, t = s / (its standard deviation / √20).
When |t| ≥ 1: trade the half hour in the direction of s.

**Q2 — a liquidity shock gives part of it back** (Nagel, "Evaporating
Liquidity"; the short-run reversal in Heston, Korajczyk and Sadka).
At T = 09:45, 10:00, …, 15:15: r = ln(P(T) / P(T − 15 min)), m = the
mean |r| at T over the 14 previous sessions, v = the volume of those 15
minutes over its mean at T over the same sessions. When |r| ≥ 3 × m and
v ≥ 1.5: trade against r, in at P(T), out at P(T + 30 min). One trade at
a time.

**Q3 — the turn of the month** (McConnell and Xu, "Equity Returns at the
Turn of the Month").
Buy at the close of the second-to-last trading day of each month; sell
at the close of the third trading day of the next. Daily chain.
Long-only (§2).

**Q4 — the day takes back the night** (Lou, Polk and Skouras, "A Tug of
War" and its sequel).
g and "big" as in O4. On a big overnight move: trade against g from O to
P(16:00). Beside: out at P(10:30).

**Q5 — month-end rebalancing** (Harvey, Mazzoleni and Melone, "The
Unintended Consequences of Rebalancing"; NQ alone stands in for the
stock-against-bond drift).
M = the close of the fourth-to-last trading day of the month over the
close of the previous month's last trading day, minus 1. Trade against
the sign of M from that close to the close of the month's last trading
day. Daily chain.

## 4. What a result leads to

- **Pass:** the rule is registered again for step 3, with the order
  flow it would use named before the recordings are read.
- **Fail:** dropped. No variant of it is tried on these bars.
- O2's F2 becomes the benchmark of step 3; O3 goes to step 3 unscreened.
- Still no live orders in any case.

## Explicitly NOT registered

- any other threshold, window, time, hold, bracket or sizing than those
  above; a second run with changed rules
- choosing between a rule's "beside" lines after seeing them
- ES, YM, RTY or MNQ; anything from 2026-07-01 on
- order flow in this wave; machine-learned models of any kind
- live, paper or simulated order placement

## Implementation record — 2026-11-24

`mrofyt_screen15.py`, `tests_mrofyt_screen15.py`. Written against this
file before any of the fifteen was computed; verified on hand-built bars
and synthetic exports, never on market evidence.
