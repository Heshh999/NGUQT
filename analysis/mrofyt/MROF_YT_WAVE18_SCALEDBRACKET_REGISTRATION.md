# MROF_YT_WAVE18_SCALEDBRACKET_REGISTRATION.md — the whole bracket scaled to the market, on wave fourteen's trades

**Status: FROZEN on 2026-11-03, before any validation session (on or
after 2026-09-21) or replay holdout session was read by any tool.**

Wave nine scaled only the target, by the market's recent range. On DEV
the scaled target came out at about 25.5 points, because September's
range was its own reference, so it could not differ from the fixed 25.
The operator asked what quants do instead. The textbook answer is to
scale the **whole bracket**: stop and target grow together in a wild
market and shrink together in a quiet one, and the position shrinks as
the stop widens, so every trade risks the same dollars. This wave tests
that beside the headline, on the headline's own trades.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on recorded tape. No order is placed.

---

## 1. The trades

Wave fourteen's: the first L2 signal at each level per CME session, at
any hour, entered at the signal mid (its §1–§2, unchanged). An event
whose session has fewer than 5 earlier recorded sessions has no recent
range; it is left out of this wave and counted.

## 2. The scale

`k = A / A_ref`, clamped to **0.4 .. 3.0**:

- `A` is wave nine's recent range: the average high-to-low range of the
  last 14 recorded sessions before the trade's session, 5 at least;
- `A_ref` is wave nine's frozen DEV reference (`w9_frozen.json`, the
  operator's DEV run: NQ 322.41, MNQ 327.73 points);
- the clamp is wave nine's (its 10–75-point target is 0.4 .. 3.0 times
  25).

## 3. The two brackets, on every trade

| bracket | stop | target | limit |
| --- | --- | --- | --- |
| **FIXED** (the headline's) | 60 ticks (15 points) | 100 ticks (25 points) | 1 800 s |
| **SCALED** | 60 × k ticks, rounded | 100 × k ticks, rounded | 1 800 s |

Both mid-to-mid on the run's path (wave six's `path_exit`). A trade
either bracket leaves unresolved is dropped from both. Costs: the same
round trip per contract (`mrofyt_costs`).

## 4. The tests (NQ; Holm over two at 0.05)

Every trade's difference, SCALED minus FIXED, session-clustered:

| test | measure | meaning |
| --- | --- | --- |
| **B1 POINTS** | net points, one contract each | is the scaled bracket better per contract? |
| **B2 RISK** | net divided by the trade's own stop, in points (R) | is it better when every trade risks the same dollars (the position shrinks as the stop widens)? |

**PASS** needs 30 or more trades, the mean difference above 0 with its
95 % interval above 0, Holm, and the mean still above 0 with the session
of the largest total difference removed. Anything else with 30 trades is
**NOT PROVEN**, with the reason. MNQ is reported beside, never tested.

Beside, not tested: the mean `k`, the mean stop and target used, each
bracket's win rate and net points, and how often `k` hit a clamp.

## 5. Withholding and where it is judged

- Fewer than 30 trades on a held-out read: the counts only (wave
  fourteen §5).
- **DEV:** describes. **Validation** (`--unblind`): a secondary test
  beside wave fourteen, part of the one-read checkpoint from V42 on.
  **Replay holdout:** separately.
- The headline is unchanged: wave fourteen is still judged on the fixed
  25 / 15.

## 6. What a verdict leads to

A PASS of B1 or B2 lets the scaled bracket replace the fixed one only in
a later registration judged on sessions read by nothing before it. A
faster, intraday volatility measure is a later registration too.

## Explicitly NOT registered

- another range length, another clamp, another reference; an intraday
  or implied volatility measure
- scaling only the stop; any other target-to-stop ratio
- every L2 signal, the strict first touch, or any other wave's trades
- trailing, partial or break-even exits
- machine-learned models of any kind
- live, paper or simulated order placement

## Implementation record — 2026-11-03

`mrofyt_scaledbracket.py`, `tests_mrofyt_scaledbracket.py`. Written
against this file before any held-out session was read by it; verified
on hand-built paths and trades and on synthetic recorder-format runs,
never on market evidence.

| registered | implemented as | precision |
| --- | --- | --- |
| §1 | `FS.first_signals(V.variant_events(r))` on `ScaledBracketRunner` (wave nine's runner) | none |
| §2 | `scale`, `r.recent_range` | none |
| §3 | `brackets` | none |
| §4 | `tests` | the best session is the one with the largest total difference |
| §5 | `run`, `text`, the ledgers | none |
