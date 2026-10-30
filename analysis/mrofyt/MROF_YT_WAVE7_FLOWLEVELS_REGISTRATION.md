# MROF_YT_WAVE7_FLOWLEVELS_REGISTRATION.md — order-flow levels, graded, with targets from the order flow: registered before any run

**Status: FROZEN on 2026-10-30, before the tool was run on any real
data.** Wave three's one supported idea, a failed break of a level
(L2), made +351 points net over September's DEV sessions, but 260 of
them came on one day (16 September, the Fed day): the six daily levels
it watches are reached on few days. The operator proposed three
changes, registered here before any of them touches data:

1. trade the levels the **order flow itself builds every day**: swing
   highs and lows, prices where aggression was absorbed, and
   yesterday's value area, not only the daily levels;
2. **grade** every setup A+, A, B or skip from the order flow at the
   level, and judge only A and A+;
3. take the **target from the order flow** too: the next level ahead,
   or no target at all with an exit when the tape says the move is
   dying. The original fixed 25 points stays beside them as the
   baseline.

Nothing below changes waves one to six.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on recorded tape. No order is placed.

---

## 0. What this study is

Module `mrofyt_flowlevels.py` (MROF-YT-W7-FLOWLEVELS-1.0). Its runner
subclasses wave four's (hooks only) and adds two fields to every 10 s
grid record: the traded volume of those 10 s (`vol10`) and the daily
levels known at that instant (yesterday's high and low, the overnight
high and low, last week's high and low, the session VWAP). Everything
else is computed after the read from the grid records and each
recording run's mid path. Wave three's detectors, wave four's features
and the signal module (pinned hash) are used unchanged.

Every price path is one recording run's compressed mid path; nothing
is ever spliced across two runs.

## 1. The levels

| type | defined as | known from |
| --- | --- | --- |
| **SWING_H / SWING_L** | one-minute bars of the mid; a bar whose high is strictly above the highs of the 5 bars before it and not below the highs of the 5 after it (lows mirrored); at least 4 of the 5 bars on each side recorded | the end of the 5th bar after it |
| **ABSORPTION** | a 10 s grid tick with the side-signed aggression z `z_delta_s >= 3.0` (the frozen `delta10` z) and the mid moving at most 1 tick (`|resp| <= 1`); the level is the grid mid | that grid tick |
| **POC / VAH / VAL** | the previous recorded session's value area: its `vol10` at the grid mid in 1-point bins, the context study's `value_area` (70 %) | the session's first grid tick |

Levels are taken in the order they become known; a level within **2
ticks** of an earlier one is the same level and dropped. **One trade
attempt per level**: the first break after it is known decides
everything (§2), whatever happens after.

## 2. The events

**Which way it breaks.** A swing high breaks upward, a swing low
downward. Any other level breaks away from the side price is on when
it becomes known; if price is within 2 ticks of it then, from the side
price first leaves it to, 2 ticks away.

**Break:** the mid 2 ticks or more beyond the level.

- **FAILED** — within 120 s of the break the mid comes back through the
  level by 1 tick or more, AND within 20 s of that a grid tick shows the
  10 s aggression on the other side with `z_delta_s >= 1.0`. Entry at
  that grid tick, **against the break** (fade). The trapped side is the
  break side.
- **HELD** — no such return within 120 s, AND the net aggression from
  the break to the first grid tick at or after 120 s (within 20 s) is in
  the break direction. Entry at that grid tick, **with the break**
  (follow). The trapped side is the side that faded the break.
- A return without the turn in flow, or a hold against the flow, or a
  run that ends first: no event, and the level is spent.

**Entries** only from 09:30 to 15:30 ET (grid tick time). Entry price:
the mid at the entry grid tick.

## 3. The grade

One point each:

| point | condition |
| --- | --- |
| **TRAPPED** | the trapped side's aggressive contracts from the break to the entry, summed per 10 s tick, at or above the **DEV median** of every event of the same kind and instrument (frozen by the DEV run) |
| **ABSORPTION** | from 600 s before the break to the entry, a grid tick within 2 ticks of the level where the trapped side hit with `z_delta_s >= 2.0` and the mid moved at most 1 tick |
| **STRONG** | the entry tick's aggression, in the trade direction, has `z_delta_s >= 2.0` |
| **FRESH** | from the moment the level counts to 60 s before the break, the mid never came within 2 ticks of it |
| **CONFLUENCE** | within 8 ticks of a daily level known at the entry, or of the previous session's POC, VAH or VAL (the level itself excluded) |

**4–5 points A+, 3 A, 2 B, 0–1 skip.** The tests in §6 take **A and
A+** only (3 points or more).

## 4. The stop and the four exits

**Stop (structural)**, from the entry mid: FAILED — 2 ticks beyond the
furthest mid of the sweep (break to return); HELD — 2 ticks back
through the level. **Clamped to 12–60 ticks.** The stop is the trade's
risk, 1 R.

Every exit is mid-to-mid on the run's path; the first mid at or beyond
the stop or the target decides. Every trade is flat by
**15:59 ET** and after **3 hours** at most, at the mid (TIME).

| exit | rule |
| --- | --- |
| **E1 NEXT LEVEL** | target = the nearest level (§1, or a daily level) beyond the entry. If it is at least **1.5 ×** the stop away it is the target, however far (no cap). If a level stands nearer than that, **no E1 trade** (no room). If there is no level ahead at all: `max(0.20 ×` the mean session mid range of the previous 14 recorded sessions (5 or more needed)`, 1.5 ×` stop`)`. |
| **E2 TAPE** | no target. Out at the mid of the first grid tick after the entry where **2 or more** of 4 signs show: **FADE** the 60 s aggression `D60` is no longer with the trade; **AGAINST** the other side's 10 s aggression is at least the DEV **90th percentile of `|D|`** (frozen); **ABSORBED** the trade side's 10 s aggression is at least that same cut and the mid moved a tick or less with it; **STALL** 120 s or more since the trade's best mid. The stop stays as the backstop. |
| **E3 HYBRID** | half the position on E1's rule, half on E2's; only when E1 has a target. Busy until both halves are out. |
| **E4 BASELINE** | the original fixed **100-tick (25-point) target, 60-tick (15-point) stop**. |

## 5. Costs

`mrofyt_costs`' round trip on every trade: $5 commission on NQ ($2 on
MNQ), a tick of spread, a tick of slippage on a stop. The hybrid's
halves are charged half each. Results are in **net R** (net ticks / the
trade's stop) and net points.

## 6. The nine tests (NQ; MNQ reported beside)

| id | events | exit |
| --- | --- | --- |
| F1 / F2 / F3 / F4 | FAILED, grade A or A+ | E1 / E2 / E3 / E4 |
| H1 / H2 / H3 / H4 | HELD, grade A or A+ | E1 / E2 / E3 / E4 |
| G | every event, any grade | E4: does net R rise with the grade points? |

F and H: **one position at a time** per test (an entry before the taken
trade is out is skipped); the mean net R above zero, session-clustered
(wave four's estimator), Student t on `G − 1` degrees of freedom. G:
the least-squares slope of net R on the points 0–5, session-clustered
(influence-function form). **Holm over the nine** at 0.05.

| NQ trades | result | verdict |
| --- | --- | --- |
| `< 30` | — | NOT TESTED |
| `>= 30` | fails Holm, or effect `<= 0` | no signal |
| `>= 30` | survives Holm, effect `> 0`, 95 % interval above 0 | promising: a sizing and execution study, **still no live orders** |

Described, never tested: the events per kind and grade, and each
grade's mean E4 result.

## 7. Where it is judged

- **DEV** (sessions `<= 20260918`): **describes, does not test**: these
  days were seen before this file existed. The DEV run computes the two
  frozen cuts (trapped median per instrument and kind; the 90th
  percentile of `|D|` per instrument) and writes them with
  `--frozen-out`; that file is committed before any held-out read.
- **Replay holdout** (`--evaluate <frozen> --holdout`): a folder holding
  ONLY NinjaTrader Market Replay recordings of sessions **before
  2026-09-01**; the tool refuses a folder that holds any later session.
  Wave six and this wave are both registered before anyone has read the
  replay folder, so each reads it once as a fresh test; neither may be
  changed after either's result. Recorded in
  `MROF_REPLAY_HOLDOUT_EXPOSURE.json`.
- **Validation** (`--evaluate <frozen> --unblind`, sessions `>=
  20260921`) at the December checkpoint; it marks every session it reads
  `EXPOSED_PILOT_DEV` for good.

## Explicitly NOT registered

- any level type, swing width, absorption threshold, merge distance,
  value-area share or bin other than above
- any break distance, return distance, window, flow threshold or entry
  hours other than above
- any grade point, weight, cut or grade boundary other than above;
  choosing the grade boundary on DEV results
- any stop rule, buffer, clamp, target floor, fallback target, tape
  sign, sign count, percentile, stall time or hold limit other than
  above; trailing stops; partial exits other than E3's half
- choosing among E1–E4 or between FAILED and HELD on DEV results (all
  nine are judged)
- combining with a context rule or ES confirmation (a later
  registration, on sessions neither has read)
- machine-learned models of any kind
- live, paper or simulated order placement

## Implementation record — 2026-10-30

`mrofyt_flowlevels.py`, `tests_mrofyt_flowlevels.py`. Written against
this file before any real data was read by it; verified on hand-built
paths and grids and on synthetic recorder-format runs
(`mles_v12_synth`), never on market evidence.

| registered | implemented as | precision |
| --- | --- | --- |
| §0 | `FlowRunner._observe_baselines` | `vol10` sums the trades in `[t − 10 s, t)`, the same window as the grid's delta |
| §1 | `swing_levels`, `absorption_levels`, `value_levels`, `merge_levels` | one-minute bars are UTC-minute buckets of the run's mid path; a swing's left and right bars must lie in the same run |
| §2 | `_side`, `detect`, `Tree` | the turn is the first qualifying grid tick at or after the return; HELD's net flow includes the entry tick |
| §3 | `points`, `confluence`, `grade_of` | the trapped cut is the median (upper middle) of the DEV events |
| §4 | `bracket`, `tape_exit`, `next_target`, `exits` | the stall clock starts at the entry; a target or stop is the first path point at or beyond it |
| §6 | `one_at_a_time`, `test_mean`, `test_slope`, `tests` | none |
| §7 | `FlowRunner.plan` with `--holdout`, `record_holdout_read`, `record_exposure` | none |
