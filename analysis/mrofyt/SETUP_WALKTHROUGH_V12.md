# SETUP_WALKTHROUGH_V12.md — plain-language install (v1.2 ONLY)

The recorder to install is **MlesV12CaptureHost**. The older
MlesV1CaptureHost and MlesV11CaptureHost files are immutable archive
lineage — do not install or attach them.

1. Open NinjaTrader 8 with your live data connection (Level II /
   market depth enabled for NQ and MNQ if your subscription has it).
2. Control Center → New → NinjaScript Editor → right-click
   `Indicators` → New Indicator → any name → replace ALL template text
   with the contents of `1_NinjaTrader_Recorder/MlesV12CaptureHost.cs`
   → press **F5** to compile (expect zero errors).
3. Open a chart for the NQ front contract (exact expiry, e.g.
   `NQ 12-26`) and another for MNQ. On each: right-click →
   Indicators → `MlesV12CaptureHost` → set `CaptureFolder` (default
   `Documents\MLES_Capture`) → OK.
4. Leave the charts open. Files appear as
   `MLES12_<inst>_<contract>_<session>_<runId>_*.csv.partial` and
   finalize automatically at the 18:00 ET session roll — recording
   CONTINUES into the new session by itself (this is the v1.2 fix).
5. Health: open the `..._quality.csv` file — a HEARTBEAT line every
   ~30 s carries row counts, queue depth and book readiness.
   (Heartbeats are in that file only; nothing prints to the
   NinjaScript Output window.)
6. To stop: remove the indicator or close the chart; wait a few
   seconds for `..._manifest.json` to appear. A `_RECOVERY.json` file
   means the run did NOT close cleanly — keep everything and report it.
7. Roll week: run instances on BOTH the old and new contracts; each
   contract records to its own isolated run automatically.
8. Send back the `_manifest.json` files first (see
   DATA_HANDOFF_V12.md).
