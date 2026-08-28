# MOFAD-V1 — MULTIPLICITY PLAN (frozen before outcomes)

## Within-program correction

- **5 confirmatory cells** (C-F12-1, C-F12-1b, C-F12-2, C-F08-1, C-F08-2).
- Primary inference: day-blocked permutation p per cell, then
  **Benjamini–Hochberg across all 5 cells; a cell passes G12 only at
  q ≤ 0.05.**
- Every diagnostic (terciles, long/short, divergence subgroup, neighbor
  variants, destruction battery) is ledgered in
  `MOFAD_V1_HYPOTHESIS_LEDGER.csv` and can never be promoted to candidate
  status; diagnostics are reported with raw p-values and marked
  non-confirmatory.

## Cumulative programme selection burden

The registry lineage carries **571 prior formal tests** (CCHC cumulative
exposure ledger) plus the ODMC arm; the closure registry
(`MOFAD_V1_SPENT_HYPOTHESIS_REGISTRY.csv`, 72 rows) keeps every dead
hypothesis in the accounting — none is removed from the selection burden.
MOFAD adds 5 confirmatory cells + declared diagnostics. This cumulative
burden is why a positive MOFAD result — if any — is capped at
provisional-exploratory status: the global familywise error over the whole
programme is not controlled at 0.05, and this is disclosed rather than
hidden. Deflated-Sharpe / PBO / SPA are computed only if a candidate
reaches the robustness stage (see freeze §6, G-gates), using the complete
ledger count.

## No fallback rule

If all 5 cells fail, the program ends with the no-candidate conclusion.
Rejected screen proposals (F03 constructions, P-F08-3) and
floor-excluded proposals (P-F12-3, P-F12-4) are **not** run as fallbacks.
