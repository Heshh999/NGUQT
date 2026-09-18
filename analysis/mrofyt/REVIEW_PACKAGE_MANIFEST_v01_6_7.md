# REVIEW_PACKAGE_MANIFEST_v01_6_7.md — independent-verification package

Additive. `REVIEW_PACKAGE_MANIFEST.md` (v01.4),
`REVIEW_PACKAGE_MANIFEST_v01_5.md` and `REVIEW_PACKAGE_MANIFEST_v12.md`
stay unchanged and hash-pinned. Every claim below is independently
re-runnable. **THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**

## New in this delivery

```
cb1ac7fa10b59955a467d140e7c17b9318eea525adb29b42c07cb15f64de1057  mrofyt_swings_v016.py
001d80630f0561749899f2ea46707bc339dd91435e082bad6da963c394d8b9de  mrofyt_engine_v016.py
84a0ca89b93eea041a82da37e5afb87c91072d3c8ed75ff77ced17706126b963  tests_mrofyt_v01_6.py
2b1f9f9159fcda2b76d5f9ac16e53771f473278bf7009b98de51cec37c95e17b  MROF_YT_OF01_6_SUCCESSOR_FREEZE.md
b6bd0b05f48a6e26871df69c97fde97112a19d3f4b17da7edf280caa5bdc354d  mrofyt_exits_v017.py
0df5357cce0d0c77c6f38759c757086a067ea90aef8efc1d373a766bbc8fe7f9  tests_mrofyt_v01_7.py
cbd25e6df806db216cf480a3445f1628fc56dff95ea0d903dc197b91ac7b4791  MROF_YT_OF01_7_EXIT_FREEZE.md
3bd2b115aa219bf14420a2e536e867689fd782db1168574c306d3918c6ae1367  mrofyt_pilot.py (MROF-YT-PILOT-1.1; supersedes a6504d0f… — event de-duplication and the 300/600/1800 s horizons, measurement only; see FINDINGS Amendment 1)
d9bd514af587b93b91d21e8317c2ad38a0f3ee3175a4b19c2b44798822523d67  tests_mrofyt_pilot.py (32 tests; supersedes a1b5cf76…)
01d5f381df774b373302f5d8867892c3403d6f7ac2a49eed09cac9d50915a4e9  MROF_YT_WAVE2_REGISTRATION.md (DRAFT — pending operator sign-off; re-hash on sign-off)
4624b199298935b72a2f906663ce7fd9b0b40f0d59be8e06f026b4771e6ac1d4  MROF_YT_PILOT_DIAGNOSTIC_FINDINGS.md (supersedes 8ab588fa… — Amendment 1)
50d0ddc78814725011714faf01b1da0d45053d3612cb08095230496ac641c1a2  MROF_ACTUAL_STATE_INVENTORY.md
```

Modified (one file, additively — a skip path, an observation hook and a
run-id field):

```
99c9b2778809d5ab0b93b6374e2db772312cb61a764ca839ee8244eb8d2867a5  mrofyt_runner.py (supersedes 3a765f3c… — retroactive disconnect-gap correction, see REVIEW_PACKAGE_MANIFEST_v12.md)
```

Archived source directive:

```
55d598a3c2e5453b9c47675f76932455dca8689084fddfd4535e5b4907def942  ../../docs/prompts/MROF_ONE_COMPLETE_CLAUDE_PROMPT_1.md
```

Delivered package (86 files, repo layout preserved so every suite runs
from inside it unchanged):

```
1ba494da4e4a89533287d3861e7c40d95ee0c8446b519a8ccc3f903d41b4a157  MROF_V1_Engine_v01_6_7.zip (supersedes d6c00abb… — pilot 1.1, recorder BOOK_READY repair, depth-completeness guard, retroactive runner correction. This file ships inside the zip it names, so the in-zip copy records the preceding zip hash by construction; hash the delivered artifact against the value here, not against its own embedded copy.)
```

```
cd analysis/mrofyt && for f in tests_*.py; do python3 "$f" | tail -1; done
# run from inside the unzipped package: 397/397, identical to the repo
```

## Predecessors — reverified unmodified

```
74ff9a99e468e22326dad9e01e4ee4dc7ab90c8da7e330a6b5f9e70e9eecb91b  MROF_YT_OF01_FINAL_SOURCE_PROMPT.md
b753a09cc077267a935df37f9b531f2179d920b8f76dc6ee5788628c264f7194  MROF_YT_OF01_5_SUCCESSOR_FREEZE.md
e3da36cd63a18a22935124e852ce8f8b785e96df136d98944f7e88654b1c6847  mrofyt_engine_v015.py
```

Reverified in-suite by `tests_mrofyt_v01_6.py::B19` and
`tests_mrofyt_v01_7.py::C12`, so a predecessor edit breaks the build.

## Reproduce everything

```
cd analysis/mrofyt
for f in tests_*.py; do python3 "$f" | tail -1; done
```

| suite | result |
| --- | --- |
| `tests_mles_v11.py` | 29/29 |
| `tests_mles_v12.py` | 46/46 |
| `tests_mrofyt.py` | 59/59 |
| `tests_mrofyt_pilot.py` | 32/32 |
| `tests_mrofyt_runner.py` | 15/15 |
| `tests_mrofyt_v01_1.py` | 56/56 |
| `tests_mrofyt_v01_2.py` | 31/31 |
| `tests_mrofyt_v01_3.py` | 32/32 |
| `tests_mrofyt_v01_4.py` | 25/25 |
| `tests_mrofyt_v01_5.py` | 36/36 |
| `tests_mrofyt_v01_6.py` | 21/21 |
| `tests_mrofyt_v01_7.py` | 15/15 |
| **total** | **397/397** |

## Runnable research commands

```
python3 mles_v12_audit.py  "<capture folder>"                      # integrity
python3 mrofyt_runner.py   "<capture folder>" --out ledger.json     # outcome-blind
python3 mrofyt_pilot.py    "<capture folder>" --out pilot.json      # §8A diagnostic
```

All three stream at flat memory. `mrofyt_runner.py --outcomes` and
`mrofyt_exits_v017.research_driver()` both raise `STATE-C LOCKED`.

## Read-only no-order proof

```
grep -nE "SubmitOrder|ChangeOrder|CancelOrder|EnterLong|EnterShort|ExitLong|ExitShort" \
     mrofyt_swings_v016.py mrofyt_engine_v016.py mrofyt_exits_v017.py mrofyt_pilot.py
# -> no matches outside header comments documenting the prohibition
```

Enforced in-suite by `B18` and `C12`, which strip comments before
scanning.

## NOT performed here

Real NinjaTrader F5 compilation; Market Replay or live smoke testing;
any market-outcome study. This environment has no NT8, Windows or live
feed. **A stub compile is not an API validation.**

Classification: **`IMPLEMENTATION_COMPLETE` / `INSUFFICIENT_DATA` /
`MARKET_RESEARCH_NOT_RUN` / `PROSPECTIVE_VALIDATION_NOT_STARTED`.**

## Amendment: two integrity repairs (2026-09-13)

Recorded in full in `REVIEW_PACKAGE_MANIFEST_v12.md`; summarised here
because both change files this package ships.

```
ce1e475a37bcad14e4e7ea10228feaea9a561c6ea4d0181e54077774fdebc060  ../../src/MlesV12CaptureHost.cs (build 1.2.2)
b0a2c0266015aeabed8855801afbdca89ba9ecc2232a91e397890e6fcffc1021  mles_v12_audit.py
3d8812b9d286b754bdd01050f4714c3dea1de13c5d59e27a5274903fc180c405  mles_v12_harness.cs
729c34f05887c7b7913604edc50ed25c43d8436fe57f3d51f1825ecc53ade78b  tests_mles_v12.py
```

1. **Recorder: spurious `BOOK_READY` after a disconnect.** The gate
   maxima were not reset when the book was invalidated, so the next
   depth row re-emitted `BOOK_READY` with no resync — and
   `mrofyt_runner.py` re-armed on it. Pinned by `T31`. **Needs a real
   NinjaTrader F5 recompile to take effect.**
2. **Auditor: `MISSING_DEPTH_ACTION` had no minimum-row guard**, so
   near-empty runs (a closed market, a few seconds before shutdown)
   failed a completeness claim they could not support. Pinned by `T32`
   and `T32b`. Analysis-side only, no recompile.

The lifecycle harness gained a depth row inside the disconnect gap —
its absence is precisely why defect 1 survived the suite.

3. **Runner: pre-repair recordings corrected retroactively.** The old
   recordings still carry `DISCONNECTED` on every gap row and no resync
   before the spurious ready; the runner now honours both, counts what it
   ignored, and prints the counts in its summary. Analysis-side only.
   Pinned by `R12`–`R12d`. Nothing captured is missing or altered.

4. **`RecorderBuild` bumped to 1.2.2.** The disconnect repair changes
   which quality events a run emits, so it had to be distinguishable in
   the manifest; it was first committed without the bump. `T33` now binds
   the repair and the build together. A `1.2.1` manifest means "may carry
   spurious post-disconnect `BOOK_READY`, runner correction applies".

   **Installing the recorder is two steps:** copy the `.cs` into
   `Documents/NinjaTrader 8/bin/Custom/Indicators/`, *then* press F5.
   F5 alone recompiles whatever is already there.

## Wave two — registered blind, 2026-09-18

`MROF_YT_WAVE2_REGISTRATION.md` (DRAFT, pending operator sign-off) records
the second-wave hypotheses **before** the data that will judge them
exists. Wave one is untouched and keeps running blind to the December
checkpoint; wave-two code, when written, lives in new modules.

The split that makes it meaningful: sessions `<= 20260918` are exposed
DEV and informed the design; sessions `>= 20260921` are untouched and are
the only data the wave-two verdict may be read from.

Design in one line: six families become **two that can actually fire**
(A1 with replenishment redefined to observe every grid tick, and A4
registered honestly as the degraded version that produced all 65 events),
plus `W2-A4-OPEN` where the mechanism is structurally forced, a placebo
level arm, a candle-only arm, a `CAUSAL_SWING` level comparison, and a
`aggrConf == HIGH` robustness variant that measures the inferred-aggressor
weakness instead of assuming it away. A2, A3 and A5 are dropped with
reasons from the funnel, not from outcomes.

`P10`–`P10e` bind the document to the code it references, so the
registration cannot go stale silently, and `P10d` re-pins the wave-one
detector hash so registering wave two provably changed nothing.
