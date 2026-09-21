# NT8_RECORDING_RUNBOOK.md — recording NQ and MNQ, step by step

Written to be followed without prior knowledge of the codebase. It
covers the nine items of the directive's §10 in order.

**This records data. It places no orders. It cannot place orders.**

Status as of this writing: genuine captures exist for 2026-09-01 →
2026-09-04, and **capture has been stopped since 2026-09-04 22:35 UTC**.
Restarting it is the single most valuable thing you can do — see item 7.

---

## 1. The file, the namespace, and where it goes

**Install exactly one file:**

```
src/MlesV12CaptureHost.cs          build 1.2.1
```

Copy it to:

```
Documents\NinjaTrader 8\bin\Custom\Indicators\MlesV12CaptureHost.cs
```

It is a **NinjaScript Indicator**, class `MlesV12CaptureHost`, declared
in `NinjaTrader.NinjaScript.Indicators`. Its worker lives in a private
namespace, `Mles.Capture.V12`, inside the same file. **There are no
other dependencies** — no NuGet package, no add-on, no second file.

**Do NOT install these**, ever:

```
src/MlesV1CaptureHost.cs      archive only
src/MlesV11CaptureHost.cs     archive only
```

Both stop writing at the first 18:00 ET session rollover. That defect is
the entire reason build 1.2 exists. They ship only so the lineage can be
audited.

The one setting the indicator exposes is **`CaptureFolder`**. Either
leave it **completely blank** (it then defaults to
`Documents\MLES_Capture`) or type a **full path with a drive letter**,
e.g. `D:\MLES_Capture`. Never type a relative path like
`Documents\MLES_Capture` yourself — NinjaTrader resolves it against its
own working directory and the files land somewhere you will not find.

## 2. Compile, and find it in the platform

1. In NinjaTrader: **New → NinjaScript Editor**.
2. Press **F5**.
3. The Errors pane at the bottom must be **empty**.

If F5 reports errors, stop and send the exact error text. Do not
work around it. A previous build failed F5 with `CS0246`/`CS0103` because
of a namespace mistake, and that was only ever caught by a real compile.

**No stub or test harness is ever compiled into NinjaTrader.** The
repository contains `nt8_stubs_v12.cs` for the automated suite only. A
stub compile is not an API validation and never substitutes for F5.

After a clean F5 the recorder appears in any chart's indicator list as
**`MlesV12CaptureHost`**, described as "MLES-CAPTURE-1.2
permanent-lifecycle capture (zero orders)".

## 3. Pick the right contracts, and confirm real Level II

**Contracts.** Use the **front month** for both instruments, and use
the *same* month for both — currently `NQ DEC26` and `MNQ DEC26` after
the September→December roll. In NinjaTrader, `NQ ##-26` selects the
active contract; confirm the resolved contract in the chart's data
series window, because the manifest records it and the auditor fails a
contract mismatch.

**Level II entitlement.** Depth is a separate market-data subscription
from Level 1. To confirm you actually have it:

1. Open **New → SuperDOM** on NQ.
2. You must see **ten price levels with sizes on both sides**, updating
   continuously.

If you see only the inside bid/ask, or the ladder is empty, you do not
have depth entitlement and the recorder will write a depth file with
almost nothing in it. Fix that with your data provider before recording
anything. Repeat the check on MNQ — the two are entitled separately.

## 4. Attach it, and confirm both instruments are recording

Use **two charts** — one NQ, one MNQ. Do not switch one chart between
instruments; that produces two half-sessions instead of two sessions.

Attach exactly **one** instance per instrument. It is easy to end up with
several by re-applying the indicator; a previous session accumulated
four NQ and seven MNQ instances, all writing byte-identical duplicates.
Check the indicator list on each chart and remove every duplicate.

About a minute after attaching, look in the capture folder. Per
instrument you should see four files growing:

```
MLES12_NQ_NQ_DEC26_<session>_<instance>-R001_depth.csv
MLES12_NQ_NQ_DEC26_<session>_<instance>-R001_quotes.csv
MLES12_NQ_NQ_DEC26_<session>_<instance>-R001_trades.csv
MLES12_NQ_NQ_DEC26_<session>_<instance>-R001_quality.csv
```

Health checks, in order of what actually goes wrong:

| Check | What good looks like |
| --- | --- |
| `..._depth.csv` | By far the **largest** file. On a real session it dwarfs the others — depth is ~90% of all events. If it is small or static, go back to item 3. |
| `..._trades.csv` | Grows steadily during active hours. |
| `..._quotes.csv` | Grows steadily. |
| `..._quality.csv` | Small. Holds heartbeats and connection events. |
| Both instruments | All four files present for **NQ and MNQ**, in the same folder. |

The `quality.csv` file is the heartbeat: it carries `BOOK_READY`,
`DISCONNECT`, `RECONNECT` and `BOOK_RESYNC_START` rows. Depth is only
trusted between a `BOOK_READY` and the next disconnect.

## 5. Five-minute smoke test — engineering data, clearly labelled

Do this **once**, before any long run, and label the output
**ENGINEERING — not research data**.

1. Attach the recorder to both charts during regular trading hours.
2. Let it run **five minutes**.
3. Remove the indicator from both charts (this finalizes the run).
4. Confirm a `..._manifest.json` appeared for each instrument.
5. Run the audit of item 8 against that folder.

A pass means: manifest present, `ok=True`, depth rows in the tens of
thousands, both depth sides present, all three depth actions present.

**These five minutes are a functional test of the plumbing.** They are
not a sample, not a session, and not evidence about the market. Move
them out of the capture folder afterwards so they never enter research.

## 6. Stop safely, verify, and hand off

**To stop cleanly:** remove the indicator from the chart, or close
NinjaTrader normally. Either path runs the finalizer, which flushes,
closes and hashes every file and writes the manifest.

**Never** end NinjaTrader from Task Manager while recording. A killed
process leaves `.csv.partial` files with no manifest — that run is
unverifiable and is discarded. (One such orphan already exists from a
crash on 2026-09-03; move it out of the capture folder.)

**A run is complete only when its `..._manifest.json` exists.** The
manifest holds every file's SHA-256, byte count and row count, plus
sequence ranges, connection segments, depth side/action counts and the
overflow/drop/write-error counters.

**Verify before sending:**

```
python3 analysis/mrofyt/mles_v12_audit.py "<capture folder>"
```

**To hand off:** send the **manifests first** — they are a few KB each
and they let the integrity chain be checked before any bulk transfer.
Then send the bulk CSVs on request. **Never edit, re-save, "clean" or
re-zip-and-unzip a CSV**: the manifest hash must match the recorder's
bytes exactly, and any edit breaks it permanently.

> This is exactly where the programme currently stands: 29 manifests
> were received, but only 15 runs — all from one date — arrived with
> their bulk CSVs. **The bulk CSVs for sessions 20260902–20260905 are
> the single missing artifact blocking every research question.**

## 7. What stays running, what matters, and how to recover

**Leave both charts running continuously.** The recorder has a permanent
lifecycle: it rolls its own files at 18:00 ET without stopping, and six
such rollovers have already been verified clean (millisecond gaps, a
`SESSION_ROLL` close reason, same instance ID, `R001` → `R002`).

**Overnight matters.** The 18:00 ET Globex open and the overnight
session are where overnight highs and lows form, and those are active
levels the strategy needs. A day-session-only capture cannot build them.

**How to spot a failure:**

- a `.csv.partial` with no matching manifest → that run crashed;
- `quality.csv` filling with `DISCONNECT` rows → feed trouble;
- the depth file no longer growing during active hours → depth
  entitlement or subscription lapsed;
- a manifest with non-zero `queueOverflows`, `droppedRows` or
  `writeErrors` → the machine could not keep up.

**If the laptop sleeps or reboots, or NinjaTrader disconnects:** you lose
only the interval you were down. Reattach the indicator to both charts;
a new run starts and the audit reconciles the gap. Disable sleep and
hibernation on the capture machine.

**Contract roll:** at the quarterly roll, update both charts to the new
front month. The recorder writes the exact contract into every filename
and manifest, and the auditor treats a roll as a boundary — it never
aggregates across one. Install build 1.2.1 at the roll if you have not
already.

**Disk:** measured at ~22.9 GB per session-day for the NQ+MNQ pair, so
roughly 480 GB per month. Sixty sessions is about 1.4 TB. Point
`CaptureFolder` at an external drive with a full drive-letter path.

## 8. Ingestion, and how to see whether research is still gated

Manifest-first, in this order:

```
python3 analysis/mrofyt/mles_v12_audit.py  "<capture folder>"
python3 analysis/mrofyt/mrofyt_runner.py   "<capture folder>" --out ledger.json
python3 analysis/mrofyt/mrofyt_pilot.py    "<capture folder>" --out pilot.json
python3 analysis/mrofyt/mrofyt_wave2.py    "<capture folder>" --both --out wave2.json
```

All four stream at flat memory — a 5 GB depth file is fine. The
wave-two pass (`--both` = real levels plus the placebo arm) is a
second full ingest, so budget about twice the pilot's wall time; it
withholds validation-session markouts exactly as the pilot does.

A healthy audit summary looks like:

```
audit ok=True failures=0 manifests=<n>
  NQ   20260902 <run-id>   rows=27009283  ok=True  build=1.2.1 levels=30/30(run) lat_p50=243ms
  MNQ  20260902 <run-id>   rows=30507789  ok=True  build=1.2.1 levels=30/30(run) lat_p50=258ms
  pair 20260902 overlap=1.000 (NQ runs 2, MNQ runs 2)
```

`ok=True` on every run and a pairing overlap near 1.000 is the target.
`RUN_AUDIT_FAILED / MISSING_FILE` simply means that run's bulk CSVs have
not been transferred yet — it is not corruption.

**How to see whether research is gated.** The runner prints:

```
MROF-YT-RUNNER-1.2.1  outcomes=LOCKED
```

`outcomes=LOCKED` means no fill, stop, target, R or P&L can be computed
by anything in the pipeline. The lock is a file check: research opens
only when `analysis/mrof/MROF_V1_STATE_C_AUTHORIZED.json` exists **and**
records both a readiness-freeze commit and all gates passed. That file
does not exist today. Asking for outcomes anyway raises
`RuntimeError: STATE-C LOCKED`, and so does
`mrofyt_exits_v017.research_driver()`.

## 9. Market Replay backup — and what Tick Replay cannot do

**Market Replay is a backup source, not a substitute**, and its output
must be kept in a **separate folder** from live capture so the two never
mix in one audit.

To use it: **Tools → Historical Data → Load**, choose **Market Replay**,
download the days you want for NQ and MNQ, then run the recorder against
a Market Replay connection. The files it writes are structurally
identical to live ones, so the same audit applies — but label the folder
`REPLAY_` so a replay day is never counted as an independently captured
session.

**The limitation that matters:** NinjaTrader's **Tick Replay** is not
the same thing and **does not give you Level 2 depth**. It reconstructs
bar-by-bar calculations from historical *tick* data — trades and, at
best, best bid/offer. There is no ten-level book in it. Any analysis of
walls, absorption, replenishment or depletion is impossible from Tick
Replay by construction. Market Replay data is also only available for a
limited recent window and only for instruments you have downloaded.

That is precisely why the recorder exists: **the ten-level book is not
recoverable after the fact.** Every hour it is not running is an hour of
depth data that cannot be obtained later, at any price.

---

## Not done here, and why

Real **F5 compilation** and the genuine **five-minute smoke test**
remain **user-side**. This environment has no NinjaTrader, no Windows
and no live feed. Compiling the test stubs proves nothing about the real
API — a stub compile is not a substitute, and instructions to compile
stubs into NinjaTrader are never given.
