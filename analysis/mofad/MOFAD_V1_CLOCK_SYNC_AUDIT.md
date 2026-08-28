# MOFAD-V1 — CLOCK SYNCHRONIZATION AUDIT

**Verdict: no clock-sync claim finer than the 1-minute bar grid is
provable, and no lead/lag claim of any kind is permitted.**

## What exists

- All MNQ streams (price 1m, order-flow 1m, morning 30s) are stamped by
  the NT8 export engine in US/Eastern **bar-close time**. There is no
  exchange timestamp, no receive timestamp, and no sequence number in any
  stream — only the derived bar stamp.
- The ES pilot (42 days, 1m) is stamped by the same NT8 engine on the same
  machine clock, so ES and MNQ bars are aligned to the *same* 1-minute
  grid; the ES↔NQ pilot certification (`docs/ES_NQ_DATA_V1_AUDIT.md`
  ADDENDUM, gate 2) proved stamp-grid agreement at 1-minute resolution.

## What follows (frozen rules)

1. Same-machine same-grid alignment supports **at best 1-minute**
   contemporaneity. Message ordering inside a minute is unobservable.
2. Per master prompt §5.5: a lead/lag claim requires clock resolution
   materially finer than the claimed lag. The finest defensible lag here
   is ≥ 2 minutes on a 1-minute grid — and the only synchronized span is
   42 days, and 1m cross-market price mechanisms are already spent
   (XMARKET-V1, 0/8). Therefore **F09/F10 lead/lag research is not run**.
3. Intra-market causality remains enforceable at bar granularity: a
   feature computed from bar T (close-stamped) may act no earlier than the
   open of bar T+1. This is the same convention proven in every prior
   engine and is retained for the READY families.
4. DST handling: the 1m grid is DST-consistent (sole anomaly 2022-11-06,
   classified in Phase 0); the OF capture inherits NT8's ET session
   template; the maintenance break 17:00–18:00 ET is observed in both.

No millisecond, second, or sub-bar latency figure will be quoted anywhere
in MOFAD-V1: `NOT IDENTIFIABLE`.
