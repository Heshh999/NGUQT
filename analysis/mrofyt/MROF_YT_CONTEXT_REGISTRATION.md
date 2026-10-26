# MROF_YT_CONTEXT_REGISTRATION.md — long, short or neither by 10:30: a counted search of 20 years of minute bars, registered before any run

**Status: FROZEN on 2026-10-26, before the tool was run on any real
data.** The operator asked what a consistently profitable intraday
order-flow trader needs that the study lacks. The largest gap is
context: knowing whether the day favours longs, shorts or neither. The
order-flow recordings cover weeks; context needs only one-minute bars,
which NinjaTrader keeps back to about 2006. This file fixes, before any
bar is read, which sessions count, what is measured at 10:30 ET, what
outcome is scored, which combinations are tried, how luck is discounted,
how the history is split, and how the survivors are judged.

**Registered:** 2026-10-26. **Data:** the operator's NinjaTrader minute
exports of NQ, every session before **2026-07-01**. Sessions from
2026-07-01 on are never read: they hold the Market Replay window and
every order-flow session recorded since 2026-09-01.

**Searched on:** 2019-06-01 → 2026-06-30. **Judged on:** every session
before **2019-06-01**. The newer years are not fresh: this repository's
earlier minute-bar studies already read NQ one-minute bars from
2019-06-02 to 2026-08-25 (canonical set 2019-07-04 → 2026-08-17:
NQ-DIRECTION-V1, which found no robust intraday directional mechanism,
CCHC, LPCC, 4H-DVT, MEMORY-PRED, MEMORY-MATH-IFVG, the RVMR family and
others under `docs/`). No document in the repository refers to any date
before 2019-06-02. So the search runs on the years already worn by other
questions, and the verdict comes from the years nobody here has read:
2008, 2011, 2015 and 2018 included, if the export reaches them.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on historical bars. No order is placed.

---

## 0. What this study is

A search for hypotheses on the older part of the history, judged once
on the newer part. It does not use, read or change anything in waves one
to five; it uses only their statistics functions (wave four's
month-clustered t and Benjamini–Hochberg, wave three's Holm), unchanged.
The module is `mrofyt_context.py` (MROF-YT-CTX-1.0).

## 1. Sessions

- **Input:** NinjaTrader minute exports, `yyyyMMdd HHmmss;open;high;low;
  close;volume`, one file per contract named like `NQ 12-26.Last.txt`
  (or one continuous file). Time stamps are UTC at the END of each bar,
  as NinjaTrader exports; `--stamps-tz ET` and `--stamps start` exist
  for other files and change nothing else.
- **Stamp check:** among the ET minutes that carry at least half the
  day's peak average volume, the one with the largest jump in average
  volume over the minute before it must be 09:30. Otherwise the tool
  stops, computes nothing and names the likely cause. (The peak filter
  keeps a thin minute with a sharp jump, 08:30 on a news day or the
  Globex reopen, from outranking the cash open.) US Eastern time uses the
  2007 DST rule from 2007 and the 1987–2006 rule before.
- **Session:** bars from 18:00 ET belong to the next date (the CME
  session). **Cash session** = bars starting 09:30–15:59 ET.
  **Overnight** = 18:00 of the previous evening to 09:29.
- **Complete:** at least 370 of the 390 cash-session bars, the first by
  09:30, the last from 15:55, a 10:30 price and a 10:00 VWAP. Early
  closes and gaps drop out.
- **Front contract:** among the contracts complete that day, the one
  with the most cash-session volume on the PREVIOUS session (known at the
  open). Yesterday's close, range and value area always come from the
  same contract as today, so the roll basis is never a gap.
- **Eligible:** complete, with 14 earlier sessions for ATR.

## 2. What is measured at 10:30 ET — 13 features, fixed

`ATR` = mean true range of the 14 previous sessions' front contracts
(true range from the same contract's previous close). `p` = the close of
the last bar before 10:30. Bars after 10:29 are never used.

**Signed:**

| id | definition |
| --- | --- |
| `gap` | (cash open − yesterday's cash close) / ATR |
| `ib_move` | (p − cash open) / ATR |
| `ib_pos` | (p − first-hour low) / (first-hour high − first-hour low) |
| `vwap_dist` | (p − cash VWAP at 10:30) / ATR; VWAP from (H+L+C)/3 × volume |
| `vwap_slope` | (VWAP at 10:30 − VWAP at 10:00) / ATR |
| `open_vs_range` | (cash open − yesterday's low) / (yesterday's high − low) |
| `open_vs_value` | (cash open − yesterday's VAL) / (VAH − VAL) |
| `prev_day_move` | (yesterday's close − yesterday's open) / ATR |

**Unsigned:**

| id | definition |
| --- | --- |
| `on_range` | overnight high − low / ATR |
| `ib_range_rel` | first-hour range / its median over the previous 20 sessions |
| `rel_vol` | first-hour volume / its median over the previous 20 sessions |
| `atr_rel` | ATR / the median true range of the previous 100 sessions |
| `shock830` | 08:30–08:34 range / its median over the previous 20 sessions |

**Value area:** yesterday's cash-session volume profile in 1-point bins,
each bar's volume spread evenly over its range; POC = the fullest bin
(lowest on a tie); grown one bin at a time toward the fuller neighbour
(higher on a tie) until it holds 70 % of the volume.

A feature without its history is `None` and that day is outside every
rule using it.

## 3. The outcome

`y = (cash close − p) / ATR`: the rest of the day after 10:30, in ATR
units, so 2006 and 2026 compare. A rule's direction is LONG or SHORT;
its days score `d · y`. **Baseline:** `d ·` (the mean `y` of every
eligible day in the same sample), so a sample that drifted up does not
flatter every long rule. **Lift** = mean `d · y` − baseline. Also
reported, never tested: points, the close's location in the day's range
(a **trend day** closes in its outer 20 %), and which of `p ± 0.5 ATR`
the post-10:30 bars touch first (a bar spanning both is BOTH).

## 4. The grammar — 676 rules, fixed

- **Singles:** each of the 13 features at its top or bottom **decile**,
  LONG or SHORT: 52 rules.
- **Pairs:** each pair of features at top or bottom **quintile**
  (four tail combinations), LONG or SHORT: 78 × 8 = 624 rules.

Cut-points are the DEV sample's own deciles and quintiles, per feature,
nearest-rank-below. A tail holding more than 1.5 times its nominal share
(ties) is untestable and counted in `m`.

## 5. Split, uncertainty, luck, status

- **Split:** DEV = sessions **2019-06-01 → 2026-06-30**; VALIDATION =
  every session **before 2019-06-01**. The split is a date fixed here, so
  it does not move with how much history the export holds, and it is
  written into every nominated rule; the evaluator refuses a rule that
  does not carry it.
- **Never read across the split:** the search drops every bar of a
  VALIDATION session the moment its session is known, before anything
  is computed from it, so no validation price, feature or outcome can
  reach the search (the first DEV sessions simply lack the history their
  features need, as at the start of any file). The validation read
  drops every DEV bar the same way. Time runs backwards across the
  split, on purpose: a context rule that held in 2019–2026 and also held
  in the older years is a rule of the market, not of one era.
- **Uncertainty:** clustered by calendar month (wave four's ratio
  estimator), Student t on `G − 1` degrees of freedom, two-sided.
- **Luck:** Benjamini–Hochberg over all 676 tests.
- **CANDIDATE:** q `<= 0.10`; lift `> 0`; lift `> 0` in **both**
  chronological halves of DEV with 30+ days each; 60+ days over 24+
  months.

## 6. Nomination — at most five, fixed now

Eligible: p `<= 0.05` and every CANDIDATE condition except q.
CANDIDATEs first, then by t. A rule is skipped if half or more of its
days are days of an already nominated rule. At most five, written out
with numeric cut-points, direction and the DEV end date, and committed
to the repository **before** the VALIDATION sessions are read. If
nothing is eligible, nothing is nominated.

## 7. Validation — once

`--evaluate <nominated> --unblind` reads the VALIDATION sessions (before
2019-06-01) once and nothing else, applies the frozen cut-points, scores each rule as in §3 with a baseline
from the same sessions, Holm over the nominated set, and records the
read in `MROF_CONTEXT_EXPOSURE.json`.

| days (validation) | result | verdict |
| --- | --- | --- |
| `< 60` | — | **NOT TESTED** |
| `>= 60` | fails Holm, or lift `<= 0` | no signal |
| `>= 60` | survives Holm, lift `> 0`, 95 % interval above 0 | promising: a context filter worth combining with an order-flow entry in a later registration, **still no live orders** |

## 8. Descriptive tables — not tests

DEV base rates by year; for each feature, deciles against the mean
`y`, the up share and the trend-day share; trend-day share by
first-hour-range quintile; and, if `--calendar` is given (lines
`YYYYMMDD,EVENT`), event days against other days. None produces a
verdict or a rule.

## 9. Explicitly NOT registered

- any decision time other than 10:30 ET; any feature not in §2; any
  combination of three or more features
- any outcome other than §3's `y`; any stop, target or exit
- any split date other than 2019-06-01; re-running the search with
  changed settings and nominating from the second run
- reading any session from 2026-07-01 on
- combining a context rule with an order-flow pattern (that is a later
  registration, judged on sessions neither study has read)
- machine-learned models of any kind
- live, paper or simulated order placement

## 10. Implementation record — 2026-10-26

`mrofyt_context.py` (MROF-YT-CTX-1.0), `tests_mrofyt_context.py`.
Written against §1–§9 before any real bar was read; the engineering
verification ran on synthetic NinjaTrader-format exports (two contracts
across a roll, UTC end-of-bar stamps) and planted-effect records, and is
asserted by the suite, never by market evidence. On pure noise a false
CANDIDATE appeared in 2 of 40 independent datasets, inside what
Benjamini–Hochberg at q = 0.10 allows (`X8b`).

| registered | implemented as | precision |
| --- | --- | --- |
| §1 | `Reader`, `bar_session`, `DayAgg`, `build_days` | the stamp check compares each minute with the nearest earlier minute that has bars, at most 10 minutes back, among minutes at or above half the peak average volume (`X6a`); files are read BOM-tolerant; a file of lines that are not minute bars (a Tick export) stops with that reason |
| §2 | `build_days`, `value_area` | VAH = top of the highest bin, VAL = bottom of the lowest, POC = bin centre |
| §3 | `build_days`, `first_touch` | none |
| §4 | `enumerate_rules`, `quantile_cuts`, `members` | a feature needs 50+ DEV values for cut-points |
| §5 | `is_dev`, `is_validation`, `Reader(allow=…)`, `day_stats`, `search` | a dropped bar is counted by session (`sessions_skipped_unread`) and never stored |
| §6–§7 | `nominate`, `frozen_rule`, `run_evaluate`, `record_validation_read` | none |
