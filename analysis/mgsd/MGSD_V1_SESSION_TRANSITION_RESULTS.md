# MGSD-V1 — SESSION-TRANSITION AND PREMARKET→OPEN RESULTS

## Premarket→open influence study (9A)
1,759 qualifying days; 8 causal predictors (all ending ≤ 09:29 ET) ×
4 open-forward outcomes = 32 tests; blocked-permutation p; BH within
study; controls (gap, overnight return/range, relative volume, weekday)
via OLS residualization; placebos: ±1/±5-day date-shift, 200× random
day-pairing, weekday comparison. Full table:
`MGSD_V1_PREMARKET_OPEN_RESULTS.csv`.

**Result: 0 of 32 cells at BH q ≤ 0.05.** No overnight or premarket
predictor added measurable information about the open-forward session
beyond chance, before controls were even needed. The deliberate
future-feature negative control was detected at ρ = 1.000 — the causal
harness demonstrably catches leakage, so the null is not an artifact of
a broken harness.

Answer to the frozen questions: overnight/premarket information did NOT
add value beyond the control set; no premarket→open effect existed to
survive date-shift or random-pairing destruction (placebos were run and
reported anyway); no premarket-entry or premarket-informed-open strategy
earned candidacy.

## Session-transition strategy families
- F16 late-premarket trend → open continuation: best stressed EV
  +3.53 pt (n 521), PF 1.13, WR 18–19% — fails quality floors.
- F17 midday-range break → afternoon: best +3.06 pt — fails floors.
- F18 closing momentum 15:31→16:00: best +4.27 pt (small n) — fails.
- F15 session drift: OPEN2CLOSE long +5.98 pt stressed with CI low
  +0.19 (the equity intraday drift) — PF ≈ 1.07 and EVR below floors →
  fails G04. ON2OPEN/ON2CLOSE variants all fail.
- F09 gap-fade (overnight inventory → open adjustment) is the standout
  near-miss: see DEV results — fails §8 profile floors (WR 20–36%) and
  BH.

No session-transition family produced a candidate.
