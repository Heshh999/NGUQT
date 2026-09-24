# RUNNER_GUIDE.md — running `mrofyt_runner.py` over a capture folder

How to point the outcome-blind ingest runner at a folder of
MLES-CAPTURE-1.2 files, what it will print, and what to do when a run
in that folder is missing, truncated or corrupt.

For the surrounding procedure (install, record, transfer) see
`OPERATING_RUNBOOK.md` and `NT8_RECORDING_RUNBOOK.md`. This file only
covers the ingest step.

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. The runner computes no
outcome: no fill, stop, target, R or P&L exists in it.

---

## 1. What the folder has to look like

The runner discovers work by globbing `*_manifest*.json` **directly
inside the folder you name** (`mles_v12_audit.discover_manifests`).
It does not recurse, so nested per-day subfolders are not found — pass
each one separately, or flatten them.

Each run is one manifest plus the four bulk CSVs it declares:

```
MLES12_NQ_NQ_SEP26_20260902_c1-R001_manifest.json
MLES12_NQ_NQ_SEP26_20260902_c1-R001_quotes.csv
MLES12_NQ_NQ_SEP26_20260902_c1-R001_trades.csv
MLES12_NQ_NQ_SEP26_20260902_c1-R001_depth.csv
MLES12_NQ_NQ_SEP26_20260902_c1-R001_quality.csv
```

A manifest is ignored without comment if its `schema` is not
`MLES-CAPTURE-1.2` or its `instrument` is not in `--instruments`. Runs
are grouped by `(instrument, session)` and replayed in `firstRecvUtc`
order, so restarts inside a session are fine.

A run rebuilt by `mrofyt_recover.py` carries a
`_RECONSTRUCTED_manifest.json` and is ingested like any other. If a run
has both the recorder's manifest and a reconstructed one, it is
ingested once, from the recorder's, and the summary names the ignored
duplicate.

Python 3.11 was used for the runs quoted below; the runner is stdlib
only, but it imports its siblings from `analysis/mrof` and
`analysis/rvmr` by relative path, so keep the tree intact. You can
invoke it from any working directory.

---

## 2. Audit first, then run

The auditor is the thing that verifies hashes, row counts, sequence
continuity and NQ/MNQ pairing. Run it first; the runner trusts the
manifests for sizes only.

```
python3 analysis/mrofyt/mles_v12_audit.py "<capture folder>"
python3 analysis/mrofyt/mrofyt_runner.py "<capture folder>" --out ledger.json
```

Both stream the files at flat memory, so a full-session multi-GB depth
file is safe.

---

## 3. Arguments

| Argument | Default | What it does |
|---|---|---|
| `capture_dir` (positional, required) | — | The folder to glob for manifests. Quote it if it has spaces. |
| `--out PATH` | none | Write the full ledger as JSON. Without it you get the printed summary only. |
| `--instruments NQ,MNQ` | `NQ,MNQ` | Comma-separated whitelist. Manifests for anything else are skipped. |
| `--sessions N` | all | Stop after N distinct sessions, in session order. Useful for a quick check on a large batch. |
| `--outcomes` | off | Attempts the State-C outcome stage. It is locked: this raises `RuntimeError: STATE-C LOCKED` before any ingest and nothing else runs. |

---

## 4. What it prints

A clean two-run synthetic folder:

```
MROF-YT-RUNNER-1.2.2  outcomes=LOCKED
sessions=1 runs=2 (ingested 2, skipped: missing-files 0, truncated 0, corrupt 0, io-error 0) events=12788
baseline sessions: {'NQ': 1, 'MNQ': 1}
approaches=10 windows=0 (suppressed 0) fires=0 vacuum_events=0
fires by family: none
approaches by family: OPEN=4, VWAP=6
wall states: {}
feature None counts: {}
book integrity: spurious BOOK_READY ignored=0, rows inside disconnect gaps suppressed=0
regime at windows: {}
latency ms: {'NQ': {'p50': 250, 'p95': 250, 'n': 6390}, 'MNQ': {'p50': 250, 'p95': 250, 'n': 6390}}
NOT WIRED (detectors disqualify by design): resid_tail_5pct, trend_dir
```

Line by line:

- **line 2** is the ingest tally. Read the four skip counters every
  time — see §5.
- **baseline sessions** is how many sessions have closed into each
  instrument's causal baseline store. Detectors that need a baseline
  z-score stay `None` until 20 are in.
- **approaches / windows / fires** is the funnel: approaches to a
  frozen level, completed 10-second decision windows, detector
  firings. `windows=0` with approaches present means every window was
  still open at session close (counted as
  `windows_incomplete_at_close` in the ledger), which is normal on
  short or synthetic captures.
- **feature None counts** is how often a feature was unavailable when a
  window was evaluated. A large count here is the usual reason a
  family never fires.
- **NOT WIRED** names the two frozen inputs that are passed as `None`
  by design (`resid_tail_5pct`, `trend_dir`); their detectors
  disqualify themselves. This is expected, not a defect.

With `--out`, the same run writes a ledger of a few KB whose top-level
keys are `runner`, `outcomes`, `not_wired`, `evaluation`, `sessions`,
`runs`, `skipped_runs`, `totals`, `feature_none`, `fires`, `states`,
`regime_at_window`, `latency_ms`, `baseline_sessions`. `runs` carries
one record per run (events, quotes, crossed quotes, recorder build),
`skipped_runs` carries one record per skipped run with the reason, and
`fires` is capped at the first 5000 firings. The summary text and the
ledger are what move to research; raw CSVs never move.

---

## 5. When a run fails on a bad input file

The runner never ingests part of a run. A run with any problem is
skipped whole, because features computed against half a book or half a
tape are wrong in a way nothing downstream can detect. "Whole" includes
what the run fed in before the problem was found: its windows,
approaches, fires, wall states, latency samples and baseline
observations are wound back to a mark taken before its first event, so
a run the ledger reports as `events=0` leaves nothing behind. One bad
run does not stop the pass: the clean runs beside it are still
ingested, and the process exits 0.

**So a zero exit status is not success.** Check the skip counters on
line 2 of the summary, or `skipped_runs` in the ledger.

There are four skip reasons:

| Reason | What happened | What to do |
|---|---|---|
| `MISSING_STREAM_FILES` | The manifest declares a CSV that is not on disk. The handoff sends manifests first and bulk CSVs later, so this is an ordinary state, not damage. | Fetch the named files and re-run. Nothing to repair. |
| `STREAM_SIZE_MISMATCH` | A file's size on disk differs from the byte count its own manifest declares — truncated or partially copied. Caught before ingest by one `stat()` per file. | Re-transfer the run from the source machine. Never edit, re-save or truncate a file to make it match. |
| `CORRUPT_STREAM` | A row failed to decode mid-stream — a wrong column count, an unknown enum, or a garbled price, sequence number or timestamp — i.e. corruption that did not change the file size. The stream is abandoned at the bad row and everything the run had fed in is wound back. The error names the file and how many rows decoded before the bad one. | Re-transfer the run. If a fresh copy fails the same way, the recorder's own output is suspect — send the manifest and the error text. |
| `IO_ERROR` | The drive failed to read one run's file (a bad sector, a brief USB reset) while the capture folder itself still answers. Handled like `CORRUPT_STREAM`: that run is wound back and skipped, the rest are ingested. | Check the drive and cable; run the recovery tool's dry run and `chkdsk` (read-only) before trusting the drive again. |

The ledger names the specific file or value in each case, for example:

```json
{"instrument": "NQ", "session": "20260902", "run_id": "c1-R001",
 "corrupt": "..._depth.csv: unknown bookType 'XBP' (after 1203 decoded rows)"}
```

The auditor, run on the same folder, independently reports the
underlying codes — `MISSING_FILE`, `BYTE_SIZE_MISMATCH`,
`HASH_MISMATCH`, `UNKNOWN_ENUM` — which is the detail to send back when
you report a bad batch. A failed audit quarantines the batch
(`DATA_SUPPRESSED`); files are never repaired in place.

**When the pass STOPS instead (exit 2, no ledger written).** A capture
that cannot be read at all is never reported as a quiet market:

- a folder with no MLES-CAPTURE-1.2 manifest for the instruments prints
  `STOPPED: no MLES-CAPTURE-1.2 manifest for NQ/MNQ in <folder>: the
  wrong folder, or a drive that came back under another letter`;
- a folder that cannot be read, or stops answering mid-pass (the drive
  unplugged), prints `STOPPED` with the reason.

In both cases nothing is written to `--out`, so an old ledger is never
mistaken for a new one. Fix the folder or the drive and re-run.

One thing that looks like a failure and is not: `--outcomes` raising
`STATE-C LOCKED` is the lock working as designed.

---

## 6. Checking the pipeline without market data

`mles_v12_synth.py` writes a self-consistent run (four CSVs plus a
manifest with exact counts and hashes) in the recorder's format, so the
auditor and the runner can be exercised at session scale on a scratch
folder. Synthetic rows verify code behaviour only; they are never
market evidence and never enter research. Run this from
`analysis/mrofyt` so the import resolves, and generate both instruments
— the auditor's pairing check fails an NQ-only folder with
`MISSING_REQUIRED_INSTRUMENT MNQ`.

```python
import mles_v12_synth as S
S.synth_run('/tmp/cap', n_depth=6000, instrument='NQ',  session='20260902', cid='c1')
S.synth_run('/tmp/cap', n_depth=6000, instrument='MNQ', session='20260902', cid='c2')
```

The runner's own suite covers the skip paths and the funnel:

```
python3 analysis/mrofyt/tests_mrofyt_runner.py     # 33/33 tests passed
python3 analysis/mrofyt/tests_mrofyt_ingest.py     # 69/69 tests passed
```

For the funnel diagnostic and markout registration built on top of this
ingest, see `mrofyt_pilot.py` and
`MROF_YT_PILOT_DIAGNOSTIC_FINDINGS.md`; that tool is outcome-exposing
and has its own blinding rules.
