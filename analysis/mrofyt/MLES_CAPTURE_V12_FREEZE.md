# MLES-CAPTURE-1.2 — FINAL RECORDER ROLLOVER REPAIR (FREEZE)

Date: 2026-09-01 · Base commit: `97d2bc1` · Purely additive successor.
No market outcomes, returns, trades, strategy results or P&L were
inspected. A1–A6, MROF-YT-OF-01.5, its thresholds, its
setup-frequency policy and every frozen predecessor are unchanged
(33 lineage hashes re-pinned and re-verified below).
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

## 1. The defect repaired

`MlesV11CaptureHost.Roll()` called `CloseSession()`, which stopped the
ONLY writer thread; post-rollover files opened with no consumer, and
counters/sequences/runId leaked across sessions. v1.2 replaces that
design with a permanent-lifecycle architecture: the capture worker
never dies; rotation happens INSIDE the worker.

## 2. New artifacts (all SHA-256 verified at freeze)

| File | SHA-256 |
|---|---|
| `src/MlesV12CaptureHost.cs` | `611b631953bddbf2619a14cc91f848ac8bf815de4ab44fcb00cb8525c6b97076` |
| `analysis/mrofyt/nt8_stubs_v12.cs` | `caaa19d497f79c4920bfeeedd70fb5dec63e6ab6a25bdb4683330c0d0027f445` |
| `analysis/mrofyt/mles_v12_harness.cs` | `520c219d28463063a0cee93dc9223b33cc82d084e9116cce7d4a707f6d0b2dc9` |
| `analysis/mrofyt/mles_v12_adapter.py` | `6c04f03756757947c050dd97eeef234a18d4b75bd64de62846d57cf202efa25b` |
| `analysis/mrofyt/mles_v12_audit.py` | `f9e01d65678460b6f5ab8078347d6ad17660318fc7c0ee1600dcc357633344df` |
| `analysis/mrofyt/tests_mles_v12.py` | `238cc82843ce7b3760b70b1388271963d86353d51c9b8db402c725ef5fc223b5` |
| `analysis/mrofyt/RECORDER_DEPLOYMENT_V12.md` | `0a30095102a241d1ebb5e5fc29e752ae6b86786e84d8e21097701e053eaeb45b` |
| `analysis/mrofyt/DATA_HANDOFF_V12.md` | `9a4262f40d312bcb2d0a0fb3fcb965b805701238185a15b43a0c4f18e109429c` |
| `analysis/mrofyt/SETUP_WALKTHROUGH_V12.md` | `15c3ef12b43cb0e059eb317da9c7ddd976971965009252aaa4357cc7a6195361` |
| `analysis/mrofyt/MROF_V1_Engine_v12.zip` | `3b2ec6b4bc6ed7aef81906ab8abe66f532adc85c5e86df9844119a1fc773c1ca` |

The zip (20 files) ships `MlesV12CaptureHost.cs` as the ONLY install
target; `MlesV1CaptureHost.cs`/`MlesV11CaptureHost.cs` live solely in
`archive_immutable_lineage/` with do-not-install wording (T21/T22/T22b
prove this and the byte-identity of the zipped recorder against
`src/`).

## 3. Architecture (requirements 1–9 → design)

1. **Permanent lifecycle worker** (`WorkerLoop`) is the SOLE queue
   consumer and owns writers, BBO state, counters, sequences,
   rotation, closure and manifest snapshots. Callbacks do bounded
   work only: stamp + sequence + enqueue under ONE `capLock`
   (`Publish`); no CloseSession/Join/flush/File.Move/SHA-256/manifest
   work on any callback path (proved structurally by T8's
   brace-matched body scan and behaviorally by the harness). A
   separate `FinalizerLoop` hashes and finalizes CLOSED runs only —
   it never touches the active run.
2. **Atomic sequence assignment + publication**: `{RecvUtc, Mono,
   eventSeq, enqueue}` are one atomic operation under `capLock`
   (no Interlocked + separate queue). T7 runs 6 concurrent
   randomized producers × 400 events and proves a clean audit with a
   gapless `1..N` union in assignment order.
3. **Identity taxonomy**: `captureInstanceId` (per attachment),
   `runId` = `captureInstanceId + "-R###"` (per instrument + contract
   + session), `segId` (connection segment), `eventSeq` (global
   monotonic per instance), `streamSeq` (per-run, per-stream, resets
   to 1). Every row and every manifest carries all of them (adapter
   enforces the header; T4/T12 prove resets and restart identity).
4. **Rollover**: session (18:00 ET) and contract changes rotate
   INSIDE the worker: END quality → `CloseRun` snapshot → new runId →
   full per-run reset → `OpenRun` → START + BOOK_RESYNC_START. The
   worker is alive throughout. T1/T2 (20260901→20260902 and three
   consecutive rolls), T3 (NQ 12-26→03-27), T6 (post-roll market
   rows), T9 (6,004 trades queued across a roll, zero loss).
5. **Safe shutdown**: one queue, one consumer; `Shutdown()` only
   flips `accepting` and does FULL `Join()`s (no 5 s timeout, no
   second drain — T11 proves a single `Dequeue` site). Failures
   preserve `.csv.partial` files and write a
   `MLES12_<inst>_RECOVERY.json` artifact.
6. **Disconnect/reconnect**: genuine
   `OnConnectionStatusUpdate(ConnectionStatusEventArgs)` reading BOTH
   `Status` and `PriceStatus`; disconnect invalidates the book
   (`bookResets`++), reconnect increments `segId`, clears BBO/levels
   and forces BOOK_RESYNC_START → BOOK_READY; all rows before
   readiness carry `DATA_SUPPRESSED`. Pre-first-event CONN events are
   not dropped (run opens on them). T13/T14/T14b.
7. **Manifest + auditor**: manifests record first/last eventSeq,
   per-stream first/last streamSeq, firstSegId/lastSegId/
   connectionSegments, reconnects, bookResets, maxBid/AskLevelSeen,
   declaredDepth, `flushPolicySeconds`, depth side+action counts,
   overflow/drop/write-error counters and per-file SHA-256. The
   auditor verifies all of it plus NQ/MNQ session pairing with
   overlap fraction (≥ 0.5), orphan partials, orphan CSVs, recovery
   artifacts, restart/roll collisions, duplicate runIds, instance
   union gaps and BOOK_READY-without-resync. Collision names keep
   the real extension (`..._manifest.collision-N.json`) so the
   scanner discovers them (T15–T20).
8. **Durability + health**: bounded periodic flush (default 30 s,
   recorded in the manifest); heartbeats carry
   quote/trade/depth-bid/depth-ask counts, queue depth, high-water
   mark, overflows, drops, write errors, runId, segId and book
   readiness. Heartbeats exist ONLY in the quality file — the code
   does not call `Print()`, and no doc claims NinjaScript Output
   printing.
9. **Genuine NT8 namespaces**: `NinjaTrader.Data.Operation.
   Add/Update/Remove`, `ConnectionStatusEventArgs.Status` +
   `.PriceStatus` (`NinjaTrader.Cbi.ConnectionStatus`),
   `NinjaTrader.NinjaScript.Indicators`. The stubs
   (`nt8_stubs_v12.cs`) mirror the real surface; the recorder was
   written to the real API, not the stubs to the recorder.

## 4. Defects found and fixed BY the lifecycle harness

The harness exists to catch what token checks cannot; it caught four
genuine defects during development, all fixed before freeze:

1. Manifest `firstEventSeq` took the first-WRITTEN seq (a synthesized
   SESSION_START) instead of the minimum → min/max tracking in
   `Head()`.
2. recv/mono were stamped BEFORE the lock, so `(seq, recv, mono)`
   were not jointly monotonic under concurrency → stamping moved
   inside `capLock` (`Publish` / `NextSeqStamped`).
3. The auditor's global-seq-order segment check false-positived on
   legitimate queue lag after reconnect → per-FILE non-decreasing
   segId check.
4. **CONN seq leak** (caught at final audit): CONN events consumed a
   published `eventSeq` that never reached any file
   (`INSTANCE_SEQ_GAP` at seqs 8, 10 in the disco scenario). Fix:
   control (CONN) events consume NO published seq; their quality rows
   mint seqs at write time — union gapless AND every file monotone —
   while the true occurrence instant is preserved in the
   `CONN_STATUS` detail (`occurredUtc=`, `occurredMono=`). Pinned by
   T14b.

## 5. Test evidence (exact commands, unabridged counts)

All run 2026-09-01 from a clean tree at `97d2bc1` + these additions.

| Command (cwd) | Result |
|---|---|
| `python3 tests_mles_v12.py` (analysis/mrofyt) | **31/31 tests passed** |
| `python3 tests_mrofyt.py` (analysis/mrofyt) | 59/59 tests passed |
| `python3 tests_mrofyt_v01_1.py` | 56/56 tests passed |
| `python3 tests_mrofyt_v01_2.py` | 31/31 tests passed |
| `python3 tests_mrofyt_v01_3.py` | 32/32 tests passed |
| `python3 tests_mrofyt_v01_4.py` | 25/25 tests passed |
| `python3 tests_mrofyt_v01_5.py` | 36/36 tests passed |
| `python3 tests_mles_v11.py` | 29/29 tests passed |
| `python3 tests_mrof.py` (analysis/mrof) | 42/42 tests passed |
| `python3 tests_closure.py` (analysis/mofad) | 15/15 tests passed |

Total: **356/356** (325 preserved predecessor tests + 31 v1.2 tests).
Every predecessor suite file is byte-identical to its pinned hash
(first line of the v1.2 suite verifies all 33 lineage hashes).

### Lifecycle harness (real writer/rotation execution, not token checks)

```
mkdir -p /tmp/mles12_hn && cd /tmp/mles12_hn
mcs -warn:4 -out:mles12_harness.exe \
    <repo>/analysis/mrofyt/nt8_stubs_v12.cs \
    <repo>/src/MlesV12CaptureHost.cs \
    <repo>/analysis/mrofyt/mles_v12_harness.cs
mono mles12_harness.exe /tmp/mles12_hn
```

mcs exit 0 (one benign CS0649 warning: reserved `NGapMarked` counter
never assigned). mono exit 0; unabridged output:

```
HARNESS rolls runs=4 opened=4 recovery=none
HARNESS croll runs=2
HARNESS conc runs=1 produced=2400
HARNESS bigq runs=2 sent=6000
HARNESS noevent files=0 runs=0
HARNESS restart idA=<inst-A> idB=<inst-B> distinct=1
HARNESS disco runs=1
HARNESS pair nq=1 mnq=1
HARNESS pairbad nq=1 mnq=1
HARNESS pairlow nq=1 mnq=1
HARNESS done ok=1
```

(`idA`/`idB` are timestamp-random instance ids, distinct on every
run.) Post-run audit of the genuine harness output:
rolls/croll/conc/bigq/disco/restart all audit clean per run (the
single-instrument capture folders report only the expected
MISSING_REQUIRED_INSTRUMENT/NQ_MNQ_SESSION_MISMATCH pairing codes);
pair passes capture-level with overlap 1.00; pairbad fails with
exactly `NQ_MNQ_SESSION_MISMATCH`; pairlow fails with exactly
`NQ_MNQ_INSUFFICIENT_OVERLAP`.

**The Mono stub compile proves syntax and core behavior only. It is
NOT an NT8 F5 compile.**

## 6. Requirement → test traceability

| Req | Proof |
|---|---|
| 1 permanent worker, bounded callbacks | T8, T11, harness all scenarios |
| 2 atomic seq+publication | T7, T7b |
| 3 identity taxonomy | T4, T12, adapter header checks |
| 4 session/contract rollover | T1, T2, T3, T6, T9 |
| 5 safe shutdown | T10, T11 (+ recovery artifacts on failure paths) |
| 6 disconnect/reconnect | T13, T14, T14b |
| 7 manifest+auditor | T5, T15–T20, pair check |
| 8 flush + heartbeats, no Print() claim | manifest `flushPolicySeconds`; docs (T21) |
| 9 genuine NT namespaces | stubs mirror real API; mcs compile |
| 10 deployment package | T21, T22, T22b |
| 11 all tests preserved + harness | table above, 356/356 |

## 7. USER-SIDE STEPS — NOT RUN HERE (no NinjaTrader in this environment)

1. Real NinjaTrader **F5 compile** of `MlesV12CaptureHost.cs`.
2. **Five-minute NQ + MNQ Market Replay smoke test**.
3. **Stop → finalize → audit** on the user machine.
4. **Restart → finalize → audit** on the user machine.
5. The **first genuine 18:00 ET session rollover audit** on live
   capture.

None of these were performed and none are claimed.

## 8. Classification

**INSUFFICIENT_DATA — ZERO GENUINE RECORDED SESSIONS.** Passing
software tests proves recorder behavior only. It does not prove
positive expected value.

---

## 9. Amendment A1 (packaging only — no code change)

`OPERATING_RUNBOOK.md` was added to the repository and to the delivered
package after the freeze above. **No recorder, adapter, auditor, test
or research file changed**; `src/MlesV12CaptureHost.cs` remains
`611b6319…c6b97076` and the suite remains 31/31 (356/356 overall).

Only the zip hash moves, because the archive gained one document:

```
3b2ec6b4bc6ed7aef81906ab8abe66f532adc85c5e86df9844119a1fc773c1ca  (freeze zip, 20 files)
d6c801ba3b9260861b73056c1abaef97e04f367818471a6fa03cad4ae6104733  (current zip, 21 files: + OPERATING_RUNBOOK.md)
```

The runbook is operating procedure for the user (install, weekly
checks, the ≥20-session verification checkpoint and the ≥60-session
State-C threshold). It states the same five user-side blocked steps
listed in §7 and the same classification. It contains no outcome,
return or P&L content.

---

## 10. Amendment A2 — REAL F5 COMPILE EVIDENCE (namespace defect fixed)

The user ran §7 step 1 (the genuine NinjaTrader F5 compile). **It
failed with three errors**, disproving a §3 item-9 claim:

```
CS0246  line 887 col 13  type or namespace 'ConnectionStatusEventArgs' not found
CS0103  line 877 col 41  the name 'Operation' does not exist in the current context
CS0103  line 878 col 41  the name 'Operation' does not exist in the current context
```

### Root cause

`nt8_stubs_v12.cs` declared BOTH `Operation` and
`ConnectionStatusEventArgs` inside `NinjaTrader.Data`. The host was
written against that stub, and the stub was written against the host —
so `mcs` validated a closed fiction. This is exactly the failure mode
the original §3 item 9 asserted had been avoided; **that assertion was
wrong** and is corrected here rather than quietly amended.

### What the compiler actually proved

- `e.Operation` resolves → the property is real; only the bare enum
  TYPE name is unresolvable.
- `NinjaTrader.Cbi.ConnectionStatus.Connected` resolves (no error on
  lines 890/893) → the Cbi namespace and that enum are correct.
- The types are NOT in `NinjaTrader.Data` (the `using` was present),
  nor in `NinjaTrader.NinjaScript`/`NinjaTrader` root (both are
  auto-searched as enclosing namespaces of the host class).

### Fix

1. **Depth operation — type never named.** The host now reads
   `e.Operation.ToString().ToUpperInvariant()` and passes the member
   name through. The ingest adapter already normalizes ADD/INSERT,
   UPDATE/CHANGE and REMOVE/DELETE and RAISES `UnknownEnumError` on
   anything else, so an unexpected member fails loudly at intake
   instead of silently mis-mapping to `REMOVE` (which the previous
   ternary chain would have done).
2. **`NinjaTrader.Cbi.ConnectionStatusEventArgs`** fully qualified in
   the override signature. Still INFERRED, not yet F5-confirmed.
3. **Stubs corrected** so they can no longer mask this: the
   depth-operation enum is now declared OUTSIDE every namespace the
   host imports, making any future bare reference fail in the harness
   too.

### Re-verification

mcs exit 0; suite 31/31; full battery 356/356 unchanged.

```
ae0bd74a4eda2dbf9cafe4e7a88e8c15604f690cef95d9b45b3b6915fb848438  src/MlesV12CaptureHost.cs
be29c36a62624ab5e18e67d104eb4e9323abcda4bf5faf1c88c54486fc446f4a  analysis/mrofyt/nt8_stubs_v12.cs
4a6391a0870a7c63420f4eae4299fa01818b3e87011c663af9dc230a27a9d325  analysis/mrofyt/MROF_V1_Engine_v12.zip
```

**Standing lesson: a stub compile is not an API validation.** Only the
user-side F5 compile can confirm NT8 namespaces.

### Amendment A3 — F5 COMPILE PASSED (2026-09-01)

The user re-ran the genuine NinjaTrader F5 compile on the corrected
host: **zero errors.**

This resolves the open inference in A2 item 2:
`NinjaTrader.Cbi.ConnectionStatusEventArgs` is **CONFIRMED** correct,
as is the `.ToString()` approach to the depth-operation enum.

**§7 blocked-step 1 (real NinjaTrader F5 compilation) is now
COMPLETE.** Steps 2–5 remain outstanding:

2. Five-minute NQ + MNQ Market Replay smoke test — NOT RUN
3. Stop → finalize → audit — NOT RUN
4. Restart → finalize → audit — NOT RUN
5. First genuine 18:00 ET rollover audit — NOT RUN

What F5 proves: the host compiles against the real NT8 API. What it
does NOT prove: that any market data is captured, that depth arrives,
that rotation survives a live 18:00 ET roll, or anything whatsoever
about expected value. Classification unchanged:
**INSUFFICIENT_DATA — ZERO GENUINE RECORDED SESSIONS.**

### Amendment A4 — FIRST GENUINE LIVE CAPTURE (2026-09-01)

A 2 m 13 s live NQ capture was recorded on the user's machine
(`captureInstanceId 20260901141246409-c9f38b1f`, contract `NQ SEP26`,
14:12:46–14:14:59 UTC) and its manifest, quotes, trades and quality
files were supplied for verification.

**Integrity verified against genuine recorder output — first time
ever possible:**

| Check | Result |
|---|---|
| SHA-256 of quotes/trades/quality vs manifest | **MATCH (all 3)** |
| byte counts vs manifest | MATCH (1697479 / 571458 / 3494) |
| row counts vs manifest | MATCH (7699 / 2373 / 14) |
| v1.2 adapter parse | 10,086 events, **zero** enum/header/schema errors |
| gaps / duplicates / reversals | 0 / 0 / 0 |
| queueOverflows / droppedRows / writeErrors | 0 / 0 / 0 |
| queue high-water vs capacity | 230 / 250,000 (0.09%) |
| closeReason | `SHUTDOWN` (orderly) |

**Depth capture CONFIRMED LIVE:** 195,048 depth rows / 41.2 MB in
2 m 13 s; `depthAdd/Update/Remove` = 94,544 / 6,020 / 94,484;
`depthBid + depthAsk` = 98,724 + 96,324 = 195,048 (consistent).

**A2's `.ToString()` depth-operation fix is now validated in
production**: all three action values are present and correctly
spelled, so `e.Operation.ToString()` returns exactly Add/Update/Remove
on the real NT8 API. No `UnknownEnumError` was raised.

**Field observations (not defects):**

- Feed delivers **30 depth levels per side**, not the declared 10
  (`maxBid/AskLevelSeen = 30`). All 30 are captured; `declaredDepth`
  only gates when `BOOK_READY` fires, and the auditor compares
  observed levels to the manifest's own value, not to `declaredDepth`,
  so this does NOT fail an audit.
- NT8 emits `DISCONNECTED` before the connection is established, so
  every capture opens with one benign DISCONNECT→RECONNECT and
  `segId` 1→2. The pre-`BOOK_READY` window was ~150 ms: only **2 of
  7,699** quote rows carried `DATA_SUPPRESSED` (0.026%).
- `crossed` = 134 (1.74% of quote rows strictly bid>ask; a further
  271 rows locked bid==ask). Expected for an MBP feed whose bid and
  ask update as separate events. Measured and recorded rather than
  silently corrected, so the research layer can filter on it.

**Blocked-step status after A4:**

1. Real NinjaTrader F5 compile — **COMPLETE** (A3)
2. Five-minute NQ+MNQ Market Replay smoke test — **superseded for NQ
   by a live capture** (stronger evidence than replay); **NOT yet
   done for MNQ**
3. Stop → finalize → audit — **finalize COMPLETE** (orderly SHUTDOWN,
   manifest written, hashes verified); full `audit_capture` still
   pending because it requires the NQ+MNQ pair
4. Restart → finalize → audit — NOT RUN
5. First genuine 18:00 ET rollover audit — NOT RUN

**No MNQ run was supplied.** Until NQ and MNQ are captured over the
same session, `audit_capture` fails by design with
`MISSING_REQUIRED_INSTRUMENT` / `NQ_MNQ_SESSION_MISMATCH`.

Classification remains **INSUFFICIENT_DATA — ZERO GENUINE RECORDED
SESSIONS**: a 2-minute fragment is not a session, and none of this
speaks to expected value.
