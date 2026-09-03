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
b9188f4d6186bf9d4acf0c9185e86a2a4cc865a1c341732f56efbaef47100110  analysis/mrofyt/mles_v12_audit.py
a2b0ed03d4ea4e64e95dd879304f4414bde2665b7364ebf95f9172bc3a675dbf  analysis/mrofyt/tests_mles_v12.py
1635f0391449260d1a15c0780a54728523834f3df4505e755ad400d63a510812  analysis/mrofyt/RECORDER_DEPLOYMENT_V12.md
65b2948c0b7877d70d71aa7a12cac2326d740ad9c0aa98d4f1b608e4f12e33a0  analysis/mrofyt/DATA_HANDOFF_V12.md
15c3ef12b43cb0e059eb317da9c7ddd976971965009252aaa4357cc7a6195361  analysis/mrofyt/SETUP_WALKTHROUGH_V12.md
1ef388e1347e47fd54186d29e45c94b22c785865147e039e98d4b52e4a340c14  analysis/mrofyt/OPERATING_RUNBOOK.md
f8e20194dba22f02ea67b0b9b0dc3aab4be62f55c938e15c6f84f093cfb3fb2d  analysis/mrofyt/mles_v12_synth.py (build 1.2.1 fixtures)
b1086f7e2af17abb469c13efc2df3f4e332ade6d8840f2dbc2d8e7dcb579c6f2  analysis/mrofyt/mrofyt_runner.py (outcome-blind runner, build 1.2.1)
f8889e5c25bac9b5aae13231d6c4c0d8ce2535445ac2f2f34183832da7c9cff0  analysis/mrofyt/tests_mrofyt_runner.py (11 tests)
```

Reproduce the entire proof (mcs + mono lifecycle harness + audits +
adversarial fixtures + package byte-identity):

```
cd analysis/mrofyt && python3 tests_mles_v12.py      # 37/37
cd analysis/mrofyt && python3 tests_mrofyt_runner.py # 11/11
```

The suite itself compiles the recorder with mcs against the stubs,
RUNS the lifecycle harness with mono (three session rolls, a contract
roll, 6 concurrent producers, a 6,000-event queued rotation,
restart, disconnect/reconnect, NQ+MNQ pairing), audits the genuine
output and then attacks the auditor with falsified fixtures.

Predecessor suites (byte-identical, re-run at freeze): 59+56+31+32+
25+36+29+42+15 = 325, all passing; grand total 373/373 (build 1.2.1: 37 + 11 new-suite tests).

## Correction of record

The first genuine F5 compile FAILED (CS0246/CS0103 x2): the stubs had
placed `Operation` and `ConnectionStatusEventArgs` in the wrong
namespace and the host was written to match them. Fixed and re-frozen
- see MLES_CAPTURE_V12_FREEZE.md sec.10. A stub compile is not an API
validation.

## NOT performed here

Real NinjaTrader F5 compile; five-minute NQ+MNQ Market Replay smoke
test; stop/finalize/audit; restart/finalize/audit; first genuine
18:00 ET rollover audit. All user-side
(`RECORDER_DEPLOYMENT_V12.md` §5).

Classification: **INSUFFICIENT_DATA — ZERO GENUINE RECORDED
SESSIONS.**
