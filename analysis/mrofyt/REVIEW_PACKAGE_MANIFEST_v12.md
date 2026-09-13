# REVIEW_PACKAGE_MANIFEST_v12.md — independent-verification package

Additive; `REVIEW_PACKAGE_MANIFEST.md` (v01.4) and
`REVIEW_PACKAGE_MANIFEST_v01_5.md` stay unchanged and hash-pinned.
Every claim below is independently re-runnable.
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

## Authoritative recorder (MLES-CAPTURE-1.2)

```
72f0ac2943f16d1431020db3d96a8d74d81b5b71ea7d456a7218dd96a9f66809  src/MlesV12CaptureHost.cs (supersedes 95b9380f… — spurious BOOK_READY after a disconnect; REQUIRES an F5 recompile, see §Amendment below)
3921631230e8c3dfc70cb7feaf3e4524a102708184c028c0166027b9b19d003b  analysis/mrofyt/MROF_V1_Engine_v12.zip (supersedes ba2704ad… — ships the repaired recorder, the guarded auditor and the retroactively-correct runner) (delivered artifact, 28 files, build 1.2.1; recorder inside byte-identical to src/MlesV12CaptureHost.cs — proved by tests T22. Supersedes freeze-time zip 3b2ec6b4… (20 files) — build 1.2.1 recorder, streaming auditor, outcome-blind runner, runbook; see MLES_CAPTURE_V12_FREEZE.md §9 and §11)
dab3abec22e16255cd27d198200125c5cd6a44192e7ff07d53ce798c755dd63d  src/MlesV1CaptureHost.cs (immutable archive lineage — do not install)
17a8c347d39e7187f81d7ca1fd6c7161440a8d1bfdc49823f23d1553c419815e  src/MlesV11CaptureHost.cs (immutable archive lineage — do not install)
```

Read-only no-order proof:

```
grep -nE "SubmitOrder|ChangeOrder|CancelOrder|Account\.|EnterLong|EnterShort" src/MlesV12CaptureHost.cs
# -> no matches outside the header comment documenting the prohibition
```

## v1.2 verification chain

```
be29c36a62624ab5e18e67d104eb4e9323abcda4bf5faf1c88c54486fc446f4a  analysis/mrofyt/nt8_stubs_v12.cs
3d8812b9d286b754bdd01050f4714c3dea1de13c5d59e27a5274903fc180c405  analysis/mrofyt/mles_v12_harness.cs (supersedes ff2cb79e… — the disconnect gap now carries a depth row, which is what the old fixture was missing)
12ab264bb466bbf1f48943c95b65ae524d9a142a249c94c3337ca186a3d23861  analysis/mrofyt/mles_v12_adapter.py
b0a2c0266015aeabed8855801afbdca89ba9ecc2232a91e397890e6fcffc1021  analysis/mrofyt/mles_v12_audit.py (supersedes b17a4732… — depth completeness needs enough depth rows to assert)
729c34f05887c7b7913604edc50ed25c43d8436fe57f3d51f1825ecc53ade78b  analysis/mrofyt/tests_mles_v12.py (44 tests; supersedes 4014a8d3…)
1635f0391449260d1a15c0780a54728523834f3df4505e755ad400d63a510812  analysis/mrofyt/RECORDER_DEPLOYMENT_V12.md
65b2948c0b7877d70d71aa7a12cac2326d740ad9c0aa98d4f1b608e4f12e33a0  analysis/mrofyt/DATA_HANDOFF_V12.md
15c3ef12b43cb0e059eb317da9c7ddd976971965009252aaa4357cc7a6195361  analysis/mrofyt/SETUP_WALKTHROUGH_V12.md
cf42022369fe3133c2725d8a8e10c69914d889945c0b99d2da280e1a46315f2c  analysis/mrofyt/OPERATING_RUNBOOK.md (supersedes 1ef388e1… — status header updated once genuine sessions existed; points to NT8_RECORDING_RUNBOOK.md)
964cdc661df578e6681d36fdef335366a56013efa7cd0d9f857a3cfa60b5a0e9  analysis/mrofyt/NT8_RECORDING_RUNBOOK.md (beginner-readable NT8 procedure)
c070e41e83cc5bb3ade42e9ba853001e5ed1145ae0ed6162d55c777377b212c8  analysis/mrofyt/mles_v12_synth.py (build 1.2.1 fixtures; supersedes f8e20194… — timezone-aware timestamp)
99c9b2778809d5ab0b93b6374e2db772312cb61a764ca839ee8244eb8d2867a5  analysis/mrofyt/mrofyt_runner.py (outcome-blind runner, build 1.2.1; supersedes 3a765f3c… — honours DISCONNECTED and requires a resync before re-arming, which corrects pre-repair recordings retroactively, see §Amendment; earlier supersedes b1086f7e… — the first genuine recordings exposed a crash on manifest-only runs and the runner gained a skip-whole path, an observation hook and a run-id field. See MROF_YT_PILOT_DIAGNOSTIC_FINDINGS.md)
c0e3796327c7db817aea14eef005d4758644befc4fc78ef00342da985504d0c1  analysis/mrofyt/tests_mrofyt_runner.py (15 tests; supersedes f8889e5c…)
```

Reproduce the entire proof (mcs + mono lifecycle harness + audits +
adversarial fixtures + package byte-identity):

```
cd analysis/mrofyt && python3 tests_mles_v12.py      # 44/44
cd analysis/mrofyt && python3 tests_mrofyt_runner.py # 15/15
```

The suite itself compiles the recorder with mcs against the stubs,
RUNS the lifecycle harness with mono (three session rolls, a contract
roll, 6 concurrent producers, a 6,000-event queued rotation,
restart, disconnect/reconnect, NQ+MNQ pairing), audits the genuine
output and then attacks the auditor with falsified fixtures.

Predecessor suites (byte-identical, re-run at freeze): 59+56+31+32+
25+36+29+42+15 = 325, all passing; grand total 390/390 across twelve suites at this revision.

## Correction of record

The first genuine F5 compile FAILED (CS0246/CS0103 x2): the stubs had
placed `Operation` and `ConnectionStatusEventArgs` in the wrong
namespace and the host was written to match them. Fixed and re-frozen
- see MLES_CAPTURE_V12_FREEZE.md sec.10. A stub compile is not an API
validation.

## NOT performed here

Real NinjaTrader F5 compile and the five-minute NQ+MNQ Market Replay
smoke test remain **user-side**; this environment has no NT8, Windows or
live feed, and a stub compile is not an API validation.

Since this manifest was first written, several of its blocked items have
been closed by genuine user-side work: **F5 PASSED** after the namespace
repair; stop/finalize/audit and restart/finalize/audit were exercised;
and **six 18:00 ET rollovers were audited clean** (millisecond gaps,
`SESSION_ROLL`, same instance, R001 → R002). See
`MLES_CAPTURE_V12_FREEZE.md` §10 and its amendments.

Classification: **INSUFFICIENT_DATA.** Seven sessions now exist
(2026-09-01 → 2026-09-09), 483,738,362 events ingested across 20 runs,
78,776 s of simultaneous NQ+MNQ coverage, and the first 11 frozen signals
have fired. Still far below every readiness gate. See
`MROF_YT_PILOT_DIAGNOSTIC_FINDINGS.md`.

## Auditor correction (found by genuine multi-session data)

`BOOK_READY_WITHOUT_RESYNC` was off by one. A run that BEGINS an instance
builds its book from nothing, so its first `BOOK_READY` legitimately has
no preceding `BOOK_RESYNC_START`; a later run of the same instance
inherits a built book and must resync before every ready. The rule
compared `book_ready > book_resync_starts` unconditionally, so every
R001 failed and every R002 passed — the signature of a bad rule, not of
bad data. The allowance is now exactly one, only when
`firstEventSeq == 1`, and is pinned by T29/T29b.

## Correction: INSTANCE_SEQ_GAP was misdiagnosed

The gaps on 2026-09-03/04 and 2026-09-09 were first attributed to the
1.2.0 CONN-event sequence leak, with the claim that build 1.2.1 would
remove them. **That was wrong.** The 2026-09-09 runs were captured BY
1.2.1 and show the same shortfall, so the leak cannot be the cause.

The actual cause: every affected instance has a later run still sitting
as an unfinalized `.csv.partial`. Rows queued across a rotation carry a
published seq but reach no manifest, so the union is short by exactly
them. That is an UNVERIFIABLE union, not a detected gap. The auditor now
reports `INSTANCE_SEQ_UNVERIFIABLE_OPEN_RUN` for the count/span shortfall
when the instance has an open run, and keeps `INSTANCE_SEQ_GAP` for
everything else - a hole or an overlap is never explained by an open run.
Pinned by T30/T30b, which build the two-run fixture with a genuine seq
offset rather than a hand-edited manifest.

## Amendment: spurious BOOK_READY after a disconnect (recorder defect)

Found 2026-09-13 by the `BOOK_READY_WITHOUT_RESYNC` failures on sessions
2026-09-10 and 2026-09-11 — the two sessions carrying 61 of the 66
de-duplicated signal events. The auditor rule was **right**; the
recorder was wrong.

On disconnect (`HandleConn`) the recorder cleared `BookReady` but left
`MaxBidLvl`/`MaxAskLvl` at full depth, and those maxima never decrease.
The gate in `HandleDepth` is

```csharp
if (!run.BookReady && run.MaxBidLvl + 1 >= declaredDepth &&
    run.MaxAskLvl + 1 >= declaredDepth)
```

so the **next depth row after any disconnect re-emitted `BOOK_READY`**
with no resync and no rebuild. Each disconnect/reconnect cycle therefore
produced two readies for one resync — 5 resyncs and 9 readies on
2026-09-10 is exactly four cycles.

It is not cosmetic. `mrofyt_runner.py` treats `BOOK_READY` as permission
to re-arm (`st.ready = True`), and `DISCONNECT` as the disarm. The
spurious ready **re-armed the research runner on a book the recorder had
just declared invalid**, so some decision windows in those runs were
evaluated against a stale book.

Repair, both in `HandleConn`'s disconnect branch:

1. reset the gate maxima with `BookReady`. `RunMaxBidLvl`/`RunMaxAskLvl`
   are the run-lifetime manifest figures and stay untouched.
2. emit `BOOK_RESYNC_START` at the disconnect as well. The resync is
   required from that instant, not from the reconnect — rows already
   queued can rebuild the book before the reconnect event lands — so
   this makes "every `BOOK_READY` is preceded by a `BOOK_RESYNC_START`"
   true by construction. A cycle now yields two resyncs for at most one
   ready: the conservative direction, which can never cause a false
   audit failure.

**Why the suite missed it.** The lifecycle harness sent only trades
inside the disconnect gap, never a depth row — so the gate was never
re-tested while the book was invalid. Real disconnects always have depth
rows. The harness now sends one there, and `T31` asserts that it
produces no ready. `T14` moves from 2 resyncs to 3.

**This repair requires a real NinjaTrader F5 recompile.** Until the
operator recompiles, sessions recorded by the old build keep the
spurious readies, and the affected windows keep the caveat.

## Amendment: depth completeness needs enough depth rows to assert

`MISSING_DEPTH_ACTION` was asserted unconditionally. Two genuine runs
tripped it: 2026-09-05 (608 rows — the market was shut, 18:04 ET Friday)
and 2026-09-08 (70 rows). A run that small legitimately never sees a
`REMOVE`, so the failure was a false positive, not a detection — the
same class of defect as the `BOOK_READY` off-by-one.

Sides and actions are now asserted only above `20 * declaredDepth` depth
rows (200 for a 10-level book), and `depth_completeness_checked` /
`depth_completeness_skipped` record which happened. A live NQ/MNQ run
carries tens of millions of depth rows, so no feed defect can hide
behind the floor. `T32` pins the skip; `T32b` pins that the identical
absence in a large run still fails.

Together these clear 4 of the 10 `RUN_AUDIT_FAILED` entries as false
positives and explain the other 6.

## Amendment: the runner corrects pre-repair recordings retroactively

The recorder repair above only helps sessions recorded AFTER the
operator recompiles. Sessions already on disk — including 2026-09-10 and
2026-09-11, which carry 61 of the 66 de-duplicated signal events — keep
their spurious readies. Two things in those recordings are still
correct, and the runner now honours both:

1. **Every row inside a disconnect gap carries `DISCONNECTED`.** The
   recorder stamped it from `run.Connected` independently of the
   `BookReady` bug (`Flags()`, line 462). The runner now treats it as
   suppression alongside `DATA_SUPPRESSED`, so no mid inside a gap
   reaches approach detection.
2. **The spurious ready has no `BOOK_RESYNC_START` before it.** The
   runner now re-arms on `BOOK_READY` only when a resync has been seen
   since the last disarm (`resync_pending`, true at run open because
   every `OpenRun` emits a resync). A ready without one is ignored and
   counted as `spurious_book_ready_ignored`.

Both counters print in the runner summary, so a re-run over the existing
folder shows exactly how many spurious readies and how many
disconnect-gap rows the recordings carried — the measure of how much of
the earlier `ledger2.json` was evaluated against a stale book.

**No captured data is missing or altered.** Every row the feed delivered
was written, sequenced and hashed; the defect was one wrong status label
in the quality stream, and the labels needed to undo it were always
present. `R12` reproduces the old gap layout byte-for-byte and pins the
correction; `R12c` pins that a post-repair recording (two resyncs per
cycle, no spurious ready) is handled identically with nothing counted.
