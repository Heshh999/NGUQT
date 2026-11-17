# MROF_YT_WAVE23_VWAPVALUE_REGISTRATION.md — the two VWAP zones and overnight value acceptance, on years of one-minute bars

**Status: FROZEN on 2026-11-17, before any minute export was read for
these questions.** No tool in this repository has traded these three
rules on any data.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on historical bars. No order is placed.

---

## 0. Where the three rules come from (seen, so this is motivation and not evidence)

**Wave four's anatomy** (`frozen_dev_20261024/w4.json`, the 15 DEV
sessions of September, about 48 000 ten-second snapshots of NQ) tabled,
for every order-flow and price feature by decile, the share of moments
from which a long and a short reach +25 points before −10 within 30
minutes. Read as **long minus short** (direction) apart from **long plus
short** (how much price moves at all):

| feature | what the deciles show |
| --- | --- |
| aggressor delta (10 s, 60 s, 180 s), order-flow imbalance, top-3 book imbalance | direction mostly within ±3 points; their extremes mark **activity** (both sides reach their targets more often), not direction |
| distance from the session VWAP | **two zones on both sides**: moderately away from VWAP, price kept going away (below: −8.1, −4.5; above: +2.9, +6.5); far from VWAP, it came back (below: +5.4, +3.4; above: −2.0, −1.9) |
| the last 30 minutes' move | continued (+2.8 to +9.3 when up, −5.3 to −8.2 when mildly down), except after the largest drops (+3.3) |

**The held-out checkpoint** (13–17 November, sessions to 2026-11-13, all
now `EXPOSED_PILOT_DEV`) agreed in three places: fades at the VWAP
bands lost on NQ and MNQ in September and after it (won 33–35 % against
the 37.5 % a random walk gives a 25 / 15 bracket); L2 fades taken back
toward VWAP from 0.25 × A or more won 46 % on both instruments against
35 % for the rest; and the first failed break of the **overnight value
area** after 09:30 was followed by the break resuming 26 times in 31 on
NQ (13 of 18 on MNQ), on 13 of the 15 days that had one.

These are reads of seen data after 67 tests failed. They choose the
three rules below; they are not evidence for them. Earlier minute-bar
studies here (2019–2026) found plain VWAP reversion losing
(`docs/RVMR_STRAT_V1_FINDINGS.md` B4) and a fade of structure breaks
two ATR from VWAP losing (`docs/NSERIES_FINDINGS.md` N10); neither
waited for the 30-minute move to turn back toward VWAP, as RUBBER does.

## 1. Bars, scale, VWAP and the 30-minute move

- **Bars:** NQ one-minute exports read exactly as part 16A and wave
  twenty-two read them (the context study's reader, time-stamp check and
  front contract; nothing from 2026-07-01), each bar's volume kept.
- **A:** the mean full-session high-to-low range of the 14 previous
  sessions (**5 at least**), wave nine's measure, as wave twenty-two
  computes it.
- **VWAP:** the session VWAP from 18:00 ET, `(high + low + close) / 3`
  weighted by volume, up to and including the bar (wave twenty-two's).
- **d** = the bar's close minus VWAP.
- **trend** = the bar's close minus the close of the last bar at or
  before 30 minutes earlier in the same session; none if that bar is
  more than 35 minutes earlier.

## 2. The three rules

Signals come from bar closes from **09:30:00 to 15:29:59 ET** (RUBBER,
MOMENTUM) or **09:30:00 to 16:59:59 ET** (ACCEPT).

| id | when | trade |
| --- | --- | --- |
| **RUBBER** | `|d| >= 0.15 × A` and the trend points back toward VWAP by `0.08 × A` or more | toward VWAP |
| **MOMENTUM** | `0.03 × A <= |d| <= 0.13 × A` and the trend points away from VWAP by `0.03 × A` or more | away from VWAP |
| **ACCEPT** | part 16A's failed break (a bar 2 ticks through, a close back within 5 bars) of the overnight POC, VAH or VAL | **with the break**, not against it |

- RUBBER and MOMENTUM take the **first** signal of each direction per
  session.
- ACCEPT takes the **first** signal at each of its three levels per
  session.

**The overnight value area:** the bars of 18:00 to 09:29 ET, each bar's
volume spread evenly over the 1-point bins from its low to its high; the
context study's `value_area` (70 %). It needs a bar by 18:30 ET and one
from 09:00 ET; otherwise that session has none.

## 3. The trades

| id | target | stop |
| --- | --- | --- |
| RUBBER | 25 points | 15 points |
| MOMENTUM | 25 points | 15 points |
| ACCEPT | 15 points | 25 points |

- Entry at the signal bar's close; at most 30 minutes; first touch on
  the following bars' highs and lows (a bar touching both is a stop),
  else the close of the last bar that starts within the 30 minutes.
- Dropped if the session's bars end first.
- One position at a time within each rule.
- `mrofyt_costs`' round trip on every trade.

ACCEPT's bracket is the one the checkpoint's numbers describe (the
break resuming 15 points before reversing 25). It needs about 64 % won
to break even after costs.

## 4. The tests (NQ), in each era

For each rule: mean net points a trade above 0 with its 95 % interval
above 0, **month-clustered**, and still above 0 without the month of the
largest total net; **at least 100 trades**. **Holm over the three** at
0.05. PASS, or NOT PROVEN with the reason; under 100 trades, NOT ENOUGH
TRADES.

## 5. The two eras

| era | sessions | how it is read |
| --- | --- | --- |
| **NEWER** | 2019-06-01 to 2026-06-30 | without a flag |
| **OLDER** | before 2019-06-01 | `--unblind`, recorded in `MROF_MINUTE_HISTORY_EXPOSURE.json` |

- **CONFIRMED:** a rule passes in both eras.
- **ONE ERA ONLY:** the older era holds fewer than 100 of its trades,
  and it passes in the newer one. This is weaker and is reported as
  such.
- Anything else: the rule is dropped.

Nothing is changed between the two reads.

## 6. Beside, not tested

By year; longs and shorts apart; for ACCEPT, by level; signal counts;
sessions without A or without an overnight value area.

## 7. What a verdict leads to

A CONFIRMED rule is registered again for the recordings' fresh sessions
(from 2026-11-16), with the order flow added as a **timing filter**
(only when the tape is active), which is the one job wave four's
anatomy suggests it can do. Still no live orders in any case.

## Explicitly NOT registered

- any other zone edge, trend length, threshold or scale; VWAP bands;
  another anchor for VWAP
- other entry hours; more than the first signal per direction (RUBBER,
  MOMENTUM) or per level (ACCEPT)
- other targets, stops or hold limits; a fade at the overnight value
  area
- order flow in this wave; MNQ; anything from 2026-07-01 on
- machine-learned models of any kind
- live, paper or simulated order placement

## Implementation record — 2026-11-17

`mrofyt_vwapvalue.py`, `tests_mrofyt_vwapvalue.py`. Written against this
file before any minute export was read; verified on hand-built bars and
on synthetic NinjaTrader-format exports, never on market evidence.

| registered | implemented as | precision |
| --- | --- | --- |
| §1 | `SF.history_sessions` (wave twenty-two's reader), `ordered`, `trend_at` | the 30-minute bar is found by its time stamp, not its position |
| §2 | `zone_signals`, `overnight_value`, `accept_signals` (part 16A's `signals` and `first_per_level`) | none |
| §3 | `outcome` (part 16A's `outcome_bars` with the rule's bracket), `take`, `ML.net_points` | none |
| §4 | `ML.month_verdict`, `BM.holm` | none |
| §5 | `run`, `main`, `LG.record_history_read` | none |
