# MROF_ACTUAL_STATE_INVENTORY.md — §2 audited actual state

Produced against the repository as it actually is, not as the directive
assumes it might be. Every "existing code" entry was opened and read;
every test count is real output.

Directive archived at `docs/prompts/MROF_ONE_COMPLETE_CLAUDE_PROMPT_1.md`

```
55d598a3c2e5453b9c47675f76932455dca8689084fddfd4535e5b4907def942   (186,994 bytes, 1,726 lines)
```

## Embedded appendix hashes — verification result

| Appendix | Stated bytes | Stated SHA-256 | Result |
| --- | --- | --- | --- |
| A `MROF_YT_OF01_FINAL_SOURCE_PROMPT(3).md` | 117,065 | `74ff9a99…eecb91b` | **VERIFIED** — byte-identical to `analysis/mrofyt/MROF_YT_OF01_FINAL_SOURCE_PROMPT.md` (and to the uploaded `MROF_YOUTUBE_ORDERFLOW_WAVE_012_2.md`) |
| B `MROF_YT_OF01_6_CAUSAL_SWING_SUCCESSOR_PROMPT.md` | 19,237 | `93738aad…f45901a2` | **NOT VERIFIABLE** — the standalone source file was not supplied; only the embedded text exists |
| C `MROF_LIQUIDITY_AND_TAPE_EXIT_CLAUDE_PROMPT.md` | 12,696 | `262f7e49…51c127c03` | **NOT VERIFIABLE** — same reason |

Appendix B and C were implemented from the embedded text. Re-embedding
cannot reproduce a source file's byte hash, so those two hashes are
recorded as unverified rather than claimed as checked. Supplying the two
standalone `.md` files would close this.

Additional pins inside Appendix B, all **VERIFIED** unmodified:

```
b753a09cc077267a935df37f9b531f2179d920b8f76dc6ee5788628c264f7194  MROF_YT_OF01_5_SUCCESSOR_FREEZE.md
e3da36cd63a18a22935124e852ce8f8b785e96df136d98944f7e88654b1c6847  mrofyt_engine_v015.py
```

## Successor identifier selection

Used: `OF01_1 … OF01_5`, `v01_1 … v01_5`. Next unused was **v01.6**,
assigned to the Appendix B swing wave. Appendix C explicitly warns
against assuming v01.6 exists merely because a swing prompt does — it
does now, so the exit wave took **v01.7**.

## Inventory

Legend — Eng: engineering status. Data: whether genuine data exists to
exercise it. Res: whether outcome research has run.

| # | Requirement | Source | Existing code | Integration path | Tests | Eng | Data | Res | Exact remaining dependency |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Level-2 / tape recorder | §10, A | `src/MlesV12CaptureHost.cs` (build 1.2.1) | NT8 indicator, permanent lifecycle | `tests_mles_v12.py` 37/37 | **DONE** | genuine captures exist | n/a | capture restarted; recorder 1.2.1 installed at the contract roll |
| 2 | Manifest / hash / sequence audit | §10, A | `mles_v12_audit.py` | streaming, O(1) memory | 37/37 incl. adversarial fixtures | **DONE** | 15 runs verified byte-for-byte | n/a | bulk CSVs for the 14 manifest-only runs |
| 3 | Event-stream adapter | A | `mles_v12_adapter.py` | `iter_file` / `merge_run` heap merge | 37/37 | **DONE** | 1,351,398 genuine events parsed | n/a | — |
| 4 | Frozen level hierarchy | A | `mrofyt_levels.py` | 14 active level IDs, families | `tests_mrofyt.py` 59/59 | **DONE** | **only 5 of 14 levels ever formed** | n/a | ≥1 completed prior session for YDAY/ONH/ONL/PP/M2/M3; ≥1 prior week for LWEEK |
| 5 | A1–A6 detectors | A | `mrofyt_signals.py` | `DETECTORS` dict | 59/59 | **DONE** | ran on 293 genuine windows, 0 fired | **NOT_OBSERVED** | z-scored inputs, which need ≥5 prior sessions per 5-min bucket |
| 6 | Wall state machine | A | `mrofyt_wall_engine.py` | overlay on approaches | 59/59 | **DONE** | `NO_QUALIFYING_WALL` on all 293 | **NOT_OBSERVED** | `wall_z`, hence the same baseline dependency |
| 7 | A4 residual `resid_tail_5pct` | A | wave one: **absent** (passed as `None`); wave two: `mrofyt_wave2.ResidualModel` | frozen A4 still receives `None`; `W2-A4f` in the new module receives the fitted tail | R9; `tests_mrofyt_wave2.py` W2–W3 | **NOT WIRED in wave one by design; wired in W2-A4f (minimal form)** | synthetic only | not run | the fuller covariate set (intensity, BI3, vol, distance) — its own wave |
| 8 | A5 `trend_dir` | A | **absent** | passed as `None`, named in ledger | R9 | **NOT WIRED by design** | n/a | not run | the already-frozen MROF multi-timeframe state; no such code exists |
| 9 | Causal baselines | A | `BaselineStore(20)` | robust median/MAD per (feature, 5-min bucket) | 59/59 | **DONE** | **never reached 5 observations** | n/a | ≥6 independent session-days per instrument |
| 10 | Regime tag (RVMR-V1) | A | `analysis/rvmr/rvmr_spec.py` | `RollingTrailingRatio` | `tests_mrofyt_runner.py` R3 | **DONE** | needs 1,440 prior bars; had 12–19 | n/a | ~1 full session of 1-minute bars |
| 11 | Outcome-blind ingest runner | A | `mrofyt_runner.py` | streaming; `compute_outcomes` locked | 11/11 | **DONE** | ran on genuine data | n/a | — |
| 12 | Executable coordinator | A | `mrofyt_engine_v015.py` | sole v01.5 entrypoint | `tests_mrofyt_v01_5.py` 36/36 | **DONE** | not exercised on genuine data | not run | genuine signals to adjudicate |
| 13 | Pilot diagnostic (§8A) | §8A | `mrofyt_pilot.py` **(new)** | instruments the runner via hooks | `tests_mrofyt_pilot.py` 18/18 | **DONE** | ran; see findings | `NOT_OBSERVED` | bulk CSVs + ≥6 sessions |
| 14 | Causal swings 5m/15m/60m | B | `mrofyt_swings_v016.py` **(new)** | experimental active-location branch | `tests_mrofyt_v01_6.py` 21/21 | **DONE** | **no data**: needs multi-hour bars; longest CSV run is 183 s | not run | ≥1 complete session of certified 1-minute bars |
| 15 | v01.6 toggles | B | `mrofyt_engine_v016.py` **(new)** | delegates to v01.5 for parity | 21/21 incl. B17 bit-identity | **DONE** | no data | not run | as #14 |
| 16 | E0/E1/E2 exit arms | C | `mrofyt_exits_v017.py` **(new)** | `research_driver` State-C locked | `tests_mrofyt_v01_7.py` 15/15 | **DONE** | no data | **NOT RUN** | frozen parent entries, which require #5 to fire |
| 17 | Session flattening | C | **absent from the parent** | new optional `session_flat_t` | C9/C9b | **NEW ASSUMPTION** | n/a | not run | documented in the v01.7 freeze §3 as an assumption, not an inherited rule |
| 18 | State-C outcome lock | A | `analysis/mrof/mrof_engine.py` | `MROF_V1_STATE_C_AUTHORIZED.json` | R1, C12 | **DONE** | file **ABSENT** → locked | locked | the readiness freeze itself |
| 19 | NT8 F5 compile / smoke test | §10 | `src/MlesV12CaptureHost.cs` | user-side only | — | **BLOCKED** | n/a | n/a | Windows + NT8 + live feed. Not performable here; a stub compile is not an API validation |
| 20 | Wave-two families, arms B/C (registration §1–§4.2, §6) | W2 | `mrofyt_wave2.py` **(new, MROF-YT-WAVE2-1.0)** | subclass of the pilot runner via the runner's observation hooks; wave-one ledger byte-identical | `tests_mrofyt_wave2.py` 28/28 | **DONE** | synthetic only; first DEV run is user-side | **BLIND** on sessions ≥ 20260921 | §4.3 CAUSAL_SWING comparison and §5 Asia labels not in this version; operator §10 sign-off |

## Repository scale (measured, `git ls-files`)

183 analysis modules, 20 test suites under `analysis/`, 34 C# hosts,
82 markdown protocol/freeze documents.

## Data status in one paragraph

29 manifests were supplied. 15 runs arrived with bulk CSVs and all 15
passed every hash, byte, row, identity and sequence check. They are all
from **2026-09-01**, during the duplicate-instance setup period, and
after collapsing concurrent copies of the same feed they cover **162.3 s
of NQ and 344.5 s of MNQ with zero seconds of overlap**. The other 14
runs — the real 18,000–83,000 second sessions with 0.991–1.000 NQ/MNQ
pairing — exist here only as manifests; their CSVs are on the capture
machine. Last recorded event: 2026-09-04 22:35 UTC.

## Classifications

| Dimension | Status |
| --- | --- |
| Pilot diagnostic | `PILOT_DIAGNOSTIC_COMPLETE — INSUFFICIENT_DATA_FOR_EV` |
| Implementation (v01.6, v01.7) | `COMPLETE` |
| Data readiness | `INSUFFICIENT_DATA` |
| Market research | `NOT_RUN` |
| Prospective validation | `NOT_STARTED` |
