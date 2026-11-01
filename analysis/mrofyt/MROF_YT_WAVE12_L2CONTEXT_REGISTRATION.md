# MROF_YT_WAVE12_L2CONTEXT_REGISTRATION.md — skip L2 on the wrong kind of day: two filters fixed in advance, judged on unseen days

**Status: FROZEN on 2026-11-01, before any replay holdout or validation
session was read by any tool.** Fading a failed break should suit a
normal two-sided day and suffer on a strong trend day or an unusually
big day. The operator asked for that filter. The context study
(`mrofyt_context.py`) reads it from years of minute bars, but only at
10:30 ET, and several of L2's best DEV trades came before then. This
file fixes two filters that use only what the recording shows at the
moment of each trade, at any hour, with every threshold set here and
none searched for.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on recorded tape. No order is placed.

---

## 1. Trades

Wave eight's L2 events, unchanged (wave three's L2 fires de-duplicated
by the pilot's 60 s rule, faded, entry at the first fire's mid, each
with its test number): **ALL** (every L2) and **FIRST** (test number 1).
Wave six's T1 exit and `mrofyt_costs`' round trip, as everywhere: target
25 points, stop 15, 30 minutes, $5 NQ / $2 MNQ, a tick of spread, a tick
of slip on a stop.

## 2. The day's scale

`A` = the mean high-to-low range of the instrument's previous recorded
sessions (the last 14 at most, **5 at least**), wave nine's measure. A
trade without `A` is outside both filters and counted apart.

## 3. The two filters

| filter | the trade is **removed** when, at its first fire |
| --- | --- |
| **TREND** | price is far from the session VWAP, `|mid − VWAP| >= 0.25 × A`, **and** the fade trades against that side (a short above VWAP, a long below it) |
| **BIG DAY** | the session's high-to-low so far (the runner's own high and low of the session's trades, from 18:00 ET) is already `>= 1.0 × A` |

Otherwise the trade is **kept**. `mid` is the entry mid; VWAP is the
runner's session VWAP at the fire (none: outside TREND).

## 4. The four tests (NQ; MNQ reported beside)

Each asks whether the filter **separates better trades from worse**: the
mean net points of the kept trades minus that of the removed trades,
above zero, session-clustered over both groups at once
(influence-function form, wave six part B's `diff_stats`), Student t on
`G − 1` degrees of freedom, **Holm over the four** at 0.05.

| id | trades | filter |
| --- | --- | --- |
| **TR-ALL** | ALL | TREND |
| **TR-FIRST** | FIRST | TREND |
| **BD-ALL** | ALL | BIG DAY |
| **BD-FIRST** | FIRST | BIG DAY |

| NQ trades | result | verdict |
| --- | --- | --- |
| kept or removed `< 20` | — | NOT TESTED |
| both `>= 20` | fails Holm, or difference `<= 0` | the filter does not help |
| both `>= 20` | survives Holm, difference `> 0`, 95 % interval above 0 | the filter helps: combined with L2 in a later registration, judged on sessions read by nothing before it |

Reported beside, not tested: the kept and removed trades' own win rate,
net points and one-position-at-a-time result; and, when a calendar file
is given (`--calendar`, lines `YYYYMMDD,EVENT`), L2 on event days against
other days.

## 5. Where it is judged

- **DEV** (sessions `<= 20260918`): describes only. Nothing is frozen.
- **Replay holdout** (`--holdout`): a folder holding ONLY NinjaTrader
  Market Replay recordings of sessions **before 2026-09-01**; refused if
  it holds any later session.
- **Validation** (`--unblind`, sessions `>= 20260921`); it marks every
  session it reads `EXPOSED_PILOT_DEV` for good.

## Explicitly NOT registered

- any other threshold, trend measure, range measure, look-back or
  reference; the context study's features or rules on recordings
- applying a filter to waves seven, ten or eleven, or to wave nine's
  targets
- a filter that changes the stop, target or size instead of skipping
- choosing a filter on DEV results (all four are judged)
- an event filter as a test (the calendar split is described only)
- machine-learned models of any kind
- live, paper or simulated order placement

## Implementation record — 2026-11-01

`mrofyt_l2context.py`, `tests_mrofyt_l2context.py`. Written against
this file before any real session was read by it; verified on hand-built
values and on synthetic recorder-format runs, never on market evidence.

| registered | implemented as | precision |
| --- | --- | --- |
| §1–§2 | `ContextRunner` (wave eleven's runner) puts the session VWAP and the range so far on every L2 / L4 fire; `context_events` | `A` and the test number come from wave nine's and wave eight's annotations |
| §3 | `classify` | the boundary values (exactly 0.25 × A, exactly 1.0 × A) remove |
| §4 | `diff_row`, `table` | none |
| §5 | `plan()` with `--holdout` (wave six's), `record_holdout_read`, `record_exposure` | none |
