# PROSPECTIVE LIVE LOGGING — phase setup and verification

**Gate status: READY TO ARM — verified off-platform; PASS/FAIL is declared
only after the first forward session's files are audited.** Everything
that can be proven without a live session has been proven (§7–§8). No
strategy logic changed. No orders exist. THIS PROJECT DOES NOT AUTHORIZE
LIVE TRADING.

## 1. Source / hash audit

| item | state |
|---|---|
| frozen hashes (FROZEN_HASHES.txt) | `cand_spec 9bea8f1cafc2b6ea` · `ofh6 e8145b7c493029de` · `ofht 272d7bca6402b6d2` · `cache 376ce829086b5224` — **recomputed from the files, all unchanged** |
| Playback-pass engine | 1.0.2, commit `69fdeeb` (later commits before this phase were docs-only) |
| this phase's engine | **1.0.3 — recording-only** (§3); the full off-platform parity gate was re-run on 1.0.3: 952/952 signals, 133/462/218/477/845 events, 0 field mismatches, management 1,190/1,190 — identical to 1.0.2 |
| registry | `prospective.py` REGISTRY frozen 2026-08-21, untouched; `prospective.py` itself **not modified** |
| candidate shelf | OFH13_PROSPECTIVE_V1 (PRIMARY, 1.5 ATR stop, no target, 60 m exit) · OFH14_PROSPECTIVE_V1 (STRUCT stop, 60 m) · G4/G3 SIGNAL-ONLY · G1 diagnostic B-arm only (`G1_ADOPTED = False`) — all verbatim from the frozen registry |

## 2. Prospective-cutoff audit

- **LAST SPENT DATA DATE = 2026-08-19** — the last bar of the history
  used for discovery, selection, management research and the freeze
  (`FREEZE_DATA_END` in frozen `prospective.py`).
- **Validation-observed extension:** bars for 2026-08-20/21 were
  processed during the parity and Playback gates and their event streams
  compared. No rule, threshold or management choice was altered on them
  (everything was frozen 2026-08-21 from data ≤ 08-19), but they were
  *seen*. They are therefore cutoff-eligible yet flagged: any events on
  those days enter the files with `barSource = HISTORICAL_LOAD` and are
  disclosed by the verifier, never counted as pristine.
- **PROSPECTIVE START DATE = day > 2026-08-19** — the registry's frozen
  cutoff, kept unchanged (the "2026-09+" intent is a stricter subset;
  changing the frozen cutoff silently is prohibited, so it stays).
- **FIRST ELIGIBLE FORWARD BAR** (frozen rule): first bar of 2026-08-20.
  **First PRISTINE live bar:** the Sunday 18:00 ET open of 2026-08-23
  (trading day 2026-08-24) — the first data that will arrive as
  `barSource = REALTIME`, never before observed by anyone.

## 3. Code changes (engine 1.0.3 — all recording-only)

No signal rule, threshold, gate, or management line was touched. The
off-platform parity gate re-ran identically after every change.

1. **Ledger preload + duplicate suppression.** In PROSPECTIVE_LOG the
   recorder reads every existing `V41_PROSPECTIVE_EVENTS_*` /
   `TRADES_*` file at startup and refuses to append a key it already
   holds (`eventId` for events, `eventId|arm` for trades). Duplicates
   are printed as `DUPLICATE_SUPPRESSED ...` and counted in the audit —
   never silent. The key is the frozen EventID
   (`CAND-yyyyMMddHHmmss-±1`), deterministic across restarts.
2. **Pre-cutoff accounting.** Warm-up/historical-initialization events
   (day ≤ 2026-08-19) are counted and logged
   (`PRE-CUTOFF (warmup) event skipped`), never recorded.
3. **Monthly merged resolution.** `V41_PROSPECTIVE_RESOLUTION_YYYY-MM.csv`
   per month; on close the file is merged — rows from earlier sessions
   are preserved, rows for events this session re-saw are updated with
   the finalized flags; pre-cutoff events are excluded.
4. **`barSource` provenance column** on event and trade rows:
   `REALTIME` (arrived on the live stream) vs `HISTORICAL_LOAD` (chart
   warm-up of already-elapsed days).
5. **Audit additions:** ledger-preload counts, written counts,
   duplicate counts, pre-cutoff count; startup diagnostic prints the
   preload summary.

## 4. Restart / reconnect / duplicate behaviour

| scenario | behaviour |
|---|---|
| strategy reload / chart refresh / workspace reopen / reconnect | Chart history replays; the engine re-detects the same events (proven deterministic by the short-window and Playback gates); the recorder suppresses every already-ledgered row (`DUPLICATE_SUPPRESSED`), so nothing is double-counted. |
| crash before a trade row was written | On restart the reloaded history re-detects the event; its event row is suppressed but the missing trade rows are written exactly once (verified in §7). Requires the gap to be inside the chart's days-to-load window. |
| stop before an event's +60 window completed | The event's resolution row finalizes `FALSE`; the verifier lists it as INELIGIBLE with the reason. **Operational rule: keep the strategy running until at least 16:01 ET** — entries are gated ≥ 60 min before the 16:00 RTH close, so by 16:01 every window and every managed trade is complete. |
| gap longer than days-to-load | Events that fired inside the gap eluded the chart entirely; they cannot be recovered (the engine never saw the bars). Already-written rows are safe. Documented limitation — the verifier's canonical cross-check against the raw capture exposes any such hole. |
| contract roll (SEP26 → DEC26 ~mid-Sep) | EventIDs are date-keyed, so no collision; roll the chart to the new front contract and continue. Prices differ across contracts — roll on the industry roll date and note the day in the ledger. |

## 5. Output files (`<Output folder>\V41_prospective\`)

- `V41_PROSPECTIVE_EVENTS_YYYY-MM.csv` — `candidateId, version, eventId,
  timestampET, direction, entryTime, entryPrice, atr, stopPrice,
  targetPrice, timeExitMin, parentEt, fvgHigh, fvgLow, fvgMid, depth,
  flow, reasonQualified, fwdEligible, parentSignalDivergent,
  engineVersion, candSpecHash, ofh6Hash, barSource`
- `V41_PROSPECTIVE_TRADES_YYYY-MM.csv` — `candidateId, version, eventId,
  arm, timestampET, direction, entryPrice, stopPts, exitReason, exitPrice,
  heldMin, netPts, netUsd, R, mfe, mae, ratio, ff05, ff1, ff2,
  fillAssumption, noFillReason, month, isoWeek, engineVersion, barSource`
- `V41_PROSPECTIVE_RESOLUTION_YYYY-MM.csv` — `eventId, candidateId,
  timestampET, sigEt, fwdEligible, parentSignalDivergent, engineVersion`
  (the finalized eligibility column; event rows themselves say PENDING
  because they are written the moment the event fires)
- `V41_PROSPECTIVE_DIAG_MNQ.txt` / `V41_PROSPECTIVE_AUDIT_MNQ.txt` —
  startup diagnostic; run audit with preload / written / duplicate /
  pre-cutoff / Q-FWD counters and write-failure warnings.

Eligibility is explicit end-to-end: `fwdEligible TRUE/FALSE` in the
resolution file (FALSE reasons: Q-FWD gap, early stop), pre-cutoff
events counted as warmup, duplicates logged — no silent drops anywhere.

## 6. prospective.py integration (frozen scorer untouched)

**NT8 records; Python scores.** The frozen `prospective.py` ingests the
**raw capture** (monthly `v4_1_orderflow_MNQ_v41of_*.csv` from the V4.1
order-flow capture host, dropped into `<scratch>/ofprospective`),
regenerates events through hash-checked `cand_spec.generate`, scores
them with the frozen registry and appends `docs/prospective_ledger.csv`.
It is unchanged.

New `analysis/v41/prospective_verify.py` (verifier only — never writes
the ledger, never modifies frozen sources) checks the NT8 files: hashes,
cutoff, duplicates, resolution completeness, provenance split — and,
when the matching raw capture is supplied, cross-checks the NT8 rows
against the canonical pipeline event-for-event and net-for-net, exactly
the relationship every previous gate proved.

## 7. Off-platform verification performed (all PASS)

`tests/ProspectiveLogHarness.cs` drove the real recorder + engine
through a two-session scenario in a scratch folder: real pre-cutoff
bars as warm-up plus **date-shifted copies (+7 days) as synthetic
post-cutoff days — plumbing test only, clearly labeled, never entering
any ledger**. Session A crashed without flushing; session B reloaded
and continued. All 12 assertions passed: zero pre-cutoff rows in any
file, event/trade/resolution keys unique after the restart, crashed
trades recovered exactly once, resolution merged and finalized,
version/provenance stamped.

Then `prospective_verify.py` ran the full first-forward-day flow
against a synthetic shifted capture: every check PASS including the
canonical cross-check (27/27 events, 8/8 managed trades exact).

## 8. Startup diagnostic — what you should see

```
volumetric read    TRUE
bid/ask available  TRUE
mode               PROSPECTIVE_LOG
output folder      C:\V41\V41_prospective
engine version     V41-PROSPECTIVE-ENGINE-1.0.3
prospective cutoff day > 2026-08-19
ledger preload     N events / M trade rows  (duplicate protection active)
STARTUP DIAGNOSTIC: PASS
```

`FAIL - primary series is not Volumetric` = wrong chart series; the
host aborts and records nothing (fail closed, no OHLCV estimation).

## 9. First-forward-day operational audit (the gate)

After ONE completed forward session, upload the five prospective files.
The audit reports: bars processed, events per candidate, duplicates
suppressed, pre-cutoff skips, Q-FWD divergences, resolution
completeness, REALTIME/HISTORICAL_LOAD split, hash/version stamps —
and, once the matching capture CSV is also available, the canonical
cross-check. **The goal is "did forward logging work correctly?", not
profitability.** The phase gate — PROSPECTIVE LOGGING PASS / FAIL — is
assigned from that audit and nothing else.

Checkpoints stay as pre-declared: reports at 20 / 50 / 100 trades from
the frozen scorer. They are reporting points, never permission to
modify. OFH13 remains the named primary regardless of early results;
early losses change nothing, early wins change nothing.

## 10. Sim101

Not in this phase. Order wiring remains deliberately unwritten; a
separate SIM101 ORDER-WIRING PHASE may follow only after at least one
clean prospective logging session is audited.
