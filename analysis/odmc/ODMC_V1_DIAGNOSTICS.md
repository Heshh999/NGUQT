# ODMC-V1 — DIAGNOSTICS (predeclared; never candidates)

Binding stress 2.00 pt RT. Seeds: bootstrap/perm 20260904,
sign-destruction 20260905, random-pairing 20260906, matched 20260907.

| test | n | EV | reading |
|---|---|---|---|
| **PRIMARY** | 257 | **+1.599** | 13 binding gates fail |
| D1 no-magnitude-gate ablation | 1,700 | −1.407 | all impulses lose |
| D2 below-threshold control | 1,443 | −1.943 | small impulses lose more |
| D3 direction-reversal placebo | 257 | −4.294 | reversing is worse |
| D4 impulse-sign destruction (10k) | null −1.374 | **p 0.1270** | **primary not separable from destroyed signal** |
| D5 random-day pairing (2k) | null −1.823 | p 0.0695 | not significant |
| D6 shift −20 / −10 | 54 / 40 | −2.56 / **+4.94** | shifted events beat the real ones |
| D6 shift +10 / +20 (non-tradable) | 40 / 54 | +1.09 / −3.38 | falsification only |
| D7 matched non-event control | 252 | −5.268 | event days genuinely differ… |
| D8 adjacent-block placebo | 257 | −2.430 | effect is block-specific |
| D9 unconditional opening drift | 1,704 | long −1.80 / short −2.20 | no free drift either way |
| **D10 residualization** | 257 | raw aligned +3.264 pt → **residual ≈ 0.000** | **decisive** |

## What the diagnostics establish
The picture is coherent and it is negative.

**D10 is the decisive result.** The raw aligned second-half return is
+3.264 pt, but after controlling causally for first-half range, opening
gap, lagged volatility, weekday and year — controls fixed in advance,
none selected by significance — the residual is **≈ 0.000 pt**. The
entire apparent continuation is explained by ordinary opening
volatility and calendar composition. There is no incremental
information in the impulse itself.

**D4 confirms it independently.** Permuting impulse *signs* in 5-day
blocks while preserving magnitudes and dates yields p = 0.127 — the
observed result is not distinguishable from a version of itself with
the directional information destroyed. The direction carries nothing;
the magnitude filter is selecting volatile days, and volatile days have
wide two-sided ranges.

**D7 and D9 together explain the illusion.** Matched non-event days
lose −5.27 and unconditional opening drift loses ~−2 in both
directions, so the primary's +1.60 looks "incremental" and G12 passes.
But D10 shows that gap is a *volatility-composition* artifact, not
predictive content — the frozen retention gate is simply not powerful
enough to catch that, which is precisely why D10 was predeclared.

**D6** shows event series shifted −10 sessions score higher (+4.94) than
the true series, and **D8** shows the adjacent 09:40–09:50 block loses
(−2.43): the result is block-local and time-fragile rather than a
robust opening-momentum law.

Influence: drop-most-influential +0.900, drop-best-trade +0.900,
drop-best-month +0.665, drop-best-year (2024) +0.620 — all still
positive, so this is not one print; the failure is that the effect is
economically tiny, statistically absent (p 0.589), and 2026 alone
(−561 pt) erases six prior years.
