# REVIEW_PACKAGE_MANIFEST_v12.md — independent-verification package

Additive; `REVIEW_PACKAGE_MANIFEST.md` (v01.4) and
`REVIEW_PACKAGE_MANIFEST_v01_5.md` stay unchanged and hash-pinned.
Every claim below is independently re-runnable.
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

## Authoritative recorder (MLES-CAPTURE-1.2)

```
95b9380f2ff423c3d550083fb365da3ffce8b9ece72a0b437e3d7d6231405aef  src/MlesV12CaptureHost.cs
2fa364b3350bece8c7cc86a6bd693118620f79a197748dfa1c454311f47396ff  analysis/mrofyt/MROF_V1_Engine_v12.zip (delivered artifact, 28 files, build 1.2.1; recorder inside byte-identical to src/MlesV12CaptureHost.cs — proved by tests T22. Supersedes freeze-time zip 3b2ec6b4… (20 files) — build 1.2.1 recorder, streaming auditor, outcome-blind runner, runbook; see MLES_CAPTURE_V12_FREEZE.md §9 and §11)
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
ff2cb79e2ac64c80f84a4dce8ca6ee3c255b7137a21903e777774ab2db3dbeb7  analysis/mrofyt/mles_v12_harness.cs
12ab264bb466bbf1f48943c95b65ae524d9a142a249c94c3337ca186a3d23861  analysis/mrofyt/mles_v12_adapter.py
b17a47325acf73cb596dd1d7c899496b4923a793069e0ac294b72fc88ab3c92a  analysis/mrofyt/mles_v12_audit.py
4014a8d3fbff29ceee9c47357bc72f0e711e26dd9cadf68c70a8fac80d9ec186  analysis/mrofyt/tests_mles_v12.py
1635f0391449260d1a15c0780a54728523834f3df4505e755ad400d63a510812  analysis/mrofyt/RECORDER_DEPLOYMENT_V12.md
65b2948c0b7877d70d71aa7a12cac2326d740ad9c0aa98d4f1b608e4f12e33a0  analysis/mrofyt/DATA_HANDOFF_V12.md
15c3ef12b43cb0e059eb317da9c7ddd976971965009252aaa4357cc7a6195361  analysis/mrofyt/SETUP_WALKTHROUGH_V12.md
cf42022369fe3133c2725d8a8e10c69914d889945c0b99d2da280e1a46315f2c  analysis/mrofyt/OPERATING_RUNBOOK.md (supersedes 1ef388e1… — status header updated once genuine sessions existed; points to NT8_RECORDING_RUNBOOK.md)
964cdc661df578e6681d36fdef335366a56013efa7cd0d9f857a3cfa60b5a0e9  analysis/mrofyt/NT8_RECORDING_RUNBOOK.md (beginner-readable NT8 procedure)
c070e41e83cc5bb3ade42e9ba853001e5ed1145ae0ed6162d55c777377b212c8  analysis/mrofyt/mles_v12_synth.py (build 1.2.1 fixtures; supersedes f8e20194… — timezone-aware timestamp)
3a765f3c304b0c23c5efbaaf3aaead7b66d6b67aaa385dbe9bb153d34f28bfc4  analysis/mrofyt/mrofyt_runner.py (outcome-blind runner, build 1.2.1; supersedes b1086f7e… — the first genuine recordings exposed a crash on manifest-only runs and the runner gained a skip-whole path, an observation hook and a run-id field. See MROF_YT_PILOT_DIAGNOSTIC_FINDINGS.md)
f8889e5c25bac9b5aae13231d6c4c0d8ce2535445ac2f2f34183832da7c9cff0  analysis/mrofyt/tests_mrofyt_runner.py (11 tests)
```

Reproduce the entire proof (mcs + mono lifecycle harness + audits +
adversarial fixtures + package byte-identity):

```
cd analysis/mrofyt && python3 tests_mles_v12.py      # 41/41
cd analysis/mrofyt && python3 tests_mrofyt_runner.py # 11/11
```

The suite itself compiles the recorder with mcs against the stubs,
RUNS the lifecycle harness with mono (three session rolls, a contract
roll, 6 concurrent producers, a 6,000-event queued rotation,
restart, disconnect/reconnect, NQ+MNQ pairing), audits the genuine
output and then attacks the auditor with falsified fixtures.

Predecessor suites (byte-identical, re-run at freeze): 59+56+31+32+
25+36+29+42+15 = 325, all passing; grand total 374/374 across twelve suites at this revision.

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
