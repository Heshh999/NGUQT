# MROF God's Eye View — read-only research monitor

A local dashboard over the existing NQ/MNQ order-flow project: recording
health, hypothesis readiness, data quality and provenance, and a replay of
already-exposed development sessions. It places no orders, changes no
frozen logic, writes nothing into the capture folder, and refuses — in the
backend, not the browser — to show anything event-level for a session the
exposure ledger does not label `EXPOSED_PILOT_DEV`.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** The dashboard imports no
order API, and `tests_godseye.py::G10b` scans every dashboard file for one.

---

## 1. What is here

| file | version | role |
| --- | --- | --- |
| `godseye_registry.py` | MROF-GODSEYE-REGISTRY-1.0 | the hypotheses, levels and context items **as the frozen code has them**: A1–A6, the wave-two families and arms, the 14 active level ids, the context inventory, and the discrepancy record (§6). Verified against the code by `G1`/`G1b` on 20,000 random inputs |
| `godseye_policy.py` | MROF-GODSEYE-POLICY-1.0 | the data-permission policy (§5): session classes, what each class permits, the event-level field list, the strip-and-scan boundary, the outcome-lock check |
| `godseye_replay.py` | — | bounded raw reads for replay: byte-offset binary search on `tRecvUtc`, row cap, book rebuilt with the runner's frozen `KLevelBook` |
| `godseye_export.py` | MROF-GODSEYE-EXPORT-1.0 | the exporter: reads the released reports plus a bounded tail of the capture folder, builds one sanitized snapshot (`MROF-GODSEYE-SNAPSHOT-1`), writes it atomically with a status file |
| `godseye_server.py` | MROF-GODSEYE-SERVER-1.0 | stdlib HTTP server on `127.0.0.1` serving the snapshot, the static page and the replay endpoints; re-checks the policy on every replay request |
| `godseye_demo.py` | MROF-GODSEYE-DEMO-1.0 | builds a labelled **synthetic** capture and its reports through the tools' library entry points (never their CLIs, so no real ledger is touched) |
| `static/index.html`, `static/style.css`, `static/app.js` | — | the dark, dependency-free frontend (vanilla JS, canvas) |
| `static/theatre.js` | — | the Mechanism theatre: one scripted scenario per hypothesis, played beat by beat while the frozen conditions light up; the thought-experiment sliders (§4a) |
| `tests_godseye.py` | 36 tests | boundary behaviour, HTTP behaviour, bounded reads, the demo, the theatre scripts against the frozen detectors, study progress |
| `launch_godseye.bat`, `export_godseye.bat` | — | ordinary Windows launchers (§3) |
| `pinokio/` | — | optional Pinokio launcher that starts and stops **only** the dashboard (§3.4, unverified here) |
| `godseye.config.example.json` | — | configuration template for real report locations (§3.2) |

Python 3.8+ standard library only; no pip installs. Any current browser.

Two predecessor tools gained one additive flag each so the dashboard can
read them rather than recompute anything: `mles_v12_audit.py --out FILE`
writes its report as JSON, and `mrofyt_pilot.py --windows-out FILE` writes
the decision windows of **exposed sessions only** (`MROF-PILOT-WINDOWS-1`)
for the replay view. No detector, threshold, level, window, baseline or
feature definition was touched; the frozen signal hash is re-pinned by the
existing suites (`P10d`, `W7b`).

---

## 2. Architecture and the permission model

```
 capture folder (recorder's; read-only, bounded)      released reports (--out JSON)
        │  scandir + manifests + last 64 KB of open runs        │
        ▼                                                        ▼
  godseye_export.py ──► policy (fail closed) ──► strip + whole-document scan
        │                                                    │
        ▼                                                    ▼  refuses to write on any hit
  out_dir/godseye_snapshot.json  (+ godseye_status.json)  — atomic, sanitized
        │
        ▼
  godseye_server.py  (127.0.0.1 only)  ──► /api/snapshot, /api/status, /api/registry
        │                                   /api/replay/*  (policy re-checked per request)
        ▼
  browser: static/app.js  (polls the snapshot every 60 s; replay reads bounded windows)
```

**Separate process, light on the recorder laptop.** The exporter is a
short-lived process (0.4 s on the demo) and the server is a second small
process (about 45 MB resident after serving replay bundles). Neither
imports NinjaTrader, opens a capture stream for writing, or holds any
capture file open between requests.

**What touches the capture folder, and how much.**

* `os.scandir` of the top level and `shutil.disk_usage` — no recursive
  walk, no row scan.
* Every `*_manifest.json` is read whole (they are a few KB each).
* For a run **without** a manifest (open or orphaned) only the header and
  the last 64 KB of each stream are read, through `mrofyt_recover.py`'s own
  probes, so the liveness rule of the recovery tool and the dashboard can
  never disagree. On Windows that includes the read-only file-sharing
  check; a run NinjaTrader holds is reported as held, never as dead.
* Replay reads one window at a time: a byte-offset binary search lands
  inside each stream, a forward read covers 60 s before the window to 60 s
  after it (15 min of 1-minute candles either side from the trade stream),
  capped at 250,000 rows per stream. A capped read says `truncated` in the
  bundle and on the page. The demo's window read 978.5 KB.
* The pilot's windows file (`--windows-out`) is ~1.5 KB per decision
  window, ~4,500 windows per session: about **100 MB** once the September
  DEV sessions are all in. It is split **once per pilot run** (or ledger
  change) into one piece per (session, instrument) of inspectable
  sessions, in `out_dir`; a routine export then reads only the ~1.5 MB
  index, and the server loads at most four pieces. Measured on a
  synthetic 63,000-window, 100 MB file: the one-time split ~20 s at 284 MB
  peak Python heap; a routine export's windows part 0.06 s and 5.7 MB;
  the server ~30 MB after opening six sessions. (1.0 parsed the whole
  file on every export and held all of it in the server: 284 MB peak per
  export, 183 MB resident.)
* The server re-reads the exposure ledger whenever it changes, so a
  weekly pilot run that labels new sessions needs no server restart; a
  missing or unreadable ledger still closes every event-level view.
* The snapshot records `resource_use.bytes_read` and `files_read`; the
  status file records duration and peak Python heap.

**What never happens.** The exporter refuses to run with `out_dir` inside
the capture folder (`G4b`). Nothing writes a manifest, a `.csv`, a
`.partial`, a `_RECOVERED` file, the exposure ledger or the outcome-unlock
file. The demo builds its own folder and calls the tools as libraries, so
building or testing the demo leaves the repository's ledger byte-identical
(`G3d`). Recovery, repair and every research pass stay outside the
dashboard; it only shows their reports.

**Freshness and provenance are always visible.** The header shows the
snapshot's age; the server marks a snapshot older than 15 minutes, or a
failed export, as stale and keeps serving the last good one (`G4c`). Every
card names the report file, its tool version and its generation time. A
capture folder that cannot be read is `UNAVAILABLE` with the error text,
never a clean zero (`G4`).

**Use elsewhere.** The snapshot is a sanitized export: copy `out_dir` to
another machine, point a config at it, and run only the server. The four
views work; replay bundles need the capture folder and report that it is
unavailable rather than inventing anything.

---

## 3. Setup and launch

### 3.1 Synthetic demonstration (works anywhere, no capture folder needed)

```
cd analysis\godseye
python godseye_demo.py demo            (add --small for a faster build)
copy demo\godseye.config.json godseye.config.json
launch_godseye.bat
```

The demo builds nine synthetic sessions × NQ/MNQ on a sine-wave tape:
six before the hold-out that the demo pilot inspects and labels exposed;
20260909, whose pair is aged and stripped of its manifests so it is never
ingested (it stays `PROTECTED_UNLISTED`, and the recovery and health views
have orphans to show); and two inside the hold-out, blind-labelled. It
runs the auditor, runner, pilot, wave two and the recovery dry-run on
them, writes a demo exposure ledger **inside the demo folder**, and stamps
`synthetic: true` in its config. Every page of a
synthetic snapshot carries a `SYNTHETIC DEMO` badge and a banner. Its
health cards read `DISCONNECTED` because the synthetic files are aged: that
is the correct reading of a folder nobody is writing to.

### 3.2 Real reports (the recorder laptop)

Produce the reports with the existing tools into one folder — the
dashboard reads them, it does not run them:

```
cd analysis\mrofyt
python mles_v12_audit.py  "D:\MLES_Capture" --out C:\MROF\reports\audit.json
python mrofyt_runner.py   "D:\MLES_Capture" --out C:\MROF\reports\ledger.json
python mrofyt_pilot.py    "D:\MLES_Capture" --out C:\MROF\reports\pilot.json --windows-out C:\MROF\reports\windows.json
python mrofyt_wave2.py    "D:\MLES_Capture" --both --out C:\MROF\reports\wave2.json
python mrofyt_recover.py  "D:\MLES_Capture" --dry-run --out C:\MROF\reports\recovery.json
                          (the dry run also says what a --repair would write
                           against the free space; 1.3 refuses a repair that
                           would leave the drive under 40 GB free)
```

Then:

```
cd ..\godseye
copy godseye.config.example.json godseye.config.json
notepad godseye.config.json        (set capture_dir, reports_dir, out_dir)
launch_godseye.bat
```

Configuration keys (paths are absolute or relative to the config file):

| key | meaning |
| --- | --- |
| `capture_dir` | the recorder's folder (read-only, bounded) |
| `reports_dir` | where the `--out` files are; the newest `audit*.json`, `ledger*.json`, `pilot*.json`, `wave2*.json`, `recover*.json` are used, or name them explicitly under `reports` |
| `exposure_ledger` | the ledger the pilot **you ran** wrote — it lives next to the `mrofyt_pilot.py` that ran (`..\mrofyt\MROF_EXPOSED_PILOT_DEV_DAYS.json` in this package). A session absent from it is protected whatever its date |
| `windows` | the pilot's `--windows-out` file; without it the replay view lists no approaches |
| `out_dir` | the only place the dashboard writes; must not be inside `capture_dir` |
| `mrof_dir` | where the outcome lock is checked (the file is only ever read, never created) |
| `blind_from` | `20260921`; the hold-out start. Do not change it here — the pilot and wave two carry the same constant |
| `synthetic` | `false` for real data; `true` labels every page |
| `bind`, `port` | `127.0.0.1`, `8765` |

**The ledger shipped in this package lists 20260901–20260905** (the
repository copy). Sessions you have inspected with your own pilot runs are
recorded in the ledger beside the pilot you ran; if you unzip this package
fresh and point the dashboard at its ledger, 20260908–20260918 show as
`PROTECTED_UNLISTED` until the pilot in this package has been run, which
labels the sessions it inspects. That is the policy working as intended:
a date before the hold-out is not automatically exposed.

### 3.3 Ordinary Windows launch

* `launch_godseye.bat` — one bounded export, then the server, which opens
  `http://127.0.0.1:8765/` in the browser once it is listening (`--open`)
  and, while its window stays open, re-runs the export every 5 minutes
  (`--refresh 300`) as a separate process at below-normal priority, so the
  health view and the 🔔 watchdog stay current without any scheduling.
  `Ctrl+C` stops the dashboard only. It never starts, stops or touches
  NinjaTrader or the recorder.
* `export_godseye.bat` — refresh the snapshot only, by hand. Not needed
  while the dashboard is open.
* Manual: `python godseye_export.py --config godseye.config.json` then
  `python godseye_server.py --config godseye.config.json [--port N]`.

The `.bat` files were reviewed, not executed: this environment has no
Windows.

### 3.4 Pinokio (optional, unverified here)

`pinokio/` holds a launcher written to Pinokio's documented script API:

* `pinokio.js` — the menu. Not installed: *Install (link to your MROF
  folder)*. Installed: *Start dashboard*, *Refresh snapshot only*, *Edit
  config*. Running: *Open dashboard*, *Server log*, *Stop dashboard (only
  the dashboard)*.
* `install.js` — links this folder as the app (`fs.link`); installs nothing.
* `start.js` — `daemon: true`; one bounded export, then
  `godseye_server.py`; the `on` matcher reads the URL the server prints and
  stores it with `local.set` so the menu can open it.
* `stop.js` — `script.stop` on `start.js`: stops the dashboard **only**.
* `export.js` — refresh the snapshot.

To use it: Pinokio → *Discover* → *Download from URL* is not needed; copy
this repository's `analysis/godseye` folder into Pinokio's `api` folder
(or link it) and it appears in the Pinokio home. It expects `python` on
the path and a `godseye.config.json` next to the scripts. **Pinokio could
not be exercised in this environment** (Linux container, no Pinokio); the
scripts follow the published schema but the first run is user-side, and if
Pinokio's schema has moved, `launch_godseye.bat` is the fallback and does
the same thing.

### 3.5 Tests

```
cd analysis\godseye
python tests_godseye.py          (builds its own small demo in a temp folder; ~40 s)
```

---

## 4. The four views

**Recording health.** Per instrument: `LIVE` (a run is held open and its
newest row is under 10 minutes old), `IDLE` (held open, no new rows, and the
market is scheduled closed — expected), `STALE` (held open, no new rows
while the market is scheduled open), `DISCONNECTED` (no run held open;
the last closed run is shown), `UNAVAILABLE` (the folder cannot be read;
the error is shown), `UNKNOWN` (Windows could not be asked). The card says
which rule decided it and whether that was the Windows file-sharing check
or indirect signs only. Below: disk, file counts, runs without a manifest
(recoverable / still being written), the audit's failure codes and its
disconnect-repair evidence, and the expected-vs-observed coverage table per
session with the **shared gap** column — hours missing in *both*
instruments — beside the pair overlap, because overlap is measured on the
hours both recorded and a 1.000 overlap does not mean a complete session.
The market schedule is CME Globex for equity index futures: Sunday
18:00 ET open, Friday 17:00 ET close, daily 17:00–18:00 ET break, all in
`America/New_York` with DST handled from the rules, not from an offset.

**Hypothesis readiness.** Registry-driven. Every family and arm has a
status with a reason: `NOT_IMPLEMENTED`, `NOT_WIRED` (the code exists but
an input it needs is passed as `None` by the runner — A5), `INSUFFICIENT_
PRIOR_HISTORY` (fewer than 5 prior sessions in the 5-minute bucket, the
frozen `BaselineStore` rule), `NO_QUALIFYING_OBSERVATIONS`,
`INVALID_OR_MISSING_DATA`, `READY`, `CONDITION_FALSE`, `UNRESOLVED_SPEC_
MISMATCH` (the registry's own check of the code failed), and `CONTROL` for
the placebo arm. A z-score that is `None` although the pass held ≥ 5
baseline sessions is reported as `INVALID_OR_MISSING_DATA` with the honest
reason that the pilot report cannot distinguish a thin bucket from a
zero-dispersion bucket — it is not called prior-history. Counts are the
released reports' accrual counts (raw firings, distinct events, NQ signal
source), quoted, never recomputed, and nothing ranks by profitability.
The inspector shows the frozen conditions, the funnel's first failing stage,
missing inputs and feature availability. The levels inventory (14 ids,
identical to `ACTIVE_LEVEL_IDS`) and the context inventory (RVMR, ADR,
running extremes, psychological, causal swings, 1-hour zones, EMA, Asia)
sit below, each with its implementation status.

**Mechanism theatre (§4a).** Every hypothesis — A1–A6, the six wave-two
families, both candle arms and the placebo control — has one scripted
scenario: five beats of a synthetic tape (price in ticks from the level,
resting size at the level, executions) with the inputs the frozen rule
reads appearing beat by beat, the condition checklist lighting up as they
arrive, and the verdict at the end (fire long / fire short, with the
direction rule quoted). Each has a **counter-example** that changes one
thing — the offer is not refilled, the far side refills, price never
comes back through, the same tape at 10:45 instead of 09:52 — and does
not fire, so the rule's edge is visible. A **thought experiment** panel
puts every input on a slider and re-evaluates the written conditions
live. The scripts live in `godseye_registry.DEMOS`; `G11` runs the
frozen detector itself (`mrofyt_signals`, `mrofyt_wave2`) on every
script's final beat and on every counter-example, and `G11c` runs the
frozen arm functions on the candle bars. Nothing in the theatre is data;
it says so on every page. Keys: `space` play/pause, `←`/`→` beat, `c`
counter-example, `1`–`5` views.

**Where the study stands (on Recording health).** Complete sessions —
window fully passed, both instruments ≥ 95% covered, no shared gap over
5 minutes, every manifest run audit-clean (a run whose only flag is
`RECONSTRUCTED_RUN_NOT_SELF_VERIFYING` counts, and the session is shown
as relying on reconstructed manifests) — against the runbook's 20- and
60-session milestones on a rail; the registration's checkpoint
(2026-12-01) with trading days left; NQ signal-source events per family
against the 30-event minimum with a linear accrual projection (a count,
never a result; families in registry order, never ranked); why each
incomplete session is incomplete. Also on that view: **disk runway** in
session-days (free space over the median finalized bytes per session-day)
and the **next scheduled market change** (opens/closes, ET, countdown).
Alerts are schedule-aware: not recording is `crit` while the market is
scheduled open and `info` on a weekend, with the time by which recording
must resume. The 🔔 **notify me** button (opt-in, this browser only)
raises a local notification when recording stops or the snapshot goes
stale during market hours; the tab title carries ⚠ while anything is
critical.

**Data quality & provenance.** One timeline per session, 18:00 ET the day
before to 17:00 ET (DST-aware), NQ and MNQ rows, recorder runs / reconstructed
manifests / orphans / open runs / audit failures distinguished by form and
by legend text. The inspector shows the ET and UTC expectation, coverage,
gaps and shared gaps, every run with its source (recorder or
reconstructed), the recorder's own counters, the audit verdict, the
ingest count, the recovery verdict, and the provenance line for each fact
(file, tool version, generation time). Nothing is supplemented from
historical data; a gap is shown as a gap.

**Exposed-data replay.** Session → instrument → approach → 10-second
decision window → the events. The session list offers only sessions the
ledger labels `EXPOSED`; the server refuses every other request with 403.
Candles are a display aggregation of the frozen inputs (1-minute), the
levels are drawn at the values the runner held in that window, the BBO and
the inferred-aggressor prints are the recorder's rows, the depth ladder is
rebuilt with the runner's frozen `KLevelBook` from 60 s before the window
— a level never updated in that time is shown as `unknown`, not invented.
Play / pause / step 250 ms; the cursor shows ET and UTC. The evidence
panel explains each family's frozen conditions at that window with the
values the pilot recorded and the pilot's own de-duplication rule.

---

## 5. How the blind is enforced

The hold-out begins **20260921** (`BLIND_FROM`, the same constant the
pilot and wave two carry). The policy (`godseye_policy.py`) classifies
every session from two inputs and fails closed:

| class | when | permits |
| --- | --- | --- |
| `EXPOSED` | the exposure ledger labels the session `EXPOSED_PILOT_DEV` | operational, counts, events, features, replay |
| `BLIND` | session ≥ `blind_from`, or ledger label `VALIDATION_BLIND_MARKOUTS_WITHHELD` | operational, counts |
| `PROTECTED_UNLISTED` | before the hold-out but **not** in the ledger | operational, counts |
| `UNKNOWN` | no session, a mixed/unparseable label, or the ledger is missing or unreadable | operational only |

Counts for `BLIND` and `PROTECTED` sessions are integers quoted from the
released reports (`G3c`); nothing event-level about them exists in the
snapshot: no prices, candles, tape, depth, directions, exact timestamps,
event-level features or markouts.

Three layers, each tested:

1. **Strip.** Every health, audit, recovery, session and count record of
   a non-exposed session is stripped of the event-level fields
   (`EVENT_LEVEL_FIELDS`) before it enters the snapshot.
2. **Whole-document scan.** Before writing, the exporter scans the entire
   snapshot outside its `exposed` section for any event-level key and
   **refuses to write** on a hit (`ExportError`); the previous snapshot
   stays in place and is served as stale (`G3`, `G4c`, `G8e`).
3. **Server re-check.** `/api/replay/windows`, `/api/replay/bundle` and
   `/api/replay/explain` re-run the policy on the session — and, for a
   bundle, on the run's own manifest session — on every request, so a
   crafted URL for a blind or unlisted session gets 403 (`G8`). Bundles are
   cached only after passing.

Also: December never auto-unlocks — the blind is a ledger label plus a
date floor, and no clock in the dashboard changes a class; the
outcome-unlock file (`analysis/mrof/MROF_V1_STATE_C_AUTHORIZED.json`) is
only ever tested for existence, never created (`G2b`); the pilot's windows
file contains exposed sessions only and names its rule (`G10`); and the
demo's ledger lives in the demo folder, so a demo build cannot touch the
real one (`G3d`).

---

## 6. Discrepancy record (found by inspecting the code, nothing changed)

| item | earlier description | what the frozen code does |
| --- | --- | --- |
| A2 direction | "a large resting order gets hit and holds → fade it" | `a2_depletion_continuation` returns `break_dir`: a wall executed **through** and not replenished, the clear holding 5 s → **continuation** in the break direction |
| A5 direction | "a level touch against the higher-timeframe trend → fade it" | `a5_pullback_resumption` returns `trend_dir`: counter-trend aggression absorbed and replenished → **resume** with the trend. Four of its five inputs (`trend_dir`, `adverse_z`, `adverse_progress_ticks`, `trend_flip_z`) are passed as `None` by the runner; `replenish_z` is wired |
| A6 vs W2-A4-OPEN | "A6: A4's setup, but only in the first hour" | A6 is a **continuation** (`break_dir`) gated to 09:30:00–09:45:00 ET on six open-type levels (`OVERNIGHT_HIGH/LOW`, `YDAY_HIGH/LOW`, `GLOBEX_OPEN`, `CASH_OPEN_0930`). W2-A4-OPEN is a **reversal** (W2-A4r) gated to 09:30–10:30 ET on `CASH_OPEN_0930` and the overnight extremes. Different mechanism, window and level set; the registration folded A6 into W2-A4-OPEN as a budget decision, not an equivalence |
| prior history: 5 vs 20 | various | z-scores need ≥ 5 **prior sessions** in the 5-minute bucket (20-session window); the W2-A4f residual model needs ≥ 20 prior **observations** in the bucket (20-session window). Neither needs 20 sessions |
| A5 inputs that exist | "4 of 5 inputs hardcoded None" | confirmed, as above |
| swings and Asia | "registered, not built" | confirmed: `mrofyt_swings_v016` exists as a frozen, tested module but is not a level provider for the runner and has never run on real tape; the Asia labels have no code |
| exposed sessions | "Sept 1–18 fully readable" | the repository ledger lists 20260901–20260905 only; sessions are exposed by the pilot run that inspects them, recorded in the ledger beside that pilot. A session not in the ledger is protected here, whatever its date |
| the fourteen level ids | as listed in the build prompt | identical to `mrofyt_levels.ACTIVE_LEVEL_IDS` |

The dashboard shows this table (Hypothesis readiness → *Discrepancies*)
and `G1c` pins it.

---

## 7. Adapters (what each report must look like)

All readers are tolerant: a missing file is reported as missing, a missing
field as `—`, never as zero.

| report | produced by | fields read |
| --- | --- | --- |
| audit | `mles_v12_audit.py --out` | `ok`, `failures[]` (`code`, `runId`, `instrument`, `session`), `runs[]` (rows, eventSeq bounds, disconnects, BOOK_READY/resync counts, depth sides/actions, latency percentiles, rows in disconnect gaps), `open_runs_in_progress`, `recovery_originals_kept`, `repair_evidence`, `pair_overlaps` |
| ledger | `mrofyt_runner.py --out` | `sessions`, per-run `rows_ingested`, skip reasons, `duplicate_manifests_ignored`, version and generation time |
| pilot | `mrofyt_pilot.py --out` | `funnels` (per family: stage → windows), `feature_availability`, `baseline_sessions`, raw firings / distinct events / NQ signal source per family and session, `blind_from`, `sessions_blind`, `events_withheld` |
| wave2 | `mrofyt_wave2.py --both --out` | per family raw / events / visible / withheld / NQ source, `w2_windows`, `arm_b`, placebo presence |
| recovery | `mrofyt_recover.py --dry-run --out` | `results[]` (run, instrument, session, state, size, newest row), `liveness_by` |
| windows | `mrofyt_pilot.py --windows-out` | `MROF-PILOT-WINDOWS-1`: exposed sessions only, per window `approach_id`, `level_id`, `level_px`, `ad`, `t_start`, `t_end`, `wall_state`, the runner's levels at that window |
| manifests | the recorder | `MANIFEST_FIELDS` of `mles_v12_adapter.py` |
| exposure ledger | `mrofyt_pilot.py` | `{session: label}` with `EXPOSED_PILOT_DEV` / `VALIDATION_BLIND_MARKOUTS_WITHHELD` |

---

## 8. Verification results (this environment: Linux container, Python 3, no Windows, no NT8, no Pinokio)

| check | result |
| --- | --- |
| `tests_godseye.py` | **46/46** |
| the 15 package suites in `analysis/mrofyt` | **572/572** (pilot 45 with `P13`, recovery 38 with `V10`–`V12b`, runner 33 with `R13f`–`R13j` and `R15e`, ingest 69) |
| package total | **618/618** |
| real-scale replay split | synthetic 63,000 windows / 100 MB: one-time split ~20 s, 284 MB peak; routine export 0.06 s, 5.7 MB; server ~30 MB |
| theatre scripts vs frozen code | 15 demos: every flow demo fires in the frozen detector in the named direction, every counter-example does not and fails exactly one clause, both candle arms fire in the frozen arm functions (`G11`–`G11c`); `resolve()` agrees with `mrofyt_wave2` on 6,000 random inputs for all six derived families (`G11d`) |
| registry vs frozen detectors | 0 mismatches on 20,000 random inputs per family (`G1b`) |
| browser render | Chromium 141 headless (Playwright): all four views rendered, replay cursor moved into a window, no page errors, no console errors |
| demo export | 0.428 s wall, 8,809,915 bytes read from 32 files, 22.75 MB peak Python heap, 155,476-byte snapshot |
| server | 44.9 MB resident after 9 min serving the demo and several replay bundles; one replay bundle read 978.5 KB in bounded seeks |
| capture folder writes by the dashboard | none (`G3d`: the capture folder's tree hash is identical before and after export, demo build and tests) |
| repository ledger after demo build and tests | byte-identical (`G3d`) |
| no order API, no outcome stage | `G10b` scans every dashboard file |

Per-test list: `G1` levels and gates are the code · `G1b` registry
reproduces the frozen detectors · `G1c` discrepancy record · `G2` fail-closed
classification (a pre-hold-out date not in the ledger is protected; a mixed
request is refused; an unreadable ledger is UNKNOWN) · `G2b` outcome-lock
file only read · `G3` synthetic export clean at the boundary · `G3b`
exposed section is ledger-exposed only · `G3c` counts quoted, not
recomputed · `G3d` no writes into capture or ledger · `G3e` distinct,
reasoned statuses · `G4` unreadable folder → UNAVAILABLE, never zero ·
`G4b` refuses to write inside the capture folder · `G4c` failed export
keeps the previous snapshot, served stale · `G5` shared gaps beside a
1.000 overlap · `G6` insufficient history vs missing code · `G6b` z None
with ≥ 5 sessions is not called prior-history · `G7` session window ET/UTC
· `G7b` market-hours rule · `G7c` timeline records · `G8` HTTP: exposed
served, blind/unlisted 403 · `G8b` bundle contents · `G8c` evidence
endpoint · `G8d` static traversal 404 · `G8e` served document clean ·
`G9` row cap says truncated · `G9b` byte-offset search · `G10` windows
file exposed-only · `G10b` no order API · `G11` every hypothesis has a
script and the frozen detector fires on it · `G11b` counter-examples do
not fire, one clause fails · `G11c` candle arms through the frozen arm
functions · `G11d` resolve() equals mrofyt_wave2 · `G12` complete-session
rule · `G12b` progress section · `G12c` market clock and trading days ·
`G12d` disk runway · `G12e` a session whose only audit flag is the
reconstructed-manifest notice is complete, labelled as such · `G13`
replay windows split once, routine exports reuse it · `G13a` rebuild on a
new windows file or ledger · `G13b` server holds ≤ 4 pieces and re-reads a
changed ledger · `G13c` the launcher lets the server open the browser ·
`G13d` the server's refresher runs one export as a separate process ·
`G8f` replay evidence matches the approach id, not only the time · `G14`
a run with a file the drive cannot read (recover 1.4
`SKIPPED_UNREADABLE_FILE`) is shown with the file name and the Windows
error, alerted, and never touched · `G14b` shared-gap alerts capped at the
five largest plus one summary line · `G14c` a file found unreadable is
remembered in the output folder and not opened again until its size or
time changes (no repeated Windows "Corrupt File" warning).

---

## 9. Blockers and what is not verified here

* **Pinokio** — scripts written to the documented API, not exercised (no
  Pinokio here). The `.bat` launcher is the fallback.
* **Windows** — the `.bat` files and the file-sharing liveness check run
  only on Windows; here liveness is decided by indirect signs and the health
  card says so. The first real launch on the recorder laptop is the test:
  with NinjaTrader recording, NQ and MNQ should read `LIVE` with
  "Windows file-sharing check" as the certainty line.
* **Real data** — every number verified here is synthetic. Report
  adapters were written against the tools' JSON writers in this
  repository; a report from an older tool version shows its fields as `—`.
* **Replay needs `--windows-out`** — a pilot report without a windows
  file gives counts and statuses but no approaches to replay.
* **`CAUSAL_SWING` and the Asia labels** are `NOT_IMPLEMENTED` and shown
  as such; the dashboard does not build them.
* **Recorder idle-loop defect** (no flush or heartbeat while the market is
  closed) remains recorded in the manifest, not fixed; the health view's
  `IDLE` state exists because of it.

---

## 10. Reading the dashboard (user guide)

* **Header**: overall recording status, per-instrument status, snapshot
  age, hold-out start, count of exposed sessions and ledger days, and the
  `SYNTHETIC DEMO` badge when the config says so. A `STALE` banner means
  the export has not succeeded in 15 minutes and the last good snapshot is
  being shown — run `export_godseye.bat` and read the status line at the
  foot of the page for the error.
* **Alerts** are ranked: `crit` for an instrument not recording while the
  market is scheduled open or an unreadable folder; `warn` for stale rows,
  low disk (under about three session-days), audit failures, orphaned runs,
  a file the drive refuses to read (the recovery tool's
  `SKIPPED_UNREADABLE_FILE`: check the drive or cable; the run is left
  alone) and shared gaps — the five largest, then one line for the rest.
  The **Runs without a manifest** table carries the same verdict per run,
  with the file name and the Windows error in its note column. Such a
  file is read once, remembered in `godseye_unreadable.json` in the
  output folder, and not opened again until its size or modification
  time changes (chkdsk): every read of it makes Windows show a "Corrupt
  File" warning.
* **A session row** (health or provenance) opens the inspector: click the
  session id. **A run** in the inspector opens its manifest facts,
  recorder counters, audit verdict and provenance.
* **Hypothesis rows** open the inspector with the frozen conditions and
  the funnel. Statuses are not scores; there is no ranking.
* **Replay**: pick a session (only `EXPOSED` ones are enabled), an
  instrument, an approach, then a window. Play, pause, or step 250 ms; the
  slider covers 60 s before the window to 60 s after it. Red bands are
  gaps or invalid-book stretches. The evidence panel shows why each family
  did or did not fire at that window.
* **Mechanism theatre**: pick a hypothesis, press play (or `space`), step
  with `←`/`→`, press `c` for the counter-example, move a slider to ask
  "what if this input were different". The verdict box quotes the
  direction rule. From a family's inspector, "▶ watch the mechanism" jumps
  here.
* **Where the study stands**: the rail fills with complete sessions; the
  chips say how many to go to each milestone; the family table says which
  families would be read at the checkpoint at the current pace. "NOT
  TESTED at this pace" means keep recording — it is not a failure.
* **Nothing here is a fill, a stop, a target or an outcome.** Markouts are
  never shown for any session.
