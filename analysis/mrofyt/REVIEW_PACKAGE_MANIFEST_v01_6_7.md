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
b955ea9db2e9956c0f433036e1af3f5bb66ce793ff690253f46101c58bf71d09  mrofyt_pilot.py (MROF-YT-PILOT-1.2; supersedes 3bd2b115… — validation blind (BLIND_FROM=20260921, markouts withheld, monotone exposure ledger), seeded bootstrap 95% intervals, skip reasons + book-integrity counters in the report; 1.1 supersedes a6504d0f… — event de-duplication and the 300/600/1800 s horizons, measurement only; see FINDINGS Amendment 1)
a9bacd646e6ce57e89406745db9ca2a182820a0f9196efe409c48ebe5995a640  tests_mrofyt_pilot.py (43 tests; supersedes 417282fd… — P1b tracks the runner summary wording)
4e398285cf52c193beb8a1a8a44eed02c733ff94a0f73992725aa0dc978f7b29  MROF_YT_WAVE2_REGISTRATION.md (DRAFT — pending operator sign-off; §8.1 interim-monitoring rule added; re-hash on sign-off)
6b0eb7ea4a9bc5deb48eec7e461b03c36d509defeb9a28023b104b489f929538  MROF_YT_PILOT_DIAGNOSTIC_FINDINGS.md (supersedes 4624b199… — Amendment 2: the validation blind; Amendment 1 supersedes 8ab588fa…)
a8b637a5ce4be0a7e4f2ae450c5be6af4389e6c1d561510488b1863c32c1a32c  mrofyt_recover.py (MROF-YT-RECOVER-1.0 — manifest reconstruction for runs killed before finalizing; --dry-run probes header+tail only, so listing what is recoverable is instant on a 6 GB file)
086a0ed22a31143049c0ec9c42a172ea26ffe83796a522719b72ffe796fc7cf9  tests_mrofyt_recover.py (21 tests)
50d0ddc78814725011714faf01b1da0d45053d3612cb08095230496ac641c1a2  MROF_ACTUAL_STATE_INVENTORY.md
```

Modified (one file, additively — a skip path, an observation hook and a
run-id field):

```
50c1de80b13a1ec6dfc88d037320dcc4337190a9331d84a2c848c4afae4bf257  mrofyt_runner.py (supersedes 99c9b277… — truncated/corrupt streams skipped whole; earlier: retroactive disconnect-gap correction. See REVIEW_PACKAGE_MANIFEST_v12.md)
```

Archived source directive:

```
55d598a3c2e5453b9c47675f76932455dca8689084fddfd4535e5b4907def942  ../../docs/prompts/MROF_ONE_COMPLETE_CLAUDE_PROMPT_1.md
```

Delivered package (88 files, repo layout preserved so every suite runs
from inside it unchanged):

```
ae2569205ef0deba01e65415e00f53c578f60a78be5e592cbb0621f609b67558  MROF_V1_Engine_v01_6_7.zip (supersedes 3d34a1cb… — instant --dry-run; earlier: adds mrofyt_recover.py; earlier: pilot 1.2 validation blind + bootstrap intervals, auditor churn-after-BOOK_READY rule; earlier: truncated/corrupt-stream guard and the wave-two registration; earlier: pilot 1.1, recorder BOOK_READY repair, depth-completeness guard, retroactive runner correction. This file ships inside the zip it names, so the in-zip copy records the preceding zip hash by construction; hash the delivered artifact against the value here, not against its own embedded copy.)
```

```
cd analysis/mrofyt && for f in tests_*.py; do python3 "$f" | tail -1; done
# run from inside the unzipped package: 437/437, identical to the repo
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
| `tests_mles_v12.py` | 48/48 |
| `tests_mrofyt.py` | 59/59 |
| `tests_mrofyt_pilot.py` | 43/43 |
| `tests_mrofyt_runner.py` | 21/21 |
| `tests_mrofyt_v01_1.py` | 56/56 |
| `tests_mrofyt_v01_2.py` | 31/31 |
| `tests_mrofyt_v01_3.py` | 32/32 |
| `tests_mrofyt_v01_4.py` | 25/25 |
| `tests_mrofyt_v01_5.py` | 36/36 |
| `tests_mrofyt_v01_6.py` | 21/21 |
| `tests_mrofyt_v01_7.py` | 15/15 |
| `tests_mrofyt_recover.py` | 21/21 |
| **total** | **437/437** |

## Runnable research commands

```
python3 mles_v12_audit.py  "<capture folder>"                      # integrity
python3 mrofyt_runner.py   "<capture folder>" --out ledger.json     # outcome-blind
python3 mrofyt_pilot.py    "<capture folder>" --out pilot.json      # §8A diagnostic
python3 mrofyt_recover.py  "<capture folder>" --dry-run             # orphaned runs (instant)
python3 mrofyt_recover.py  "<capture folder>" --repair              # rebuild manifests
```

All three stream at flat memory. `mrofyt_runner.py --outcomes` and
`mrofyt_exits_v017.research_driver()` both raise `STATE-C LOCKED`.

## Read-only no-order proof

```
grep -nE "SubmitOrder|ChangeOrder|CancelOrder|EnterLong|EnterShort|ExitLong|ExitShort" \
     mrofyt_swings_v016.py mrofyt_engine_v016.py mrofyt_exits_v017.py \
     mrofyt_pilot.py mrofyt_recover.py
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
1f264e3b54646c5d474107ed38c25072bed7fd95865bad2a669c00a8dfdb9a6f  mles_v12_audit.py
3d8812b9d286b754bdd01050f4714c3dea1de13c5d59e27a5274903fc180c405  mles_v12_harness.cs
665b0a06d3079c23fd55691f9e361e64573d62ee434f1d277ac5896b94da56fa  tests_mles_v12.py
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

5. **Runner: a truncated or corrupt stream no longer kills the pass.**
   Two files copied while the recorder was writing ended mid-row and
   would have crashed a multi-hour run with no ledger written. The
   runner now checks each file's size against its manifest before
   ingest (skip whole as `STREAM_SIZE_MISMATCH`) and catches in-stream
   corruption as `CORRUPT_STREAM`, resetting run state so nothing
   partial survives. Pinned by `R13`-`R13e`. Never copy the capture
   folder while recording.

6. **Pilot 1.2: the validation blind, and the interval the kill criterion
   needs.** Registering wave two created a hole: the weekly wave-one
   pilot would have read markouts on -- and labelled `EXPOSED_PILOT_DEV`
   -- the very sessions the registration declares untouched, and
   `W2-A4r` is A4 as it ran. The pilot now withholds every markout for
   sessions `>= BLIND_FROM = 20260921` by default (events are counted so
   accrual stays visible), labels them `VALIDATION_BLIND_MARKOUTS_WITHHELD`,
   and unblinds only on an explicit, loud, permanent `--blind-from none`.
   Exposure is monotone: blind may become exposed, never the reverse.
   Also added: a seeded percentile-bootstrap 95% interval on every
   markout population (what §7's "interval includes zero" reads; none
   below five events), and the skip-reason and book-integrity counters
   in the report and summary. Pinned by `P11`-`P11k`; `P11k` binds the
   date and label to the registration text.
7. **Auditor: depth completeness is asserted on churn after `BOOK_READY`.**
   A 228-row restart stub still tripped the first floor because ~60 of
   its rows were the book being built, when only ADDs can occur. Rows
   are now counted after the run's first `BOOK_READY`; a run that never
   reached it built no book and can support no completeness claim.
   Pinned by `T32c`/`T32d`.

8. **`mrofyt_recover.py`: manifest reconstruction for runs killed before
   finalizing.** An ungraceful termination (power loss, forced reboot)
   stops the recorder before its finalizer writes the manifest. The CSVs
   survive, often complete, but the manifest IS the authoritative
   entrypoint for both the auditor and the runner — so the data is
   invisible to every downstream tool. The first fourteen-session
   capture had one such run on **every day of a week**.

   The tool rebuilds a manifest from the rows. Three refusals are built
   in, and they are the point of it:

   * **Originals are never modified.** A damaged stream is rewritten as
     a new `_RECOVERED.csv`; the damaged file stays exactly as it is.
   * **The recorder's self-reported integrity counters are never
     invented.** `gaps`, `duplicates`, `droppedRows` and the rest are
     the recorder's own account of what it saw; nothing in the rows can
     reveal them. Writing `0` would assert "no rows were ever dropped",
     the one claim that cannot be made, so they are **omitted**.
   * **A reconstructed manifest cannot validate its own file.** Its
     hashes, counts and sequence bounds are computed from that file and
     match by construction. The auditor now says so —
     `RECONSTRUCTED_RUN_NOT_SELF_VERIFYING` — instead of either a pile
     of `MISSING_COUNTER` noise or an unearned clean pass.

   A damaged run is truncated to one **common** eventSeq across all four
   streams, constrained only by the damaged ones: rows beyond a cut-off
   stream describe a world it can no longer account for, and merged they
   would advance quotes past the last depth update and freeze the book.
   An undamaged run is not cut at all — its streams legitimately end at
   different sequences. Pinned by `V1`–`V6` (18 tests), including that
   the recovered run becomes ingestible, that originals are unchanged by
   hash, and that a run missing a whole stream is refused rather than
   papered over.

   `--dry-run` probes only each file's header and last 64 KB, never the
   middle, so answering "what is recoverable here?" costs the same on a
   6 GB depth file as on a small one and reports total recoverable GB
   plus a per-stream verdict. The first implementation scanned every row
   even for a dry run, which made that question a 30-minute operation on
   a real capture folder. `V7`-`V7c` pin the cheapness by counting bytes
   actually read.
