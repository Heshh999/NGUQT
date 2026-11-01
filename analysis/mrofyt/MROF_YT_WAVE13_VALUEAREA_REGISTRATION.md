# MROF_YT_WAVE13_VALUEAREA_REGISTRATION.md — back into yesterday's value area with speed, filtered by the order flow, with targets from value itself: registered before any held-out read

**Status: FROZEN on 2026-11-01, before any replay holdout or validation
session was read by any tool.** The operator proposed a fair-value
setup: price leaves yesterday's value area, fails to be accepted outside
it, and comes back in fast; the order flow confirms the return; the
trade goes back into value. It is the value-area re-entry of Market
Profile practice (often called the "80 % rule": once back in value,
price tends to travel to the other side). It shares L2's mechanism, a
failed move outside an accepted price range, and it comes with targets
from structure: the POC and the far edge of value. The operator also
asked that the volatility-scaled target (wave nine's quant target) be
tested here. All four tests are fixed below, before any session that
judges them is read.

Wave seven listed yesterday's POC, VAH and VAL among its levels, from
10 s volume, one attempt each; their first break nearly always came
overnight and used the level up, so wave seven made no trade there and
did not test this idea.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on recorded tape. No order is placed.

---

## 1. Yesterday's value area

- **Profile:** every recorded trade of the instrument's **cash session**
  (09:30:00–15:59:59 ET), its size added to its price's **1-point bin**.
- **Value area:** the context study's `value_area` (POC = the fullest
  bin's centre; grown toward the fuller neighbour until it holds **70 %**
  of the volume; VAH = its top, VAL = its bottom).
- **Complete:** the session's first recorded cash trade at or before
  10:00 ET and its last at or after 15:30 ET; otherwise that session has
  no value area.
- **Yesterday's:** the most recent earlier recorded session of the same
  instrument that has a value area.

## 2. The event

On the 10 s grid of each recording run (mid, aggressor delta `D`, its
frozen side-signed z `z_delta_s`), against yesterday's value area:

- **Out:** a grid mid at least **2 points** above VAH (`b = +1`) or below
  VAL (`b = −1`).
- **Back in:** the first later grid tick whose mid is back inside value
  by at least 1 tick (below VAH for `b = +1`, above VAL for `b = −1`).
  That tick ends the episode either way; a new one needs price out by 2
  points again.
- **With speed, confirmed by the order flow:** at that tick, the mid has
  moved at least **4 points back toward value over the last 30 s** (from
  the grid tick 30 s earlier), **and** the tick's aggression is into value
  (`D` against `b`) with `z_delta_s >= 2.0`.
- **Trade:** at that tick's mid, into value (`−b`). Entries **09:30–15:30
  ET** only.

## 3. Exits and costs

The same **60-tick (15-point) stop** and **1 800 s** limit for every
version, mid-to-mid on the run's path (wave six's `path_exit`); a trade
whose run ends before all four versions resolve is dropped from all.

| target | rule |
| --- | --- |
| **FIXED** | 100 ticks (25 points) |
| **POC** | yesterday's POC, if at least 2 points ahead of the entry; otherwise FIXED |
| **FAR EDGE** | the far edge of value (VAL after a re-entry from above, VAH from below), if at least 2 points ahead; otherwise FIXED |
| **SCALED** | wave nine's: `100 ticks × A / A_ref`, clamped to 40–300 ticks, `A_ref` from wave nine's frozen file (`--a-ref`); without `A` or `A_ref`: FIXED |

`mrofyt_costs`' round trip: $5 NQ, $2 MNQ, a tick of spread, a tick of
slip on a stop.

## 4. The four tests (NQ; MNQ reported beside)

| id | question | statistic |
| --- | --- | --- |
| **VA1** | does the setup make money with the fixed exit? | mean net points per trade (FIXED) above zero |
| **VA2** | does the POC target beat the fixed 25? | per-trade net(POC) − net(FIXED), mean above zero |
| **VA3** | does the far edge beat it? | net(FAR EDGE) − net(FIXED) |
| **VA4** | does the scaled target beat it? | net(SCALED) − net(FIXED) |

Session-clustered (wave four's estimator), Student t on `G − 1`
degrees of freedom, **Holm over the four** at 0.05. Every event counts;
one position at a time is reported beside.

| NQ trades | result | verdict |
| --- | --- | --- |
| `< 30` | — | NOT TESTED |
| `>= 30` | fails Holm, or the mean `<= 0` | no signal / no better |
| `>= 30` | survives Holm, mean `> 0`, 95 % interval above 0 | promising / beats the fixed 25, **still no live orders** |

## 5. Where it is judged

- **DEV** (sessions `<= 20260918`): describes only. Nothing is frozen
  here; `A_ref` is wave nine's.
- **Replay holdout** (`--holdout`): a folder holding ONLY NinjaTrader
  Market Replay recordings of sessions **before 2026-09-01**; refused if
  it holds any later session.
- **Validation** (`--unblind`, sessions `>= 20260921`); it marks every
  session it reads `EXPOSED_PILOT_DEV` for good.

## Explicitly NOT registered

- any other session for the profile (the full session, today's
  developing value), bin size, value share, completeness rule
- any other out distance, back-in distance, speed distance or window,
  z threshold, entry hours; a hold-inside-value condition
- any other target, a stop at the excursion's extreme, trailing or
  partial exits
- combining with L2, the day-context filters or the level groups
- choosing among the targets on DEV results (all four are judged)
- machine-learned models of any kind
- live, paper or simulated order placement

## Implementation record — 2026-11-01

`mrofyt_valuearea.py`, `tests_mrofyt_valuearea.py`. Written against this
file before any real session was read by it; verified on hand-built
profiles and grids and on synthetic recorder-format runs, never on
market evidence.

| registered | implemented as | precision |
| --- | --- | --- |
| §1 | `ValueRunner` (wave twelve's runner) adds each cash-session trade to the session's profile and keeps the value area at the session's close; `prev_value` | the Eastern offset is taken once per hour; an abandoned run's trades leave the profile |
| §2 | `va_events` | the 30 s look-back is the grid tick exactly 30 s earlier; none: no trade |
| §3 | `score` | none |
| §4 | `table` (`mrofyt_l2targets.paired_stats` for VA2–VA4) | none |
| §5 | `plan()` with `--holdout` (wave six's), `record_holdout_read`, `record_exposure` | none |
