# MROF-YT-OF-01.5 — SUCCESSOR FREEZE (EXECUTABLE ENGINE + INGESTION)

Frozen before any market outcome is computed or computable. Purely
additive. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

## 1. Lineage

Predecessors immutable: v01 `f99c521`, v01.1 `0bf0ec5`, v01.2
`3aa0f61`, v01.3 `4f821f1`, v01.4 `8cdacfd` — **23 pinned hashes**
plus the MLES-CAPTURE-1.0.0 recorder hash, all re-verified by the
v01.5 suite on every run. A1–A6, every frozen threshold, the frozen
reset-type table and the uncapped-valid-setup policy are unchanged.
`mrofyt_engine_v015.ResearchEngineV015` is the sole executable
entrypoint; an import-graph test proves no executable path reaches the
superseded v01.2/v01.3/v01.4 coordinators.

## 2. Artifacts and hashes

```
e3da36cd63a18a22935124e852ce8f8b785e96df136d98944f7e88654b1c6847  mrofyt_engine_v015.py
2f4c26df78246d739cb8bd3d1efec2cf283c2f7777b0710e37eff33f4c8bdebb  tests_mrofyt_v01_5.py
4ce2f94200334dc4597f7c2d79995158b8954e3d523e626dba5657855e53b8e1  mles_v11_adapter.py
a4aed25eedc161e5c31db4b2144c9393408cdedc4d515229a5d9b2afc5efcbb9  mles_v11_audit.py
89cb51f4f18d45c1e2c7b1f2a449f763d04b08e5703907f1e5d002f177b78330  tests_mles_v11.py
17a8c347d39e7187f81d7ca1fd6c7161440a8d1bfdc49823f23d1553c419815e  src/MlesV11CaptureHost.cs
```

## 3. Requirement traceability

| req | implementation | test |
|---|---|---|
| A. recorder identity/storage | `MlesV11CaptureHost` (runId per start, segId per connection segment, contract in path, `.partial`→atomic finalize, `CreateNew`, `.collision-N`, never overwrite a manifest) | v01.5 recorder-token tests; MLES E14/E15 |
| B. causal ordering | one atomic `eventSeq` across all five event kinds, per-stream seq secondary, single ordered writer thread, both clocks, overflow/drop/write-error counters | MLES E3, E9; E2E-2 |
| C. complete manifests | manifest carries files/hashes/sizes/rows, first-last global+stream seqs, timestamps, contract, runId, segments, gaps, dups, reversals, drops, write errors, depth side and action counts | MLES E1, E1b, E8 |
| D. canonical adapter | ISO-8601 without `float()` (7-digit truncation), QUOTE/TRADE/DEPTH + Add/Update/Remove + Bid/Ask normalization, `UnknownEnumError` on unknown values, literal recorder fixture end-to-end | D1–D4, E10, E2E-1..5 |
| E. integrity audit | manifest-authoritative; hash/size/row/schema/run/contract/session verification; FAIL on gap, duplicate, reversal, mixed run, mixed contract, missing stream, hash mismatch, malformed header; NQ+MNQ required, ES optional; both depth sides + all three actions | E1–E15 (corrupt hash, sequence reset, restart collision, contract-roll collision, missing depth side all adversarially proven) |
| F1. open-position checked before consumed/re-arm | position gate precedes the SPENT gate in `on_group` | F1, F1b, F1c |
| F2. adjudicated occurrence never retried from stale data | `CONSUMING` set + `_consume()` on conflict, risk, data, causality, miss, overlap and trade | F2a–F2f |
| F3. approach ID minted at the price event | `on_price` mints on band entry, before any signal or fill; `approach_minted` recorded (`PRICE_EVENT` vs `SIGNAL_FALLBACK`) | F3, F3b, F3c, F3d |
| F4. union of level IDs / level families / signal families | union accumulated across every agreeing signal | F4 |
| F5. buffer until time advances or explicit completion | `SignalGroupBufferV015`; `on_price` calls `time_advanced` (strict `>`) | F5, F5b, F5c, F5d |
| F6. conflicts → zero fill, zero position, no TRADE_OPENED | conflict branch returns before any `fill_fn` call | F6 |
| F7. wired entrypoint, no superseded imports | `ResearchEngineV015` + import-graph scan | F7, F7b, F7c |

## 4. Exact commands and unabridged counts

```
cd analysis/mrofyt
python3 tests_mrofyt.py           →  59/59
python3 tests_mrofyt_v01_1.py     →  56/56
python3 tests_mrofyt_v01_2.py     →  31/31
python3 tests_mrofyt_v01_3.py     →  32/32
python3 tests_mrofyt_v01_4.py     →  25/25
python3 tests_mles_v11.py         →  29/29
python3 tests_mrofyt_v01_5.py     →  36/36
cd ../mrof  && python3 tests_mrof.py     →  42/42
cd ../mofad && python3 tests_closure.py  →  15/15
                                   TOTAL   325/325
mcs -target:library nt8_stubs.cs src/MlesV11CaptureHost.cs → exit 0
```

## 5. Blocked — stated exactly, not worked around

1. **NT8 F5 compile: NOT RUN.** No NinjaTrader/Windows in this
   environment. Substitute performed and reported as such: a Mono
   `mcs` syntax/type compile against purpose-written NT8 API stubs.
2. **Five-minute NQ+MNQ Market Replay smoke test: NOT RUN.** No feed,
   no replay database, no NinjaTrader. Procedure is specified in
   `RECORDER_DEPLOYMENT_v01_3.md` §5 and §7 and remains user-side.
3. Captured genuine sessions = 0; the recorder has never been
   attached.
4. H1-zone / PSY / ADR certification still impossible on historical
   continuous data; historical depth does not exist anywhere.
5. All probability models, grades and zone interactions remain
   shadow-only pending State-C readiness.

## 6. Classification

**`INSUFFICIENT_DATA`** — unchanged and unchangeable until genuine
recorded sessions exist. The 325 green checks demonstrate
implementation behavior on synthetic fixtures; **none of them is, or
is claimed as, evidence of positive expected value.**
