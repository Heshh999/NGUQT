# MOFAD-V1 — EXECUTION / FILL DATA AUDIT

**Verdict: zero real fills, zero paper/shadow fills, zero latency records
exist. No execution-model calibration is possible. Any statistical
survivor is at most a provisional research candidate pending forward
shadow-execution calibration.**

## Search performed

- This project has never been authorized to place live or test orders
  ("THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING"), so no broker fill
  records can exist.
- The NT8 prospective infrastructure (`docs/NT8_PROSPECTIVE_ENGINE.md`,
  `docs/NT8_PROSPECTIVE_LOGGING.md`) logs *signals*, not orders. The
  forward ledgers are empty of fills: `RVMR_PROSPECTIVE.csv` is
  header-only and no OFH13/OFH14 forward ledger rows exist yet.
- No order-send, acknowledgment, fill, partial-fill, cancel, reject,
  arrival-quote, or fee record was found anywhere in the repository,
  scratchpad, or configured NT8 exports.
- Spreads: no quote data exist (`MOFAD_V1_DATA_AUDIT.md` §1.3), so
  realized/effective spread, adverse selection, and queue position are
  unobservable historically.

## Consequences (frozen)

1. Cost modeling for the READY families continues to use the frozen
   programme cost model: base 0.87 pt round-trip; stressed 1.305 pt RT
   (RTH) / 1.740 pt RT (non-RTH legs), inherited unchanged from the
   MGSD/CCHC freeze lineage. These are assumptions, not measurements, and
   are labeled as such in every result.
2. Limit-order strategies are **inadmissible** in MOFAD-V1 (no queue/fill
   evidence of any kind); only market-order-at-next-bar-open translations
   are allowed, paying the frozen cost model.
3. Latency stress at millisecond granularity: `NOT IDENTIFIABLE`. The
   only executable delay stress available is whole-bar delay (+1 bar),
   which is included in the protocol.
4. The capture program (`MOFAD_V1_CAPTURE_SPEC.md`) specifies the shadow
   order-log schema required before any future execution claim.
