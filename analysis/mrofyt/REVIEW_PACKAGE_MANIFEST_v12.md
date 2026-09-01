# REVIEW_PACKAGE_MANIFEST_v12.md — independent-verification package

Additive; `REVIEW_PACKAGE_MANIFEST.md` (v01.4) and
`REVIEW_PACKAGE_MANIFEST_v01_5.md` stay unchanged and hash-pinned.
Every claim below is independently re-runnable.
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

## Authoritative recorder (MLES-CAPTURE-1.2)

```
ae0bd74a4eda2dbf9cafe4e7a88e8c15604f690cef95d9b45b3b6915fb848438  src/MlesV12CaptureHost.cs
4a6391a0870a7c63420f4eae4299fa01818b3e87011c663af9dc230a27a9d325  analysis/mrofyt/MROF_V1_Engine_v12.zip (delivered artifact, 21 files; recorder inside byte-identical to src/MlesV12CaptureHost.cs — proved by tests T22. Supersedes freeze-time zip 3b2ec6b4… by the addition of OPERATING_RUNBOOK.md only — see MLES_CAPTURE_V12_FREEZE.md §9)
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
520c219d28463063a0cee93dc9223b33cc82d084e9116cce7d4a707f6d0b2dc9  analysis/mrofyt/mles_v12_harness.cs
6c04f03756757947c050dd97eeef234a18d4b75bd64de62846d57cf202efa25b  analysis/mrofyt/mles_v12_adapter.py
f9e01d65678460b6f5ab8078347d6ad17660318fc7c0ee1600dcc357633344df  analysis/mrofyt/mles_v12_audit.py
238cc82843ce7b3760b70b1388271963d86353d51c9b8db402c725ef5fc223b5  analysis/mrofyt/tests_mles_v12.py
0a30095102a241d1ebb5e5fc29e752ae6b86786e84d8e21097701e053eaeb45b  analysis/mrofyt/RECORDER_DEPLOYMENT_V12.md
9a4262f40d312bcb2d0a0fb3fcb965b805701238185a15b43a0c4f18e109429c  analysis/mrofyt/DATA_HANDOFF_V12.md
15c3ef12b43cb0e059eb317da9c7ddd976971965009252aaa4357cc7a6195361  analysis/mrofyt/SETUP_WALKTHROUGH_V12.md
```

Reproduce the entire proof (mcs + mono lifecycle harness + audits +
adversarial fixtures + package byte-identity):

```
cd analysis/mrofyt && python3 tests_mles_v12.py      # 31/31
```

The suite itself compiles the recorder with mcs against the stubs,
RUNS the lifecycle harness with mono (three session rolls, a contract
roll, 6 concurrent producers, a 6,000-event queued rotation,
restart, disconnect/reconnect, NQ+MNQ pairing), audits the genuine
output and then attacks the auditor with falsified fixtures.

Predecessor suites (byte-identical, re-run at freeze): 59+56+31+32+
25+36+29+42+15 = 325, all passing; grand total 356/356.

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
