# MROF_YT_WAVE11_EARLY_LEVELS_REGISTRATION.md — an early order-flow entry after a real break, and four more level groups judged apart: registered before any held-out read

**Status: FROZEN on 2026-11-01, before any replay holdout or validation
session was read by any tool.** Two requests from the operator, fixed
here before the sessions that judge them are read:

1. **Enter earlier.** Wave ten waits for a one-minute candle to close
   back inside after a one-minute close through a big level. L2's
   half-life on DEV put most of its move in the first 30 s to 5 minutes,
   so part of that move is gone by the reclaim close. The **EARLY** entry
   keeps wave ten's real break (a one-minute close through) and enters
   at the first 10 s grid tick where price is back through the level and
   the order flow confirms it.
2. **More key levels.** VWAP and its bands, the pivots, confirmed 1-hour
   and 4-hour swing highs and lows, the 09:30 cash open and the Globex
   open. They are **not** mixed into the six daily range levels, where
   the only supported idea lives: each group is judged on its own, so
   each one earns its place or not.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on recorded tape. No order is placed.

---

## 1. The level groups

| group | levels |
| --- | --- |
| **MAIN** (unchanged) | yesterday's high and low, the overnight high and low (from 09:30 ET), last week's high and low |
| **A. HIGHER-TIMEFRAME SWINGS** | confirmed 1-hour and 4-hour swing highs and lows |
| **B. OPENS** | the 09:30 cash open, the Globex open |
| **C. VWAP** | the session VWAP, its upper and lower bands (the runner's ±2 σ) |
| **D. PIVOTS** | PP, R1, S1, M2, M3 from the previous session's high, low and close (the runner's `pivots`) |

MAIN, B, C and D are read from the runner at every 10 s grid record
(VWAP and its bands move; the others are fixed for the session). R1 and
S1 come from the same formula as PP, M2 and M3.

**Swings (group A).** Candles of the instrument's mid, across every
recording run in time order: **1-hour** candles on Eastern-time hours and
**4-hour** candles on 18:00, 22:00, 02:00, 06:00, 10:00 and 14:00 ET.
A candle whose high is above the highs of the **2 candles before it**
and not below the highs of the **2 after it** is a swing high (lows
mirrored); the five candles must be consecutive and recorded. It becomes
a level when the 2nd candle after it closes, and stops being one when a
later candle of its own timeframe **closes beyond it**, or after **5
more sessions** have closed, whichever is first.

## 2. Sides, breaks and the three entries

A price is **beyond** a level when at least 1 tick past it, **back** when
at least 1 tick on the original side. Each entry trades **against the
break**, at the mid of its entry instant, with an order-flow condition
measured on the 10 s grid (`D`, the aggressor delta; `z_delta_s`, its
frozen side-signed z):

| entry | break | entry instant |
| --- | --- | --- |
| **WICK** | a 10 s grid close beyond the level, the last close not *at* it having been on the other side | the first 10 s grid tick within **300 s** of the break where the mid is back and that tick's aggression is against the break with `z_delta_s >= 1.0` |
| **EARLY** | a **one-minute close** beyond the level, as in wave ten | the first 10 s grid tick within the **5 one-minute candles** after the break candle where the mid is back and that tick's aggression is against the break with `z_delta_s >= 1.0` |
| **CLOSE** | a one-minute close beyond, as in wave ten | wave ten's rule: the first one-minute close back within 5 candles, the candle's net aggression against the break and its last 10 s with `z_delta_s >= 1.0` |

An episode ends at its entry, at the first close back without the
order flow (CLOSE only), or when its window runs out with no entry (no
trade). After it, the side is whatever the last close shows, and the
next break needs a close on the other side. **WICK** on the six MAIN
levels is reported beside L2 (wave three's detector, fixed to those
levels) as a check of the analogue; it is not tested there.

**Test number:** breaks are counted per instrument and level, per
session for MAIN, B, C and D, and over the swing level's whole life for
A; the **first test** is number 1.

## 3. Exit, costs and the scaled target beside it

Every trade: wave six's T1 exit (target 100 ticks, 25 points; stop 60
ticks, 15 points; 1 800 s; mid-to-mid on the run's path; dropped if the
run ends first) and `mrofyt_costs`' round trip ($5 NQ, $2 MNQ, a tick of
spread, a tick of slip on a stop). **The tests use this exit.**

Reported beside every row, not tested: the same trades with wave nine's
**SCALED** target (100 ticks × the recent average daily range ÷ its DEV
median, 40–300 ticks), when wave nine's frozen `A_ref` file is given.

## 4. The tests (NQ; MNQ reported beside)

Each tests the **mean net result per trade above zero**,
session-clustered (wave four's estimator), Student t on `G − 1` degrees
of freedom; every event counts (one position at a time reported beside).

| family of tests | tests | Holm over |
| --- | --- | --- |
| **MAIN** | **E1** EARLY, every break; **E2** EARLY, first test | the two |
| **A** | WICK, EARLY, CLOSE, each every break and first test | the six |
| **B** | WICK, EARLY, CLOSE, every break | the three |
| **C** | WICK, EARLY, CLOSE, every break | the three |
| **D** | WICK, EARLY, CLOSE, every break | the three |

| NQ trades | result | verdict |
| --- | --- | --- |
| `< 30` | — | NOT TESTED |
| `>= 30` | fails its family's Holm, or mean net `<= 0` | no signal |
| `>= 30` | survives it, mean net `> 0`, 95 % interval above 0 | promising |

Reported beside MAIN from the same read, not tested: L2 (wave eight V0,
V1), wave ten's C1 and C2, and WICK on the MAIN levels.

**What a verdict decides.** A group that is promising may be added to
the main levels, but the combined level set is a new rule: it is
registered and judged again on sessions read by nothing before it (the
December days), never accepted on this read alone.

## 5. Where it is judged

- **DEV** (sessions `<= 20260918`): describes only. Nothing is frozen
  from it; the scaled-target column uses wave nine's frozen `A_ref`.
- **Replay holdout** (`--holdout`): a folder holding ONLY NinjaTrader
  Market Replay recordings of sessions **before 2026-09-01**; refused if
  it holds any later session.
- **Validation** (`--unblind`, sessions `>= 20260921`); it marks every
  session it reads `EXPOSED_PILOT_DEV` for good.

## Explicitly NOT registered

- any other level, band width, pivot level (R2, S2 and beyond), swing
  width, swing timeframe, candle alignment or swing lifetime
- any other side distance, window, flow threshold or flow window; a
  filter on the break itself
- mixing any group into MAIN, or two groups into one test, on this read
- first-test versions of B, C and D
- any other exit tested; the scaled target as a test here (it is wave
  nine's test)
- choosing among the entries or the groups on DEV results
- machine-learned models of any kind
- live, paper or simulated order placement

## Implementation record — 2026-11-01

`mrofyt_earlylevels.py`, `tests_mrofyt_earlylevels.py`. Written against
this file before any real session was read by it; verified on
hand-built paths, candles and grids and on synthetic recorder-format
runs, never on market evidence.

| registered | implemented as | precision |
| --- | --- | --- |
| §1 | `LevelsRunner` (wave ten's runner) puts every group's levels on each grid record; `htf_swings` | swing candles are of the recorded mids; the 4-hour grid is the Eastern hour minus 18, in steps of 4; the 5 sessions are counted among the instrument's recorded sessions, from the swing's own session (or the next one recorded) |
| §2 | `run_episodes` with `wick_events`, `early_events`, `close_events_g` | levels are read at each 10 s tick or minute close from the grid record ending there; a tick without one is skipped and the clock still runs |
| §3 | `score`, `scaled_net` | none |
| §4 | `family_table`, `main_table` | none |
| §5 | `plan()` with `--holdout` (wave six's), `record_holdout_read`, `record_exposure` | none |
