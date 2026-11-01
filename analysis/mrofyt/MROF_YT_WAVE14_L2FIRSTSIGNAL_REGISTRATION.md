# MROF_YT_WAVE14_L2FIRSTSIGNAL_REGISTRATION.md — L2 at the first signal of each level: the primary test on the unseen days

**Status: FROZEN on 2026-11-01, before any validation session (on or
after 2026-09-21) or replay holdout session was read by any tool.**

Wave three's L2 (fade a failed break of a daily range level) is the one
idea with support on DEV. The operator chose **the first L2 signal at
each level each day, at any hour** as the version to take to the unseen
days, and asked that it be the one test those days decide.

What DEV showed (seen, so this is the motivation and not evidence), from
the saved DEV report (`frozen_dev_20261024/w3.json.gz`), NQ, one
position at a time, net of costs:

| rule | trades | won | net points a trade | sessions |
| --- | --- | --- | --- | --- |
| **this rule** (§2) | 12 | 7 (58 %) | +9.44 | 6 |
| every L2 (wave eight V0) | 57 | 30 (53 %) | +6.15 | 6 |
| strict first touch (wave eight V1) | 3 | 2 | — | 1 |

A count shown to the operator earlier (13 trades, 62 %, +10.60) keyed
signals by the set of levels each one touched. One signal touched two
levels at once, and that let a later signal at one of them through as
a "first". §2 counts every level separately; that is the rule meant,
and it is the one registered, though it reads lower.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on recorded tape. No order is placed.

---

## 1. Events

Wave six's L2 events, unchanged (its registration A1, as wave eight §1):
wave three's L2 fires, de-duplicated by the pilot's 60 s rule, traded
against the approach (`-ad`), entry at the first fire's mid, on its own
recording run's mid path. Wave three's detector and the signal module
(pinned hash) are untouched.

## 2. The first signal at a level

Per instrument and per CME session (18:00 ET to 17:00 ET), in time
order. An event's **levels** are the levels of the fires it collects
(the pilot's de-duplication lists them; nearly always one). An event is
a **first signal** when **none of its levels has had an L2 event
earlier in that session**. Every L2 event uses up all its levels,
whether it is taken or not. An event with no level is not taken. Any
hour of the session counts, overnight included.

## 3. The trade

Target 100 ticks (25 points), stop 60 ticks (15 points), 1 800 s
(30 minutes), mid-to-mid on the run's compressed path (wave six's
`path_exit`); a trade whose run ends before it resolves is dropped.
`mrofyt_costs`' round trip on every trade: $5 commission on NQ ($2 on
MNQ), a tick of spread, a tick of slip on a stop. **One position at a
time** on each instrument, in time order: a first signal that comes
while the previous trade is still open is skipped.

## 4. The test (NQ only; one test, so no multiplicity correction)

| NQ trades | result | verdict |
| --- | --- | --- |
| `< 30` | — | NOT ENOUGH TRADES (§5) |
| `>= 30` | (a) mean net per trade `> 0` with its 95 % interval above 0, session-clustered (wave four's estimator, Student t on `G − 1` degrees of freedom), **and** (b) mean net per trade still `> 0` with the session of the largest total net removed | **PASS** |
| `>= 30` | anything else | **NOT PROVEN**, with the reason: loses after costs; could be luck (the interval reaches 0); or rests on one day |

MNQ is the same market; it is reported beside and never tested.

## 5. Fewer than 30 trades: results withheld

A held-out read (`--unblind` or `--holdout`) with fewer than 30 NQ
trades shows **the trade count and the number of days only**. Win rate,
points, the per-day table and the reference rows are withheld from the
screen and from the report file. The read still marks every session it
inspects as an `--unblind` read always does. Recording continues; the
verdict is taken at **the first read that holds 30 NQ trades**, on every
session after 2026-09-18 read by then. The threshold is not lowered, no
session is dropped, and nothing in §1–§4 changes in between.

## 6. Beside (not tested; shown only when the results are shown)

- every L2, one at a time (wave eight V0 / wave six T1);
- the strict first touch, one at a time (wave eight V1);
- the test's trades day by day: trades, wins, net points.

## 7. Where it is judged

- **DEV** (sessions `<= 20260918`): describes only. Read by the runner it
  should give the first row of the DEV table above (12 trades, 7 won,
  +9.44).
- **Validation** (`--unblind`, sessions `>= 20260921`): **the primary
  test.** It marks every session it reads `EXPOSED_PILOT_DEV` for good.
- **Replay holdout** (`--holdout`): a folder holding ONLY NinjaTrader
  Market Replay recordings of sessions **before 2026-09-01**; judged by
  the same rule, separately; recorded in
  `MROF_REPLAY_HOLDOUT_EXPOSURE.json`.

Waves six to thirteen were registered before this read; their own tests
on these sessions stand as registered and are secondary to this one.
Any idea registered after this read is judged on sessions recorded
after it.

## 8. What a verdict leads to

- **PASS:** a simulated-trading and execution study in NinjaTrader
  (fills, slippage, timing against the recorded result). **Still no
  live orders**; real F5 compilation and the genuine smoke test are
  user-side.
- **NOT PROVEN:** L2 at the first signal is not shown to be an edge on
  unseen days. Nothing is re-tuned on these sessions.

## Explicitly NOT registered

- any other first-signal definition: per calendar day instead of per CME
  session, the RTH session only, first signal per side of a level,
  a cooldown instead of "first"
- any time window, weekday or event-day filter
- any other target, stop, hold limit, trailing or partial exit
- wave nine's targets, wave twelve's filters, wave seven's grade or any
  other combination
- dropping the Fed day or any session; a verdict on MNQ
- machine-learned models of any kind
- live, paper or simulated order placement

## Implementation record — 2026-11-01

`mrofyt_l2firstsignal.py`, `tests_mrofyt_l2firstsignal.py`. Written
against this file before any held-out session was read by it; verified
on hand-built events and on synthetic recorder-format runs, and the DEV
row checked against the saved DEV report, never judged on market
evidence.

| registered | implemented as | precision |
| --- | --- | --- |
| §1 | `FirstSignalRunner` (wave eight's runner), `V.variant_events` | none |
| §2 | `first_signals` | an event's levels are `levels` from the pilot's de-duplication |
| §3 | `V.score_variants` (fixed exit), `V.one_at_a_time` per instrument | one position at a time among the first signals only |
| §4 | `verdict` | "the session of the largest total net" is the largest per-session sum of net points among the test's trades |
| §5 | `run` (`withheld`), `text` | the withheld report keeps `n` and `sessions` only |
| §6–§7 | `run`, `record_exposure`, `record_holdout_read` | none |
