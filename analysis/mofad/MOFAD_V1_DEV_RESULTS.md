# MOFAD-V1 — DEV RESULTS

**Verdict: 0 of 5 frozen confirmatory candidates passed. Every candidate
fails at G05 (not positive after costs) — all five are negative even
GROSS, before any cost.** The complete frozen search ran to completion;
nothing was stopped early, merged, expanded, or rescued.

Freeze commit `643343fa76233f7952c15bafd0fa79006abed987` (protocol v1.0,
committed before outcomes). Closure commit `7c8a854`. Engine tests 25/25
green before the run. Data: 313 DEV days 2025-08-18 → 2026-08-17, OF
capture only. Costs: base 0.87 / stressed 1.305 pt RT. Seeds:
bootstrap 20260828, permutation 20260829, control 20260830.
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

## 1. Primary cells

| cand | n | days | gross | base | stressed | PF_b | PF_s | win_b | CI(stressed) | perm p | BH q | first fail |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---|
| C-F12-1 (overnight flow → open, T30) | 256 | 256 | −1.32 | −2.19 | −2.62 | 0.86 | 0.84 | 9.0% | [−8.82, +4.25] | 0.6584 | 0.9449 | G05 |
| C-F12-1b (same, T60) | 256 | 256 | −2.87 | −3.74 | −4.18 | 0.77 | 0.75 | 7.4% | [−10.73, +3.17] | 0.7870 | 0.9449 | G05 |
| C-F12-2 (preopen flow → open, T30) | 256 | 256 | −0.04 | −0.91 | −1.35 | 0.94 | 0.92 | 10.5% | [−7.49, +5.41] | 0.5112 | 0.9449 | G05 |
| C-F08-1 (λ-asymmetry, T15) | 2,061 | 253 | −0.92 | −1.79 | −2.22 | 0.88 | 0.85 | 37.9% | [−3.89, **−0.54**] | 0.8541 | 0.9449 | G05 |
| C-F08-2 (λ-asymmetry, T30) | 1,246 | 252 | −2.09 | −2.96 | −3.39 | 0.83 | 0.81 | 30.4% | [−5.90, **−0.82**] | 0.9449 | 0.9449 | G05 |

(Points per trade, MNQ $2/pt. F12 win rates are low because the frozen
1.5 × 1-minute-ATR stop is tight relative to a 30–60 minute hold — ~90%
of F12 trades stop out; that management was frozen before outcomes and
stands. Failure lists beyond the first: all five also fail G06–G12; the
F12 cells fail G16 (2/4 quarters); every cell fails the trade-quality
profiles at the stressed win rate.)

## 2. What the diagnostics say (all ledgered, none promotable)

- **Direction content is absent or adverse.** Permutation p ∈
  [0.51, 0.94]: the observed gross means sit at or below the median of
  the random-sign distribution everywhere. The two F08 cells have
  stressed CIs entirely below zero; C-F08-2's wrong-signedness is
  borderline at gross level (opposite-tail p ≈ 0.055) — reported as
  wrong-signed, **not** claimed as a significant opposite effect.
- **Monotonically harmful signal (F08):** stressed mean by |A| tercile,
  C-F08-1: +0.19 / −2.97 / −3.90; C-F08-2: −1.99 / −2.75 / −5.45. The
  stronger the measured impact asymmetry, the worse following it does —
  the mechanism is not merely absent, its strong readings mark bad
  drift-following conditions.
- **Neighbors agree everywhere** (G15 moot): F08 Q70/Q80 variants −2.2 to
  −2.8; F12 eligibility 250/350 (and 50/70) variants all negative within
  0.1 pt of the primary cells. No plateau of positivity exists anywhere
  in the frozen neighborhood.
- **Ablations (F08):** buy-side-only −1.27/−0.76, sell-side-only
  −1.52/−1.39 — no component carries hidden value.
- **Price-twin comparison (F12):** the price-only twin (sign of the
  overnight/preopen price change) loses less (−1.91 vs −2.62 stressed for
  C-F12-1) and agrees with the flow sign on 85% of days. Flow adds
  nothing beyond (already-dead) price momentum; the divergence subgroup
  (flow ≠ price, n=37) is −3.77 — following flow against price is worst.
- **Quarters:** F12 cells positive in 2/4 (sign-flipping regime noise);
  F08 cells negative in **all four quarters** — consistent absence.
- **Destructions behave like noise, not structure:** +1-bar delay,
  best-day removal, and top-1% removal all stay negative. The F12
  day-pairing shift (yesterday's signal on today's trades) came out
  positive (+3.8 to +5.9) — recorded as a red flag about noise scale at
  n≈255, **not** as an anomaly: it is a different (unfrozen) hypothesis,
  is inside ~2σ of the per-trade noise, and rescue-from-diagnostics is
  prohibited by the closure rules.

## 3. Economic reading

The two genuinely new mechanism classes this repository's data could
still support — **overnight/premarket aggressor-flow inventory** and
**side-split bar-level price-impact asymmetry** — carry no exploitable
directional information at 1-minute aggregation over the 12 exposed
months. Combined with the closed OF lineage (OFH1–12, OF-N1–12, PROOF:
0 for 25+), the consistent picture is that **bar-aggregate order flow on
MNQ describes what happened but does not predict what happens next** at
horizons a non-HFT trader can execute. Testing anything finer requires
the message-level data specified in the capture program.

## 4. Consequences

- `MOFAD_V1_FROZEN_CANDIDATES.json` = `[]` (was guaranteed by the <5-year
  coverage ceiling; now also empty on the merits).
- `MOFAD_V1_PROVISIONAL_OBSERVATIONS.json` = `[]` — no statistical
  survivor exists at any gate level.
- Robustness/walk-forward/Monte-Carlo/parameter-stability/execution-
  stress/risk-of-ruin stages: **NOT REACHED** (no preliminary passer);
  stub deliverables record this with the binding reason.
- The five cells and their diagnostics enter the spent registry lineage
  as `DEAD_FROZEN` at the next registry update; the INVENTORY_TRANSITION_FLOW
  and IMPACT_ASYMMETRY fingerprint classes are now spent.
- FIVE-YEAR MICROSTRUCTURE DURABILITY: INSUFFICIENT DATA.
