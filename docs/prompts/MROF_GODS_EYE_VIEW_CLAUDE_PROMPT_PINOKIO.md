# MROF God’s Eye View — Claude build prompt (including Pinokio)

Send this entire file to Claude in the existing MROF project/repository.

---

Build **MROF God’s Eye View**: an interactive research dashboard for my existing NQ/MNQ order-flow project. Implement a working application in this repository. Complete the implementation, meaningful tests, and setup instructions. Work through routine implementation decisions independently.

## Mission

Give me one place to understand:

- Whether recording and data ingestion are healthy.
- Which hypotheses are implemented and ready to evaluate.
- Why a detector is blocked or a setup does not qualify.
- How candles, key levels, tape, and depth interact on data we are allowed to inspect.

Use the God’s Eye View idea of an overview with layers and drill-down inspection. Organize this application around sessions, time, price, levels, and research evidence. The current project is a **read-only scientific study**. Preserve its research protocol throughout this build.

## 1. Inspect the actual project first

Read the current governing instructions, registrations, exposure ledger, source code, report schemas, and tests. Relevant components may include `MlesV12CaptureHost.cs`, `mles_v12_audit.py`, `mrofyt_runner.py`, `mrofyt_pilot.py`, `mrofyt_wave2.py`, and `mrofyt_recover.py`. Resolve actual locations and versions from the repository.

Use the registered specification and implementation as evidence. Previous conversational summaries contain discrepancies. Specifically check:

- The descriptions and direction of A2, A5, and A6.
- The distinction between the original A6 opening window and W2-A4-OPEN.
- Which studies require five prior sessions versus twenty.
- Which A5 inputs actually exist.
- Whether swing levels and Asia labels remain registered but unimplemented.

Document discrepancies. Do not silently resolve them by changing frozen research logic. Inspect schemas and synthetic or explicitly exposed fixtures without opening protected outcome data.

## 2. Enforce the current blind

The stated holdout begins **2026-09-21**. During the blind, only protocol-permitted monitoring information may be shown. Research counts are available at the permitted weekly releases. Confirm the controlling rules in the repository; if rules conflict or permissions are unclear, use the more restrictive interpretation and document it.

Implement permissions in the backend and data-export boundary, not just as hidden frontend controls.

Operational health may show permitted information such as recorder heartbeat, last received event time, file and manifest status, storage availability, connection gaps, book readiness, NQ/MNQ capture coverage, and audit failures.

Protected research information must not reach the frontend, exports, logs, caches, or any AI integration. In particular, protected sessions must not expose prices, candle charts, tape, depth replay, signal directions, exact signal timestamps, event-level feature values, forward markouts, outcome summaries, or details that let someone reconstruct outcomes.

Weekly research counts must come from an approved released summary. Do not expose continuously updating counts or arbitrary filters that reconstruct individual events.

Detailed inspection is permitted only for explicitly identified exposed DEV data, clearly labeled synthetic fixtures, or data later released under the existing research protocol. Do not assume every date before the holdout is automatically approved; consult the exposure ledger.

December arriving must not automatically unlock results. Follow the existing release procedure. Do not create the absent outcome-unlock file. Unknown permission, mixed permitted/protected requests, and missing exposure records must fail closed.

## 3. Build four main views

### A. Recording health

Show separate NQ and MNQ status and paired coverage. Include, when available:

- Exact contract, session, recorder build, run, and segment.
- Latest heartbeat and report timestamp.
- Expected recording coverage versus observed coverage.
- Shared gaps as well as gaps in only one instrument.
- Manifest, hash, row-count, and sequence audit results.
- Dropped events, write errors, disconnects, and book resets.
- Depth coverage on both sides.
- Orphaned or partial files.
- Disk space and source accessibility.

A paired-coverage ratio of 1.000 must not imply a complete session: both instruments can be missing the same hours. Distinguish `LIVE`, `STALE`, `DISCONNECTED`, `UNAVAILABLE`, and `UNKNOWN`. An unreadable folder or failed scan must never become a clean zero report. Preserve the last successful result with a visible stale label and the current error. Use in-app health alerts; keep capture and recovery actions outside this dashboard.

### B. Hypothesis readiness

Create a registry-driven view for A1–A6 and the actual registered wave-two arms: `W2-A1`, `W2-A4r`, `W2-A4f`, `W2-A4-OPEN`, `W2-A4r-z15`, `W2-A4r-HC`, `ARM-B1`, `ARM-B2`, and `ARM-C`. Verify names and meanings against the current registry.

For each hypothesis show its registered purpose and version, whether implementation is complete, required inputs, baseline requirements, applicable time window and level set, readiness and blocking reasons, approved weekly counts when available, and links to the relevant specification and implementation.

Use distinct statuses for `NOT_IMPLEMENTED`, `NOT_WIRED`, `INSUFFICIENT_PRIOR_HISTORY`, `NO_QUALIFYING_OBSERVATIONS`, `INVALID_OR_MISSING_DATA`, `READY`, `CONDITION_FALSE`, and `UNRESOLVED_SPEC_MISMATCH`.

“Unavailable” alone is insufficient. An incomplete feature must not be described as merely waiting for more sessions. A valid non-setup must not be described as missing data. For protected data, detailed funnels and readiness breakdowns must obey the existing monitoring permissions; if permission is unclear, leave that breakdown unavailable.

Do not rank hypotheses by profitability, calculate new significance tests, or interpret firing frequency as evidence of an edge.

### C. Data quality and provenance

Provide a session timeline and inspector showing capture and audit status, contract identity, gaps and affected intervals, manifest provenance, recovery history, source report, source version, and generation time.

Distinguish original finalized capture, recovered capture, historically supplemented price data, and missing order-flow data. Historical candles may support a level calculation when the research protocol allows it. They must never be represented as reconstructed historical depth.

Account for futures session boundaries and `America/New_York` daylight-saving time. Keep UTC available in technical details.

### D. Exposed-data replay

Build a synchronized inspection view using approved exposed data or synthetic fixtures: candles and price, key-level overlays, time and sales, bid/ask quotes, available market depth, and detector state and feature evidence.

Allow **session → instrument/contract → level approach → decision window → underlying events**. Include play, pause, stepping, and a synchronized cursor where supported. Show 10-second decision windows explicitly. Offer other resolutions only when the existing pipeline supplies them or an approved display aggregation can construct them causally. Display aggregations must not modify detector inputs.

For an exposed event, explain which level was approached, which measurements were available, which conditions passed or failed, whether the event was suppressed or deduplicated, whether NQ was the signal source, and the distinction between a raw firing and a deduplicated event. These are research events; do not turn them into simulated trades.

Show gaps and invalid book periods as gaps. Do not interpolate invented liquidity. Distinguish displayed size, executed volume, and inferred withdrawal. Show inferred aggressor confidence and unknown classifications when available. Do not identify an individual hidden buyer, seller, iceberg, or spoofer from aggregated MBP data.

## 4. Levels and context

Discover the actual active level registry. The reported fourteen base levels are:

`YDAY_HIGH`, `YDAY_LOW`, `LWEEK_HIGH`, `LWEEK_LOW`, `OVERNIGHT_HIGH`, `OVERNIGHT_LOW`, `GLOBEX_OPEN`, `CASH_OPEN_0930`, `SESSION_VWAP`, `VWAP_UPPER`, `VWAP_LOWER`, `PP`, `M2`, `M3`.

Verify exact identifiers and definitions before displaying them. For permitted replay, show when each level became available, its source, and its validity status. Never display a future-completed level as though it was known earlier.

Also inventory swing highs and lows, one-hour supply/demand zones, EMA context, ADR, psychological levels, Asia conditioning, and RVMR. Show these only according to their actual implementation and registration status. Registered-but-unbuilt items should say so. Do not build new research features or activate new level families as part of this dashboard.

## 5. Keep the recorder laptop light

The reported capture volume is approximately **23 GB per day**, and laptop reliability matters. Use small derived monitoring snapshots and approved reports for normal dashboard refreshes.

- No full raw-data scan on page load or refresh.
- No whole-day CSV files loaded into browser memory.
- Bounded reads and caching for permitted replay.
- Separate dashboard work from the recorder process.
- Never interrupt recording to build or launch the dashboard.
- Never modify raw captures or finalized manifests.
- Display freshness and provenance of cached results.
- Allow the UI to run on another computer using sanitized summary exports.

If an exporter is needed, make it a separate, bounded process that emits only permitted fields. Use the existing project stack when practical. Keep dependencies minimal and pinned. Start locally with straightforward Windows launch instructions.

A continuously running LLM is unnecessary. Compute facts deterministically. Keep voice and AI commentary out of the initial version.

## 6. Visual design

Create a polished, readable dark dashboard with a compact health/status header; navigation between the four views; an overview that makes blocked inputs and recording failures obvious; a detailed inspector for selected items; consistent color meanings with text labels; and restrained animation.

The main interaction should be selecting a session or hypothesis and understanding the evidence behind its status. Avoid decorative elements that obscure values or consume substantial resources. Keep synthetic demo data visibly labeled. Missing integrations must display a clear unavailable state.

## 7. Verify important behaviors

Use synthetic fixtures and explicitly approved exposed data. Test that:

- Protected prices, directions, timestamps, and outcomes cannot be retrieved through APIs, exports, caches, or alternate routes.
- A request spanning exposed and protected data is rejected.
- Weekly counts cannot be turned into event-level monitoring.
- Unreadable storage produces `UNAVAILABLE`, not zero.
- Cached results are clearly marked stale after a source failure.
- Shared NQ/MNQ outages remain visible.
- Missing code and insufficient history produce different statuses.
- Session boundaries and daylight-saving transitions work.
- Research identifiers and counts agree with approved source reports.
- Dashboard activity does not write to research captures or alter frozen detector behavior.
- Replay remains bounded in memory and handles missing depth honestly.

Use applicable existing synthetic regression tests. Report actual commands, results, and any tests that could not run. Do not describe synthetic tests as evidence of predictive ability or positive EV.

## 8. Add optional Pinokio support

After the dashboard works through its normal Windows launcher, add a **Pinokio one-click launcher** for convenient local use. Check the current installed Pinokio version and its script conventions rather than guessing a format. Pinokio must remain optional: the ordinary Windows launcher must work independently.

The Pinokio launcher must start and stop **only the dashboard**. It must not start, stop, restart, modify, or install over the NinjaTrader recorder, ingestion jobs, or research pipeline. Keep dashboard dependencies isolated and do not reinstall them on every launch. Do not copy raw capture files into Pinokio or install duplicate research datasets. Configure the dashboard to read only its permitted summary exports and approved exposed-data sources.

Default to access on the local computer. If the user later runs the dashboard on another computer, document a separate setup using sanitized summary exports and the existing research permissions; do not expose raw or blind data as part of remote setup. Give exact Pinokio installation, launch, and stop instructions. Verify both launch paths, and report honestly if Pinokio itself cannot be exercised in the available environment.

## 9. Deliver a usable application

Provide working source code, a concise architecture and data-permission explanation, documented adapters for the current report schemas, a clearly labeled synthetic demonstration, exact Windows installation and launch commands, a simple ordinary launcher plus the optional Pinokio launcher, configuration instructions for real report locations, test results and measured resource use, a list of genuine missing integrations and blockers, and a short user guide.

Complete the usable build before returning your final summary. If a real report is unavailable, implement its adapter against a documented fixture and identify the real-data integration as unverified.

In the final response give me: **(1)** what was built, **(2)** how to launch normally and with Pinokio, **(3)** what it shows now, **(4)** how the blind is enforced, **(5)** what remains blocked, and **(6)** exact verification results.

The first successful version should help me keep recording reliably and understand research readiness while the study continues.
