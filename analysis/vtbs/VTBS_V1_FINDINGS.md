# VTBS-V1 — FINDINGS

**Verdict: FAILED — 0 of 4 cells. And the failure is the most
informative one the programme has produced in weeks.**

Freeze commit `8dfc2de` (before outcomes). 13/13 tests. DEV
2019-07-04→2026-08-17, 1,689 eligible days, 468 HIGH days. Costs
0.87/1.305. Seeds 20260901/02/03. THIS PROJECT DOES NOT AUTHORIZE LIVE
TRADING.

## 1. Results

| cell | n | stressed/trade | PF_s | perm p | BH q | state p | verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| C1 k=0.15 hold-to-15:55 | 468 | **+2.31** | 1.049 | 0.318 | 0.636 | 0.747 | FAIL (G06–G13b, G16) |
| C2 k=0.30 hold-to-15:55 | 464 | **+3.78** | 1.061 | 0.276 | 0.636 | 0.687 | FAIL (same) |
| C3 k=0.15 exit-13:00 | 468 | −5.12 | 0.883 | 0.784 | 0.784 | 0.947 | FAIL (G05 …) |
| C4 k=0.30 exit-13:00 | 464 | −3.12 | 0.941 | 0.617 | 0.784 | 0.869 | FAIL (G05 …) |

## 2. The three answers hiding in this failure

**(a) The magnitude forecast is real but worthless for this.** The
binding failure is G13: the **unconditional** bracket beats the
HIGH-state bracket in every cell (+6.25 vs +2.31; +7.16 vs +3.78).
Predicted-high-volatility days are *not* better trend-harvest days —
if anything worse (high-overnight-range days contain more two-sided
chop). The programme's one predictive asset — magnitude — does not
convert to EV through range-harvesting structure. That question is now
asked and answered, not just suspected.

**(b) The bracket's positive residue is long-drift beta, not alpha.**
The full-day cells are positive only through the long trigger
(C2: long +11.46 vs short −3.37 per trade; C4 short −9.49). A two-sided
structure in an upward-drifting index degenerates into "sometimes get
long the drift, pay whipsaw for the privilege." Year signs flip with the
market (2022/2024/2025 positive; 2020/2026 badly negative). Sharpe-like
scale: +3.8 per trade against a ~90-pt per-trade sd — CI spans ±14.
Anyone wanting this exposure should hold the index, not day-trade
brackets.

**(c) Morning-only harvesting is negative everywhere** (C3/C4, every
year but one) — consistent with BRK-H1's minute-scale autopsy:
short-window expansion harvesting pays whipsaw and captures nothing.

## 3. Disposition

All four cells `DEAD_FROZEN`; fingerprint class
`BIDIRECTIONAL_RANGE_HARVEST_DAILY` is spent (registry updated). The
LOW-state and unconditional arms are ledgered diagnostics and are not
rescueable candidates. No neighbor, no delay variant, no state
threshold escapes the gate pattern.
