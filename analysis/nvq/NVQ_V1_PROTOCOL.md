# NVQ-V1 — NOVEL QUESTION CLASSES — PROTOCOL FREEZE

Frozen and committed **before any outcome is computed**.
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.

## 0. Scope discipline

User directive: no anomalies or strategies already found — completely new
objects only. Verified against the 81-row spent registry before freeze:

- **Volume-clock sampling** has never been used by any prior test (all
  ~700 ran in clock time; MOFAD §8 permitted event-based bars and none
  were run). New measurement basis, class `VOLUME_CLOCK_STRUCTURE`.
- **Day-type taxonomy** (NR7 / inside / outside / trend / wide-range
  days) appears nowhere in the registry; no prior program classified
  days by range structure. Class `DAY_TYPE_TAXONOMY`.
- **Daily same-sign streaks** are distinct from the cumulative k-day
  sign spectrum (MTF-A2, null): a streak is a path constraint, not a
  sum. Disclosed adjacency: MTF-A2 and NQDIR live in the daily-direction
  neighborhood; the streak conditioning is new, the outcome variable is
  not. Class `DAY_TYPE_TAXONOMY` (shared).

Explicitly excluded (already found → off limits per directive): ordinal
motifs, VR cells, VWAP/OU, anchors/memory, all flow constructions,
brackets, gap fade, calendar/weekday, opening range, session
transitions.

## 1. Data

Canonical 1m grid, tradedays ≤ 2026-08-17 (exposed; every verdict
ceiling is exploratory). Buffer/VALIDATION/OOS/LOCKBOX untouched.

## 2. Module V — volume-clock structure (6 cells)

Volume bars built RTH-only (stamps 571–960) from 1m blocks: a bar closes
at the first 1m bar where cumulative volume ≥ the causal target;
target_d = trailing-20-day mean RTH volume / K (≥10 valid days
required), K ∈ {78, 26} ("5m-equivalent", "15m-equivalent"). Bars never
span days. Limitation disclosed: 1m building blocks, not ticks — valid
at these granularities, not finer.

Cells per K: lag-1 AC, lag-2 AC (adjacent bars, same day), VR(6)
(variance of 6-bar sums / 6× variance, per-day non-overlapping, global
demeaning, day-cluster bootstrap). 6 descriptive cells; day-clustered
bootstrap B=5,000, seed 20260901.

## 3. Module D — day-type taxonomy (10 direction cells + range map)

Causal day types from RTH OHLC (all relative to trailing history only):
- NR7 / WR7: narrowest / widest RTH range of the trailing 7 days.
- INSIDE / OUTSIDE: high/low inside (outside) the prior day's range.
- TREND_UP / TREND_DN: close in top (bottom) 10% of range AND range ≥
  trailing-20-day median.
- After classifying day t, outcome = next-day close-to-close log return
  (direction cells, bp) and next-day range / trailing-20d median range
  (range cells, descriptive only — volatility clustering is known and
  unmonetizable here; range cells can never become candidates).

Direction cells (10): NR7, WR7, INSIDE, OUTSIDE, TREND_UP, TREND_DN,
INSIDE∧NR7, streak3up, streak3dn, streak4+ (either sign, signed
against the streak = reversal convention, declared now). Stationary
20-day block bootstrap B=5,000, seed 20260902.

## 4. Multiplicity, translation, gates

One BH family across all 16 primary cells (6 V + 10 D). A cell may be
considered for strategy translation ONLY if BH q ≤ 0.05 AND the effect
in points exceeds the 0.87 pt base cost at one MNQ contract AND the
similarity screen accepts it (decision recorded either way). Frozen
translation if reached: enter next session open, exit next session
close, house gates, costs 0.87/1.305 (+1.740 disclosure for any
overnight leg). No other translation may be invented after outcomes.
The full frozen battery runs to completion; no cell added, merged, or
re-thresholded after results. All outcomes registered at close-out.
