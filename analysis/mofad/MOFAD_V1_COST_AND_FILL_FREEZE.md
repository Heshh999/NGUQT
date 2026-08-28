# MOFAD-V1 — COST AND FILL FREEZE (frozen before outcomes)

No quote, spread, latency, or fill data exist
(`MOFAD_V1_EXECUTION_DATA_AUDIT.md`), so costs are **assumed, not
measured**, and are inherited unchanged from the frozen programme model:

| model | round-trip cost | applies to |
|---|---|---|
| gross | 0.00 pt | reporting only — never a promotion basis |
| base | **0.87 pt** | all frozen candidates (commission + 1 tick each side + slippage allowance) |
| stressed | **1.305 pt** (base × 1.5) | all frozen candidates (every entry/exit is RTH) |
| non-RTH stressed | 1.740 pt (base × 2.0) | not binding — no frozen candidate holds outside RTH; retained for completeness |

- MNQ, $2.00 per point, one contract, non-compounded.
- **Market orders only.** Entry/exit at the frozen bar-open prices; the
  cost model carries the spread+slippage burden. Limit orders are
  inadmissible in MOFAD-V1 (no queue/fill evidence — master prompt §12).
- Stops: stop-market; same-bar ambiguity resolved stop-first (adverse);
  gap-through fills at the worse of stop level and bar open.
- Millisecond latency stress: `NOT IDENTIFIABLE` (1m bars). The
  executable delay stress is **+1 full bar on entry** (in the destruction
  battery) — the only honest latency test this data supports.
- No fill-probability model is fitted (nothing to fit it on). Any
  surviving candidate remains provisional pending forward shadow-execution
  calibration under the capture program's shadow-order schema.
