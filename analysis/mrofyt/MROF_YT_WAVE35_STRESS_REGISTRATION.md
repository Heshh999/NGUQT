# MROF_YT_WAVE35_STRESS_REGISTRATION.md — how often the account plan would lose the account: NQ's ten years in another order

**Status: FROZEN on 2026-11-28, before the tool was written and before
any resampling below was computed.** What had been seen beforehand is
listed in §0.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only planning on historical bars. No order is placed.

---

## 0. Where this comes from, and what was already seen

Wave twenty-six put A and B on one $150,000 account in MNQ and found
how often NQ's ten years would have lost it. That is one history: the
same days in another order give other falls. A prop account is lost by
its worst stretch, not by its average, so the question for planning is
how often a year of such days loses the account, and how much smaller
the positions must be for that to be rare.

**This file judges nothing.** No rule passes or fails by it, and nothing
goes on or stops. It gives planning numbers for the size of the
positions.

**Seen beforehand:** wave twenty-six's report on NQ's ten years: the
account's result, the accounts lost, the largest fall, by year.

**Not known here:** the prop firm's own rules. The account below is wave
twenty-six's; when the firm's rules are known they replace it in a later
file.

## 1. The days

Wave twenty-six's plan, unchanged: A and B in MNQ with its costs, A
about $150 at risk a trade and B about $500 for its day's volatility,
at most 15 micros and at least one. A session gives two numbers: its
result in dollars and its lowest value at a minute close. A session
without a trade gives 0 and 0. NQ's ten years only (to 2026-06-11).

## 2. The sizes

The two budgets together times **1**, times **1/2** and times **1/4**
(still at least one micro). Each **without** a day stop and **with**
wave twenty-six's day stop, $1,000 times the same factor.

## 3. The account

Wave twenty-six's: it starts at $150,000 and is **lost** when the
balance plus a session's lowest value is at or below the highest
end-of-day balance so far less $4,500. After a loss it starts again at
$150,000 and the year goes on.

## 4. The resampling

A **year** is 252 sessions put together from **blocks of 20
consecutive sessions** of the history; each block starts at a session
drawn with equal chance, and a block that reaches the last session goes
on from the first. **5,000 years**, from the fixed random seed 35, the
same for every size.

## 5. Reported, for each size, with and without the day stop

- the share of years with at least one account lost, and the mean
  number lost a year;
- the year's result in dollars: its median and the values that 5 % and
  95 % of years stay below;
- the median of the year's largest fall;
- beside them, the history itself in its own order: the accounts lost
  and the result a year.

## 6. What this is not

Not a forecast. The resampling keeps the days as they were and assumes
that later days are drawn from the same ones: if B stops working, the
truth is worse than any line here. Blocks keep twenty days of a stretch
together, no more. The same ten years have been looked at by many
waves.

## 7. Reads

NQ's ten years (already read), by this wave's own command **once**,
recorded before any result is shown. No other market; NQ's later
months are not read. Sessions from 2026-07-01 are never read.

## Explicitly NOT registered

- any verdict, any change to A or B, any other account or budget
- other block lengths, year lengths or seeds
- live, paper or simulated order placement

## Expected beforehand (written 2026-11-28, before anything was computed)

At wave twenty-six's own size a lost account in more than half of the
years; at a quarter of it, in fewer than one year in four, with the
year's result a quarter as large. The day stop changes little.
