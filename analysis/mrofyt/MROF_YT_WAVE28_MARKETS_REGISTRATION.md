# MROF_YT_WAVE28_MARKETS_REGISTRATION.md — A and B on markets that are not stock indices

**Status: FROZEN on 2026-11-26, before any bar of any market below was
read by anything in this repository.** What had been seen beforehand is
listed in §0.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on historical bars. No order is placed.

---

## 0. Where this comes from, and what was already seen

On 2026-11-26 the operator lifted every limit on what may be studied
(the holding times of wave twenty-seven among them) and asked for the
plan a quantitative firm would follow. That plan is to stop mining NQ's
bars, where wave twenty-seven's 181 hypotheses found nothing, and to
carry the two day-trading rules that passed NQ's screen, **unchanged**,
to markets that do not move with NQ. One weak edge on several unrelated
markets is worth more than a better-fitted edge on one; and markets
whose bars have never been read are the only place left where a rule
can be tested without a single choice made after seeing the data.

Wave twenty-five takes the rules to ES and RTY, which move with NQ.
This wave takes them to crude oil, natural gas, gold, silver, copper,
the euro, the yen and bitcoin.

Both rules have a public history outside stock indices: the opening
range breakout was first published on bonds, grains and other futures
(Crabel, 1990), and momentum within the day is documented on more than
sixty futures of every kind (Baltussen, Da, Lammers and Martens, 2021).

**Seen beforehand:** everything waves twenty-four to twenty-seven
showed of A and B on NQ's ten years (to 2026-06-11): their results by
half and by year, their trades, wins and losses, their largest falls,
three changes to A, and both rules on a prop account. Those results set
the cost gate of §3 (item 4).

**Not seen:** any bar of any market of §2. Wave twenty-five's results
on ES and RTY (its exports had not been made when this file was frozen).

## 1. The rules

A (the 5-minute opening range breakout) and B (out of the noise area)
**exactly as wave twenty-four registered and coded them**
(`mrofyt_screen15.py`: `trade_a`, `rule_a`, `day_b`, `rule_b`, `nets`,
`judge`), read by the same reader, with the same front contract (the
previous session's volume), the same daily chain and the same rule for
an eligible session.

On NQ those rules are written for the cash session, 09:30 to 16:00 ET.
Here **the day session is the market's own** (§2). Everything that was
tied to 09:30 or 16:00 is tied to the day session's open and close, and
nothing else changes:

- **O** is the close of the last bar in the hour before the open; P(m)
  the price m minutes after the open; the VWAP runs from the open; the
  previous close is the previous trading day's price at the close of
  its day session, on the same contract.
- **A:** the first five minutes of the day session; entry at P(5); the
  stop at the far side of those five bars; the target ten times the
  risk; out at the day session's close.
- **B:** its times are every 30 minutes, from 30 minutes after the open
  to the last such time that is at least 30 minutes before the close;
  out at the close. Its noise area, its 14 sessions and its 14 daily
  returns are as on NQ.
- **A complete day session:** at most 20 of its minutes without a bar
  (370 of 390 on NQ), a bar in its first minute and one in its last
  five. **A trading day:** a weekday with 100 bars or more in the day
  session.

## 2. The markets

| market | class | day session (ET) | minutes | tick | dollars a point | spread assumed | round trip | on a stop |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CL | energy | 09:00–14:30 | 330 | 0.01 | 1,000 | 1 tick | 0.015 | 0.025 |
| NG | energy | 09:00–14:30 | 330 | 0.001 | 10,000 | 1 tick | 0.0015 | 0.0025 |
| GC | metals | 08:20–13:30 | 310 | 0.10 | 100 | 1 tick | 0.15 | 0.25 |
| SI | metals | 08:25–13:25 | 300 | 0.005 | 5,000 | 1 tick | 0.006 | 0.011 |
| HG | metals | 08:10–13:00 | 290 | 0.0005 | 25,000 | 1 tick | 0.0007 | 0.0012 |
| 6E | currencies | 08:20–15:00 | 400 | 0.00005 | 125,000 | 1 tick | 0.00009 | 0.00014 |
| 6J | currencies | 08:20–15:00 | 400 | 0.0000005 | 12,500,000 | 1 tick | 0.0000009 | 0.0000014 |
| BTC | crypto | 09:30–16:00 | 390 | 5.00 | 5 | 4 ticks | 21.00 | 41.00 |

- **The day session** is each market's former pit session, which ends
  at its daily settlement. Bitcoin never had one: it takes the stock
  session, whose close is also its settlement.
- **Costs**, in the market's own price: a round trip pays 5 dollars of
  commission and one spread; a stop one spread more; each contract
  bought or sold pays half a round trip (wave twenty-five's model). The
  spread is one tick, on bitcoin four.
- **The tick** is the one in the table, or the smallest step the
  market's prices are seen to move in when that is larger: in each
  contract file, the smallest one-minute change of the close that
  makes up at least 1 in 100 of the non-zero changes; over the files,
  the largest of these. Costs can only rise by this.
- **Exports:** one-minute bars, one file a contract, from 2016 (bitcoin
  from its first contract), made by `src/MrofBarExport.cs` or by hand in
  the Historical Data window; the two give the same files.

**Not in this wave, decided beforehand on cost alone:** Treasury notes
and bonds, grains, and the other currencies. Their prices move in large
steps: a round trip costs about 3 to 5 % of a normal day's move, against
0.4 % on NQ, which is about all that B earned on NQ.

## 3. Data gates (each market, before any result is computed)

A market that fails a gate is **left out**, and the report says which
gate. No rule is run on it.

1. **The time stamps.** Every market here is closed from 17:00 to 18:00
   ET. Fewer than 1 in 1,000 of the market's bars may start in that
   hour.
2. **No hole.** No two trading days in a row more than 5 calendar days
   apart. Where the operator's feed has no bars for such days the read
   may be made with `--gaps-ok`, said before any result exists.
3. **Enough history.** 1,500 eligible sessions or more.
4. **The cost gate.** Over the eligible sessions, the median of (round
   trip ÷ O) ÷ s is at most **0.02**: a round trip costs at most 2 % of
   a normal day's move (s is B's own 14-day standard deviation of daily
   returns). On NQ this number is about 0.004, and a market at 0.02
   would pay in costs a little under half of what B earned there.

The gate of the minute reader stands: sessions from 2026-07-01 are
never read by this wave.

## 4. What is measured

For each market and rule, one number per session, in units of that
session's own risk:

- **B:** (gross − cost) ÷ s, on every session where B has its 14
  sessions and its s; 0 when B does not trade.
- **A:** (gross − cost) ÷ (risk ÷ entry), the result in multiples of
  the risk of the trade, on every eligible session; 0 when A does not
  trade.

**The pooled series of a rule** is, for each calendar trading day, the
plain average of that number over the markets that have a session of
the rule that day. **A class's series** is the same over the markets of
the class.

**The statistic** is wave twenty-seven's: the series is summed by ISO
week, and t is the mean of the weekly sums over its standard error.

Reported beside, never judged: each market alone (the same statistic;
and wave twenty-four's bar in the source's sizing, also with costs
doubled).

## 5. The verdicts

**The pooled test (one for A, one for B).** A rule **holds outside
stock indices** when its pooled series has **t of 2.5 or more** and a
mean above 0 in **each half** (to 2020-12-31, from 2021-01-01).

**The class tests.** For each class and rule: the one-sided p of its t.
Over all the class tests of the wave (at most eight), Benjamini and
Hochberg at 10 %. A class **passes** for a rule when it is among those
kept and its mean is above 0 in each half.

**What goes on to the shadow step** (tracked day by day on later
sessions, no orders), fixed now:

- when a rule holds outside stock indices: every class whose own mean
  is above 0 in each half;
- when it does not: the classes that pass their class test, if any.

A rule that goes on does so on **every market of the class**, unchanged.
Nothing else goes on. No variant of a rule that fails here is tried on
these bars.

**The decision is made once**, on every market this wave has read. It
needs at least four markets from at least two classes; with fewer there
is no decision. A market that was read cannot be left out of it.

Each rule is judged here whatever wave twenty-five says of it: the
markets are different.

## 6. Reads

- Each market is read **once** by this wave's own command, recorded in
  `MROF_MINUTE_HISTORY_EXPOSURE.json` before any result is shown.
- The decision of §5 is recorded there too, once.
- Sessions from 2026-07-01 stay unread on every market of §2. What goes
  on is to be checked on them later, once, under a rule fixed before
  that read.

## Explicitly NOT registered

- any change to A or B: thresholds, times, targets, stops, filters
- another day session or another anchor than §2's for any market
- other markets; Treasuries, grains and other currencies (§2)
- E (it holds overnight); any rule that failed NQ's screen
- sizes, budgets or stops on an account (a later file, if anything
  goes on)
- order flow, machine-learned models
- live, paper or simulated order placement

## Expected beforehand (written 2026-11-26, before any bar was read)

The cost gate leaves out the yen, and perhaps the euro. **B:** about one
chance in three of holding outside stock indices; if any class passes
alone it is most likely metals or energy. **A:** about one chance in
seven; its stop is the first five minutes, which on most of these
markets is only a few ticks wide, so costs take a large part of every
trade. The most likely single outcome is that neither rule holds and no
class passes, and that the plan then rests on the stock indices alone.
