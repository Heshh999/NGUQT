# MROF-YT-OF-01.4 — SUCCESSOR FREEZE (ENGINE BOUNDARY + LEDGER)

Frozen and committed **before any outcome is computed or computable**.
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.

## 1. Lineage

Predecessors immutable: v01 `f99c521`, v01.1 `0bf0ec5`, v01.2
`3aa0f61`, v01.3 `4f821f1` — **19 pinned hashes** re-verified by the
v01.4 suite on every run. A1–A6, their thresholds, and the
uncapped-valid-setup policy are untouched. The v01.2/v01.3
coordinators are superseded, never edited: an import-graph test proves
no executable path uses them (their immutable regression tests only).
`mrofyt_engine_v014.py` (`ResearchEngineV014`) is the research
engine's sole execution path.

## 2. v01.4 artifacts and hashes

```
8f80458add811d1799d31f061b91c585755c102f32854ce58f77678195b81a2d  mrofyt_engine_v014.py
d71e919549e8537d10e42cbc492206bf3a1ee4f8602e703204a27c14f4ba11c0  tests_mrofyt_v01_4.py
d3b4ad26b97ca20a3ccbdd93260dfbb26396ba25d14aeb5eb3b169e5ca233df1  REVIEW_PACKAGE_MANIFEST.md
```

## 3. Requirement traceability

| requirement | implementation | test |
|---|---|---|
| 1. SignalGroupBuffer at the engine boundary; exact completion-timestamp grouping before any fill; opposing separate callbacks → zero fills/positions/TRADE_OPENED | `SignalGroupBuffer.submit/flush` → `CoordinatorV014.on_group` | req1, req1b, req1c |
| 2. re-arm tracking only after terminal + flat; open-position price moves cannot complete the next reset | `on_price` early-returns while a position is open; transitions gated on `terminal_t` set at exit | req2, req2b |
| 3. open-position signals → OVERLAP_SUPPRESSED, permanently consumed; re-entry needs genuine reset + new approach + later-formed conditions | consumption marks the key SPENT/awaiting-flat with a ledger row | req3, req3b, req3c |
| 4. `reset_t < formed_from_t <= signal_t`; future → CAUSALITY_FAILURE; equal/stale → DATA_SUPPRESSED | causality gate in `on_group` | req4–req4d |
| 5. first-executable-book fills: one snapshot, partial + cancel remainder, no accumulation; hours-later quote never fills | `fill_first_book` (frozen 150 ms latency + 5 s marketable window) | req5, req5b |
| 6. approach ID created when the approach begins (price event), retained for suppressions/conflicts/misses/trades | `on_price` reset-completion assigns the ordinal pre-fill; `_ledger` writes a row for EVERY outcome | req6, req6b |
| 7. ledger persists levels, level families, agreeing families, contract, session, cluster, reason | `_ledger` record schema | req7 |
| 8. reset behavior from frozen type table, not a hardcoded family list | `RESET_TYPES` + constructor override; dispatch on type | req8, req8b, req8c |
| 9. engine wired end-to-end; no executable import of superseded coordinators | `ResearchEngineV014`; import-graph scan | req9, req9b |
| 10. review package with recorder C#/ZIP + engine files, verifying 42/42, 15/15, and the read-only proof | `REVIEW_PACKAGE_MANIFEST.md` (hash-pinned), review ZIP folder | req10, req10b |

## 4. Test commands and complete counts

```
cd analysis/mrofyt
python3 tests_mrofyt.py          →  59/59
python3 tests_mrofyt_v01_1.py    →  56/56
python3 tests_mrofyt_v01_2.py    →  31/31
python3 tests_mrofyt_v01_3.py    →  32/32
python3 tests_mrofyt_v01_4.py    →  25/25
cd ../mrof  && python3 tests_mrof.py     →  42/42
cd ../mofad && python3 tests_closure.py  →  15/15
```

## 5. Still blocked

Captured event sessions = 0 (recorder attachment is user-side);
H1/PSY/ADR certifications impossible on historical continuous data;
historical depth nonexistent; probability/grade/zone interactions
shadow-only pending State-C.

## 6. Classification

**`INSUFFICIENT_DATA`** — unchanged. 260 green checks across seven
suites prove the machine matches its frozen specification; none is,
or is claimed as, evidence of positive EV.
