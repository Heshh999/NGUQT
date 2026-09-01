# MLES-CAPTURE-1.1 — RECORDER SUCCESSOR FREEZE

Frozen before any market outcome exists. Additive: the predecessor
recorder `src/MlesV1CaptureHost.cs` (MLES-CAPTURE-1.0.0, Freeze A
`c40f39a`, SHA-256 `dab3abec…`) is UNTOUCHED and still pinned by the
v01.5 suite. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

## Artifacts

```
17a8c347d39e7187f81d7ca1fd6c7161440a8d1bfdc49823f23d1553c419815e  src/MlesV11CaptureHost.cs
4ce2f94200334dc4597f7c2d79995158b8954e3d523e626dba5657855e53b8e1  analysis/mrofyt/mles_v11_adapter.py
a4aed25eedc161e5c31db4b2144c9393408cdedc4d515229a5d9b2afc5efcbb9  analysis/mrofyt/mles_v11_audit.py
89cb51f4f18d45c1e2c7b1f2a449f763d04b08e5703907f1e5d002f177b78330  analysis/mrofyt/tests_mles_v11.py
```

## A. Recorder identity and storage

- Every row carries `schema, runId, segId, session, instrument,
  contract, stream, eventSeq, streamSeq, tRecvUtc, tExchUtc, tMono`;
  the file path carries instrument + EXACT contract + session + runId.
- `State.Configure` mints a NEW `runId` on every start, so a restart
  can never resolve to a previous file name. Files are opened
  `FileMode.CreateNew` — a finalized file is never appended to.
- Old-contract and new-contract capture are isolated by path
  (`contract` is a path component) and `Roll()` closes the session on
  any contract change.
- Writing is `.csv.partial` → `File.Move` atomic finalization. If a
  final name or a manifest name already exists it is **never
  overwritten**: the new artifact takes a `.collision-N` suffix.

## B. Causal event ordering

- ONE globally monotonic `eventSeq` assigned at callback receipt by
  `Interlocked.Increment(ref eventSeq)` across quote, trade, depth,
  connection and quality events; per-stream `streamSeq` retained as a
  secondary field.
- All disk writes are serialized through ONE ordered writer thread
  draining a FIFO queue, so file order equals assignment order.
- Callback receive UTC and exchange/event UTC are written as ISO-8601
  (`yyyy-MM-ddTHH:mm:ss.fffffffZ`), with runId and segId on every row.
  A reconnect increments `segId` and logs `RECONNECT`.
- Queue overflow (`queueOverflows`), dropped rows (`droppedRows`) and
  write failures (`writeErrors`) are counted and reported.

## C. Manifests

Each run manifest carries: per-stream filename, SHA-256, byte size and
row count; first/last global `eventSeq`; first/last per-stream
sequences; first/last receive and exchange timestamps; exact contract,
instrument, session, runId, connection segments; gaps, duplicates,
reversals, drops, write errors, reconnects, crossed, book resets; and
depth **side** counts (`depthBid`, `depthAsk`) plus depth **action**
counts (`depthAdd`, `depthUpdate`, `depthRemove`).

## D/E. Adapter and audit (Python side)

`mles_v11_adapter.py` parses the recorder's actual ISO-8601 stamps
without `float()` (7 fractional digits truncated, never rounded),
normalizes QUOTE/TRADE/DEPTH, Add/Update/Remove and Bid/Ask into one
canonical schema, and raises `UnknownEnumError` on any unrecognized
value. `mles_v11_audit.py` makes the **manifest the authoritative
entrypoint** and FAILS on hash mismatch, byte-size or row-count
disagreement, malformed header, unknown enum, mixed run / contract /
session / instrument, sequence gap, duplicate or reversal, timestamp
reversal, missing required stream, missing depth side or action, or
any non-zero recorder-reported drop/overflow/write-error counter. NQ
and MNQ are REQUIRED at capture level; ES is explicitly OPTIONAL.
Capture-level checks also detect restart collisions (duplicate runId)
and contract-roll collisions (one runId spanning contracts).

## Compile status — stated exactly

- **Done here:** `mcs -target:library nt8_stubs.cs
  src/MlesV11CaptureHost.cs` → exit 0. This proves the source is
  syntactically valid and type-consistent against the NT8 API surface
  it uses (stubs written for that purpose only).
- **NOT done here and NOT claimable:** the NinjaTrader **F5 compile**
  and the **five-minute NQ+MNQ Market Replay smoke test**. This
  container has no NinjaTrader, no Windows runtime, no data feed and
  no replay database. Both remain user-side steps, specified in
  `RECORDER_DEPLOYMENT_v01_3.md` §2 and §5.

Classification unchanged: **`INSUFFICIENT_DATA`** — zero genuine
sessions exist.
