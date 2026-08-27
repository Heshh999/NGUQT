# MGSD_V1_PROTOCOL_FREEZE.md — version 1.0

Frozen 2026-08-27 (UTC), BEFORE any DEV candidate outcome was computed.
Authorization: repository/data audit, exposure audit, partition design,
protocol freeze, DEV-only discovery and robustness, freezing ≤3 full-gate
candidates. NOT authorized: VALIDATION/OOS/LOCKBOX outcomes, deployment,
NinjaTrader code, order/logger changes, calling any DEV result confirmed.
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

## 1. Data and partitions
- Primary grid: canonical close-stamped 1m MNQ (manifest hashes in
  `MGSD_V1_DATA_MANIFEST.json`), 2019-07-04 → 2026-08-17, 2,218 days,
  six complete years 2020–2025.
- 30s arm: ph2 raw OHLCV `timeframe==30s` rows only; 34,944 bars,
  192 days, 2025-09-01 → 2026-05-29, 182 slots 09:30:00–11:00:30.
  All non-OHLCV ph2 columns PROHIBITED.
- Exposure: per `MGSD_V1_EXPOSURE_LEDGER.csv` the ENTIRE historical span
  is previously analyzed/used for selection. **No untouched history
  exists → DEV = all admissible data ≤ 2026-08-17 (30s ≤ 2026-05-29).**
- **VALIDATION = 2026-09-01→2027-02-28; OOS = 2027-03-01→2027-08-31;
  FINAL LOCKBOX = 2027-09-01→ (all future, not yet collected; reserved;
  never backfilled with exposed data).** 2026-08-18→31 = buffer, no role.
- Held-out rules: mechanical integrity checks only; candidate signals,
  outcomes, MFE/MAE, P&L, conditional performance, feature/parameter
  selection PROHIBITED (enforced by test: engine refuses days >
  2026-08-17).

## 2. Sessions, strata, timing, causality
- Strata (ET close stamps): S1 post-close 16:01–17:00; S2 Globex night
  18:01–02:00; S3 early premarket 02:01–08:00; S4 late premarket
  08:01–09:29; S5 opening drive 09:31–10:00; S6 RTH morning 10:01–11:30;
  S7 midday 11:31–14:00; S8 afternoon 14:01–15:30; S9 close 15:31–16:00.
  Strata are research strata; no finer post-hoc cutoffs.
- Signal = state of completed bars at close stamp T. **Earliest entry =
  open of the next 1m bar (stamp T+1, em-contiguous); no entry across a
  gap.** HTF features (3m/15m/60m) use only completed groups (B−k, B].
  Prior-day/week levels use completed sessions. Session extremes use
  values known at T.
- All positions exit no later than the RTH close (16:00) of the entry's
  CME trade date (trade date of a ≥18:00 entry = next calendar RTH).
  Overnight/premarket entries may hold through the open to that close.
- Open-of-day for gap logic = open of the bar stamped 09:31.
  Premarket-to-open predictors end at stamp 09:29; the 09:30 bar and
  later belong to outcomes only.
- Same-bar target/stop ambiguity (no finer genuine path): **stop-first**;
  ambiguous trades counted; exclusion sensitivity reported. 30s arm: same
  rule at 30s granularity.
- No limit entries in V1 (all entries are next-bar-open market entries),
  so touch-fill modeling is not required; entry-delay and slippage stress
  cover latency realism.

## 3. Duration classes and horizons
- Classes by frozen exit: micro-scalp (≤5m), scalp (≤15m), standard
  (≤60m), extended (≤120m or RTH-close).
- Anomaly screening horizons (frozen): 1, 3, 5, 10, 15, 30, 60, 120
  minutes and RTH-close. Every horizon is a counted test.
- 30s-arm horizons: 30s, 60s, 90s, 2m, 3m, 5m, 10m, 15m.

## 4. Management grid (frozen)
- Stop ∈ {1.0, 2.0} × ATR14(15m, completed, causal at signal). Finite
  risk required; R = stop distance in points.
- Exits: TIME30 (30 bars), TIME120 (120 bars), RTHCLOSE (16:00), and for
  mean-reversion families a REFERENCE target (VWAP / gap-fill level) with
  the stop; race resolved bar-by-bar, stop-first inside a bar.
- Per-family management cells are fixed in §6 (≤4 per signal rule).
  No trailing/breakeven/partials in V1.

## 5. Costs (frozen)
- Base: 0.87 pt round turn (frozen repository MNQ model), all strata.
- Stressed: 1.305 pt (1.5×) for RTH entries (S5–S9); 1.740 pt (2.0×) for
  non-RTH entries (S1–S4) — thinner-session penalty.
- Commission-and-fee-only: **UNRESOLVED** (no genuine commission schedule
  in the repository; none invented). Results reported gross, base, and
  stressed in points and R; dollars at $2/pt where shown.
- Reported always: gross / base / stressed. No zero-friction promotion.

## 6. Discovery matrix (frozen families and budgets)
Base grid 1m; both directions analyzed separately; thresholds and
budgets fixed; every variant is one ledger row. Signal definitions:

| id | family (economic class) | stratum | signal (completed bars) | thresholds | mgmt cells | variants |
|---|---|---|---|---|---|---|
| F01 | displacement mean-reversion | S6–S8 | 15m return ≤ −k·ATR14_15m (mirror +k) → fade | k∈{1.5,2.5} | stops×{T30,T120} | 16 |
| F02 | displacement continuation | S6–S8 | same event → trade with displacement | k∈{1.5,2.5} | stops×{T30,T120} | 16 |
| F03 | compression→expansion | S5–S6 | 30m opening range ≤ q×trailing-20d-median, first 1m close beyond OR before 11:30 → break dir | q∈{0.6,0.75} | stops×{T30,T120} | 8 |
| F04 | expansion→exhaustion | RTH | 3 consecutive same-dir 15m bars, cum ≥ m·ATR14_15m → fade | m∈{2.5,3.5} | stops×{T30,T120} | 8 |
| F05 | failed-break/reclaim (REFERENCE BASELINE, non-promotable; existing FB system analogue) | S5–S6 | OR15 break then 1m close back inside ≤15m → fade | — | 1.0-stop×{T30,T120} | 4 |
| F06 | breakout acceptance (prior-day levels) | S5–S7 | first 15m close beyond PDH/PDL by ≥0.25·ATR14_15m → continuation | fixed | stops×{T30,T120} | 8 |
| F07 | VWAP stretch reversion | S6–S8 | |close−sessVWAP| ≥ k·ATR14_15m → fade | k∈{2,3} | stops×{T30, VWAP-target} | 8 |
| F08 | VWAP reclaim trend | S6–S8 | ≥60m on one side, first 15m close across → with cross | fixed | stops×{T120,RTHCLOSE} | 8 |
| F09 | gap fade (overnight inventory) | S5 entry 09:31 | |gap| ≥ g×prior RTH range → toward prior close | g∈{0.3,0.5} | stops×{T120, gap-fill target} | 8 |
| F10 | gap continuation | S5 entry 09:31 | same event → with gap | g∈{0.3,0.5} | stops×{T30,T120} | 8 |
| F11 | opening-range breakout | S5–S6 | first 1m close beyond OR15 (+c·ATR14_15m) after 09:45 → break dir | c∈{0,0.25} | stops×{T30,T120} | 8 |
| F12 | overnight-range break at open | S5–S6 | first 1m close beyond ON(18:00–09:29) H/L after 09:30 → continuation | c∈{0,0.25} | stops×{T30,T120} | 8 |
| F13 | cross-TF alignment pullback | S6–S7 | 60m and 15m same dir, 3m counter bar, first 3m close resuming → trend dir | fixed | stops×{T30,T120} | 8 |
| F14 | volatility-regime transition | RTH | ATR14_15m ≥ 1.25× its value 20 15m-bars ago AND new session extreme → continuation | fixed | stops×{T30,T120} | 8 |
| F15 | session drift / time-of-day | S2/S5 | unconditional: ON 18:01→09:31-open; ON 18:01→RTHCLOSE; 09:31→RTHCLOSE; L and S | stops {2.0,3.0}·ATR14_15m(prior) | — | 12 |
| F16 | late-premarket trend → open | entry 09:31 | 08:00→09:29 return ≥ p·ATR14_15m → continuation at open | p∈{0.5,1.0} | stops×{T30,T120} | 8 |
| F17 | midday-range break | S8 | first 15m close beyond 11:30–14:00 range after 14:00 → continuation | c∈{0,0.25} | stops×{T30,T120} | 8 |
| F18 | closing momentum | S9 | 14:00→15:30 return ≥ p·ATR14_15m → 15:31 entry, exit 16:00 | p∈{1.0,1.5} | 1.5-stop | 4 |
| F19 | path-sequence run reversal | S6–S8 | ≥r consecutive same-dir 3m closes then first opposite 3m close → reversal dir | r∈{4,6} | stops×{T30,T120} | 8 |

**Promotable 1m strategy variants M_strat = 152** (F05's 4 baseline rows
excluded from promotion, included in the ledger). Anomaly layer: each
family's underlying condition × 9 horizons, descriptive conditional
means (M_anom = 19×9 = 171, report-only, BH separately).
Lineage flags (distinctness duties): F05→existing Fake Breakout; F19→
MEMORY-MATH A4 (1m aged-run, real-but-sub-material) — F19 is its 3m
strategy conversion and must beat the F19-specific baselines; F12/F11
must be distinguished from Break-and-Retest (no retest requirement —
acceptance/continuation only); F14 uses ATR (not RVMR) by design.

## 7. Premarket→open influence study (9A)
Predictors (all end ≤ 09:29 stamp): overnight return (18:01→09:29), gap
vs prior RTH close, ON range/prior-range, PM(02:01→09:29) return,
late-PM(08:01→09:29) return, position of 09:29 close inside ON range,
relative volume (04:01→09:29 vs trailing 20-day same-window mean), ON
extreme timing (fraction of night elapsed at ON high/low). Outcomes:
09:30→10:00, 09:30→11:30, open→RTH-close signed returns, OR15 break
direction. M_pm = 8×4 = 32 tests, BH within study. Controls: gap, ON
return/range, volatility (ATR14_15m at 09:29), relative volume, weekday;
residualization + matched terciles. Placebos (frozen): ±1/±5 trading-day
date-shift of the predictor vector; random day-pairing (1,000 draws);
weekday/seasonality comparison; top-decile influential-day removal;
deliberate future-feature negative control (the 09:30→10:00 outcome
itself injected as a "predictor" must show near-perfect strength — if
the harness fails to flag it, the harness fails).

## 8. 30-second arm (9B)
Standalone families (budget): S30-A opening 30s momentum — first n
completed 30s bars from 09:30:00 net direction ≥ threshold → continuation,
n∈{4,10}, thr∈{0.5,1.0}·ATR(30s,28); S30-B 30s ORB(5m) break →
continuation, c∈{0,0.25}. Management: stop {1.0,2.0}·ATR(30s,28)×
exits {5m,15m} → 12+8 = 20 variants (M_30s=20; BH within arm).
Incremental-refinement arm: NOT RUN — there is no previously frozen
1-minute parent candidate; recorded as inapplicable.
**Any 30s passer is PROVISIONAL by frozen rule: 9 months of coverage can
never satisfy five-year durability; label `SUB-MINUTE TEMPORAL
DURABILITY: INSUFFICIENT DATA` regardless of statistics.**

## 9. Event independence
EventID per signal; MARKET EVENT = same family, same day, same direction
within 30 minutes → clustered (first signal only is traded; max 1 trade
per variant per side per day). Effective independent events = unique
(family, day, direction) market events. Inference clustered by day.
Overlapping outcome windows within a variant are impossible by the
1-per-side-per-day rule; cross-variant overlap is reported in the
correlation matrix.

## 10. Statistics and multiplicity (frozen)
- Seed 20260827. Bootstrap: day-clustered percentile, B = 10,000, 95% CI.
- Permutation null (conditional families): matched random-entry — P =
  10,000 draws of the same number of entries drawn uniformly from the
  same stratum slot-grid on the same trading days, scored with identical
  management and costs; p = (1+#{null mean ≥ observed})/(P+1). This is
  simultaneously the signal-destruction test. Unconditional families
  (F15, F18 threshold-free rows): bootstrap p doubles as the test.
- BH q within each frozen family-group: STRAT_1M (152), ANOM (171),
  PM (32), S30 (20). M_total = 375. Never shrunk; failures retained.
- Trade-quality floors (§8 of the directive, binding): base PF ≥ 1.30;
  stressed PF ≥ 1.15; base EV ≥ +0.10R; stressed EV ≥ +0.05R; stressed
  CI lower bound > 0; realized payoff = avg net win / |avg net loss|;
  profile floors {38%/2.00, 45%/1.50, 55%/1.00, 65%/0.70} or
  nondominated-stronger; break-even margin ≥ 5 win-rate points above the
  payoff-implied break-even.
- Preliminary gates 1–19 exactly as the directive §17, with: floors
  ≥100 effective events / ≥40 days / ≥30 per binding subgroup;
  residual retention ≥50% + no sign flip vs baselines (signed 15m
  momentum, ATR tercile, ToD, relative volume, VWAP distance, trend
  regime, unconditional same-stratum drift — via residualization +
  matched terciles); nearby thresholds (the family's other frozen
  threshold) same sign & ≥50%; drop-most-influential keeps sign; ≥70% of
  eligible half-year segments same sign; ablation of each rule component;
  deterministic reproduction.

## 11. Durability, walk-forward, Monte Carlo, stress (for preliminary passers)
- Five-year durability: six complete years exist (2020–2025). Gates per
  directive §18 (≥4/5 or ≥80% years positive stressed; ≥70% rolling-12m
  positive; positive after best-year removal; no year >50% of profit; no
  regime domination; frequency persistence; coherent rationale).
- Walk-forward (frozen folds): expanding — train ≤2020→test 2021,
  ≤2021→2022, ≤2022→2023, ≤2023→2024, ≤2024→2025, ≤2025→2026H1 (6 folds);
  rolling — 24m train / 6m test stepping 6m from 2020-01. Selection per
  fold = the family variant with best TRAINING stressed EV (only fitted
  quantity). Gates per §19.
- Monte Carlo: 100,000 paths × 5-year-equivalent trade count per method:
  (1) trade reshuffle; (2) trading-day block bootstrap; (3) stationary
  block bootstrap (mean block from daily-P&L autocorrelation time,
  min 5 days); (4) regime-stratified (year-strata) resampling;
  (5) cost/fill jitter (cost ±25% uniform, 10% random missed trades).
  Seeds 20260827+method; multi-seed confirmation at 3 seeds. Percentiles
  {1,5,10,50,90,95,99} of terminal P&L, EV, PF, maxDD, DD duration,
  losing streak, recovery, Sharpe, Sortino, CVaR(5%), P(negative 5y).
  Strong gate: 10th-percentile terminal > 0 at BASE cost.
- Risk of ruin per §21 (ruin = −50% of stated capital OR margin breach;
  capital scenarios $5k/$10k/$25k per MNQ contract; fixed-fraction grid
  0.25–2.0% per trade).
- Execution stress per §22 (full matrix incl. ±1/±2-bar delay, missed
  5/10/20%, win/loss haircuts, best-trade/day/month removal).
- Parameter stability per §23: ±10%/±20% perturbations of every numeric
  parameter; ≥70% of neighborhood positive stressed; plateau requirement.
- Overfitting diagnostics per §23: DSR, PSR, PBO (CSCV, S=16 splits on
  daily P&L panel of ALL ledger variants), SPA-style reality check vs
  the full variant family; targets DSR ≥95%, PBO <20%, SPA p ≤0.05;
  `INSUFFICIENT/NOT IDENTIFIABLE` where invalid.
- Tail/dependency per §24; multi-passer correlation per §24.

## 12. Ranking, ceiling, stopping
Ranking (frozen): 1 stressed-EV CI lower bound; 2 stressed PF & payoff;
3 temporal/regime stability; 4 MC/ruin strength; 5 drawdown burden;
6 execution tolerance; 7 plateau breadth; 8 frequency; 9 distinctness.
Maximum 3 advance; zero advance if zero pass; no fallback; no rescue.
The FULL matrix runs to completion regardless of early passers. The
search stops only on completion or a binding data/causality defect.
Any protocol correction → new version, committed before rerun, defective
results invalidated and ledgered.

## 13. Deliverables
As directive §26, all under `analysis/mgsd/`. Reproduction:
`python3 analysis/mgsd/run_all.py` (deterministic, seed 20260827).
