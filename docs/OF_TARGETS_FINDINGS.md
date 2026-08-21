# Order Flow for Take-Profits: Findings

**Date:** 2026-08-21
**Scripts:** `analysis/v41/of_targets.py`, `analysis/v41/of_adaptive.py`
**Data:** full order-flow capture, 281,195 one-minute volumetric bars,
2025-11-02 -> 2026-08-19, with the causal developing session profile
(POC / VAH / VAL) on every row.

**Ledger note.** The order-flow layer has no sealed holdout left - it was
spent on the $1,000 P&L illustration by explicit user decision on
2026-08-20. DEV (through 2026-03) / VAL (2026-04 onward) below is a
within-window replication split, not out-of-sample. The structure HOLD
(2024-07 onward) was not touched.

**Method notes.** This capture is a raw 1m path, so first-touch and
stop-vs-target races are exact bar-by-bar walks - no ordering proxy.
Entries are deliberately direction-agnostic (every RTH 5-minute boundary,
both sides), because the question is about exits; nothing here is
expected to be net positive, and nothing is.

---

## Q1 - Do volumetric features predict MAGNITUDE beyond bar shape? YES

Target: unsigned reach of the next 90 minutes in ATR (mean of long-side
and short-side MFE, which removes the drift component). Every order-flow
feature was scored on the RESIDUAL after a bar-shape composite was
bucketed out, so only genuine increment counts.

Nine of fourteen features add signal with the same sign on both splits:

| feature | resid rho DEV | resid rho VAL | reading |
|---|---|---|---|
| valueWidthAtr | +0.199 | +0.239 | wide value area -> more reach |
| deltaRange | +0.187 | +0.202 | intra-bar delta swings -> more reach |
| absorptionStrengthRaw | -0.161 | -0.205 | absorption -> LESS reach |
| volPerTick | -0.161 | -0.203 | thick tape -> less reach |
| imbal3x | -0.133 | -0.156 | many imbalances -> less reach |
| absCumDeltaSlope | -0.091 | -0.080 | strong one-way delta -> less reach |
| absDistPocAtr | +0.078 | +0.146 | far from POC -> more reach |
| stacked3x | -0.078 | -0.116 | |
| maxImbalRatio | -0.059 | -0.047 | |

Combined shape+OF score vs reach: **+0.225 DEV / +0.256 VAL.**

The picture is coherent and matches the structure-capture finding from
the other side: activity that looks decisive (absorption, heavy
imbalances, thick tape, strong one-way delta) marks a move that is
already spent; a stretched, wide-value, whippy-delta tape marks room
still to travel.

## Q2 - Are POC / VAH / VAL magnets or barriers? NO

Distance-matched design: at each target distance (0.25-3.0 ATR, both
sides, ~11k event-sides per bucket per split), targets that coincide with
a developing profile level (within 0.10 ATR) were compared with targets
at the same distance that do not. Placebo: everything re-run with the
levels shifted +0.37 ATR.

- **Magnet test (first-touch rate):** ON-level minus OFF-level differences
  are -4.5 to +3.4 pp, signs flip between splits and distances, and the
  placebo levels show the same spread. No magnet effect.
- **Barrier test (continuation +0.5 ATR beyond a reached target):** same
  result - small, sign-flipping, indistinguishable from placebo. Price
  does not stall at these levels either.

## Q2c - Level-based take-profit vs fixed take-profit: NO EDGE

Exact 1m race, stop frozen at 1.5 ATR, identical entries, only the
target changes. On the identical subset where both a real and a placebo
level were available as targets:

| exit | mean net pt/trade |
|---|---|
| target at nearest real level | -0.366 |
| target at nearest placebo level | -0.772 |

LEVEL minus PLACEBO = **+0.405 pt/trade, day-block 95% CI [-0.096,
+0.939]** - the interval includes zero. Suggestive at best, not a
demonstrated effect, and the sign is worth nothing without a directional
edge underneath it.

## Supplement - Using the magnitude score to SIZE the target: NO GAIN

Adaptive rule (frozen: low-score tercile -> 0.5R target, mid -> 1.0R,
high -> 2.0R; terciles cut on DEV):

| rule | net DEV | net VAL | capture DEV | capture VAL |
|---|---|---|---|---|
| best fixed | -0.880 | -0.505 | 0.191 | 0.173 |
| ADAPTIVE | -0.904 | -0.587 | 0.182 | 0.181 |
| ADAPTIVE inverted | -1.443 | -1.112 | 0.177 | 0.179 |

The inverted control is clearly worse (so the score's direction is real),
but ADAPTIVE minus best-fixed is **-0.02 pt (CI [-0.29, +0.25]) on DEV
and -0.08 pt (CI [-0.37, +0.19]) on VAL** - zero. Knowing how far price
will travel does not raise capture, because the travel is symmetric: the
adverse side grows with the favourable side, so a bigger target on a
high-score bar wins more when right and loses the same stop when wrong.

---

## Verdict

1. **Order flow DOES add real, replicating magnitude prediction** on top
   of bar shape (combined rho ~0.24, nine features, both splits). This is
   the third independent confirmation that this market's predictable
   dimension is volatility, not direction.
2. **Liquidity zones (developing POC/VAH/VAL) are neither magnets nor
   barriers** once distance is controlled - the placebo kills both
   readings. Using them as take-profit targets is not better than a fixed
   target at the same distance.
3. **Neither helps take-profits in P&L terms**, for the same structural
   reason every exit study has hit: median favourable and adverse
   excursions are symmetric. An exit rule redistributes outcomes; it
   cannot manufacture asymmetry that entry timing does not provide.

The exit side of this system is as good as fixed-R already gets. Any
further gain has to come from the entry (direction), which remains the
unpredicted dimension.
