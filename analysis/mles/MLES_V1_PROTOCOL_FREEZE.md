# MLES-V1 — FREEZE A (CAPTURE AND SCHEMA FREEZE)

Committed **before any captured message is treated as research data**.
Freeze A commit hash is recorded in every Mode A artifact via the commit
that introduces this file. Freeze B (analysis freeze) does **not** exist
yet and may only be written after readiness and separate user
authorization, without viewing any outcome label.

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

## 1. Frozen: source streams and fields
Per `MLES_V1_CAPTURE_SCHEMA.json`, schema `MLES-CAPTURE-1.0.0`.
Instruments NQ, ES, MNQ. Streams quotes / trades / depth / quality.
Field lists are frozen as written there.

## 2. Frozen: timestamp semantics
Four clocks per row (`tExch`, `tCb`, `tRecv`, `tMono`). **Causal rule:
where exchange and receive time disagree, the later availability time
governs any trading simulation.** A completed bar may be used only at or
after its close timestamp; a message only at or after its availability
timestamp.

## 3. Frozen: event ordering
Per-stream monotonic arrival `seq` assigned by the recorder in original
arrival order. No provider sequence ID exists on this feed. Replay must
reproduce the identical feature stream from append-only files in arrival
order.

## 4. Frozen: file format and versioning
`MLES_<inst>_<session>_<stream>.csv`, append-only, UTF-8, header row
fixed by schema. Session = ET date rolling at 18:00 ET. Manifest is
atomic JSON with per-file SHA-256. **Schema changes are permitted only
for engineering reasons, must increment the version, and may never be
motivated by return outcomes**; days spanning a material change are
excluded from research.

## 5. Frozen: integrity checks and thresholds
`analysis/mles/mles_integrity.py` and the PASS/WARN/FAIL table in
`MLES_V1_CAPTURE_HEALTH_SPEC.md`. FAIL days are excluded from research.

## 6. Frozen: outcome-blinding controls
Per `MLES_V1_PARTITION_AND_BLINDING.md`. Health monitoring may run
during protected partitions; outcome computation may not. Enforced
structurally (no analysis imports; outcome-bearing columns rejected).

## 7. Frozen: candidate-family budget
Per `MLES_V1_CANDIDATE_BUDGET.json`: **4 families max, 3 candidates per
family, 2 horizons per candidate, 12 candidates total.**

- **M1** directional high-range session vs two-sided chop — the existing
  magnitude model is used as **frozen context only** and is never
  retrained; M1 must show incremental value beyond magnitude state,
  realized volatility, time of day, and a price-only control. VTBS and
  any other daily bracket may **not** be resurrected here.
- **M2** executable ES→NQ information transfer — requires proven clock
  quality; if uncertainty is not materially smaller than the claimed
  lead, this is descriptive only and may **not** be called lead/lag.
- **M3** absorption / replenishment / liquidity vacuum — requires the
  feed to separate cancellations from trades; if it cannot, the
  mechanism is rejected as **unidentifiable**.
- **M4** OFH13/OFH14 execution overlay — parent signal, direction,
  eligibility and exits are **immutable**; an overlay that skips parent
  trades, flips direction, alters the setup or changes the horizon is a
  new derivative strategy and is **prohibited**.

Multiplicity plan: one primary per family with the family's confirmatory
alpha; Holm across the four primaries; BH/FDR across permitted
secondaries. An unadjusted `p` is never confirmation. Ideas rejected by
the spent screen still count toward the search burden if real outcome
information was visible when they were rejected.

## 8. Frozen: what is NOT in this freeze
Event definitions, feature formulas, lookbacks, thresholds, directions,
horizons, latency rules, exits, costs, models, clustering, statistical
tests and promotion gates belong to **Freeze B** and are deliberately
absent. Writing them now, before a single message has been captured,
would be a pre-commitment made in ignorance of the feed's real
properties (tick cadence, depth availability, clock quality).

## 9. Standing prohibitions carried into every later mode
No reconstruction of ticks/quotes/depth/fills from bars. No treating 1m
aggregates as messages. No spread inferred from candle ranges. No
midprice fills. No touch-is-a-fill. No queue claim from MBP. No
resurrection of a dead hypothesis under an execution label. No
redesign of OFH13/OFH14 as "execution improvement". A negative-gross
parent stays dead — tick execution may never rescue it.
