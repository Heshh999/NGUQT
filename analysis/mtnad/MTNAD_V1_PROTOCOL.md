# MTNAD-V1 — MULTI-TIMEFRAME NEW-ANOMALY DISCOVERY — PROTOCOL FREEZE

Frozen and committed **before any outcome is computed**.
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.
Subordinate to every existing partition guard, spent-hypothesis
prohibition, protected-parent rule, and freeze. Stricter rule controls.

## 0. Startup and governing-protocol gate (Deliverable A)

- Governing lineage: V4.1 freeze → MGSD → MOFAD → MTF → NVQ → RMA.
  Latest completed wave: **RMA-V1** (protocol freeze `7407f12`,
  pre-outcome corrections `17aa5c7`/`5b38c87`, results+close-out
  `284e46f`). HEAD at this freeze: `284e46f`, working tree clean.
- Predecessor honesty check: every prior wave shows protocol commit
  preceding results commit (MTF `70ba8de`, NVQ `7c4cad4`, RMA
  `7407f12`). NMAE-V1 remains **NOT STARTED** (MLES-V1 Mode B capture
  precondition incomplete) — independent of this wave, unchanged.
- Surviving candidates awaiting untouched confirmation: **OFH13,
  OFH14** (docs/PROSPECTIVE_REGISTRY.md) and **NVQ-STREAK3DN**
  (analysis/nvq/NVQ_V1_PROSPECTIVE_FREEZE.md). Per the continuation
  directive this wave is therefore **bounded and preregistered**, not
  an unrestricted search: it touches none of the protected parents, no
  DAY_TYPE_TAXONOMY variant at any timeframe, and no protected
  partition.
- Partitions restated: DEV exposed ≤ 2026-08-17 · buffer 2026-08-18→31
  unused · VALIDATION 2026-09-01→2027-02-28 untouched · OOS and FINAL
  LOCKBOX untouched. All new results are labeled
  `EXPLORATORY DEV EVIDENCE — NOT INDEPENDENT CONFIRMATION`.

## 1. Data and timeframe audit (Deliverable B)

| dataset / timeframe | status | disposition |
|---|---|---|
| canonical 1m OHLCV (2,503,622 bars, 2019-07-04→2026-08-17, close-stamped ET, RVMR-certified) | native | **used** (base grid) |
| 3/5/15/30/60m aggregates | derived (em-bucket, complete-only) | 5/15/30/60 spent for ordinal path (MTF-B1); usable for new mechanisms |
| 240m (4h) aggregate | derived | **used** (S2 rolling window); 4h vol-timing spent (DVT) |
| daily RTH bars | derived | **used** (S3); day-type/streak classes protected+spent |
| weekly bars | derived (~371 weeks) | excluded: weekly-scale conditioning cannot satisfy the ≥1 trade/week gate; calendar class spent |
| volume bars / event-time sampling | derived | bar-sampling use spent (NVQ-VOLCLOCK); **volume used here only as an age clock** (new use) |
| sub-minute (30s Wave-4 lineage, LTF capture) | native, ~weeks | INSUFFICIENT DATA for 7y discovery |
| ES 1m (pilot) | native, 42 session days (1.86% of span) | INSUFFICIENT DATA (ES_NQ_DATA_V1_AUDIT.md); lead-lag class spent |
| quotes/depth/ticks/aggressor/fills/events | absent | INSUFFICIENT DATA (MOFAD audit); MLES capture at 0 days |
| V4.1 order-flow capture (~2 months) | native | OF classes spent; span insufficient for new discovery |

No genuine timeframe silently ignored; every exclusion has a recorded
reason above. Nothing is fabricated, interpolated, or proxied.

## 2. Novelty screen (Deliverable C)

Registry reconciled at 86 rows / 27 fingerprint classes (~740 tests).
**No prior test has ever conditioned on the AGE of a causally defined
event.** All spent classes condition on prices, displacements, paths,
flows, volumes, moments, calendars, or day types — never on elapsed
time (or elapsed volume) since an event.

Admitted family — statement required by the directive:

`NEW CAUSAL SOURCE: event-age (renewal) clocks — elapsed wall-time and
elapsed traded volume since the most recent refresh of a causally
tracked extreme, at session / rolling-4h / 20-day scales. NEW
MECHANISM: initiative persistence measured by refresh-age asymmetry —
the auction keeps working the extreme it has refreshed recently; a
fresh extreme on one side with a stale extreme on the other marks
one-sided initiative, and price continues toward the fresh side.
NEAREST SPENT CLASS: SESSION_ANCHOR_DISPLACEMENT (price displacement
from anchors — not ages) and PRICE_CONTINUATION_INTRADAY (return
impulse — not ages). MATERIAL DIFFERENCE: the conditioning variable is
a duration, invariant to displacement magnitude; a preregistered
incrementality gate against a displacement benchmark is binding.`

New class token set (registered at close-out):
`DURATION_HAZARD_RENEWAL` = {event_age_clock, extreme_refresh_drought,
renewal_hazard_state}, granularity state. Screen verdict: ACCEPT
(no R1/R2/R3 hit; verified against the frozen similarity screen).

Proposals REJECTED before testing (recorded, not run):
- entropy-conditioned continuation → transformation of spent
  PRICE_CONTINUATION_INTRADAY;
- HTF range-composition fade (upside vs downside range share) →
  cosmetic cousin of spent REALIZED_MOMENT_ASYMMETRY;
- swing-size hazard fade (ε-zigzag survival) → spent
  PRICE_MEANREV_INTRADAY in survival clothing;
- total-volume absorption at HTF → spent OF_ABSORPTION_REVERSAL /
  OF_EFFORT_RESULT mechanism;
- ON→RTH sign transfer, gap fill/continuation → spent MGSD
  session-transition and gap families;
- anything derived from the RMA extreme-time map or CALENDAR_TOD;
- every day-type/streak variant → protected DAY_TYPE_TAXONOMY.

## 3. Frozen wave manifest (Deliverable D)

One family, **8 confirmatory cells**, one coherent mechanism
(continuation toward the recently refreshed extreme). Multi-timeframe
by construction: session scale, rolling-4h scale, volume clock, and
20-day daily scale.

**Refresh definition** (all scales): the refresh bar of a period
maximum is the most recent completed bar whose high equals the current
running/rolling maximum; age = elapsed exchange minutes (em units)
from that bar to the evaluation stamp. Mutatis mutandis for minima.
Asymmetry `AR = (A_lo − A_hi)/(A_lo + A_hi)` ∈ [−1,1]; AR high = high
fresh / low stale. Skip if `A_lo + A_hi = 0`.

Evaluation stamps (intraday): `m ∈ {631,661,691,721,751,781,811,841,
871}` ET (RTH, ≥60m elapsed). Completed bars only, contiguity per em.

| cell | scale | signal | direction |
|---|---|---|---|
| C1 | S1: RTH running session extremes (from 571) | AR ≥ causal q90 | LONG |
| C2 | S1 | AR ≤ causal q10 | SHORT |
| C3 | S2: rolling 240 em-minute window extremes (full session) | AR ≥ q90 | LONG |
| C4 | S2 | AR ≤ q10 | SHORT |
| C5 | S1V: session extremes, ages in cumulative traded volume since refresh | AR ≥ q90 | LONG |
| C6 | S1V | AR ≤ q10 | SHORT |
| C7 | S3: daily — DH = trade-days since a day set a 20-day high of highs, DL likewise for lows; ARd=(DL−DH)/(DL+DH), known at prior close | ARd ≥ causal **q80** | LONG day |
| C8 | S3 | ARd ≤ causal **q20** | SHORT day |

S3 uses quintile extremes by frozen design (decile would mechanically
violate the n≥200 floor at ~1,580 eligible days; decision made now,
before outcomes). Intraday thresholds: type-7 quantiles of pooled
prior-**250-day** checkpoint values per scale (≥1,000 pool floor;
satisfiable: 9 stamps/day). S3 thresholds: prior 250 daily ARd values
(≥200 floor). Neighbors (diagnostic only): q85/q95 intraday, q75/q85
daily.

**Translation (frozen).** Intraday cells: enter at next 1m bar open
after the stamp; stop 3×ATR20(1m) raced bar-by-bar (stop-first
ambiguity, gap-through at worse open); exit at the open of the bar 60
minutes after entry (first later bar; day-last close if none); 60m
cooldown, each cell evaluated standalone (RMA convention). S3 cells:
enter at today's first RTH bar open, exit at day-last RTH close, no
stop (day-cell precedent), signal known at prior close. Costs 0.87
base / 1.305 stressed per RT; MNQ $2/pt; one contract, non-compounded.

**Statistics and gates (house standard, frozen).** Per cell:
day-clustered bootstrap B=10,000 (seed 20260920) on stressed mean;
day-blocked sign-flip permutation P=10,000 (seed 20260921); BH across
the 8 cells (q≤0.05). Gates: n≥200 · days≥60 · base+stressed>0 · PF
≥1.30/≥1.15 · EV ≥+0.10R/+0.05R (intraday; day cells: stressed
mean>0 and PF gates) · CI LB>0 · p≤0.05 · q≤0.05 · ≥6/8 years
positive · no single year >50% of profit · survives best-day and
top-1% removal · +1 delay positive (day cells: entry at open+30m
positive) · frozen neighbors majority positive · **incrementality:
split events by displacement benchmark sign (trailing 60m return for
intraday, trailing 20-day return for daily); the stressed mean must
keep its sign in BOTH strata** · full frequency table (Section 7 of
the directive): mean/median trades/week, weekly distribution,
zero-trade-week %, ≥60% of complete weeks with ≥1 trade and mean ≥1.0
required for the primary high-frequency mandate; otherwise
`LOWER-FREQUENCY SECONDARY CANDIDATE`. **Monte Carlo (100,000
day-block bootstrap paths, seed 20260922, five-year-equivalent) runs
ONLY for a cell passing every preliminary gate; MC can never rescue a
failure.**

Variant budget: exactly the 8 cells + frozen neighbors/delay/exit
(45m/90m) diagnostics. Nothing added, merged, inverted, or
re-thresholded after outcomes. Full battery runs to completion; every
cell is registered at close-out (DEAD_FROZEN on failure). Failure
kills the family as frozen — no rescue.

Unit tests precede the run: age computation on synthetic refresh
schedules (wall-clock and volume clock), rolling-240 correctness,
S3 DH/DL on synthetic daily paths, causality (ages use only completed
bars ≤ stamp; thresholds from prior days only), race function
adverse-sequence behavior.
