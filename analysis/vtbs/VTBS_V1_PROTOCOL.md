# VTBS-V1 — VOLATILITY-TIMED BIDIRECTIONAL STRUCTURE — PROTOCOL FREEZE

Frozen and committed **before any outcome is computed**.
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.

## 0. Why this exists, and the honest lineage disclosure

The programme's one repeated positive finding is that **magnitude is
predictable while direction is not** (MAG-AUC-V1 headline; MGSD screens;
the 48.3% side-agreement measured by BRK-H1's own bracket). Every failed
strategy asked a direction question. The only structure that monetizes a
direction-blind magnitude forecast in a linear instrument is a
**two-sided stop-entry structure** that harvests realized range.

**Spent relative:** BRK-H1 (commit-registered DEAD) was a bracket — but a
*minute-scale* one: ±0.5×ATR(1m) bands at intraday OFH6 signal minutes,
15–60 min life, 100% trigger rate, "no selectivity at all". Its autopsy
killed minute-scale expansion harvesting at flow events. VTBS-V1 differs
on every axis the registry fingerprints: anchor (RTH open, once per day,
no flow event), scale (bands = 0.15–0.30 × **median daily RTH range**,
~an order of magnitude wider), conditioning information (day-level
overnight-range magnitude forecast, not OFH6), and hold (hours to a
fixed afternoon exit). The similarity-screen decision, with this
relationship recorded, is in `VTBS_V1_SCREEN_DECISION.json`. If the
reader judges day-scale to be "nearby timeframe" to minute-scale, the
verdict below must be discarded — that judgment is preserved, not hidden.

New fingerprint class: `BIDIRECTIONAL_RANGE_HARVEST_DAILY`
(tokens: day_vol_forecast, open_anchored_two_sided_bands,
realized_range_harvest; granularity: state).

## 1. Data (exact)

Canonical 1m grid (`analysis/rvmr/rvmr_run.py::load_bars()`,
STAMP_SHIFT=0, close-stamped ET), tradedays ≤ **2026-08-17** (DEV cap).
Buffer/VALIDATION/OOS/LOCKBOX untouched. Full 7.1-year DEV — all
**exposed** data; any positive verdict is exploratory by construction.

## 2. Frozen definitions

Per calendar day `d` with previous available day `d−1`:

- `RR_e` = max(high) − min(low) over stamps 571..960 of day `e`
  (≥300 RTH bars required for validity).
- `base_d` = type-7 median of valid `RR_e` over the prior 60 days
  (≥40 valid required).
- `ONrange_d` = max(high) − min(low) over stamps ≥1081 of `d−1` plus
  stamps 1..569 of `d` (≥200 bars required). Window closes at the
  09:29 close-stamp — one full bar before entry monitoring.
- Predictor `P_d = ONrange_d / base_d`.
- **HIGH state**: `P_d ≥` type-7 Q75 of the prior 60 days' valid `P`
  values (≥40 required). Only HIGH days trade.
- `O` = open of the stamp-571 bar (the 09:30:00 price).
- Bands: `up = O + k·base_d`, `dn = O − k·base_d`.
- **Trigger scan** stamps 571..900 (no entry after 15:00). First bar
  with high ≥ up → LONG, stop-entry fill at max(up, bar open); first
  bar with low ≤ dn → SHORT at min(dn, bar open). A bar touching BOTH
  bands with no prior trigger = frozen adverse whipsaw: counted as
  entered and stopped, gross = −(up−dn) with gap-through at that bar's
  worse prices not credited better than −2k·base_d.
- After entry: **stop at the opposite band**, raced bar-by-bar from the
  entry bar (entry bar included; stop-first ambiguity adverse;
  gap-through fills at the worse of band and bar open).
- **Exit**: open of the first bar with stamp ≥ H, else the day's last
  RTH bar close. Horizons: `EXIT_A` H=780 (13:00), `EXIT_B` H=955 (15:55).
- No trigger by 15:00 → no trade (day logged).

**Four confirmatory candidates** (2 widths × 2 horizons, the full budget):
`C1 k=0.15/EXIT_B · C2 k=0.30/EXIT_B · C3 k=0.15/EXIT_A · C4 k=0.30/EXIT_A`.
One structure, no direction ever chosen by us.

## 3. Costs, risk, floors, gates

Base 0.87 / stressed 1.305 pt RT; MNQ $2/pt; one contract.
`R = 2·k·base_d` (band-to-band). Feasibility (counts-only, committed
first): 1,689 eligible days, **468 HIGH days**.

House gates, unchanged: n≥200 · days≥60 · positive after base AND
stressed · base PF≥1.30 · stressed PF≥1.15 · base EV≥+0.10R · stressed
EV≥+0.05R · day-clustered bootstrap 95% CI LB>0 (B=10,000, seed
20260901) · trigger-side sign-flip day-blocked permutation p≤0.05
(P=10,000, seed 20260902 — tests whether first-touch continuation beats
random side at identical entries) · BH q≤0.05 across the 4 cells ·
HIGH-state increment: HIGH mean must exceed the unconditional-bracket
mean (else the forecast adds nothing) with a year-stratified
random-subset permutation p≤0.05 (10,000 draws, seed 20260903) ·
≥6 of 8 calendar years positive after stress · no single
year/day/direction >50% of net · survives best-day and top-1% removal ·
neighbors (k ±20%: 0.12/0.18, 0.24/0.36; state Q70/Q80) majority
positive · +1-bar entry delay stays positive · trade-quality profile per
the house table. Any binding failure kills the cell; no rescue; no
post-hoc changes. Diagnostics (LOW-state placebo, unconditional arm,
side split, per-year table) are ledgered, never promotable.

## 4. Outcome ceiling

DEV is exposed history. Best possible verdict:
PASSED_HISTORICAL_EXPLORATORY, subject to untouched VALIDATION
(2026-09-01+) before anything more is claimed.
