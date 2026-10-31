# MROF_YT_WAVE8_L2VARIANTS_REGISTRATION.md — L2 on the first test, in the morning, both, or held five minutes: registered before any held-out read

**Status: FROZEN on 2026-10-31, before any replay holdout or validation
session was read by any tool.** Wave three's L2 (fade a failed break of
a daily range level) remains the one idea with support. On the DEV
sessions (seen, so this is the motivation and not evidence), the
operator asked two trader's questions of it, and the saved DEV report
(`frozen_dev_20261024/w3.json.gz`) answered them descriptively:

- **The first test of a level is worth more than a retest.** The first
  L2 signal at a level that session: 12 trades one position at a time,
  67 % won, +12.79 points a trade net; later signals at the same level:
  45 trades, 49 %, +4.38. (That count saw only levels that produced an
  L2 signal; the definition below counts every test.)
- **The morning is the best window.** 09:30–11:30 ET: 14 trades, 57 %,
  +7.25 net; 11:30–16:00: 38 trades, 47 %, +4.39. Without 16 September
  the morning falls to 7 trades, +1.50.
- Wave five's half-life curve: L2's move is in its favour from 5 s to
  5 min and against it from 10 min on.

Each is registered here as a rule, fixed before the sessions that judge
it are read. The operator picked **V3, both together**, as the version
they would trade.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on recorded tape. No order is placed.

---

## 1. Events

Wave six's L2 events, unchanged (its registration A1): wave three's L2
fires, de-duplicated by the pilot's 60 s rule, traded against the
approach (`-ad`), entry at the first fire's mid, on its own recording
run's mid path. Wave three's detector and the signal module (pinned
hash) are untouched.

## 2. The test number of a level

The runner's approaches (its §2: price comes within the level's radius;
a new approach to the same level needs the previous one to have ended
by retreating beyond the radius by 2 more ticks) are counted **per
instrument, per session, per level**, in order, from the start of the
CME session (18:00 ET), every approach counted whether or not it
produced a signal. An L2 event's **test number** is that count for the
approach of its first fire. The count resets at each session's close
and goes back with an abandoned run.

## 3. The four variants

| id | events | exit |
| --- | --- | --- |
| **V1 FIRST TEST** | test number 1 | fixed: target 100 ticks (25 points), stop 60 ticks (15 points), 1 800 s |
| **V2 MORNING** | first fire at 09:30:00–11:29:59 ET | fixed |
| **V3 FIRST TEST + MORNING** (the operator's pick) | both | fixed |
| **V4 QUICK** | every L2 event | target 100, stop 60, and **out at the mid 300 s (5 minutes) after entry** if neither came first |

A reference row **V0** (every L2 event, fixed: wave six's T1) is
reported beside them and is not tested.

## 4. Scoring

Mid-to-mid on the run's compressed path (wave six's `path_exit`); a
trade whose run ends before it resolves is dropped. `mrofyt_costs`'
round trip on every trade: $5 commission on NQ ($2 on MNQ), a tick of
spread, a tick of slip on a stop. Every event counts (as in wave six,
so V1–V4 compare directly with T1); one position at a time and per
session results are reported beside.

## 5. The four tests (NQ; MNQ reported beside)

Each tests the **mean net result per trade above zero**,
session-clustered (wave four's estimator), Student t on `G − 1`
degrees of freedom, **Holm over the four** at 0.05.

| NQ trades | result | verdict |
| --- | --- | --- |
| `< 30` | — | NOT TESTED |
| `>= 30` | fails Holm, or mean net `<= 0` | no signal |
| `>= 30` | survives Holm, mean net `> 0`, 95 % interval above 0 | promising: a sizing and execution study, **still no live orders** |

V1 and V3 are rare by design (DEV: about one first-test L2 every
session or two, fewer in the morning). On a short holdout they may stay
NOT TESTED; they are then judged at the read that first holds 30 NQ
trades. No threshold is lowered to reach a verdict sooner.

## 6. Where it is judged

- **DEV** (sessions `<= 20260918`): describes only.
- **Replay holdout** (`--holdout`): a folder holding ONLY NinjaTrader
  Market Replay recordings of sessions **before 2026-09-01**; refused
  if it holds any later session. Read once, recorded in
  `MROF_REPLAY_HOLDOUT_EXPOSURE.json`. Waves six, seven and eight are
  all registered before anyone has read the replay folder.
- **Validation** (`--unblind`, sessions `>= 20260921`) at the December
  checkpoint; it marks every session it reads `EXPOSED_PILOT_DEV` for
  good.

Nothing is computed from DEV and frozen: every setting is fixed in
this file.

## Explicitly NOT registered

- any other definition of a test (touch distance, re-arm rule, a test
  counted per day instead of per CME session, overnight approaches
  excluded); a second or third test as its own variant
- any other window (09:30–10:30, the afternoon, the overnight) or a
  window chosen per weekday or per event day
- any other hold limit, target or stop; trailing or partial exits
- combining with wave six's stops, wave seven's grade or a context rule
- dropping the Fed day or any session from the evaluation
- machine-learned models of any kind
- live, paper or simulated order placement

## Implementation record — 2026-10-31

`mrofyt_l2variants.py`, `tests_mrofyt_l2variants.py`. Written against
this file before any held-out session was read by it; verified on
hand-built states and paths and on synthetic recorder-format runs,
never on market evidence.

| registered | implemented as | precision |
| --- | --- | --- |
| §1 | `L2VariantRunner`, `variant_events` | the test number travels with the event's first fire, like wave six's annotations |
| §2 | `L2VariantRunner._count_test` (called where the runner opens an approach) | counted from the first approach the recording holds; a recording gap hides the approaches inside it |
| §3–§4 | `in_morning`, `score_variants` (wave six's `path_exit` with a 300 s limit for V4) | V4's exit is the last mid at or before 300 s |
| §5 | `table` | none |
| §6 | `plan()` with `--holdout`, `record_holdout_read`, `record_exposure` | none |
