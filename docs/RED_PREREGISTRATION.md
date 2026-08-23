# RED-* FAMILY — PRE-REGISTRATION (frozen before any performance was seen)

Four Reddit-**inspired**, mechanically translated, **exploratory-derived**
hypotheses. They are NOT official strategies of any trader or community,
and they are NOT assumed to work. M = 4 primary hypotheses. No RED-H11
will be created; no variants will be added after results.

**These rules were written and committed before any RED-* outcome was
computed.** Everything below is fixed.

## Data availability audit

| feature | status |
|---|---|
| 1m OHLC, volume | AVAILABLE |
| bid volume / ask volume / bar delta / delta % | AVAILABLE |
| cumulative delta, min/max delta, slope | AVAILABLE |
| stacked imbalance counts 2x / 3x / 4x, buy+sell | AVAILABLE |
| aggressive buy / sell volume | AVAILABLE |
| price progress up/down ticks; volume per up/down tick | AVAILABLE (native effort-vs-result) |
| absorption candidate flags + raw strength | AVAILABLE (capture's own proxy) |
| ATR(20) | AVAILABLE |
| developing volume profile: POC, VAH, VAL, insideValueArea | AVAILABLE and **causal** (verified: 23 distinct POCs within one day, value area widens intraday and resets at the session boundary) |
| HVN / LVN **counts** | AVAILABLE |
| **HVN / LVN price locations** | **NOT AVAILABLE** — only counts are stored |
| per-price footprint bid/ask ladder | **NOT AVAILABLE** (`f_outputMode = MODE1_SUMMARY`) — not invented |
| DOM / depth history | **NOT AVAILABLE** (`f_depthHistoryAvailable = FALSE`) |
| VWAP | **NOT AVAILABLE** in the order-flow capture |
| 3m / 15m swings | **DERIVED CAUSALLY HERE** from 1m (the separate structure capture is a *break-event* record, incomplete as a swing inventory, so it is not used) |
| prior-day RTH high/low | DERIVED CAUSALLY |
| FVG | DERIVED CAUSALLY (3-candle, known at close of candle 3) |

### Consequence for RED-H1

The rule requires "a causal HVN or high-volume-value area". Discrete HVN
**prices** are NOT stored, so the strict HVN form is **INSUFFICIENT DATA**
and is reported as such. The rule's alternative — "high-volume-value
area" — *is* available as the developing value area (VAL/VAH), which is
by construction the region of accepted volume. RED-H1 is therefore run as
an explicitly labelled **value-edge translation (RED-H1/VE)**, never
claimed to be an HVN test. POC is NOT substituted (the directive forbids
it); only the value-area boundaries are used.

## Causality rules (enforced in code)

- Every feature used at entry comes from bars with `tmin <= entry tmin`.
- Every derived swing carries `known_j` = the 1m index at which its
  confirmation bar closed; it is invisible before that index.
- FVGs are known only at the close of candle 3.
- The developing profile is the capture's own causal field.
- Forward path metrics require the full consecutive window to exist.
- Entry gate (frozen): RTH, `minutesToRthClose >= 60`, valid ATR.

## Frozen constants

| constant | value | source |
|---|---|---|
| cost | 0.87 pt round trip | existing frozen MNQ assumption |
| aggression threshold | `|delta| >= 511` | **previously frozen** Q_BD75 — reused, not refitted |
| effort scale | causal rolling median `|delta|`, 60 bars | fixed |
| swing confirmation | 2 bars either side, 3m and 15m | fixed |
| compression window | 5 bars (primary) | fixed |
| horizons | 5 / 10 / 15 / 30 / 60 min | fixed |

## Effort-vs-result (one primary, two robustness)

- **E2 — PRIMARY (frozen):** `(|opposing delta| / rolling median |delta|)
  ÷ (adverse tick progress × 0.25 / ATR)`. Most direct reading of the
  mechanism: aggression per unit of price actually achieved.
- E1 robustness: the capture's native volume-per-tick-of-progress
  (verified to use a different volume basis, so genuinely independent).
- E3 robustness: same effort ÷ adverse **range** in ATR.

E1/E3 are reported as robustness only and are **never** used to select.
The "failure" cut is the DEV 75th percentile of the E2 score, frozen on
DEV before IR is examined.

## RED-H1/VE — value-edge defence + trapped aggression

LONG: (1) developing value area known and price is at/below VAL within
0.25 ATR; (2) the bar shows elevated **selling** aggression
(`delta <= -511`); (3) E2 failure score in the top DEV quartile (effort
without result); (4) a completed 1m close back **above VAL**. Enter long
at that reclaim close. SHORT mirrors around VAH.

Controls: value-edge touch only · touch + aggression · touch + aggression
+ failure · full (+ reclaim) · same aggression failure **away** from the
value edge · matched non-value-edge locations.

## RED-H2 — CVD nonconfirmation at a causal extreme

LONG: (1) price retests a causally-known structural low (3m swing low,
15m swing low, or prior-day RTH low — **reported separately, not pooled**)
within 0.25 ATR; (2) cumulative delta is materially **more bearish** than
it was at that level's confirmation time (`cumDelta_now < cumDelta_then`,
margin ≥ the DEV median absolute cumDelta change); (3) price does **not**
confirm: it undercuts by less than 0.25 ATR or reclaims; (4) **no entry
yet** — require a completed 1m close above the most recent causally-known
1m micro swing high (2-bar confirmation). Enter long on that close.
SHORT mirrors.

Controls: plain CVD divergence · CVD divergence at a causal extreme ·
extreme + confirmation **without** CVD divergence · full RED-H2.

## RED-H6 — compression + delta alignment → directional release

LONG: (1) the 5-bar high-low range ÷ ATR is at/below the DEV 25th
percentile (compression), all 5 bars consecutive; (2) the sum of delta
across those 5 bars is ≥ +511 (aligned, frozen); (3) price has not
already broken above the compression high; (4) a completed 1m close
**above** the compression high. Enter long on that close. SHORT mirrors.

Controls: compression breakout alone · delta alignment without
compression · compression + delta but breakout **opposite** the delta ·
full. Plus a matched price-momentum comparison to test whether delta adds
anything price momentum does not.

## RED-H10 — FVG + failed aggression + contextual location

Separate from and not affecting frozen OFH13.

LONG: (1) a causal bullish FVG exists; (2) it lies within 0.5 ATR of ONE
contextual location family — **3m swing support**, **15m swing support**,
**prior-day low**, or **value edge** — each reported separately, never
pooled initially; (3) price performs the FIRST mitigation of that FVG;
(4) during mitigation, selling aggression is elevated (`delta <= -511`);
(5) E2 failure score in the top DEV quartile; (6) a completed close back
above the **FVG midpoint** (frozen primary trigger). Enter long on that
close. SHORT mirrors.

Mandatory ablation: A FVG only · B FVG + location · C FVG + failed
aggression · D location + failed aggression without FVG · E full.

## Reporting (fixed in advance)

Per hypothesis and per direction: N, signals/week, signals/month, mean and
median forward points, MFE and MAE at all five horizons, MFE/MAE,
favourable-first at ±0.25 / ±0.5 / ±1 / +1.5 vs −1 / +2 vs −1 ATR (with
AMBIGUOUS marked, never assigned), long vs short, positive weeks and
months, P&L concentration (top 1% / 5%), cost-adjusted expectancy,
DEV→IR consistency, matched-control advantage.

**Primary criterion is ENTRY ASYMMETRY, not average points.**

## Gates

- **Stop research only for raw survivors** — a hypothesis whose raw
  geometry shows no credible improvement in MFE/MAE, favourable-first or
  MAE reduction versus matched control is stopped and NOT rescued with
  management.
- Stop families are mechanically justified only (structure, 1 ATR,
  1.5 ATR, rule-specific invalidation). No arbitrary ATR grid search.
- R:R tested only for survivors, looking for a broad plateau, never an
  isolated maximum.
- Multiple testing: M = 4, with raw p, day-clustered bootstrap CI,
  sign-flip permutation p, and BH q.

## Partitions and status

| partition | span | status |
|---|---|---|
| U | ≤ 2025-11-01 | historical, SPENT |
| DEV | 2025-11-02 → 2026-03-31 | thresholds frozen here |
| IR | 2026-04-01 → 2026-08-19 | internal replication |

All three are already-spent history. These hypotheses were written after
that history was examined, so **however good the numbers look, they are
EXPLORATORY-DERIVED and NOT externally validated.** Only prospective data
can change that.

## Prohibitions honoured

Frozen OFH13_PROSPECTIVE_V1 is not modified. No current or future OFH13
prospective trade is used to design these rules. No hypothesis is added
after results.
