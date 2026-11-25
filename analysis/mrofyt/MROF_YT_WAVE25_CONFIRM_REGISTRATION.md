# MROF_YT_WAVE25_CONFIRM_REGISTRATION.md — the three survivors of the screen, on data they have not seen

**Status: FROZEN on 2026-11-25, before any bar or recording was read for
these questions.**

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research. No order is placed.

---

## 0. Where this comes from

Wave twenty-four screened fifteen ideas on ten years of NQ minute bars.
Three passed: **A** (the 5-minute opening range breakout), **B** (out of
the noise area) and **E** (buy weakness at the close). The screen ran on
bars that had been read before, so a pass proved nothing.

The funnel's second step was to be an order-flow check on the 55
recorded sessions. A review of how order flow is used on index futures
(published research and practitioners, 2026-11-24) found no support for
order flow choosing direction beyond about a second, which is what this
repository's own tests had found. The operator changed the second step
on 2026-11-25: **the three rules are confirmed on data they have not
seen, and the recordings are used for what they measure well, the real
cost of a trade.**

**Seen beforehand:** everything in wave twenty-four's report (the three
rules' results on NQ by half and by year, their exits, and that all
three still passed with costs doubled; A also with costs tripled, B
strongly). Nothing below had been computed on any data when this file
was frozen.

## 1. The rules

A, B and E **exactly as wave twenty-four registered and coded them**
(`mrofyt_screen15.py`: `rule_a`, `rule_b`, `rule_e`, `nets`, `judge`).
Nothing in them is changed, on any market.

## 2a. Other markets, the same ten years

- **Markets:** **ES** and **RTY** (RTY from its first contract, 09-17);
  **YM** as well if the operator's feed has it. One-minute exports as
  for NQ, read by the same reader with the market's own contracts.
- **Hours:** the cash session 09:30–16:00 ET, as on NQ. Markets with
  other hours (crude, gold, bonds) are not in this wave.
- **Costs:** the same model as NQ: a round trip pays 5 dollars of
  commission and one tick of spread, a stop one tick more; each
  contract bought or sold pays half a round trip.

  | market | tick | dollars a tick | round trip | on a stop |
  | --- | --- | --- | --- | --- |
  | NQ | 0.25 | 5.00 | 0.50 | 0.75 |
  | ES | 0.25 | 12.50 | 0.35 | 0.60 |
  | RTY | 0.10 | 5.00 | 0.20 | 0.30 |
  | YM | 1.00 | 5.00 | 2.00 | 3.00 |

- **The bar:** wave twenty-four's, unchanged, on each market apart: in
  each half (to 2020-12-31, from 2021-01-01) 30 trades or days, a
  profit after costs, and still one without its best month; E over the
  half's average holding.
- **Beside:** the same with costs doubled.

These markets move with NQ on most days. Passing on them shows the
effect is not an accident of NQ's bars; it is not a second independent
sample.

## 2b. NQ, the months after the screen

- **Bars:** NQ one-minute bars for sessions **2026-07-01 to
  2026-11-13**, which the screen never read (it stopped at 2026-06-11).
  Earlier sessions are read only to build the rules' histories.
- **The gate:** the minute reader refuses sessions from 2026-07-01, to
  keep the recorded sessions unread by minute-bar tools. The recorded
  sessions to 2026-11-13 are all `EXPOSED_PILOT_DEV` since the
  checkpoint. **For this read only, and only with `--later-months`, the
  refusal moves to 2026-11-14.** Sessions from 2026-11-16 stay refused:
  they are kept for the third step.
- **The read is made once.**
- **The verdict, per rule** (same units as the screen; E over the
  window's average session):

  | verdict | when |
  | --- | --- |
  | IN LINE | 30 trades or days, mean net above 0 |
  | WEAK | 30 or more, mean net at or below 0 but within two standard errors of 0 |
  | COLLAPSED | 30 or more, mean net below 0 by more than two standard errors |
  | TOO FEW | fewer than 30 |

About 96 sessions cannot prove a rule of this size (a real one would
show a loss here about one time in four). Only COLLAPSED counts against
it.

## 2c. What a trade really costs (the recordings)

- **Sessions:** the 55 recorded sessions (2026-09-01 to 2026-11-13),
  NQ, tape and book.
- **Trades:** every A and B trade those sessions give, by the rules of
  §1 on one-minute bars of the recorded trades.
- **Measured, for each entry and exit:** the spread at that second (the
  best ask minus the best bid, in ticks) and the contracts shown at the
  best price on the side taken; for A's stops, the slip: the stop price
  against the best price on the far side at the first trade at or
  through the stop.
- **The measured round trip** = 5 dollars of commission + half the
  spread at entry + half the spread at exit + the slip on a stop, in
  points, averaged over each rule's trades.
- **The bar:** the measured average round trip is **at most twice** the
  assumed one (0.50 points; 0.75 on a stop). Both rules passed the
  screen at twice the assumed cost.
- E trades at the close, about four times in these sessions: not
  measured.

The tool for 2c is a later file written against this section; nothing
in the section changes when it is written.

## 3. What the verdicts lead to

A rule goes on to the third step (tracked day by day on sessions from
2026-11-16, no orders, read once at a date fixed beforehand) when:

- it passes the bar of §2a on **ES and RTY** (and YM if read);
- it is not COLLAPSED in §2b; and
- for A and B, the measured cost of §2c is within its bar.

Otherwise it is dropped. No variant of a dropped rule is tried on these
data. Still no live orders in any case.

## Explicitly NOT registered

- any change to A, B or E; any other threshold, time, hold or sizing
- other markets or hours than §2a's; MNQ
- a second read of §2b's months; any read of sessions from 2026-11-16
- order flow as a filter on entries or exits
- machine-learned models of any kind
- live, paper or simulated order placement

## Implementation record — 2026-11-25

`mrofyt_confirm25.py`, `tests_mrofyt_confirm25.py` (§2a, §2b). Written
against this file before any of its bars was read; verified on
synthetic exports, never on market evidence.
