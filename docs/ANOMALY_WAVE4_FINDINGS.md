# ANOMALY WAVE 4 — MATHEMATICAL STRUCTURE MAPS — FINDINGS

Date 2026-08-27. **EXPLORATORY.** All 2019–2026 data is exposed
development data; nothing below is a confirmed or tradable edge; any
strategy derived from these maps requires its own preregistration and
future-data evidence. Engines `analysis/wave4/wave4_run.py` /
`wave4b_incr.py`; raw output `WAVE4_OUTPUT.txt`, `WAVE4_RAW.json`.
90 BH-corrected cells across modules A–D + descriptive module E; seed
20260828; day-clustered bootstrap throughout. Spent objects (open
gap-fade F09, VWAP-fade F07, daily TSMOM, SHOCK-CONT) were not re-tested.

## A. Where the drift lives (46 half-hour cells)
Total unconditional drift ≈ **+6.0 bp/day**, split ≈ **+3.6 overnight /
+2.4 RTH** — 60% of MNQ's drift accrues outside RTH. **No single
half-hour survives BH** (0/46): the drift is diffuse, which is exactly
why every time-window drift strategy (F15 family) had CI-positive but
floor-failing economics. Knowledge: there is no "magic half-hour".

## B. Diffusion map — where trending is real (32 VR cells, 3 survive BH)
Variance ratios VR(q) with non-overlapping windows, day-clustered:

| window | q | VR | CI | BH q |
|---|---|---|---|---|
| **late premarket 08:01–09:29** | 30 | **1.324** | [1.140, 1.521] | **0.032** |
| **opening drive 09:31–10:00** | 10 | **1.082** | [1.029, 1.140] | **0.032** |
| **close 15:31–16:00** | 30 | **1.270** | [1.083, 1.469] | **0.032** |

Everything else ≈ 1 (random walk); no mean-reverting cell survives
anywhere. **Super-diffusion (trending) concentrates in exactly three
windows: late premarket, the opening drive, and the closing half-hour.**
This is the cleanest stable structural result of the wave, and it
coheres with the failed-but-positive F16 (late-PM trend), F18 (closing
momentum) and the 30s opening-momentum observation — all three of those
sit inside the super-diffusive windows.

## C. Anchor-attraction field — significant, then destroyed honestly
Univariate: forward-30m drift vs displacement/ATR from four anchors
(prior close, day open, overnight mid, VWAP) is **positive (repulsive =
continuation) for all four, BH q ≤ 0.009** — the field-level statement
of "fading displacement loses", unifying F07's harmful fades and
MOM-H2's real 30m trend.

**Destruction (the result that matters):**
- Joint day-clustered OLS: the four anchors are one collinear
  displacement factor; the x_open partial slope is +0.198 with
  **CI [−0.03, +0.44], p 0.084** — not attributable per-anchor.
- Velocity is NOT the driver: prior-30m momentum's partial slope is
  +0.008 (p 0.72). The field is **position-based, not momentum-based** —
  mathematically interesting.
- **Per-year sign flips**: 2019 −0.14, 2020 −0.11, 2021 +0.08,
  2022 **+0.78**, 2023 −0.05, 2024 −0.02, 2025 +0.32, 2026 **+0.52**.
  4/8 years negative. This would fail every temporal-stability gate.

**Verdict: REGIME-DESCRIPTOR, NOT AN ANOMALY.** The *sign* of the
displacement field is itself a slowly-varying regime variable
(trend-years 2021/22/25/26 vs fade-years 2019/20/23/24). Top-decile
displacement long earns +1.93 pt/30m gross (2.2× cost, CI positive)
pooled — but that pooled number is regime concentration, not edge.

## D. First-passage geometry — symmetric (8 cells, 0 survive)
P(+1·ATR15 before −1·ATR15 | 120m) is indistinguishable from ½ at every
sampled hour (10:00–15:00) and is NOT moved by the prior-30m sign
(0.498/0.494). Barrier-race geometry carries no exploitable asymmetry —
consistent with the registry's universal fixed-R target failures and
with the MFE≈MAE distribution identity in the profit-taking study.

## E. The two-regime ACF (descriptive)
RTH 1m returns: **lag-1 +0.013 (momentum)**; overnight: **lag-1 −0.007,
lag-2 −0.011 (reversal)**. The sign of 1-minute serial correlation flips
between sessions — a compact restatement of MEMORY-PRED's state
dependence (overnight is LOW-activity-dominated → reversal; RTH is
higher-activity → continuation), from an independent construction.

## What this wave adds to the programme
1. **Stable, BH-surviving:** trending concentrates in late premarket,
   the opening drive, and the close (Module B). If any future
   continuation strategy is preregistered, those are its windows.
2. **Stable, descriptive:** session-sign ACF flip; drift 60% overnight
   and diffuse; barrier symmetry (stop/target geometry cannot be the
   source of edge).
3. **Regime frontier (hypothesis-generating only):** the displacement
   field's sign flips by year. A *conditional* hypothesis — "trade
   displacement continuation only when a trailing causal regime
   statistic (e.g., trailing 60-day VR or trailing field slope) is
   > 1 / > 0" — is the single most promising untested idea this wave
   produces. It is second-order (a meta-parameter on exposed data), so
   it may ONLY be pursued as a new preregistration whose confirmation
   is future data. It is NOT tested here, deliberately.

**Nothing is promoted. No strategy exists. The maps are knowledge.**
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
