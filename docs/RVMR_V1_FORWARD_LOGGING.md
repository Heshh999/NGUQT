# RVMR-V1 — FORWARD LOGGING ARCHITECTURE AND PROCEDURE

## The architecture choice, and why the frozen engine is untouched

RVMR is computed and logged by a **separate offline companion module**
(`analysis/rvmr/rvmr_prospective.py`), never inside NinjaTrader.

Why this path was chosen over adding logging to the prospective host:

1. The NT8 prospective engine is parity-verified, hash-frozen, and
   **midway through forward collection**. Any edit — even passive
   logging — changes source hashes and forces a full parity
   re-verification. That price buys nothing, because:
2. RVMR needs only completed 1m OHLCV, and the existing capture
   pipeline already delivers exactly that (`v4_1_orderflow_MNQ_v41of_*`
   monthly files, `f_barCloseEt` schema).
3. Order safety becomes **architectural rather than a boolean**: this
   code has no possible path to EnterLong / EnterShort / SubmitOrder /
   SetStopLoss / SetProfitTarget / sizing, because it does not run in
   the platform at all. Verified: **zero occurrences of "rvmr" in
   `src/*.cs`.** There is no trading-filter switch to flip, by design.

Consequence: **no strategy logic changed; no NT8 parity re-run was
needed; the frozen hashes stand.**

## Canonical forward source

The **V4.1 order-flow capture feed** — the same data the frozen
strategy engine consumes. States logged from it are the states the
strategy's own world implied. Other feeds (LTF capture, V3 export) are
used only for CROSS_SOURCE_AUDIT diagnostics; the known cross-feed
divergences are catalogued in `docs/RVMR_V1_SPEC.md` (84 flips /
154,924 comparisons, every one classified).

## Ledger design

`analysis/rvmr/ledger/RVMR_PROSPECTIVE.csv` — separate file from the
frozen trade/event ledger; the trade ledger is never touched.

```
timestampEt, rvmrAvailableTimeEt, rvmrVersion, rangeScore, rangeRegime,
volumeScore, volumeRegime, sourceBarTimestamp, sessionDate,
dataSourceMode, instrument, inCertifiedUniverse, loggerVersion, specHash
```

- `dataSourceMode` ∈ {`LIVE_PROSPECTIVE_RVMR`,
  `RETROACTIVE_CONTEXT_BACKFILL`, `CROSS_SOURCE_AUDIT`} — forward
  evidence stays distinguishable **by column and by file**; nothing is
  ever relabelled as live that was not logged live.
- Scores at 10 decimals; regime labels exact; `specHash` pins every row
  to the frozen spec file that produced it.
- **Restart / reconnect safety:** the logger is an idempotent batch:
  same key + identical values → dedupe-skip; same key + different
  values → **FAIL CLOSED**, nothing silently replaced. Verified by
  selftest (replay run added +0 rows, 5 skipped; injected conflict
  aborted).
- **Data gaps:** never inferred, interpolated, or carried forward. An
  eligible stamp without a computable state logs `UNAVAILABLE` with a
  reason (`INSUFFICIENT_WARMUP`, `MISSING_BAR`, `SESSION_GAP`,
  `SOURCE_UNAVAILABLE`, `PARSE_ERROR`, `TIME_ORDER_ERROR`).

## Causality

A state is the score of a **completed** bar and becomes available at
that bar's close, never earlier: `rvmrAvailableTimeEt == timestampEt ==
sourceBarTimestamp` by construction, and the per-session audit asserts
it on every row. The trailing normaliser uses only the 1,440 bars
strictly **before** the bar. The frozen strategy decides on bar close;
the RVMR state of that same close is fully determined at that instant,
so snapshot causality is `rvmrAvailableTime <= decisionTime` with
equality at the decision bar.

## Event snapshots

`analysis/rvmr/ledger/RVMR_EVENT_SNAPSHOTS.csv` — one immutable row per
strategy event (`eventId, strategyId, eventTime, entryTime,
rvmrAvailableTime, scores, regimes, version, dataSourceMode`). The
strategy behaves identically regardless of these values; the file
exists only so a future pre-registered study can ask "how did strategy
X behave when RVMR was LOW/MED/HIGH."

Backfilled now for all 2,135 canonical historical events (2,127 with
states, 8 UNAVAILABLE inside the warmup), labelled
`HISTORICAL_RECONSTRUCTION`. Forward events get rows labelled
`LIVE_PROSPECTIVE_RVMR` as capture months arrive. **No previously
generated prospective row was altered.**

## Gates executed

| gate | result |
|---|---|
| Historical reproduction (gate A vs archived discovery tables) | **PASS — exact** (all bucket Ns, Spearmans to 4 dp) |
| Pure-OHLCV equivalence (gate B) | **PASS — byte-identical universe, delta +0 rows** |
| Row-level parity, certified engine vs production logger | **PASS — 593,190 rows, 0 score / 0 regime / 0 timestamp mismatches** |
| Idempotence under restart replay | **PASS** (+0 rows, all skipped) |
| Conflict FAIL-CLOSED | **PASS** (aborts, nothing replaced) |
| Multi-day cross-source parity (capture vs LTF feed, 13 sessions) | **PASS — 5,083 rows, 0 regime mismatches** |
| Freshest-session audits (2026-08-20, 2026-08-21) | **PASS — 391/391 rows, 0 dup, 0 UNAVAILABLE, causal** |
| Strategy behaviour unchanged | **PASS — zero NT8 edits; hashes stand** |

## First LIVE forward day — procedure (armed, awaiting next capture)

Every bar currently on disk predates this freeze, so nothing on disk
may be labelled live; the 2026-08-20/21 sessions above were audited as
the operational dry run. When the next capture month arrives:

```
python3 rvmr_prospective.py log --source <capture-dir> --mode LIVE_PROSPECTIVE_RVMR
python3 rvmr_prospective.py audit --ledger analysis/rvmr/ledger/RVMR_PROSPECTIVE.csv --day <session>
```

then verify, per the ten-point first-day checklist: startup, warmup,
session date, no duplicates, no missing eligible stamps, causal state
changes, snapshots only from already-available states, **unchanged
strategy event counts, unchanged qualification, unchanged outcomes**
(the last three are trivially true — the strategy cannot see RVMR).
Repeat the ledger-vs-independent-recalculation comparison for several
sessions; require 0 regime mismatches, as achieved in the dry run.

## Live display

Deliberately **not built** in this phase — keeping the zero-NT8-change
property was judged worth more than a screen label. If wanted later, a
standalone read-only NinjaTrader *indicator* (not part of any strategy)
can render `Range: HIGH / Volume: MEDIUM / Expected movement: ELEVATED
/ Direction: NONE` without touching frozen code; that would be its own
small parity exercise.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
