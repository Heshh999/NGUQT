# MROF_YT_WAVE4_DISCOVERY_REGISTRATION.md — a counted search of the DEV tape, registered before any run

**Status: FROZEN on 2026-10-09, before the tool was written or run.**
The operator asked: instead of only testing hypotheses written in
advance, search the recorded order flow for something that recurs and
precedes 25-point moves with positive expectancy, and use what is found
as the hypothesis. This file fixes, before the search runs, everything
that would otherwise be chosen after seeing results: what is measured,
which combinations are tried, how each is scored, how luck is
discounted, how many survivors may be carried forward, and how they are
judged.

**Registered:** 2026-10-09. **Searched:** sessions `<= 20260918` only
(all labelled `EXPOSED_PILOT_DEV`). **Judged on:** sessions
`>= 20260921`, which nobody has examined, at the December checkpoint.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only shadow research on recorded tape. No order is placed.

---

## 0. What this wave is

A search engine for hypotheses, not a source of evidence. Its output is
a short list of **nominated rules** (at most five), each frozen with
exact numeric thresholds, which are then judged once on the validation
sessions. Nothing it finds on DEV is a result.

Waves one to three continue unchanged. The module
(`mrofyt_discover.py`, MROF-YT-W4-DISCOVER-1.0) subclasses the
wave-three runner, which subclasses the pilot runner, and uses
observation hooks only; the frozen detectors are never edited and the
suite re-pins their hash. One read of the DEV sessions produces both
this wave's report and wave three's real-level report.

## 1. What is measured — the feature set, fixed

On every frozen 10 s grid tick `te` at which the book is ready, causal
(nothing after `te` is used). `z(k, v)` is the runner's robust
minute-of-day z-score against its 20-session baseline with its
5-prior-observation floor; `None` disqualifies. A feature that needs a
history of grid ticks is `None` unless every tick it names exists in
the same recording run.

**Signed features** (a high value points up, a low value points down):

| id | definition |
| --- | --- |
| `z_delta` | `z(delta10, D)`, `D` = signed aggressor volume in `[te-10 s, te)` |
| `z_d60` | `z(w4_d60, D60)`, `D60` = sum of `D` over the 6 grid ticks ending at `te` |
| `z_d180` | `z(w4_d180, D180)`, sum over 18 grid ticks |
| `z_ofi` | `z(ofi10, OFI)` |
| `z_bi3` | `z(bi3, BI3)`, top-3 book imbalance |
| `resp` | 10 s mid response, ticks |
| `resp60` | `(mid(te) - mid(te-60 s)) / tick` |
| `resp180` | `(mid(te) - mid(te-180 s)) / tick` |
| `trend30` | `(mid(te) - mid(te-1800 s)) / tick` |
| `dist_vwap` | `(mid(te) - SESSION_VWAP) / tick` |

**Unsigned features:**

| id | definition |
| --- | --- |
| `z_n10` | `z(n10, trade count in [te-10 s, te))` |
| `spread` | `(ask - bid) / tick` at `te` |
| `range30` | `(max - min of the grid mids over [te-1800 s, te]) / tick`; needs at least 171 of the 181 ticks |
| `dist_level` | distance in ticks from `mid(te)` to the nearest active level of the frozen level set |

`w4_d60` and `w4_d180` are new baseline keys observed on every grid
tick; no frozen key is observed differently.

## 2. Which combinations are tried — the grammar, fixed

Tail cut-points are the per-instrument quantiles of each feature over
the DEV grid ticks where it is available. A **decile tail** is `<= q10`
or `>= q90`; a **quintile tail** is `<= q20` or `>= q80`. A tail that
holds more than 1.5 times its nominal share of ticks (ties, as with a
one-tick spread) is degenerate and is not tested; it still counts
toward the number of tests.

Direction is part of the rule. For a signed feature in a tail, **with**
means long in the top tail and short in the bottom tail; **against** is
the opposite. For an unsigned single, direction comes from the sign of
`D60`: **with** the 60 s flow, or **against** it.

| family | form | count |
| --- | --- | --- |
| single signed | one signed feature, decile tail, with / against | 10 × 2 × 2 = 40 |
| single unsigned | one unsigned feature, decile tail, with / against `D60` | 4 × 2 × 2 = 16 |
| pair signed × signed | two different signed features, quintile tails, with / against the first | 45 × 4 × 2 = 360 |
| pair unsigned × signed | one unsigned and one signed feature, quintile tails, with / against the signed one | 4 × 10 × 4 × 2 = 320 |
| **rules** | | **736** |

Each rule is scored at three stops: **K = 2 208 tests**. That number is
the denominator of every correction below, whatever the data does.

## 3. How each rule is scored

- **Events.** The ticks satisfying the rule, de-duplicated per
  (instrument, session, rule, direction) with a 300 s cooldown anchored
  on the event's first tick. 300 s, not the 60 s of waves one and two,
  because the outcome spans up to 1 800 s and ticks a minute apart are
  the same trade.
- **Outcome.** Wave three's path score unchanged: target 100 ticks
  (25 points), stops 40 / 60 / 80 ticks (10 / 15 / 20 points), limit
  1 800 s, a tie is a stop, mid-to-mid inside one recording run, no
  fill, spread, slippage or commission. `UNRESOLVED` (the run ended)
  is excluded.
- **Baseline.** Every DEV grid tick scored by the same rule in both
  directions; cells by (instrument, ET hour). An event's expectation is
  its cell's hit rate; a rule's **lift** is its hit rate minus the mean
  expectation of its events.
- **Uncertainty.** Events within a session are not independent.
  Standard errors are cluster-robust by session (ratio estimator), the
  t-statistic is referred to Student's t with `G - 1` degrees of
  freedom (`G` = sessions with events), and the p-value is two-sided.
- **Expectancy** (before costs, mid-to-mid): mean of `+100` (target),
  `-S` (stop), the 1 800 s markout (timeout), in ticks and points.
- **Internal replication.** The DEV sessions are split chronologically
  into a first and second half. The lift is computed in each half.
- Primary instrument **NQ**. MNQ is reported beside it and is not a
  separate test.

## 4. Luck correction and status

Benjamini–Hochberg false-discovery rate over all 2 208 NQ tests
(untestable ones counted in `m`). A rule-and-stop is a **CANDIDATE**
when all hold:

- q-value `<= 0.10`;
- lift `> 0`, and lift `> 0` in **both** halves with at least 10
  resolved events in each;
- at least 30 resolved events on at least 6 sessions;
- expectancy before costs `> 0`.

## 5. Nomination — at most five, fixed now

Eligible: rule-and-stop pairs with p `<= 0.05`, lift `> 0` in both
halves (10+ events each), 30+ events on 6+ sessions and expectancy
`> 0`. Ranked CANDIDATEs first, then by t-statistic. Each rule
contributes only its highest-t stop. Taken greedily; a rule is skipped
if its NQ events overlap an already nominated rule's by half or more
(events within 300 s of each other count as the same). At most five.
If nothing is eligible, nothing is nominated, and the report says so.

The nominated rules are written out with their exact numeric
cut-points for NQ and MNQ, direction, stop, target, limit and cooldown,
and committed to the repository **before** any validation session is
read. That commit is wave four's hypothesis set.

## 6. Validation — at the December checkpoint

`--evaluate <nominated rules> --unblind` reads the validation sessions
once, applies the frozen cut-points, and scores each nominated rule as
in §3 with an hour-matched baseline built from the same sessions.

| NQ events (validation) | result | verdict |
| --- | --- | --- |
| `< 30` | — | **NOT TESTED** (keep recording) |
| `>= 30` | fails Holm over the nominated set at 0.05, or lift `<= 0` | no signal |
| `>= 30` | survives Holm, lift `> 0`, 95 % interval excludes 0, expectancy before costs `> 0` | promising: proceed to a sizing and friction study, **still no live orders** |

Expectancy after costs is reported with wave two's friction figures
(NQ 0.09, MNQ 0.91 points round trip, pending operator sign-off); it
is reported, not part of the verdict.

## 7. Descriptive tables — not tests

For every feature: deciles on NQ against the share of ticks that reach
`+100` before `-40` going long, and going short, beside the base rate.
This is the "what came before the big moves" view. It produces no
verdict and no rule; a rule drawn from it by eye is a new registration
on sessions not yet recorded.

## 8. Exposure

- The search reads DEV sessions only; every later session is refused
  and listed (the wave-three gate).
- `--evaluate` without `--unblind` reads DEV only (it reproduces the
  search's numbers for the frozen rules, as a check).
- `--evaluate --unblind` is the checkpoint read. It announces itself
  and writes every session it reads to the exposure ledger as exposed
  by this wave, permanently.

## 9. Explicitly NOT registered

- any feature not in §1; any cut-point other than the deciles and
  quintiles of §2; any combination of three or more features
- any target other than 100 ticks, stop other than 40 / 60 / 80,
  limit other than 1 800 s, cooldown other than 300 s
- time-of-day restrictions on a rule (the hour-matched baseline already
  conditions on the hour)
- more than five nominated rules; re-running the search with changed
  settings and nominating from the second run
- machine-learned models of any kind
- live, paper or simulated order placement

## 10. Implementation record

Filled in by the commit that adds the module and its suite.
