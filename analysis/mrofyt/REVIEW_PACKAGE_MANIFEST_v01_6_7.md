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
51c2996ffcd15faeca7670864cecb51de26d9741c2903abcd2fe572af43ade80  mrofyt_pilot.py (MROF-YT-PILOT-1.2; supersedes b955ea9d… — an unreadable or empty capture STOPS the pilot before anything is written, so no report and no exposure label from a pass that did not complete; io-error skip reason reported; Amendment 11. Earlier 3bd2b115…: validation blind (BLIND_FROM=20260921, markouts withheld, monotone exposure ledger), seeded bootstrap 95% intervals, skip reasons + book-integrity counters; 1.1 a6504d0f…: event de-duplication and the 300/600/1800 s horizons)
3f118e151d4634a177a148df9f26dc45dc5e94037bbe9f39b0796d205a1d4d9e  tests_mrofyt_pilot.py (45 tests; supersedes d174d26a… — P13 the level snapshot is kept only for non-blind windows; earlier a9bacd64… → P12: a stopped pass leaves the exposure ledger byte-identical)
6af137d68f1feb4f39206056534952712fe9468cc4818f0a409a26cb726692fa  MROF_YT_WAVE2_REGISTRATION.md (DRAFT — pending operator sign-off; supersedes 4e398285… — §11 implementation record and two implementation-precision notes in §4.1/§4.2, no hypothesis parameter changed; earlier: §8.1 interim-monitoring rule; re-hash on sign-off)
241034220e70c661c8c5463c425c0c1b06a7b91181b93c39ce55f160b6250fd8  mrofyt_wave2.py (MROF-YT-WAVE2-1.0; supersedes 18ba3b83… — an unreadable or empty capture folder STOPS the pass with no report instead of printing zero fires on zero sessions, Amendment 11. The registration as running code: W2-A1, W2-A4r, W2-A4f, W2-A4-OPEN, W2-A4r-z15, W2-A4r-HC, arm B, arm C placebo; subclass of the pilot runner via the runner's observation hooks; wave one untouched; §4.3 CAUSAL_SWING declared not-in-this-version)
50158d03c0cbde186b2e1fd31c16fc2b8776d29bce6e3374c29ff1bc4324804f  tests_mrofyt_wave2.py (29 tests; supersedes fbeb2623… — W8)
6b0eb7ea4a9bc5deb48eec7e461b03c36d509defeb9a28023b104b489f929538  MROF_YT_PILOT_DIAGNOSTIC_FINDINGS.md (supersedes 4624b199… — Amendment 2: the validation blind; Amendment 1 supersedes 8ab588fa…)
3bed26e09a3f702b9d4340ce4e0e01872afea4b7a19782a5a32c4b7a30afc44e  mrofyt_recover.py (MROF-YT-RECOVER-1.4; supersedes bc2d60d5… — every read is memory-bounded (a zero-filled file with no line break, what a drive drop leaves, no longer pulls its whole size into memory: MAX_LINE_BYTES), and one unreadable file (the first real 1.3 dry run died on OSError 22) is named with its Windows error and set aside as SKIPPED_UNREADABLE_FILE, never repaired, and the pass carries on; 1.3 (bc2d60d5…) supersedes dcd01f4a… — a repair must not fill the drive the recorder writes to: the dry run states what --repair would write against the free space, a pass that would leave under 40 GB free is refused before writing anything, and each run is re-checked; Amendment 14. 1.2 (dcd01f4a…) supersedes 0e73abfb… — asks Windows directly whether the recorder still holds a run (file-sharing check), the only sign that holds over a weekend; anything held or unanswerable is refused; Amendment 11. 1.1 (0e73abfb…): indirect live-run signs; 1.0 (a8b637a5…): manifest reconstruction, instant --dry-run)
1a91fed7e64df6542cd90eadfac5f623ef03ae3a2b2e05efb53577fbe114cc13  tests_mrofyt_recover.py (38 tests; supersedes 7960bb10… — V11 the unreadable file, V12–V12b bounded reads of zero-filled files (peak memory asserted); earlier 04f7d842… → V10–V10c the free-space guard, each test stating the drive it simulates; earlier ed72a3fd… → V9–V9g: the direct check with an injected answer, the closing-window veto, the recorder-source premise, the atomic manifest write)
f61a1f23fe31a479d04d4fd98cd59c66a9b018e0ef6c5f52459e2bea4094f84c  MROF_ACTUAL_STATE_INVENTORY.md (supersedes 50d0ddc7… — row 7 records the W2-A4f wiring, row 20 the wave-two module)
```

God's Eye View — the read-only dashboard (`analysis/godseye/`, Amendment 12):

```
e79dd336adfea628846db28c3d4019ea0b4f2fad72aa00d6fac5cc1e3da78bf0  ../godseye/godseye_registry.py (MROF-GODSEYE-REGISTRY-1.0; supersedes f7c4d222… — resolve() judges each wave-two family exactly as mrofyt_wave2 does (G11d), and DEMOS: one scripted mechanism scenario per hypothesis with a counter-example, every one run through the frozen detector by G11–G11c; Amendment 13. Earlier: hypotheses, levels, context and the discrepancy record as the frozen code has them; G1b reproduces every frozen detector from its written conditions)
71126ff55621e752576179e7e6f937b0410dc76eedb5bde56a4487507ca82aaf  ../godseye/godseye_policy.py (MROF-GODSEYE-POLICY-1.0: EXPOSED / BLIND / PROTECTED_UNLISTED / UNKNOWN, fail closed; event-level field list; strip-and-scan boundary; outcome lock read only)
bb5ce978700145faebd3d211ebbe4232c55e5081661363eaf9255b9827a3a328  ../godseye/godseye_replay.py (bounded raw reads: byte-offset search, 250,000-row cap that says truncated, book rebuilt with the runner's frozen KLevelBook, depth never invented)
dc4d9793089f4830043af11bab4570e242e45fe93b5146892b0536eddc57809e  ../godseye/godseye_export.py (MROF-GODSEYE-EXPORT-1.0; supersedes 7fb480f5… — a run set aside by recover 1.4 as SKIPPED_UNREADABLE_FILE carries the file name and the Windows error into the health and session sections; earlier 60e463e3… → the replay windows file is split once per pilot run into one piece per (session, instrument) of inspectable sessions, so a routine export reads a small index instead of ~100 MB; a session whose only audit flag is RECONSTRUCTED_RUN_NOT_SELF_VERIFYING counts as complete, labelled; Amendment 14. Earlier 16aa4c57… → progress section (complete-session rule, runbook milestones, checkpoint clock, accrual counts), disk runway, next scheduled market change, resolved conditions for wave-two families; Amendment 13. Earlier: reports + bounded capture tail -> one sanitized snapshot, atomic, refuses to write on any event-level key outside the exposed section, refuses an out_dir inside the capture folder)
8b61f9abbf5b7db3aae302f086038f02d8b57713822d4341a86993a4824ffa9c  ../godseye/godseye_server.py (the evidence endpoint matches the approach id as well as the time (two levels approached at one instant no longer swap evidence); MROF-GODSEYE-SERVER-1.0; supersedes 775e412f… — serves replay windows one (session, instrument) piece at a time, at most four held; re-reads the exposure ledger when it changes; --open opens the browser once listening; --refresh N re-runs the export every N s as a separate below-normal-priority process (the launchers use 300); Amendment 14. Earlier: stdlib HTTP on 127.0.0.1; policy re-checked on every replay request; stale after 15 min; last good snapshot kept)
b0aaf0743b2f87c3661bfeaa9fc02caeb24b6c81da6dafd650e97147f9588de1  ../godseye/godseye_demo.py (MROF-GODSEYE-DEMO-1.0: labelled synthetic capture + reports through library entry points only; its own ledger, inside the demo folder)
041eaffdc109a5a445c6a1d854264e742b77db1305761e04f4e6f6d7c8112db7  ../godseye/tests_godseye.py (45 tests, G1–G14b + G8f; supersedes a264c7de… — G14 the unreadable-file verdict reaches the page, alerted, capture untouched; G14b shared-gap alerts capped; earlier edc2d6bf… → G12e reconstructed-only sessions complete and labelled, G13–G13d the replay split, the server's bounded pieces and ledger re-read, the launcher, the refresher; earlier 3d2d5111… → G11–G11d theatre scripts vs the frozen code, G12–G12d study progress, clock, runway)
23517ae39a7fbb6a7cb4a271c858057e2c02033105fefaa9f9beb870179ee39a  ../godseye/static/app.js (supersedes a19771cc… — alerts name a run the drive cannot read and cap shared-gap warnings at the five largest plus one summary line; the orphan table shows the unreadable file; replay level labels drawn over the candles on a dark box; earlier a19771cc… → the page sends the approach id with every evidence request; earlier 44bfe9ea… → the progress rail names sessions relying on reconstructed manifests; earlier 0fd3a368… → progress rail, schedule-aware alerts, runway, watchdog notifications, funnel bars)
c0d29207c0b283751bd38e5b4c614b3f4e86025c4b0c09ae3e9f40ac8a0a27e3  ../godseye/static/theatre.js (the Mechanism theatre view and keyboard shortcuts; Amendment 13)
b65447cb56b2ef6e8067095adf094413f4ffc5094c450771b530577021fd7c69  ../godseye/static/index.html
c3dd56058931c0f773d15648e5de1ce659c722d390d81a99ff6c87063c3e44a3  ../godseye/static/style.css
57ae9519a2ba7eb2b84e7115468d0b1c4bb9b34838534aedde2c796311074fb6  ../godseye/GODS_EYE_README.md (architecture, permission model, setup, the four views, blind enforcement, discrepancy record, adapters, verification, blockers, user guide)
8169159cbf3444a82bc59538d6053fc4c693606c7d4c6f7f73e811f42fb635f6  ../godseye/launch_godseye.bat (supersedes a3cf2105… — the server opens the browser once listening instead of racing it; reviewed, not executed: no Windows here)
6d52566b3cd6dcc310517733fc94b4cdc355beecd10fe3ff7260082040420b36  ../godseye/export_godseye.bat
8799ff3dc698a7f2a186be1dc18c3c35e1697bce554f350b9f77f74ca17fd21e  ../godseye/godseye.config.example.json
ec8366a0e493efe33963a227bda8084e9f5a1e7123de66687b6881387d511c00  ../godseye/pinokio/pinokio.js (optional Pinokio launcher, dashboard only; NOT exercised here — no Pinokio)
31526b3cee7dfe325758e4eb321134897a1f52232cd4094d73581e58df480b3f  ../godseye/pinokio/install.js
e89a18767df0469c2c15262f90937e19a9577f453b9070cfc63064829fa118c1  ../godseye/pinokio/start.js
451a3544e1a854195bdb62b247186cfc15eaf70aedc49a9d0b270f63f537eb83  ../godseye/pinokio/stop.js
8d1b123206885250b9a9b21951b58e37ed318fd0d2f93656c91926135b097e16  ../godseye/pinokio/export.js
```

Modified (one file, additively — a skip path, observation hooks and a
run-id field):

```
10485b6655e65a5d1b91f40e2023ba8bbed8b604dd526a37ab014433dd4e1c40  mrofyt_runner.py (supersedes c48dfe9e… — a capture folder that cannot be read, or stops answering mid-pass, STOPS the pass with no ledger; a read error on one run while the folder answers is that run's IO_ERROR skip; a run carrying both the recorder's manifest and a reconstructed one is ingested once; Amendment 11. Earlier c48dfe9e…: two no-op observation hooks for wave two; 99c9b277…: truncated/corrupt streams skipped whole; earlier: retroactive disconnect-gap correction. See REVIEW_PACKAGE_MANIFEST_v12.md)
8ea5c6be8295ccfb41e4ca24345892067e0376722157d470269d4ad526e57ac0  tests_mrofyt_runner.py (27 tests; supersedes 51e08e10… — R15–R15d)
6b52264498428c347a2a57feeaa2de37f65028181e27c5413f115ca329338ba6  mles_v12_audit.py (supersedes 003f03b8… — `--out FILE` writes the audit report as JSON for the dashboard, Amendment 12; no rule changed. 003f03b8…: a run still being recorded is OPEN, not failed; damaged originals kept beside recovered copies are KEPT, not failed; unreadable capture stops the audit; per-build disconnect evidence says whether the 1.2.2 repair was exercised or merely not contradicted; Amendment 11. See REVIEW_PACKAGE_MANIFEST_v12.md)
1c9b8973135025c5aca4d5803ac79e9df2cb29107859641f62c3088846aa03cc  tests_mles_v12.py (54 tests; supersedes 665b0a06… — T30c, T34–T34c, T35–T35b; T30's orphan fixture is now aged, because a file written a second ago is what a live run looks like)
cdf6d14cfd324225340795932eac96c830e4eb936a3d7dee686141fd9e6fd534  NT8_RECORDING_RUNBOOK.md (supersedes 1c47b9c9… — §8 names the dashboard and the `--out` files it reads; earlier: §8 lists the wave-two command)
```

The pilot line above (51c2996f…) is superseded in Amendment 12 by:

```
2b6efce22c51d84b12fb264a837aad0fb46e6f6a23f1df46d1bc53d7807aa6a6  mrofyt_pilot.py (MROF-YT-PILOT-1.2; supersedes f81c6b14… — a window keeps the level snapshot only when its session is not blind (the validation sessions grow weekly and are never written); Amendment 14. f81c6b14… supersedes 51c2996f… — `--windows-out FILE` writes the decision windows of EXPOSED sessions only (MROF-PILOT-WINDOWS-1) for the dashboard's replay, and each window record carries the approach id, side and the runner's levels; no detector, threshold, level, window, baseline or feature definition touched — P10d re-pins the frozen signal hash; Amendment 12)
```

Archived source directives:

```
55d598a3c2e5453b9c47675f76932455dca8689084fddfd4535e5b4907def942  ../../docs/prompts/MROF_ONE_COMPLETE_CLAUDE_PROMPT_1.md
b2a0122b40e6ef140a1cb6fe7011068bfa3cc52039a75b19da54c9fc1e7ae389  ../../docs/prompts/MROF_GODS_EYE_VIEW_CLAUDE_PROMPT_PINOKIO.md (the dashboard directive, Amendment 12; archived from the upload as it was read — 166 lines — so the hash is of this archived copy)
```

Delivered package (111 files, repo layout preserved so every suite runs
from inside it unchanged):

```
c5f652c501169adee930dd5dda4730a6d1bdd2f5532092be46a5a703663019f5  MROF_V1_Engine_v01_6_7.zip (supersedes 416beef6… — unreadable-file verdict on the page, capped shared-gap alerts, legible replay level labels; earlier 694c6367… — replay evidence matches the approach id; earlier 2fa33aed… — recover 1.4 bounded reads; earlier f930879f… — recover 1.4 unreadable-file guard; earlier f930879f… — Amendment 14: replay split, recover 1.3 free-space guard, reconstructed-session completeness, pilot level trim, launcher open/refresh; earlier 4e67cd09… — God's Eye 1.1: the Mechanism theatre, study progress, runway, Amendment 13; earlier 108325dd…: adds analysis/godseye/ (19 files) and the archived dashboard directive, Amendment 12; earlier 15852c89…: recover 1.2 asks Windows, stop-never-report guards, auditor OPEN/KEPT/repair evidence; earlier 5b8e8ceb…: recover 1.1 refuses live runs; earlier ae256920…: wave two as code (mrofyt_wave2.py + suite), runner hooks, 90 files; earlier 3d34a1cb…: instant --dry-run; earlier: adds mrofyt_recover.py; earlier: pilot 1.2 validation blind + bootstrap intervals, auditor churn-after-BOOK_READY rule; earlier: truncated/corrupt-stream guard and the wave-two registration; earlier: pilot 1.1, recorder BOOK_READY repair, depth-completeness guard, retroactive runner correction. This file ships inside the zip it names, so the in-zip copy records the preceding zip hash by construction; hash the delivered artifact against the value here, not against its own embedded copy.)
```

```
cd analysis/mrofyt && for f in tests_*.py; do python3 "$f" | tail -1; done
cd ../godseye && python3 tests_godseye.py | tail -1
# run from inside the unzipped package: 497/497 + 45/45, identical to the repo
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
| `tests_mles_v12.py` | 54/54 |
| `tests_mrofyt.py` | 59/59 |
| `tests_mrofyt_pilot.py` | 45/45 |
| `tests_mrofyt_runner.py` | 27/27 |
| `tests_mrofyt_v01_1.py` | 56/56 |
| `tests_mrofyt_v01_2.py` | 31/31 |
| `tests_mrofyt_v01_3.py` | 32/32 |
| `tests_mrofyt_v01_4.py` | 25/25 |
| `tests_mrofyt_v01_5.py` | 36/36 |
| `tests_mrofyt_v01_6.py` | 21/21 |
| `tests_mrofyt_v01_7.py` | 15/15 |
| `tests_mrofyt_recover.py` | 38/38 |
| `tests_mrofyt_wave2.py` | 29/29 |
| **wave-one/two total** | **497/497** |
| `../godseye/tests_godseye.py` | 45/45 |
| **package total** | **542/542** |

## Runnable research commands

```
python3 mles_v12_audit.py  "<capture folder>"                      # integrity
python3 mrofyt_runner.py   "<capture folder>" --out ledger.json     # outcome-blind
python3 mrofyt_pilot.py    "<capture folder>" --out pilot.json      # §8A diagnostic
python3 mrofyt_recover.py  "<capture folder>" --dry-run             # orphaned runs (instant); runs the recorder holds listed apart
python3 mrofyt_recover.py  "<capture folder>" --repair              # rebuild manifests — safe with NinjaTrader running; do it on a weekend anyway (I/O)
python3 mrofyt_wave2.py    "<capture folder>" --both --out wave2.json  # wave two, real + placebo, blind
```

All of them stream at flat memory. `mrofyt_runner.py --outcomes` and
`mrofyt_exits_v017.research_driver()` both raise `STATE-C LOCKED`.

## Read-only no-order proof

```
grep -nE "SubmitOrder|ChangeOrder|CancelOrder|EnterLong|EnterShort|ExitLong|ExitShort" \
     mrofyt_swings_v016.py mrofyt_engine_v016.py mrofyt_exits_v017.py \
     mrofyt_pilot.py mrofyt_recover.py mrofyt_wave2.py
# -> no matches outside header comments documenting the prohibition
```

Enforced in-suite by `B18` and `C12`, which strip comments before
scanning, and by `W7` for the wave-two module (which additionally
forbids any fill / stop / target / simulate / P&L call).

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

9. **Wave two as running code (2026-09-21).** `mrofyt_wave2.py`
   (MROF-YT-WAVE2-1.0) implements the registration's families, the
   candle-only arm B and the placebo arm C, with the §4.3 CAUSAL_SWING
   comparison declared `not_in_this_version` rather than half-built.
   The registration's §11 records exactly what each family became and
   where implementation had to be more precise than the prose (arm-B
   decision instant, placebo seed rule, the residual model's minimal
   first-wave form). No hypothesis parameter was changed.

   How wave one stays untouched: the module subclasses the pilot runner
   and reads only two new **no-op** observation hooks on the frozen
   runner (`_on_trade_event`, `_on_depth_event`, carrying the full
   adapter event after the frozen handling has run). `R14b` pins that
   the base runner's ledger is unchanged by their presence; `W5c` pins
   that the wave-one ledger the wave-two runner emits — fires, totals,
   feature counters, sessions, baselines, regimes — is byte-identical to
   the pilot's on the same seven synthetic sessions, and that the
   comparison is not vacuous; `W7b` and `P10d` re-pin the frozen signal
   hash.

   What the suite proves and what it does not: `W1`–`W1f` prove each
   wave-two detector IS the frozen one with a single input swapped or
   one threshold parameterised (2,000 random inputs for `W2-A4r == A4`);
   `W4`–`W4e` drive arm B's register → bar close → fire path directly;
   `W6`–`W6c` prove every placebo level sits ≥ 3 radii from every real
   level and that the placebo run is deterministic. The end-to-end run
   is on **synthetic** 33-minute sessions, so it verifies that bars
   close, registrations resolve, baselines mature and the residual
   model reaches a fit — code behaviour only. Zero fires on synthetic
   tape is expected and is not evidence about anything. The first
   real-data run is user-side, on DEV sessions ≤ 20260918, and reads
   nothing from validation sessions: the blind is the pilot's.

10. **`mrofyt_recover.py` 1.1: a run still being written is not an
    orphan (2026-09-21).** The first `--dry-run` on the real capture
    folder found 16 runs without a manifest, 84 GB — and listed the two
    runs being recorded *at that moment* (today's NQ and MNQ, 8.76 and
    7.79 GB, `.partial`, ending mid-flush) under `WOULD_RECONSTRUCT_
    WITH_REPAIR`. They have no manifest because the recorder writes it
    at close, and they end mid-row because a flush was in progress.
    1.0 could not tell that from a crash. Had `--repair` been run, it
    would have pinned a manifest declaring the session complete at
    whatever byte the scan reached, the recorder's own manifest would
    later have contradicted it, and the runner would have ingested a
    truncated day as if it were whole — on a **validation** session.

    1.1 recognises a live run by either of two independent signs and
    refuses it under every flag, re-checking at write time so a direct
    `reconstruct()` call cannot bypass discovery: a stream written
    within `LIVE_MTIME_S = 600 s` (the recorder flushes every 30 s, so
    a live file is never minutes stale), or a session label that is the
    current CME session or later (a recorder alive but idle over a
    weekend goes mtime-stale while its run is still open). Both err
    toward refusing. Such runs are listed as `SKIPPED_LIVE_RUN`, counted
    apart from orphans, and excluded from the recoverable total. Pinned
    by `V8`–`V8d`; `V8c` proves the refusal is per run, so the dead
    orphan beside a live run is still recovered.

    The other fourteen runs on that folder are genuine: seven complete
    sessions (14th–17th, 3–7 GB each) that need only a manifest, and
    seven cut mid-write by the laptop's shutdowns (4th, 8th, 14th, 15th)
    that need `--repair`. Operator rule added to the tool's usage text:
    **run `--repair` only when the recorder is idle** — it rewrites
    every stream of a damaged run as a new file on the drive the
    recorder is writing to.

11. **Recover 1.2: ask Windows, because the indirect signs do not hold
    (2026-09-22).** The second real dry run showed 1.1's live runs were
    caught by the session-label rule alone: the modified-time rule
    never fired, because Windows does not keep a held file's modified
    time current (the operator had seen this in Explorer a week earlier
    — size growing, date not moving). Reading the recorder source then
    showed the label rule would not have held either on the day
    `--repair` is meant to run: the session roll is driven by market
    events (`Process()` rotates when an event's session differs), so
    the run open over a weekend keeps Friday's label; and the
    recorder's idle-loop housekeeping is unreachable (`WorkerLoop`'s
    `while (queue.Count == 0 && accepting) Monitor.Wait(...)` never
    falls through to the `ev == null` branch), so nothing — no flush,
    no heartbeat — is written while the market is closed. A run
    NinjaTrader still held on a Saturday would have passed every 1.1
    sign as dead, been given a reconstructed manifest, and been
    finalized again by the recorder on Sunday: two manifests, one run,
    that stretch of a **validation** session counted twice. 1.1 was not
    used for a repair; 1.2 replaces it before one.

    1.2 asks directly. The recorder opens every stream
    `FileMode.CreateNew, FileAccess.Write, FileShare.Read` and holds it
    for the life of the run (`V9f` pins this in the source), so a
    read-only `CreateFileW(GENERIC_READ, FILE_SHARE_READ)` fails with
    `ERROR_SHARING_VIOLATION` for exactly as long as the recorder holds
    the file. HELD refuses; any other failure refuses too ("a check
    that could not be asked is never read as not held"); FREE still
    yields to a newest row under ten minutes old by the recorder's own
    row clock (a run being closed has released its files but not yet
    written its manifest). Off Windows only the indirect signs exist,
    and they stay in force there. The Windows call itself cannot be
    exercised in this environment; `V9`–`V9d` pin every decision around
    it with an injected answer, and the operator's own dry run is its
    real test: today's runs must be listed as "NinjaTrader still has
    ... open for writing". The reconstructed manifest is now written
    aside and moved into place (`V9g`), so a drive that drops
    mid-repair leaves a `.tmp` every tool ignores.

    The recorder idle-loop finding is a recorder defect (no flush and
    no heartbeat during quiet periods; exposure is the last unflushed
    buffer per stream, a few KB, when the machine dies during a break).
    It is recorded here, not fixed: a recorder change is an F5 the
    operator schedules deliberately, and nothing about it is urgent.

    **The same day, a loose USB cable failed three passes at once.**
    Runner, pilot and wave two all died on `OSError 22` mid-read — and
    the wave-two pass, finding no manifests on the vanished drive,
    printed a clean, well-formatted report of zero fires on zero
    sessions. Read as a result that is "nothing fires". Now: a capture
    folder that cannot be read, holds no manifest for the instruments,
    or stops answering mid-pass raises `CaptureUnavailable` /
    `NoCaptureData`; runner, pilot, wave two and auditor print `STOPPED`
    with the reason, exit 2, and write **nothing** — the pilot's
    exposure ledger stays byte-identical (`P12`), because a pass that
    did not complete labels no session exposed. A read error on ONE run
    while the folder still answers is that run's `IO_ERROR` skip and the
    pass continues (`R15b`, `T34b`). Pinned by `R15`–`R15d`, `T34`–
    `T34c`, `P12`, `W8`.

    Two more closures in the same batch. The runner ingests a run
    **once** when both the recorder's manifest and a reconstructed one
    exist for it, preferring the recorder's and naming the other in the
    ledger (`R15d`) — the double-count above closed a second way. And
    the auditor reports a run still being recorded as `OPEN`, not as
    eight `ORPHAN_PARTIAL` failures plus an instance shortfall (the
    2026-09-21 audit carried ten such lines), using the recovery tool's
    own liveness rule so the two can never disagree (`T30c`); damaged
    originals kept beside their recovered copies are `KEPT`, not
    orphans, so the post-repair audit reads honestly.

    **Repair evidence, because the operator caught a confounder.** "Six
    spurious `BOOK_READY` on builds 1.2.0/1.2.1, zero on 1.2.2" was
    presented as proof the recorder repair works. It is not: old
    sessions *are* the old-build sessions, so build is confounded with
    the calendar. The repair acts only after a feed disconnect, and the
    auditor now counts that trigger per build and prints a verdict:
    `NOT_EXERCISED` (no repaired-build run has had a disconnect — the
    repair is untested, however clean the runs look),
    `EXERCISED_AND_HELD`, or `FAILED`. Runs whose rows could not be read
    are counted, never assumed clean. `T35b` is the end-to-end case on
    the real recorder code: the mono lifecycle harness's
    disconnect/reconnect run, built from `src/`, reads as exercised and
    held. Whether the operator's 1.2.2 sessions have had a disconnect
    is what the next real audit will say.

    A caveat made explicit while touching the skip paths: `CORRUPT_
    STREAM` and `IO_ERROR` reset the run's book and report the run
    skipped, but windows, fires and baseline observations produced
    *before* the failing row are not rolled back — they came from valid
    rows. `R13c` ("a partly read run leaves nothing behind") passes
    because its fixture cannot produce a window before the bad row, not
    because anything is undone. No real run has taken either path yet:
    the damaged files on the capture are caught by the pre-flight size
    check, before any row is read.

12. **God's Eye View: a read-only dashboard over the project
    (2026-09-22).** `analysis/godseye/` — registry, policy, bounded
    replay reader, exporter, local server, synthetic demo, 28 tests,
    Windows launchers, an optional Pinokio launcher and
    `GODS_EYE_README.md`. Built from a second directive, supplied as an
    upload and archived under `docs/prompts/` (hash below), after the
    operator said "stop" on the previous batch — that batch was committed
    as its own revertible commit (d650dac) before this one began.

    What it is: four views — recording health (LIVE / IDLE / STALE /
    DISCONNECTED / UNAVAILABLE / UNKNOWN, decided by the recovery tool's
    own liveness rule so the two can never disagree; an unreadable folder
    is UNAVAILABLE with its error, never zero; shared NQ+MNQ gaps shown
    beside the pair overlap because a 1.000 overlap cannot see them),
    hypothesis readiness (registry-driven statuses with reasons, counts
    quoted from the released reports, nothing ranked), data quality and
    provenance (DST-aware ET session timeline, UTC in the inspector,
    recorder / reconstructed / orphan / open / failed distinguished, gaps
    shown as gaps), and a replay of exposed sessions (session →
    instrument → approach → 10-s window → the frozen inputs, book rebuilt
    with the runner's own `KLevelBook`, a level never seen is `unknown`).

    How the blind holds, in the backend: the policy classifies every
    session EXPOSED (ledger label), BLIND (≥ 20260921 or the blind
    label), PROTECTED_UNLISTED (before the hold-out but not in the
    ledger) or UNKNOWN (missing/unreadable ledger, mixed or absent
    label), and fails closed; the exporter strips event-level fields from
    every record of a non-exposed session and then scans the whole
    document outside its `exposed` section, refusing to write on any hit;
    the server re-runs the policy on every replay request (403). December
    changes nothing by itself; the outcome-unlock file is only ever
    tested for existence. `G2`, `G2b`, `G3`, `G3b`, `G8`, `G8e`, `G10`.

    What it costs the recorder laptop: a separate process; `scandir`,
    manifests and the last 64 KB of open runs; no row scan on load; the
    demo export read 8.8 MB from 32 files in 0.43 s at 22.75 MB peak
    heap; the server sits at ~45 MB resident; a replay window is one
    bounded seek per stream, capped at 250,000 rows and saying so when
    capped (`G9`). It writes only into its own `out_dir`, refuses an
    `out_dir` inside the capture folder (`G4b`), and the capture folder's
    tree hash is identical after export, demo build and tests (`G3d`).

    Two additive flags on predecessors so nothing is recomputed:
    `mles_v12_audit.py --out` and `mrofyt_pilot.py --windows-out`
    (exposed sessions only). No detector, threshold, level, window,
    baseline or feature definition changed; `P10d` and `W7b` re-pin the
    frozen signal hash, and `G1b` shows the registry's written conditions
    reproduce every frozen detector on 20,000 random inputs.

    Discrepancies found by inspection and recorded, not changed (the
    README's §6 and the registry's `DISCREPANCIES`, pinned by `G1c`): A2
    and A6 are continuations, not fades; A5 resumes with the trend and
    has four of five inputs passed as `None`; A6 (09:30–09:45 ET, six
    open-type levels, continuation) is not W2-A4-OPEN (09:30–10:30 ET,
    three levels, reversal); z-scores need 5 prior sessions per bucket
    while the residual model needs 20 prior observations; the swing
    module exists but is not a level provider and has never run on real
    tape; the Asia labels have no code; the repository ledger exposes
    20260901–20260905 only, so a pre-hold-out date not in the ledger is
    protected here; the fourteen level ids match `ACTIVE_LEVEL_IDS`.

    Not verified here, said plainly: Pinokio (no Pinokio in this
    environment; scripts follow the documented API; `launch_godseye.bat`
    is the fallback), the `.bat` files and the Windows file-sharing
    liveness check (no Windows here — the health card names which rule
    decided liveness), and every number on real data (all verification
    is on the labelled synthetic demo). The browser render was verified
    with headless Chromium 141 on all four views.

13. **God's Eye 1.1: the Mechanism theatre, and where the study stands
    (2026-09-23).** The operator asked for a demonstration of how each
    hypothesis should work. Rather than prose, each of the fifteen
    registry entries now carries a scripted five-beat scenario
    (`godseye_registry.DEMOS`): a synthetic tape in ticks from the level,
    resting size at the level, executions, and the inputs the frozen rule
    reads appearing beat by beat; the condition checklist lights up as
    they arrive and the verdict quotes the direction rule. Each script has
    a counter-example that changes ONE thing and does not fire. None of
    it is data and every page says so. What makes it more than a story:
    `G11` runs the frozen detector itself (`mrofyt_signals.DETECTORS`,
    `mrofyt_wave2.w2_*`) on every script's final beat and asserts it fires
    in the named direction; `G11b` asserts every counter-example does not
    fire in the frozen code and fails exactly one resolved clause; `G11c`
    runs `arm_b1`/`arm_b2` on the candle arms' bars. The registry gained
    `resolve()`, which derives each wave-two family's conditions from its
    base with the registration's one change (input swapped, forced None,
    required, threshold, gate) — `G11d` shows it agrees with `mrofyt_wave2`
    on 6,000 random inputs for all six derived families — so the theatre,
    the inspector and the replay evidence are judged by one evaluator. A
    thought-experiment panel puts each input on a slider and re-evaluates
    the written conditions; it calls no frozen function and touches no
    data.

    On Recording health: a "where the study stands" rail — complete
    sessions (window passed, both instruments ≥ 95%, no shared gap over 5
    min, every manifest run audit-clean; `G12`) against the runbook's 20
    and 60 milestones, the registration's 2026-12-01 checkpoint with
    trading days left (`G12c`), NQ signal-source events per family against
    the 30-event minimum with a linear accrual projection that is a count
    and never a result, families in registry order; disk runway in
    session-days from the median finalized bytes per session-day (`G12d`);
    the next scheduled market change; alerts that call "not recording"
    critical only while the market is scheduled open and say by when
    recording must resume; an opt-in local browser notification when
    recording stops during market hours. Keyboard shortcuts throughout.
    No frozen file changed; the package suites stay 490/490; the dashboard
    suite is 36/36.

14. **Before the first real deployment: four things the real data would
    have hit (2026-09-23).** Found while writing the operator's steps
    against the capture's real numbers, not the demo's.

    *The replay file.* The first real pilot produced 44,628 windows from
    ~10 sessions; the pilot's `--windows-out` file is ~1.5 KB per window,
    so the September DEV sessions make ~100 MB. God's Eye 1.0 parsed the
    whole file on every export (284 MB peak each time, every 5 minutes if
    scheduled) and the server held all of it (183 MB) -- on the laptop
    that is recording. It is now split once per pilot run (or ledger
    change) into one piece per (session, instrument) of inspectable
    sessions, in `out_dir`; a routine export reads the ~1.5 MB index
    (0.06 s, 5.7 MB); the server holds at most four pieces (~30 MB).
    Measured on a synthetic 63,000-window, 100 MB file. `G13`-`G13b`.
    The server also re-reads the exposure ledger when it changes, so a
    weekly pilot run needs no restart (still fail-closed).

    *The repair's size.* `reconstruct()` copies every `.partial` stream
    in full as `_RECOVERED.csv` (the original is never renamed), not only
    damaged ones, and every orphan on the real folder is `.partial`: a
    `--repair` writes up to the orphans' full size (~67 GB at the last
    dry run) onto the drive the recorder resumes writing to on Sunday
    18:00 ET. Nothing checked the space. Recover 1.3 prints what
    `--repair` would write against the free space in every dry run,
    refuses a pass that would leave under 40 GB free (about three
    session-days) before writing anything, and re-checks per run.
    `V10`-`V10c`; the suite now states the drive each test simulates,
    because this sandbox itself has only ~30 GB free.

    *Complete sessions after the repair.* The auditor flags every
    reconstructed run `RECONSTRUCTED_RUN_NOT_SELF_VERIFYING` (correctly:
    such a manifest cannot verify its own file). The progress rail read
    any flag as "not complete", so after the repair the repaired DEV
    sessions would never have counted toward the 20/60 milestones even
    though the runner ingests them. A session whose only flag is that
    one now counts and is labelled "relying on N reconstructed
    manifest(s)"; any other flag still excludes it. `G12e`.

    *Memory the pilot does not need.* The pilot kept each window's level
    snapshot for blind sessions too, though `write_windows` never writes
    them; validation sessions grow every week to December. Now kept only
    for non-blind windows (`P13`); no detector, threshold, level, window
    or feature definition touched.

    Also: the Windows launcher could open the browser before the server
    listened ("site can't be reached"); the server now opens it once
    bound (`--open`, `G13c`). And the snapshot went stale 15 minutes
    after launch unless the operator set up Task Scheduler, which would
    have made the new watchdog report "stale while the market is open"
    all day; the server now re-runs the export every 5 minutes while it
    is open, as a separate below-normal-priority process, one at a time
    (`--refresh 300` in both launchers, `G13d`).

    *Addendum, the same day.* The operator's first real dry run with 1.3
    died with `OSError: [Errno 22] Invalid argument` reading the first
    line of one leftover file, while the recorder was demonstrably fine
    (the live `.partial` files were growing). Python reports many
    Windows disk errors as errno 22; the likely cause is a file cut off
    when the drive dropped on 2026-09-22. Recover 1.4 catches a read
    error on ONE file, names it with its Windows error code, sets that
    run aside as `SKIPPED_UNREADABLE_FILE` (never repaired, nothing
    written for it), and carries on; a vanished drive still stops the
    pass. The dashboard's own tail reader already survived this. `V11`.

    *Second look, the same day.* Reading the same failure again: a file
    cut off when a drive drops is often zero-filled, with no line break
    at all, and every reader here iterated lines -- `readline()` on such
    a file pulls the whole multi-GB file into memory before it can fail
    (on the recording laptop). Now every read is bounded: the header is
    read from the first 1 MB, rows come from a chunked reader that stops
    at any line over 1 MB and names the stretch, and the repair copy
    uses the same reader. `V12` asserts peak memory under 8 MB on a
    40 MB zero-filled file; `V12b` that a repair keeps every good row
    before such a stretch and writes no zero byte.

    *Replay evidence, found in a screenshot.* Two levels approached at
    the same instant share a window end time; the evidence endpoint
    matched on time only and returned the first, so the panel could
    explain a different level than the header named. It now matches the
    approach id too, and the page sends it. `G8f` (the demo has such
    twins).

    *Review pass, the same day.* Three things the dashboard did not yet
    say or show well. (1) The two files the 9/22 drive drop left
    unreadable are a drive fact the operator should see without running
    the recovery tool: the exporter now carries recover 1.4's
    `SKIPPED_UNREADABLE_FILE` verdict, with the file name and the
    Windows error, into the health section and the session timeline;
    the page raises a warn alert for it ("check the drive / cable") and
    the orphan table shows it; nothing touches the file (`G14`, the
    capture folder's tree hash is identical before and after). (2) A
    long history of overnight restarts produced one shared-gap alert
    per session and buried the ones that matter: the five largest are
    listed, then one line for the rest (`G14b`). (3) Replay level labels
    were drawn under the candles and a candle body could swallow them;
    they are now drawn last, on a dark box, still pushed apart when two
    levels sit within a text height of each other. Rendered in headless
    Chromium: no page errors, no console errors.
