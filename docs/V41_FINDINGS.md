# V4.1 Findings — Confirmatory Verdict on the Full Capture

Date: 2026-08-20. Executes docs/V41_PREREGISTRATION.md (frozen the same
day, before any outcome was viewed) on the verified 7.1-year structure/
entries capture and the 9.5-month order-flow capture.

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

## 1. Audit verdict

PASS with two logged exceptions (chart spot-check user-owned; depth
failed by design) and cost model NEEDS-CONFIRMATION. Full detail in
docs/V41_PHASE0_AUDIT.md. The structure file passed the same
independent battery as the entries: 28,554 rows exact, 0 duplicate
eventIds, 0 causality violations, 0 label-invariant violations, 350
engine CONTROL rows, only known warm-up/end-of-data artifacts in the
per-year distinctness sweep.

## 2. Research ledger summary

- Primary confirmatory hypotheses tested: **8** (H1–H6 registry,
  TR-H1-W, TR-H2-M) — all reported below, none dropped.
- Exploratory cells examined (Lane 2, DEV only): **20**, logged, none
  promoted.
- Prior programme multiplicity carried on the ledger: V4 8 hypotheses
  (0 survived), V5 10 (0 survived) + 8,329-conjunction search with
  permutation control, V4.1 engine phase (no outcome analysis).
- Surviving candidates: **0**. OOS (2024-07→2025-09) and LOCKBOX
  (2025-10→2026-08) remain **untouched** for the structure layer;
  OF-OOS (Jun–Aug 2026) remains untouched.

## 3. Primary confirmatory results

Metric: mean probe-side net points at 60m. Costs per round turn:
gross / commission 0.37 / base 0.87 / stressed 1.37 pt. p_boot =
day-block bootstrap (2000), one-sided. p_perm = within-day permutation
(200). H0 = matched same-architecture structure-only baseline.

### DEV (2019-07-01 → 2022-12-31)

| Hyp | n | mean | net@base | 95% CI | p_boot | p_perm | vs H0 |
|---|---|---|---|---|---|---|---|
| H1 sweep-reversal (ARCH-C) | 1,902 | +0.72 | −0.15 | [−1.56, +3.05] | 0.255 | 0.259 | +2.08 |
| H2 break-continuation (ARCH-B) | 3,042 | +0.00 | −0.87 | [−1.86, +1.76] | 0.503 | 0.060 | +1.27 |
| H3 wick-take (ARCH-A) | 2,500 | +1.52 | +0.65 | [−0.47, +3.56] | 0.058 | 0.005 | +2.68 |
| H4 vector-at-level (ARCH-B) | 3,227 | +1.37 | +0.50 | [−0.29, +3.10] | 0.057 | 0.005 | +2.65 |
| H5 zone-destination (ARCH-B) | 5,918 | −0.17 | −1.04 | [−1.42, +1.09] | 0.607 | 0.582 | +1.10 |
| TR-H1 W+exit-vector (long) | 299 | +1.21 | +0.34 | [−3.76, +6.09] | 0.310 | 0.105 | +2.48 |
| TR-H2 M+exit-vector (short) | 305 | −0.46 | −1.33 | [−5.34, +4.62] | 0.589 | 0.627 | +0.81 |

**BH q=0.05 across the family: nothing passes.** H3 and H4 are the
closest (p_perm 0.005 but p_boot ≈ 0.06; the divergence means the
effect is concentrated in clustered days — exactly what day-block
inference exists to discount).

### VAL (2023-01-01 → 2024-06-30)

| Hyp | n | mean | net@base | p_boot | vs H0 |
|---|---|---|---|---|---|
| H1 | 956 | −0.37 | −1.24 | 0.580 | −1.51 |
| H2 | 1,304 | −1.30 | −2.17 | 0.850 | −2.37 |
| H3 | 1,281 | −2.28 | −3.15 | 0.955 | −3.21 |
| H4 | 1,494 | −0.95 | −1.82 | 0.809 | −2.03 |
| H5 | 2,807 | +0.11 | −0.76 | 0.443 | −0.97 |
| TR-H1 | 131 | +2.99 | +2.12 | 0.172 | +1.91 |
| TR-H2 | 107 | −1.73 | −2.60 | 0.700 | −2.80 |

**Every DEV-positive vector hypothesis flipped sign in VAL, including
the excess over its matched baseline.** H3: +2.68 excess → −3.21.
H4: +2.65 → −2.03. The per-year table shows the mechanism: the whole
vector-conditioned family was mildly positive 2019–2022 and negative
2023–2024, while the unconditional baseline drifted the other way.
The family tracked regime drift; it carried no incremental
information that survived the split boundary.

### H6 (order-flow window, own split)

The frozen conjunction (BREAK at level + delta non-confirmation +
opposing absorption at the event minute) fired **5 times** in OF-DEV
(4 months) and **0 times** in OF-VAL (3 months). The 5 observed went
−12.75 mean against the predicted reversal. Verdict: **insufficient
sample and adverse** — order-flow history insufficient at this
conjunction's frequency, reported as such rather than relaxed.

### The one sign-consistent candidate, reported precisely

TR-H1 (confirmed W + GREEN/BLUE exit vector, long) is the only
primary positive in both splits (+1.21 DEV, +2.99 VAL gross; positive
in 5 of 6 calendar years; base-cost net positive in VAL). It is also
**nowhere near statistical significance in either split** (p_boot
0.31 / 0.17), its CIs span ±6 points, its mirror TR-H2 is negative in
both splits (asymmetry = fragility flag under the prompt's own rule),
and its DEV n is 299. Under the frozen gates it is a **failed
primary** — it does not advance to OOS, and OOS stays untouched. A
successor ("TR-H1 v2") may be preregistered as a NEW hypothesis and
judged on the untouched OOS+LOCKBOX only; that decision is left open
deliberately.

## 4. Controls and diagnostics

- **Permutation null**: consistent with bootstrap conclusions
  everywhere except H3/H4 DEV, where the day-clustering discount is
  decisive (and vindicated by VAL).
- **Matched baselines (B-class read)**: no hypothesis kept a positive
  excess over its same-architecture structure-only baseline across
  splits → B1 (vector ablation) answers: **vector state added no
  surviving incremental information**. B3/B4 render moot with no
  surviving parent.
- **Symmetry**: H1 long +1.57 vs short −0.12 (DEV); TR pair split
  +/−. No symmetric edge anywhere.
- **Decay bins**: no monotone delay pattern; the 16–60m bins swing
  ±7–21 pt on small n — noise.
- **Stability**: no primary is sign-stable across all six DEV+VAL
  years except TR-H1 (5 of 6), covered above.
- **AMBIGUOUS races**: not reached — no candidate advanced far enough
  for race-resolution bounds to matter.

## 5. Lane 2 exploratory (DEV only, 20 cells, none promoted)

Best cell: level-interaction ACCEPTED_ABOVE on ARCH-B, +3.16 gross
(n=344); worst: APPROACHING_FROM_BELOW −2.56. Spread of ±3 pt across
20 cells matches what the V5 shuffled-outcome search produced from
comparable multiplicity. RTH_AM was the only positive broad
time-of-day window (+0.36 — under base costs). VIOLET-parent probes
+2.54 (n=448). All cells EXPLORATORY — NOT YET CONFIRMED; any
candidate drawn from them needs a frozen rule and data it has never
touched.

## 6. Failure classification (prompt taxonomy)

- H3, H4: **Case D** — DEV-suggestive, VAL fails. Rejected; any
  modification is a new candidate needing untouched evidence.
- H1, H2, H5, TR-H2: **Case B** — no meaningful gross edge. Rejected
  without rescue attempts.
- H6: insufficient-sample fail inside the only window its data layer
  permits; re-testable only as the order-flow window grows.
- TR-H1: failed primary, sign-consistent; successor path documented
  above.

## 7. Cost / slippage

At the provisional base cost (0.87 pt RT) every primary is net
negative in at least one split; TR-H1 VAL is the single net-positive
cell and is statistically indistinguishable from zero. No candidate
survives stressed costs anywhere. NET figures remain provisional
until the user confirms actual commissions — no conclusion above
changes sign under any plausible retail cost model.

## 8. Final output items the prompt requires

- Best base edges: none surviving.
- Best positive confluence: none confirmed (Lane 2 cells logged).
- Best negative confluence: none confirmed.
- Time-of-day: no confirmed effect.
- Entry/stop/exit findings: not reached (no parent edge; Class C/D
  correctly remain unexamined per the promotion ladder).
- OOS / walk-forward: **not opened** — preserved untouched.
- Survival score table: empty (no finalists).
- PlayBook cards: none.
- Unique underlying edges found: **0**.
- Phase-2 recommendation: **NONE** — the prompt forbids starting
  sub-minute research merely because Phase 1 failed, and no gross
  edge warrants it.
- Order-flow recommendation: keep capturing; H6-class conjunctions
  need a longer volumetric window before they are testable at all.

## 9. FINAL DECISION

**D — NO ROBUST EDGE SURVIVED.**

Third consecutive programme verdict of D (V4: 0/8; V5: 0/10;
V4.1: 0/8) across three different hypothesis classes — price-action
conjunctions, exogenous calendar/exit geometry, and now
structure+vector+order-flow — on seven years of causally-clean,
independently verified data with preregistration, matched baselines,
day-block inference, permutation nulls, and untouched holdouts.

Both successful research outcomes were defined in advance. This is
outcome B: the evidence prevents us from trading an illusion.

What could still change the picture, all preregistered paths:
1. VEC-H1 — the user's parent-wick hypothesis — needs 1m vector
   emission (small engine addition + event-window run); it has never
   been tested.
2. A TR-H1 v2 preregistration against the untouched OOS+LOCKBOX.
3. H6-class order-flow conjunctions once the volumetric window is
   several times longer.
