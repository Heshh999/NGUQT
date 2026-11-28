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

## Implementation record — 2026-11-28

`mrofyt_stress35.py`, `tests_mrofyt_stress35.py` (8 tests), written
after this file was frozen and before any bar was read by it; verified
on sequences whose answer is known and on synthetic exports, never on
market evidence. Nothing above this line was changed.

| registered | implemented as | precision |
| --- | --- | --- |
| §1 the days | `plan`, `paths` | wave twenty-six's `prop_days` and `day_path`; at size 1 the suite finds the plan identical to wave twenty-six's and the account over the history, in its own order, equal to wave twenty-six's `account` in its result, the accounts lost and the largest fall |
| §2 the sizes | `a_micros`, `b_micros` | wave twenty-six's two formulas with the budget multiplied before rounding; at least one micro, at most 15 |
| §3 the account | `run` | "at or below" includes the line itself; the session on which the account is lost still counts in the year's result |
| §4 a year | `a_year` | thirteen blocks, the last cut to twelve sessions; Python's `random.Random(35)`, started again for every size, so every size sees the same years |
| §5 5 %, median, 95 % | `below` | the value at that share of the sorted years, counted from 0 |
| §5 the largest fall | `run` | from the highest running sum to the lowest value inside a session, as in wave twenty-six |
| §5 the history | `history` | the result a year is the whole result times 252 over the number of sessions |
| §7 once | `main`, `read_made`, `record_read` | NQ is read once, recorded in the minute-history ledger before anything is shown |

**Dry run, on fabricated sequences only.** Days that all win lose no
account; days that all lose $100 lose it every 45 sessions, five times
a year. This shows that the code counts what this file says; it says
nothing about the market.
