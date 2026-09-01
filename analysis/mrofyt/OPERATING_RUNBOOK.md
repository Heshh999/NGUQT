# OPERATING_RUNBOOK.md — what you do, in order, with which files

Plain operating procedure for the MROF capture → research programme.
Everything here is capture and verification only.
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

Current status: **INSUFFICIENT_DATA — ZERO GENUINE RECORDED SESSIONS.**

---

## The two packages, and which one is live

| Package | Role | Status right now |
|---|---|---|
| `MROF_V1_Engine.zip` (20 files) | Capture + verification | **THIS IS THE ONE YOU USE** |
| `MROF_YT_TapeScalp_Wave.zip` (44 files) | Strategy/research logic | Dormant archive — do not open, do not install |

Everything in Phases 0–2 below uses ONLY `MROF_V1_Engine.zip`.

---

## PHASE 0 — One-time install (about 30 minutes)

### Files you use

```
MROF_V1_Engine/1_NinjaTrader_Recorder/MlesV12CaptureHost.cs   <- install THIS
MROF_V1_Engine/1_NinjaTrader_Recorder/SETUP_WALKTHROUGH_V12.md
MROF_V1_Engine/3_Docs/RECORDER_DEPLOYMENT_V12.md
```

### Files you must NOT install

```
MROF_V1_Engine/archive_immutable_lineage/MlesV1CaptureHost.cs
MROF_V1_Engine/archive_immutable_lineage/MlesV11CaptureHost.cs
```

Both stop writing at the first 18:00 ET session rollover. That defect
is the entire reason v1.2 exists. They ship only so the lineage can be
independently verified.

### Steps

1. Unzip `MROF_V1_Engine.zip` anywhere (e.g. `Documents\MROF`).
2. Open NinjaTrader 8 with your live data connection. If your
   subscription includes Level II / market depth for NQ and MNQ,
   make sure it is enabled.
3. Control Center → New → NinjaScript Editor → right-click
   `Indicators` → New Indicator → give it any name → **delete all the
   template text** → paste the entire contents of
   `MlesV12CaptureHost.cs` → press **F5**.
4. **Expect zero compile errors.** If you get errors, stop and send me
   the exact error text — do not edit the file to make errors go away.
5. Open a chart for the **NQ front contract** (exact expiry, e.g.
   `NQ 12-26`). Right-click → Indicators → `MlesV12CaptureHost` →
   set `CaptureFolder` → OK.
   - Default if left blank: `Documents\MLES_Capture`
   - The folder path must NOT contain the words `analysis`, `docs` or
     `scratchpad` — a built-in guard refuses those paths.
6. Repeat step 5 on a **MNQ front contract** chart.
   **Both NQ and MNQ are required.** The auditor pairs them by session
   and fails a batch if they do not overlap by at least 50%. ES is
   optional and not needed.
7. Leave both charts open.

### Confirm it is actually running (do this once, now)

Open the capture folder. Within a minute you should see files named:

```
MLES12_NQ_NQ 12-26_20260901_<runId>_quotes.csv.partial
MLES12_NQ_NQ 12-26_20260901_<runId>_trades.csv.partial
MLES12_NQ_NQ 12-26_20260901_<runId>_depth.csv.partial
MLES12_NQ_NQ 12-26_20260901_<runId>_quality.csv.partial
```

Open the `_quality` file in a text editor. A `HEARTBEAT` line should
appear roughly every 30 seconds with row counts, queue depth and book
readiness. **That file is the only place heartbeats appear** — the
recorder deliberately does not call `Print()`, so nothing shows up in
the NinjaScript Output window. An empty Output window is normal and
is not a fault.

---

## PHASE 1 — Passive capture (weeks to months)

Your job in this phase is almost nothing. Leave NinjaTrader running.

### Weekly, 60 seconds

1. Look in the capture folder for any file named `*_RECOVERY.json`.
   **If one exists, a run did not close cleanly.** Keep everything,
   change nothing, and tell me — that file is the diagnostic.
2. Confirm `..._manifest.json` files are appearing — one per completed
   run. A run finalizes automatically at the 18:00 ET roll.
3. Count the manifests. That is your session count.

### Rules that matter

- **Never edit, re-save, rename or "clean" any capture file.** Every
  manifest carries a SHA-256 that must match the recorder's bytes
  exactly. Opening a CSV read-only is fine; saving it destroys the run.
- **Never send `.csv.partial` files.** A partial with no manifest next
  to it means the run did not close cleanly.
- **Contract roll week:** run instances on BOTH the old and new
  contracts simultaneously. Each contract records to its own isolated
  run automatically — you do not need to stop or restart anything.
- **Restarting NinjaTrader is safe.** A restart mints a new capture
  instance; finalized files are never appended to or overwritten.
- A session = one 18:00 ET to 18:00 ET period. Recording continues
  across that boundary by itself. That continuation is the v1.2 fix,
  and the first genuine rollover is the thing worth checking.

---

## PHASE 2 — At roughly 20 complete sessions

This is a verification checkpoint, **not** a strategy test. No market
outcome, return or P&L is computed or looked at.

### The audit command

Open a terminal in the unzipped `MROF_V1_Engine` folder:

```
python3 -c "import sys; sys.path.insert(0,'2_Analysis_Engine'); \
import mles_v12_audit as AU; \
r=AU.audit_capture('<your capture folder>'); \
print(r['ok'], r['failures'])"
```

- `True []` → the batch is clean.
- `False [...]` → send me the exact failure codes. The batch is
  quarantined; files are never repaired in place.

### What you send me

Send the `..._manifest.json` files FIRST. They are tiny and carry
every hash, row count, sequence boundary and counter. Bulk CSVs follow
only on request.

### What happens then

I build the ingest runner — the piece that connects parsed capture
files to the signal detectors and the research engine. **That code
does not exist yet**, deliberately: nothing in the repository
currently imports both an adapter and the research engine. Building an
outcome path before real data exists is how overfitting gets
manufactured, so it waits for genuine files to be shaped against.

This phase is engineering validation only. It is never used as a
strategy holdout.

---

## PHASE 3 — At roughly 60 complete sessions

The readiness threshold for State-C authorization. Only at this point
does the strategy half of the project wake up:

1. State-C authorization is committed (`research_unlocked()` currently
   returns False because `MROF_V1_STATE_C_AUTHORIZED.json` does not
   exist — that is the hard lock).
2. The A1–A6 tape-scalp logic in `MROF_YT_TapeScalp_Wave.zip` is run
   against real captured sessions for the first time.
3. Results go through the frozen protocol: pre-registered thresholds,
   Romano-Wolf multiplicity control at alpha .05 cumulative, and the
   registry.

Until then that zip stays closed.

---

## Five things NOT done by me, ever — they are yours

None of these have been performed, and none are claimed:

1. Real NinjaTrader **F5 compile**.
2. **Five-minute NQ + MNQ Market Replay smoke test.**
3. **Stop → finalize → audit.**
4. **Restart → finalize → audit.**
5. The **first genuine 18:00 ET rollover audit.**

Software tests in this repository prove recorder behavior only. They
prove nothing whatsoever about profitability.

---

## Quick reference

| I want to... | File / command |
|---|---|
| Install the recorder | `1_NinjaTrader_Recorder/MlesV12CaptureHost.cs` |
| Read install steps | `1_NinjaTrader_Recorder/SETUP_WALKTHROUGH_V12.md` |
| Check it is alive | the `..._quality.csv` heartbeat lines |
| Audit a capture folder | `mles_v12_audit.audit_capture(<dir>)` |
| Understand what to send | `3_Docs/DATA_HANDOFF_V12.md` |
| Verify the whole package | `3_Docs/RECORDER_DEPLOYMENT_V12.md` |
