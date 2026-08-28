# MOFAD-V1 — CAPTURE-ONLY PROGRAM

Missing data are the binding constraint of this program
(`MOFAD_V1_DATA_AUDIT.md`). This spec defines exactly what must be
captured, by what code, with what integrity guarantees, so that the
CAPTURE_ONLY families (F01/F02/F04/F05/F06/F07/F10) and the INSUFFICIENT
families (F09/F11) can become runnable in a future program. **The capture
program places zero orders and reads zero outcomes.**

## 1. Recorder code (implemented, compile-verified)

`src/MofadV1MicroCaptureHost.cs` — a NinjaTrader 8 **Indicator** (not a
Strategy: it is structurally incapable of order submission; it contains no
order API call of any kind). One instance is attached per instrument
(MNQ, NQ, ES). It records, per instrument per UTC day:

| file | content |
|---|---|
| `…_quotes.csv` | every L1 best-bid/ask price+size update, seq + utcRecv + utcExch |
| `…_trades.csv` | every last-trade print with size and the prevailing best bid/ask + sizes |
| `…_depth.csv` | every L2 market-by-price add/update/remove with side, level, price, size |
| `…_quality.csv` | 30s heartbeats with cumulative sequence counters, >10s gap alarms, disconnect/reconnect markers, locked/crossed flags, session start/end |
| `…_manifest.txt` | daily immutable SHA-256 per file |

Details:
- **Clocks**: exchange timestamp as delivered by NT8 and local receive
  timestamp, both stored as UTC ISO-8601 at native .NET precision
  (100 ns ticks); ET renderings are derived downstream and covered by the
  existing DST-tested rendering utilities, never stored as primary.
- **Sequence**: per-file monotonically increasing sequence numbers; feed
  resets appear as RECONNECT rows in the quality file.
- **Aggressor side**: NOT inferred at capture. Trade rows carry the
  prevailing quote so a classification rule can be frozen downstream and
  validated; NT8's own bid/ask trade marking, when present in a future
  provider upgrade, is stored additively, never substituted.
- **Depth type**: NT8 retail feeds deliver market-by-price. The `mbo`
  column is fixed at `MBP` so no order-level queue reconstruction can ever
  be silently claimed from this capture.
- **Verification status**: compile-verified against the repository's NT8
  API stub harness (`mcs`, COMPILE-CLEAN). Deployment onto the user's
  live NT8 instance requires the user to attach the indicator; that step
  is outside this session's authority (no new logins, no live platform
  actions). Until deployed, this remains implemented-but-idle.

## 2. Derived bars

Deterministic 30-second bars are built downstream from `…_trades.csv` by a
separate batch job (never inside the recorder), stored separately from raw
messages, with the aggregation proven exactly against overlapping 1m data
(same proof pattern as the committed 30s→1m proof, 17,190/17,190 exact).

## 3. Authenticated events (spec only — requires new authority)

Ingestion requires an official/authenticated source (agency feed or
licensed vendor). Required fields are in `MOFAD_V1_CAPTURE_SCHEMA.json`
(`events` stream): stable event id, class, official scheduled UTC
timestamp + timezone, actual publication timestamp, actual/consensus/
prior/revision values where licensed, revision chain, cancellation
markers, source id + source hash. **Blocker**: no authenticated source is
configured, and connecting one needs separate authorization. Reported,
not bypassed.

## 4. Shadow order log (spec only — requires separate authorization)

Before any execution claim, a shadow log per §5.4 of the master prompt:
decision ts → order-send ts → ack ts → fill/partial/cancel/reject ts,
order type, limit price, requested/filled qty, arrival bid/ask/mid, fees,
realized/effective spread, slippage vs arrival mid, missed orders,
disconnects. Paper and broker fills labeled separately. Not implemented
here: any order pathway — even simulated-order submission inside NT8 —
exceeds capture-only authority.

## 5. Outcome blindness

Capture integrity summaries contain counts, gaps, and hashes only. No
return, P&L, or strategy metric may be computed from forward capture until
a hypothesis and unsealing date are frozen in a successor preregistration.
