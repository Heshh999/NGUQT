# RECORDER_DEPLOYMENT_v01_3.md — completed deployment runbook

Supersedes the v01.2 `RECORDER_DEPLOYMENT.md` (which stays unchanged,
hash-pinned). Implements every deployment deliverable of the final
prompt (SHA-256 `74ff9a99…`, §Operational data acquisition).
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

## 1. Package audit (done before this runbook claims anything)

`MROF_V1_Engine.zip`: PRESENT, SHA-256 `f4658e9b68f131aa6b568d7034e9a
77c5b3171e799c2056cc10bd629571f7ec2`, 13 files; the recorder `.cs` and
`mles_integrity.py` are byte-identical to the committed repo sources.
The authoritative recorder is EXTENDED-BY-REUSE — no competing
recorder exists.

## 2. Exact code, namespace, install location, F5 compile

- File: `1_NinjaTrader_Recorder/MlesV1CaptureHost.cs`
- Namespace: `NinjaTrader.NinjaScript.Indicators`, class
  `MlesV1CaptureHost : Indicator` (an indicator — it has no strategy
  base class and touches no order API).
- Install: NinjaTrader 8 → New → NinjaScript Editor → right-click
  `Indicators` → New Indicator → replace the template with the file's
  contents (or copy the `.cs` into
  `Documents\NinjaTrader 8\bin\Custom\Indicators\`).
- Compile: press **F5** in the NinjaScript Editor (or Tools →
  Compile). Expect zero errors; the two known benign warnings are
  documented in the MLES freeze.

## 3. Windows, instruments, instances, settings, start/stop

1. Open two charts: **NQ front contract** and **MNQ front contract**
   (exact expiry, e.g. `NQ 12-26` — never a continuous symbol; both
   instances share a `runId`, one recorder per instrument/book).
2. Right-click chart → Indicators → `MlesV1CaptureHost` → set the
   output folder (default `Documents\MLES_Capture\`; must NOT contain
   `analysis`, `docs`, or `scratchpad` — the guard refuses those).
3. **Start** = indicator applied with the connection live. **Stop** =
   remove the indicator or close the chart; the session file closes
   and the manifest is written atomically. Files roll at 18:00 ET.
4. Keep the workstation on from before the Globex open through at
   least 11:35 ET; a morning-only file is labeled partial by the
   integrity checker, per the final prompt.
5. Roll week: run instances on BOTH old and new contracts (declared
   overlap); the parser refuses silent mixing and zones/walls retire
   at rolls.

## 4. Health counters (visible)

The quality stream and 30-second `HEARTBEAT` line carry per-instrument
counters `q=<quotes> t=<trades> d=<depth>` plus `GAP`, `DISCONNECT`,
`RECONNECT`, `TS_REVERSAL`, `LOCKED_OR_CROSSED`, and write-error
events; the session manifest totals trade/bid/ask/depth-bid/depth-ask
rows, gaps, drops, and write errors. Watch the heartbeat advance in
the NinjaScript Output window (bid and ask depth counters must BOTH
advance when Level II is subscribed).

## 5. Five-minute smoke test (SIM or live)

1. Attach both instances (NQ + MNQ) for ≥5 minutes during market
   hours.
2. Confirm all four files per instrument grow (quotes/trades/depth/
   quality) and heartbeats advance for BOTH instruments
   independently (proves separate subscriptions and books).
3. **Ten-level verification**: run the parser on the depth file and
   confirm the maximum observed `level` index reaches your provider's
   depth (10 for CME MBP-10); if fewer, the provider limitation is
   recorded — not disguised.
4. Stop the instances; confirm each `..._manifest.json` appears
   atomically with row counts and SHA-256 per file.
5. Restart the instances; confirm a clean new session/run without
   touching the closed files (crash-recovery = same path: closed
   files are never reopened).

## 6. Read-only order-submission proof

The recorder is an `Indicator` with **no order API calls** — verified
by the frozen MLES test that greps the compiled source for every
account/order/submission API (`SubmitOrderUnmanaged`, `Order`,
`Account.`, etc.) and by class type (indicators cannot submit managed
orders). Start, stop, reconnect, replay, or exception paths therefore
cannot place, change, or cancel an order on any account. Recording is
not permission to paper trade or trade live.

## 7. Redundant Market Replay backup (backup, never substitute)

- Control Center → Tools → Options → Market Data → enable **market
  recording for playback**.
- Keep a Level II or SuperDOM window OPEN for NQ and for MNQ — NT8
  records replay depth only while such a window receives depth.
- Native files live under `Documents\NinjaTrader 8\db\replay`; back
  them up after close, unchanged.
- Run one sample replay parity check against the MROF recorder before
  relying on it for recovery. Replay is a redundancy layer; it never
  replaces the loss-audited raw schema.

## 8. Completion status

Deployment remains **NOT complete** until the user has performed §2–§5
on their machine: the recorder has never been attached and captured
sessions = 0. Research classification stays `INSUFFICIENT_DATA` until
the required streams and minimum independent sessions exist.
