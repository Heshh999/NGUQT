# MLES-V1 — CAPTURE SPECIFICATION

Recorder: `src/MlesV1CaptureHost.cs`, schema `MLES-CAPTURE-1.0.0`.
Machine-readable schema: `MLES_V1_CAPTURE_SCHEMA.json`.

## Instruments and streams
One recorder instance per instrument — **NQ** (directional/liquidity
discovery), **ES** (cross-market), **MNQ** (execution and cost). All
instances in a session share a `runId` so streams are relatable; every
row carries `instrument` and full `contract`.

Streams: BBO changes (price + displayed size), last trades, depth
updates for every supplied level, and connection/session/quality events.

## Every row carries
`schema, runId, session, instrument, contract, stream, seq, tExch, tCb,
tRecv, tMono` plus stream-specific fields and `flags`
(`DISCONNECTED|BOOKRESET|CROSSED`).

- **Four clocks** so causality is auditable: exchange time, platform
  callback time, UTC receive time, and a monotonic Stopwatch counter.
  When exchange and receive disagree, **the later availability time
  governs** any future simulation (§5).
- **Full BBO on every quote row** — not just the side that changed.
- **`seq`** is the recorder's per-stream arrival counter. NT8 supplies
  no provider sequence ID; that limitation is recorded, not disguised.

## Aggressor provenance
`aggrRaw` is written **empty** — this feed supplies no exchange
aggressor flag. A separate versioned classification is stored in
`aggrInf` / `aggrMethod` (`QUOTE_TEST_v1`) / `aggrConf`
(HIGH at/through the quote, LOW inside the spread, NONE exactly at mid).
Raw fields are never overwritten with derived values.

## Depth type
`bookType=MBP`. Market-by-price gives level sizes, not order identity.
**Queue position and passive-fill proof are `NOT IDENTIFIABLE`** from
this feed and must never be claimed.

## Sessions, files, integrity
Session ID is the **ET session date, rolling at 18:00 ET**. Files are
`MLES_<inst>_<session>_{quotes,trades,depth,quality}.csv`, opened
append-only, flushed every heartbeat (~30 s), and closed at rollover.
A `MLES_<inst>_<session>_manifest.json` is then written **atomically**
(temp file + move) with row counts, first/last receive times, quality
counters, and a SHA-256 per file.

## Safety
Indicator only — no order API of any kind (grep-tested). Refuses to
write into any path containing `analysis`, `docs`, or `scratchpad`.
Logs no account or credential data. Writes no derived feature and no
outcome value: derived features must live in separate versioned files
with parent hashes, produced later and never by the recorder.

---
Freeze A commit: `c40f39a18a3741836b7849d0e2ab3c758c0e67e5`
