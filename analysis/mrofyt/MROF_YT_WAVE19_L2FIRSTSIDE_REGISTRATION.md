# MROF_YT_WAVE19_L2FIRSTSIDE_REGISTRATION.md — L2 at the first signal from each side of a level

**Status: FROZEN on 2026-11-05, before any validation session (on or
after 2026-09-21) or replay holdout session was read by any tool.**

Wave fourteen takes one L2 signal per level per session, whichever side
price comes from. The operator asked whether each side of a level should
get its own first signal: once a level breaks and price later tests it
from the other side ("support becomes resistance"), the traders trapped
there are different traders. Wave fourteen listed "first signal per side
of a level" as not registered; this wave registers it as its own test,
beside the headline, which is unchanged.

What DEV showed (seen, so this is the motivation and not evidence), from
the saved DEV report (`frozen_dev_20261024/w3.json.gz`), NQ, one
position at a time, net of costs:

| rule | trades | won | net points a trade | total |
| --- | --- | --- | --- | --- |
| first signal per level (wave fourteen) | 12 | 7 (58 %) | +9.44 | +113.25 |
| **first signal per side** (§2) | 16 | 11 (69 %) | +13.20 | +211.25 |
| the trades only this rule takes | 5 | 4 | +16.45 | +82.25 |
| first signal per side, 16 September left out | 10 | 6 (60 %) | +10.45 | +104.50 |

Three of the five added trades came on 16 September (the FOMC day).
Without that day the rule is no better than wave fourteen's (+11.97 a
trade without it).

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on recorded tape. No order is placed.

---

## 1. Events

Wave six's L2 events, unchanged (wave fourteen §1).

## 2. The first signal from each side

Per instrument and CME session, in time order. A **side** of a level is
the side price comes from, which is the trade's direction: a short fades
a break up through the level, a long fades a break down through it. An
event is taken when **none of its levels has had an L2 event in the same
direction earlier in that session**. Every L2 event uses up all its
levels for its own direction, taken or not. An event with no level is
not taken. Any hour.

So each level gives at most one short and one long per session; wave
fourteen's single trade per level is one of them.

## 3. The trade

Wave fourteen §3, unchanged: target 100 ticks (25 points), stop 60 ticks
(15 points), 1 800 s, mid-to-mid, `mrofyt_costs`' round trip, one
position at a time on each instrument.

## 4. The test (NQ)

Wave fourteen's verdict, unchanged: 30 or more trades; mean net per
trade above 0 with its 95 % interval above 0, session-clustered; and
still above 0 with the session of the largest total net removed. **PASS**
or **NOT PROVEN** with the reason; under 30, **NOT ENOUGH TRADES**. MNQ
is reported beside, never tested.

Beside, not tested: wave fourteen's per-level trades from the same read,
and the trades only this rule takes.

## 5. Withholding and where it is judged

- A held-out read with fewer than 30 NQ trades shows the counts only
  (wave fourteen §5).
- **DEV:** describes (the table above). **Validation** (`--unblind`):
  a **secondary** test beside wave fourteen, part of the one-read
  checkpoint from V43 on. **Replay holdout:** separately.
- Wave fourteen stays the headline.

## 6. What a verdict leads to

A PASS lets the per-side rule replace the per-level rule only in a later
registration judged on sessions read by nothing before it.

## Explicitly NOT registered

- a second or later signal from the same side; per calendar day; the
  cash session only
- a cooldown instead of "first"; requiring the level to have broken
  first
- any other target, stop or hold limit; scaled brackets
- any other wave's levels or entries
- machine-learned models of any kind
- live, paper or simulated order placement

## Implementation record — 2026-11-05

`mrofyt_l2firstside.py`, `tests_mrofyt_l2firstside.py`. Written against
this file before any held-out session was read by it; verified on
hand-built events, the saved DEV report and synthetic recorder-format
runs, never on market evidence.

| registered | implemented as | precision |
| --- | --- | --- |
| §1 | `FirstSideRunner` (wave fourteen's runner), `V.variant_events` | none |
| §2 | `first_per_side` | the side is the event's `direction` |
| §3 | `V.score_variants` (fixed exit), `V.one_at_a_time` | none |
| §4 | `FS.verdict` | none |
| §5 | `run`, `text`, the ledgers | none |
