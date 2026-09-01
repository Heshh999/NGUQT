# RECORDER_DEPLOYMENT_V12.md — authoritative deployment (MLES-CAPTURE-1.2)

Supersedes the v01.3 runbook for recorder choice. **Install
`MlesV12CaptureHost` and nothing else.**
Do not install `MlesV1CaptureHost` (immutable archive lineage only).
Do not install `MlesV11CaptureHost` (immutable archive lineage only;
the 1.1 recorder stops writing after the first 18:00 ET rollover —
that defect is what 1.2 repairs).
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

## 1. What 1.2 is

A permanent-lifecycle recorder: one capture worker owns all files,
counters, BBO classification state and rotation, and lives from start
to termination. Market callbacks only stamp/sequence/enqueue under one
short lock. Session (18:00 ET) and contract rollovers close the old
run, mint a new `runId`, reset every per-run counter and continue
recording — the writer never dies. A separate finalization worker
hashes and finalizes closed runs only. Restarts mint a new
`captureInstanceId`; finalized files and manifests are never appended
or overwritten (collisions get `...collision-N.csv` /
`..._manifest.collision-N.json`, which the auditor still discovers).

## 2. Install (namespace + F5)

- File: `1_NinjaTrader_Recorder/MlesV12CaptureHost.cs`; class
  `MlesV12CaptureHost : Indicator` in
  `NinjaTrader.NinjaScript.Indicators` (core logic in
  `Mles.Capture.V12`). Depth uses the real
  `NinjaTrader.Data.Operation.Add/Update/Remove`; connection updates
  record BOTH `Status` and `PriceStatus`
  (`NinjaTrader.Cbi.ConnectionStatus`).
- NinjaScript Editor → New Indicator → paste the file → **F5**
  compile (or copy into
  `Documents\NinjaTrader 8\bin\Custom\Indicators\`).
- Attach one instance to the **NQ front contract** chart and one to
  the **MNQ front contract** chart (exact expiries; NQ and MNQ are
  REQUIRED, ES optional). Set the output folder (must not contain
  `analysis`, `docs` or `scratchpad` — the guard refuses those).

## 3. Files, health and durability

Per run: `MLES12_<inst>_<contract>_<session>_<runId>_{quotes,trades,
depth,quality}.csv` (written as `.csv.partial`, atomically finalized)
plus `..._manifest.json`. The worker flushes on a bounded periodic
policy (default 30 s; recorded in the manifest as
`flushPolicySeconds`). **Heartbeats exist ONLY in the quality file**
(the code does not call `Print()`, so nothing appears in the
NinjaScript Output window); each heartbeat carries quote/trade/
depth-bid/depth-ask row counts, queue depth, queue high-water mark,
overflows, dropped rows, write errors, current `runId`, `segId` and
book readiness. Disconnects invalidate the book; reconnects increment
`segId`, force a full resync to the declared depth, and every interval
before `BOOK_READY` is flagged `DATA_SUPPRESSED`.

## 4. Verify a session

```
python3 -c "import sys; sys.path.insert(0,'2_Analysis_Engine');
import mles_v12_audit as AU;
r=AU.audit_capture('<capture folder>'); print(r['ok'], r['failures'])"
```

## 5. User-side steps still blocked (NOT performed by Claude)

The Mono stub compile and the mono lifecycle harness prove syntax and
core behavior only. These remain user-side and were NOT run here:

1. Real NinjaTrader **F5 compilation**.
2. **Five-minute NQ+MNQ Market Replay smoke test**.
3. **Stop → finalize → audit** test on the user machine.
4. **Restart → finalize → audit** test on the user machine.
5. The **first genuine 18:00 ET rollover audit** on live capture.

Deployment is complete only when all five pass on the user's machine.
Classification stays `INSUFFICIENT_DATA — ZERO GENUINE RECORDED
SESSIONS` until then.
