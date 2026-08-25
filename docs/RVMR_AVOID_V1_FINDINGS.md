# RVMR-AVOID-V1 — FINDINGS

Pre-registered before results (`docs/RVMR_AVOID_PREREGISTRATION.md`).
**RVMR PARITY GATE: PASS** (593,190 rows, 0/0/0). Strategies scored
exactly as canonically registered; nothing frozen touched; no filter
applied to any live or prospective system. Full raw output:
`analysis/rvmr_avoid/AV_OUTPUT.txt`.

## **OVERALL VERDICT**

> **RVMR HIGH INDICATES MORE MOVEMENT BUT NOT WORSE FADE QUALITY.**
> **NO AVOIDANCE RULE.**

This is the pre-declared failure case, and the data delivered it almost
verbatim: HIGH inflates favourable and adverse excursions **in
lockstep**, the pooled HIGH-vs-rest expectancy difference is
indistinguishable from zero, the motivating leads did not replicate on
any independent fade mechanism, and avoid-HIGH removes winning and
losing P&L in a ratio of ~1.06 : 1.

---

## 1–4. Registry and gate

M = 7 families frozen before results (two labelled **MOTIVATING** —
their HIGH-state numbers were first seen in RVMR-STRAT-V1 and cannot
count as confirmation): F1 gap fade\* (232) · F2 VWAP reversion
(19,201) · F3 session-extreme reversion\* (442) · F4 V-recovery (984) ·
F5 overnight sweep-reclaim (187) · F6 failed-breakout return (2,005) ·
F7 level sweep-reclaim (2,713) · plus a canonical-year F7 echo (581).
Opening-drive failure excluded in advance (n=40). OFH13/OFH14 excluded
by the counter-movement definition; OFH13_PROSPECTIVE_V1 untouched.

## 5. RANGE results — the primary

| family | Δ = EV(HIGH) − EV(LOW∪MED) | p | BH q | ATR-ctl | ToD-ctl |
|---|---|---|---|---|---|
| F1 gap fade **\*** | **−10.72** | 0.127 | 0.847 | −9.05 | −10.72 |
| F2 VWAP reversion | −0.11 | 0.864 | 0.922 | +0.23 | +0.49 |
| F3 session rev **\*** | −5.37 | 0.470 | 0.847 | −4.75 | −2.52 |
| F4 V-recovery | **+2.04** | 0.605 | 0.847 | +3.43 | +2.42 |
| F5 ovn reclaim | **+0.76** | 0.922 | 0.922 | +2.36 | +1.38 |
| F6 failed-breakout | **+2.04** | 0.586 | 0.847 | +3.68 | +6.77 |
| F7 level reclaim | −1.58 | 0.433 | 0.847 | −2.00 | −1.55 |
| **POOLED** | **+0.09** | **0.924** | — | — | — |

The only meaningful negatives are the two MOTIVATING families — the
same data the lead came from, now non-significant even uncorrected.
The five independent families scatter around zero with **three
positive**. The canonical-year F7 echo shows the same nothing.
**Strategy-level replication: FAILED.** F1's own year-by-year delta
flips sign four times (−29.6 → +15.1 → −40.0 → …).

## 6. VOLUME results — the secondary

Pooled +0.61 (p = 0.325). The single q < 0.05 cell — F5 overnight
reclaim, **+29.32, q = 0.014 — has the WRONG SIGN for avoidance**
(HIGH-volume reclaims did *better*) on a degenerate comparison cell of
11 LOW∪MED events; 94% of that family is VOLUME-HIGH. Selectivity
artifact, not evidence. F1's −21.90 (p = 0.096) rests on 23 comparison
events. **No volume avoidance signal.**

## 7–10. Geometry — the decisive tables (F2, n = 19,201)

| state | med MAE | p90 MAE | med MFE | p90 MFE | MFE/MAE | ff@0.25 | stop-hit | avg win | avg loss |
|---|---|---|---|---|---|---|---|---|---|
| LOW | 2.54 | 7.36 | 2.42 | 7.47 | 0.95 | 48.7% | 76.5% | +44.0 | −13.8 |
| MEDIUM | 2.63 | 7.27 | 2.40 | 6.98 | 0.91 | 47.9% | 75.1% | +54.2 | −18.5 |
| HIGH | **3.04** | **9.95** | **2.94** | **8.76** | **0.97** | 49.5% | 76.1% | **+65.5** | **−21.3** |

Adverse excursion grows in HIGH — **and favourable excursion grows by
the same proportion.** MFE/MAE flat, favourable-first flat, stop-hit
flat, P(+xR before stop) flat. Winners get bigger, losers get bigger.
That is RVMR doing exactly — and only — what it was certified to do:
predict movement magnitude, symmetrically.

## 11–13. Avoidance economics (drop RANGE-HIGH), per family

| family | per-ORIGINAL-opp EV before → after | saved / sacrificed | top-10 kept | winner P&L kept |
|---|---|---|---|---|
| F1 \* | −5.52 → **+0.33** | 1.67 | 5/10 | 47% (top-5%: **0%**) |
| F2 | −1.33 → −0.97 | 1.09 | 5/10 | 69% |
| F3 \* | −1.93 → −0.23 | 1.23 | 6/10 | 63% |
| F4 | −1.15 → −1.19 | **0.99** | **3/10** | 49% |
| F5 | +10.42 → **+2.64** | **0.70** | 3/10 | 26% |
| F6 | −1.11 → −1.21 | 0.99 | 4/10 | 63% |
| F7 | +0.52 → +0.65 | 1.01 | 7/10 | 45% |
| **POOLED** | — | **≈ 1.06** (141,708 saved / 134,046 sacrificed) | **33/70 = 47%** | — |

Only the two motivating families "benefit" — and F1's version destroys
its entire top-5% winner P&L. On the independent families, avoidance is
neutral-to-harmful; on F5 it would have forfeited three-quarters of a
genuinely profitable family's expectancy. **Pooled, avoid-HIGH removes
winning and losing P&L in essentially equal measure** — the exact
signature the failure case named.

## 14–16. Controls and diagnostics

- **ATR / ToD strata:** deltas survive only in the motivating families;
  independent families stay ≈ 0 or positive within strata (table
  above). Not a volatility story in either direction — there is simply
  no effect to explain.
- **Extension buckets:** no state separation emerges within small /
  medium / large pre-entry moves (raw output §per-family).
- **Efficiency diagnostic (R-HIGH fades):** loEFF/midEFF/hiEFF EVs stay
  within noise of each other — the "dangerous efficient move" refinement
  found nothing to refine.
- **Transitions (diagnostic):** L→L −1.49, M→M −0.53, H→H −0.99, L→M
  −2.18 … all within noise; entering a fade right after regime
  expansion is not measurably worse.

## 21. Promotion gate — the twelve declared conditions

| # | condition | result |
|---|---|---|
| 1 | HIGH materially worse than LOW/MED | **FAIL** (pooled +0.09) |
| 2 | deterioration in raw MFE/MAE geometry | **FAIL** (flat 0.95/0.91/0.97) |
| 3 | worse favourable-first in HIGH | **FAIL** (flat) |
| 4 | removes more losing than winning P&L | **FAIL** (1.06 : 1 pooled) |
| 5 | per-original-opportunity EV improves | FAIL (motivating-only) |
| 6 | top winners preserved | **FAIL** (33/70; F1 loses all top-5% P&L) |
| 7 | multiple independent families | **FAIL** (0 of 5) |
| 8 | temporal stability | **FAIL** (F1 flips sign by year) |
| 9 | survives ATR/ToD controls | FAIL (no effect to survive) |
| 10 | beyond generic volatility | FAIL (same) |
| 11 | adequate sample | PASS (25,764 fade events) |
| 12 | not one-tail-event driven | PASS |

**RVMR-AVOID-V1 is NOT promoted.**

---

## FINAL ANSWERS

1. Worse in RANGE-HIGH? **NO** (pooled +0.09, p 0.92; independent
   families 3 of 5 positive).
2. Worse in VOLUME-HIGH? **NO** (pooled +0.61; only significant cell is
   wrong-signed on n=11).
3. Larger MAE in HIGH? **YES** (med 2.54→3.04, p90 7.36→9.95).
4. Larger MFE too? **YES** (med 2.42→2.94; avg winner +44→+65).
5. Does MFE/MAE deteriorate? **NO** (0.95 / 0.91 / 0.97).
6. Does favourable-first deteriorate? **NO** (48.7 / 47.9 / 49.5%).
7. Does skipping HIGH improve per-original-opportunity EV? **NO** —
   only in the two motivating families; neutral-to-harmful elsewhere
   (F5: −7.78/opportunity).
8. Losing P&L avoided: **141,708 points** (pooled, all seven).
9. Winning P&L sacrificed: **134,046 points** — ratio 1.06.
10. Top-10 winners preserved: **47% (33 of 70)**.
11. Survives ATR matching? **NO** (independent families ≈ 0 within strata).
12. Survives ToD matching? **NO** (same).
13. RVMR beyond normal volatility here? **NO** — there is no fade-quality
    effect for it to explain.
14. Strongest avoidance effect? **F1 gap fade — MOTIVATING data only**,
    non-significant, year-unstable, tail-destroying. Effectively NONE.
15. Same effect across multiple independent mechanisms? **NO.**
16. Should HIGH become a general "do not fade" context? **NO.**

## Per-strategy verdicts

F1 **HIGH RVMR INCREASES BOTH MFE AND MAE** (motivating lead did not
strengthen) · F2 **HIGH RVMR INCREASES BOTH MFE AND MAE** · F3 RVMR
CONTEXT ONLY (motivating) · F4 NO AVOIDANCE VALUE · F5 NO AVOIDANCE
VALUE (HIGH is its best state) · F6 NO AVOIDANCE VALUE · F7 NO
AVOIDANCE VALUE.

## What this closes

The one lead RVMR-STRAT-V1 produced is now resolved: it was the
motivating families' own noise, not a property of counter-movement
trading. RVMR's certified role is unchanged and complete: **movement
magnitude, symmetric, direction-free — context only.** No further
RVMR trading application is suggested by any study to date. The forward
logger keeps collecting; the only instrument that can add anything now
is forward data.

**OFH13_PROSPECTIVE_V1 REMAINS THE BEST SPECIFICATION AND REMAINS
UNTOUCHED. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
