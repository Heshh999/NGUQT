# MROF_YT_OF01_7_EXIT_FREEZE.md — liquidity-target and flow-controlled exits

Additive. No predecessor was modified. **This project does not authorize
live trading.**

## Four separate classifications

| Dimension | Status |
| --- | --- |
| Implementation | **COMPLETE** — three arms, both evaluations, 15/15 tests |
| Data | **INSUFFICIENT** — one date of complete bulk CSVs, 0 s of simultaneous NQ+MNQ coverage |
| Market research | **NOT RUN** — `research_driver()` raises `STATE-C LOCKED` |
| Prospective validation | **NOT STARTED** |

`INSUFFICIENT_DATA` here means data readiness fails. It is not a verdict
on the hypotheses and will not remain the label once sufficient research
has actually run.

## 1. Identifier

Appendix C requires selecting the next unused successor identifier and
warns against assuming v01.6 was implemented merely because a swing
prompt exists. v01.6 **was** implemented in this same delivery
(`MROF_YT_OF01_6_SUCCESSOR_FREEZE.md`), so the exit wave is **v01.7**.

## 2. Artifacts and hashes

```
b6bd0b05f48a6e26871df69c97fde97112a19d3f4b17da7edf280caa5bdc354d  mrofyt_exits_v017.py
0df5357cce0d0c77c6f38759c757086a067ea90aef8efc1d373a766bbc8fe7f9  tests_mrofyt_v01_7.py
```

Predecessors reverified by the v01.7 suite (test C12), **unmodified**:
`mrofyt_engine_v015.py` `e3da36cd…`,
`MROF_YT_OF01_5_SUCCESSOR_FREEZE.md` `b753a09c…`,
`MROF_YT_OF01_FINAL_SOURCE_PROMPT.md` `74ff9a99…`.

## 3. What was actually verified about the parent

Appendix C says to verify what the executable code does rather than
assume the proposed management comparisons are already active. The
authoritative baseline is `mrofyt_signals.simulate`, and it implements
exactly: structural stop, fixed 2R target, a 10-second early
invalidation, a later control-loss exit, and the 30-minute cap —
whichever is executable first, with the stop checked before the target.

Two things it does **not** do, both material:

1. **It has no session-flattening rule.** The 30-minute cap is the only
   time exit. Session flattening is therefore a *new assumption* in
   v01.7, not an inherited rule, and it is implemented as an explicit
   optional `session_flat_t` on the trade. It is off unless supplied.
2. **It resolves an exit AT the decision price**, with no latency, no
   spread crossing and no partial fill.

Point 2 would silently confound the whole experiment: E1 and E2 route
through the latency/fill engine as Appendix C §5 requires, so a naive
`E1 − E0` difference would measure execution modelling, not exit logic.
The freeze therefore defines **four** arms rather than three:

| Arm | Role |
| --- | --- |
| `E0` | Parent parity. Delegates to `SIG.simulate`. Proves reproduction. |
| `E0_EXEC` | The parent's *decisions* routed through the same fill engine as E1/E2. **This is the comparison baseline.** |
| `E1` | Liquidity hybrid. |
| `E2` | Flow-controlled. |

`E1 − E0_EXEC` and `E2 − E0_EXEC` are the like-for-like differences.
`E0` versus `E0_EXEC` measures the execution model alone and must be
reported alongside them.

## 4. The three arms

**E0 — parent.** Reproduced by delegation to `mrofyt_signals.simulate`,
so it cannot drift from the parent it exists to reproduce (test C1).

**E1 — liquidity hybrid.** Parent stop, early invalidation, session
flattening and timeout preserved. **Only** the fixed target is replaced.
It takes profit before the selected wall and introduces no runner and no
discretion to hold through it.

**E2 — flow-controlled.** Same protective set. The fixed target is
removed and the confirmed opposing-control exit is added. It may
continue through a consumed wall while the frozen conditions stay false.
Absence of an exit condition is **not** certainty that control persists.

No scaling-in, partial-profit, breakeven, trailing-stop or runner
variant is introduced. Entries, eligibility, initial stops, sizing,
session windows and the 30-minute cap are unchanged, and no daily or
weekly trade cap exists (test C11).

## 5. Frozen E1 wall selection

Initial research choices, **not** established optimal settings, and not
to be tuned on results.

At the parent's target-initialization time, on the latest valid **MNQ**
book available then — ask levels for a long, bid levels for a short — a
candidate must:

- lie strictly beyond the actual entry fill in the profitable direction;
- sit inside the currently supported visible depth;
- carry displayed size at robust time-of-day z **≥ 2.0** on the strict
  prior-20-session median/MAD baseline for that instrument, side and
  depth rank (slot `wall|<side>|<rank>`, frozen before research);
- have been continuously visible at the **same price** for the preceding
  **2 seconds** with z **≥ 1.5** throughout the supported observations;
- have a valid baseline and complete observable history for that
  interval.

A missing baseline or a zero MAD makes the candidate unavailable. **No
outcome-tuned epsilon is added.**

Nearest qualifying price wins. Trigger = wall − 1 tick (long) / wall + 1
tick (short), and the trigger must still be beyond entry in the
profitable direction. Price, side, size, z, observation window and
selection timestamp are frozen.

Fallbacks — `NO_QUALIFYING_LIQUIDITY_TARGET` and
`TARGET_DATA_UNAVAILABLE` — use the parent's fixed target and are
labelled `PARENT_TARGET_FALLBACK` on exit. **Neither is ever reported as
a successful liquidity-target trade** (tests C3, C7).

The trigger does not move after entry. Later wall changes are tracked
diagnostically only: no chasing, no extension after removal, no
retroactive reselection (test C5). Profit-taking triggers on the
executable MNQ bid (long) or ask (short) reaching the trigger, and exits
as a simulated **market** order — not a resting limit, and no assumption
of a fill at the wall or the trigger price.

An NQ wall price is never transferred into an MNQ order. No such mapping
experiment is authorized (test C4).

## 6. Frozen E2 opposing-control exit

At a **completed** 10-second window, all three must hold:

1. signed control favours the direction **opposite** the position at
   magnitude z ≥ 1.0 — signed control, never unsigned intensity;
2. at least **3 of 4** subwindows favour that opposing direction;
3. NQ price progress across the completed window is adverse by at least
   **1 NQ tick**.

Authoritative polarity: `mrofyt_signals.control_score`, evaluated
against the position direction, matching the parent's frozen
price-response convention.

A missing feature is **unknown** — not zero, not favourable control — so
it returns no exit (test C6). A completed-window condition can never
exit at the window's beginning: the decision timestamp is the window
**end**, and the fill is later still (test C6b). Wall disappearance by
itself triggers neither continuation nor exit.

## 7. Book accounting and protective execution

Executions, displayed additions, net size changes, removals and loss of
visibility are tracked **separately** (`BOOK_EVENTS`). MBP changes do
not always identify a cancellation or hidden replenishment, so ambiguous
attribution is recorded as `UNKNOWN_ATTRIBUTION`. A level leaving the
visible ten-level window is `VISIBILITY_LOST`, which is **not** evidence
of cancellation or consumption.

Fills use later valid MNQ quotes after latency, respect available
quantity, and never fill against an already consumed snapshot twice
(test C8). An unfilled remainder stays **open** with stop protection —
it is not cancelled and the trade is not pretended flat. Gaps and
insufficient depth produce `unresolved` outcomes and stay in the
denominator.

At a common decision timestamp protective and control exits take
precedence over profit taking, and the target touch is still recorded as
`TARGET_ALSO_TOUCHED` (test C9). A stop and a fixed target can never be
touched by the same price, since the stop sits on the losing side of
entry and the target on the winning side; the reachable coincidence is a
completed-window condition against a target touch, and that is what is
tested. A deadline liquidation is issued at the deadline while its fill
may be genuinely later — no deadline fill is manufactured, and none is
manufactured during a disconnect (test C9b).

## 8. The two evaluations

**1. Paired exit attribution.** Each frozen parent entry is replayed
with identical entry fill, quantity, initial stop and initial risk in
isolated shadow trades, one per arm. Hypothetical trades may overlap.
This is **not** a deployable equity curve and cross-arm liquidity
consumption is never summed.

**2. Deployable sequential replay.** Each complete arm runs
independently under identical account limits, one-position gating and
genuine re-arm rules. Faster or slower exits admit or suppress different
subsequent entries, so entry sets legitimately diverge between arms;
that divergence is reported, not assumed away (test C10).

## 9. Preregistration

Declared **before** any outcome is opened:

- primary comparisons: `E1_minus_E0`, `E2_minus_E0` (against `E0_EXEC`
  for the like-for-like reading), corrected **jointly**;
- secondary diagnostics: `E1_vs_E2`, wall size, side, time of day, with
  multiplicity control;
- primary economic metric: **net expectancy per trade after costs**;
- inference: session-block resampling, since millions of callbacks are
  not millions of independent samples.

The metric will not be switched to rescue a losing arm. All previous
trials and failed fingerprints are preserved; relabelling an earlier
management test does not create a new independent hypothesis.

Reporting will include net expectancy per trade and per day, paired
net-P&L differences, drawdown, tail loss, holding duration, maximum
adverse and favourable excursion, favourable excursion given back before
exit, realized reward/risk, costs, partial and unresolved fills, target
fallback rate, and entry-opportunity changes. Not every metric must
improve; promotion needs the governing positive-net-EV and incremental
evidence gates plus the preregistered risk limits.

## 10. Test results (actual output)

```
cd analysis/mrofyt && python3 tests_mrofyt_v01_7.py     # 15/15
```

Full battery at this freeze: **370/370** across twelve suites (table in
`MROF_YT_OF01_6_SUCCESSOR_FREEZE.md` §6).

**Synthetic tests prove implementation behaviour only.** No study was
run and nothing here is evidence of profitability or positive EV.

## 11. Traceability

| §7 requirement | Code | Test |
| --- | --- | --- |
| E0 parity incl. fills and ledger | `run_e0` → `SIG.simulate` | C1 |
| future data leaves earlier decisions unchanged | `select_liquidity_target` reads `t <= t_init` | C2 |
| 2 s persistence, missing/zero-MAD, absent wall | selection gates | C3 |
| mirrored long/short, MNQ not NQ | `side_for`, single-book signature | C4 |
| wall removal does not move the trigger | `track_wall`, `frozen=True` | C5 |
| signed score, completed windows, 3-of-4, adverse | `opposing_control_exit` | C6, C6b |
| healthy unchanged level vs unhealthy feed | `snapshot['healthy']` gate | C7 |
| latency, partials, remainder, unresolved gaps | `market_exit` | C8 |
| stop/target/time precedence, no deadline fill | `run_arm` ordering | C9, C9b |
| paired vs independently gated sequential | `paired_attribution`, `sequential_replay` | C10 |
| uncapped setups, logged exclusions | `sequential_replay` | C11 |
| no live orders, predecessors unchanged | — | C12, C12b |

## 12. Blocked, user-side

Real NinjaTrader F5 compilation and Market Replay or live smoke testing
were **not** performed. This environment has no NT8, Windows or live
feed, and a stub compile is not an API validation.

## 13. Where this stands

Three exit arms are implemented, plus the execution-matched baseline
that makes them comparable. **No study ran.** Neither alternative has
been shown to improve the parent, and neither has been shown not to —
the market-outcome driver is locked and the data is nowhere near the
readiness gates.

A perfectly valid outcome of this experiment, once it can run, is that
the parent's fixed 2R target works better than both alternatives, or
that no verified edge exists in either. Nothing in this freeze leans
against that.
