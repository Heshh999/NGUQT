# RNVP-V1 — ROUND-NUMBER GRID + VOLUME PARTICIPATION — PROTOCOL FREEZE

Frozen and committed **before any outcome is computed**.
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.
Subordinate to every existing partition guard, spent-class prohibition,
protected-parent rule and freeze; stricter rule controls. Governing
lineage: latest completed wave MTNAD-V1 (freeze `7deabd8`, results
`248f642`); HEAD `248f642` clean. Partitions unchanged (DEV ≤
2026-08-17; buffer, VALIDATION, OOS, LOCKBOX untouched). All results
are `EXPLORATORY DEV EVIDENCE — NOT INDEPENDENT CONFIRMATION`.

## Novelty (screen verdicts recorded pre-freeze: both ACCEPT)

**Family RNL — ROUND_NUMBER_GRID** (tokens: exogenous_price_grid,
round_level_first_touch, stop_cluster_break; granularity event).
`NEW CAUSAL SOURCE: the exogenous fixed 100-point index-price grid
(option strikes / psychological round numbers), via price-modulo
arithmetic — no spent hypothesis conditions on absolute price levels.
NEW MECHANISM: clustered passive liquidity defends a round level on
first approach (fade the touch); clustered stops just beyond it fuel
continuation once decisively crossed (trade the break). NEAREST SPENT
CLASS: PATTERN_GEOMETRY (endogenous swing structure), SESSION_ANCHOR_
DISPLACEMENT (endogenous session anchors). MATERIAL DIFFERENCE: the
level set is exogenous and fixed in index points, independent of the
recent path.`

**Family VTP — VOLUME_TIME_PARTICIPATION** (tokens:
total_volume_surprise, participation_timing, information_day_state;
granularity state). `NEW CAUSAL SOURCE: total traded volume as a
conditioning state — raw volume has never conditioned any of the 88
registered hypotheses (volume-clock only resampled bars; OF classes
used signed capture-data flows). NEW MECHANISM: heavy-morning-
participation days are information/repricing days whose direction
persists into the afternoon; light-morning days are noise and revert.
NEAREST SPENT CLASS: VOLUME_CLOCK_STRUCTURE (descriptive sampling);
PRICE_ONLY_FAMILY_SEARCH (price-only, unconditioned AM/PM tests).
MATERIAL DIFFERENCE: the conditioning volume state is absent from
every prior test; directions frozen from the information-vs-noise
dichotomy.`

## Family RNL — 4 confirmatory cells (RTH, 1m execution)

Levels: L ∈ 100·ℤ in index points. First-interaction window W = 60
exchange-minutes (em units, all sessions). Trigger bars: RTH bars with
mod ∈ [631, 900] (≥60m of session context; exits fit before close).

| cell | trigger at bar t | direction |
|---|---|---|
| R1 touch-reject upper | L = 100·⌊high[t]/100⌋; high[t] ≥ L; close[t] < L; close[t−1] < L; no bar j in prior W with high[j] ≥ L | SHORT |
| R2 touch-reject lower | L = 100·⌈low[t]/100⌉; low[t] ≤ L; close[t] > L; close[t−1] > L; no bar j in prior W with low[j] ≤ L | LONG |
| R3 break upper | ∃L: close[t] ≥ L+5, close[t−1] < L, no bar j in prior W with high[j] ≥ L (L = 100·⌊(close[t]−5)/100⌋) | LONG |
| R4 break lower | mirror: close[t] ≤ L−5, close[t−1] > L, no prior-W low ≤ L | SHORT |

Break buffer ε = 5 index points (frozen). Entry at next 1m bar open;
stop 3×ATR20(1m) raced (stop-first, gap-through at worse open); exit
at open of the bar 60 minutes after entry (first later bar; day-last
close if none). 60m cooldown per cell, each cell standalone (house
convention). Neighbors (diagnostic only): W ∈ {30, 120}; ε ∈ {2.5,
10} for R3/R4; exits 45/90m; delay +1 bar.

## Family VTP — 4 confirmatory cells (12:00 state → afternoon)

At the 721 stamp (12:00 ET bar): V_am = Σ volume of RTH bars mod
571–720 (require ≥ 140 bars present); N20 = mean of prior 20 eligible
days' V_am (require 20); S = V_am/N20. Morning move M = close[721 bar]
− day's first RTH bar open; skip if M = 0. Causal thresholds: type-7
quantiles of prior-250-day S values (deque, ≥200 floor). **Quantiles
q70/q30 by frozen design** — decile/quintile tails cannot meet the
n≥200 floor after the direction split (~1,560 eligible days × 30% ÷ 2
≈ 230); decided now, before outcomes.

| cell | condition | direction |
|---|---|---|
| V1 | S ≥ q70 and M > 0 | LONG (continuation) |
| V2 | S ≥ q70 and M < 0 | SHORT (continuation) |
| V3 | S ≤ q30 and M > 0 | SHORT (reversion) |
| V4 | S ≤ q30 and M < 0 | LONG (reversion) |

Entry at open of the next 1m bar after the 721 stamp; exit at day-last
RTH close; no stop (afternoon day-cell precedent). Strategy pairing
frozen for the frequency mandate: **V-HI = {V1,V2}** (information-day
continuation) and **V-LO = {V3,V4}** (noise-day reversion) are the
tradeable strategies; frequency is reported at both cell and strategy
level. Neighbors: q60/q80 (V1/V2), q40/q20 (V3/V4); delay = entry at
12:30 (first bar mod ≥ 751).

## Statistics and gates (house standard, frozen)

Costs 0.87 base / 1.305 stressed; MNQ $2/pt; one contract. Per cell:
day-clustered bootstrap B=10,000 (seed 20260930) on stressed mean;
day-blocked sign-flip permutation P=10,000 (seed 20260931); **BH
across all 8 cells** (q ≤ 0.05). Gates: n≥200 · days≥60 ·
base+stressed>0 · PF ≥1.30/≥1.15 · EV ≥+0.10R/+0.05R (RNL only; VTP
day cells: stressed mean>0 + PF gates) · CI LB>0 · p≤0.05 · q≤0.05 ·
years positive ≥ covered−1 (min 6) · no single year >50% of profit ·
survives best-day and top-1% removal · delay diagnostic positive ·
frozen neighbors majority positive · incrementality: RNL events split
by trailing-60m displacement sign — stressed mean keeps sign in both
strata; VTP events split by |M| above/below causal median — keeps
sign in both strata · frequency (directive §7): mean ≥1.0 trade/week
and ≥60% of complete eligible weeks (≥4 eligible days) with ≥1 trade,
at cell level for RNL and at strategy level (V-HI, V-LO) for VTP;
below that = `LOWER-FREQUENCY SECONDARY CANDIDATE`. **Monte Carlo
(100,000 day-block paths, 5y-equivalent, seed 20260932) ONLY for a
cell passing every preliminary gate — MC can never rescue a failure.**

Variant budget: exactly these 8 cells + the frozen neighbor/delay/exit
diagnostics. Full battery runs to completion; nothing added, merged,
inverted or re-thresholded after outcomes; every cell registered at
close-out (DEAD_FROZEN on failure); failure kills each family as
frozen — no rescue. Unit tests precede the run: level arithmetic
(floor/ceil grids, multi-level bars), first-interaction window,
mutual exclusion of touch vs break, V_am/N20/S causality, race
adverse behavior.
