# MGSD-V1 — DEV DISCOVERY RESULTS

Protocol freeze commit `7062e6783f96d59b071c6d31527f30e96f76411a`
(v1.0.0), correction v1.0.1 at `f8ec75f` (F15 dedupe; committed before
the rerun; the defective first run was invalidated and deleted without
inspecting its gate outcomes). Seed 20260827. Reproduction:
`python3 analysis/mgsd/run_dev.py` after `tests_mgsd.py` (19/19 PASS).

## HEADLINE
> **MGSD-V1 DEV FOUND NO FULL-GATE STRATEGY CANDIDATE.**
> 0 of 244 scored strategy variants passed the preliminary gates
> (152 promotable frozen variants produced 244 scored direction rows;
> every family completed its frozen budget; nothing was stopped early,
> nothing rescued, no floor lowered).

## Search burden (complete, failures retained)
- 19 one-minute families + 1 baseline family, 240 promotable scored
  rows + 4 baseline rows = **244 ledger rows**
  (`MGSD_V1_HYPOTHESIS_LEDGER.csv`).
- Anomaly screen layer: **162 cells** (19 family conditions × 9 horizons
  minus insufficient cells), `anom_screen.csv`.
- Premarket→open study: **32 tests**. 30-second arm: **20 variants**.
- Statistical tests total ≈ **458** frozen cells across four BH families.

## First-binding-failure anatomy
| first failing gate | variants |
|---|---|
| G04 trade-quality floors (§8) | 212 |
| G01 ≥100 effective events | 32 |

Every variant that survived sample floors failed the quality floors
before any statistical gate even mattered. 80 of 212 adequately-sampled
variants had positive stressed EV — but none with the required PF/EVR/
profile combination.

## Nearest misses (recorded, NOT candidates, NOT rescuable)
| variant | n | stressed EV | EVR | PF | WR | CI lo | perm p | BH q | fails |
|---|---|---|---|---|---|---|---|---|---|
| F09_g0.5_S10_T120 (gap-up fade, 1.0 stop, 120m) | 323 | +11.19 | +0.44 | 1.59 | 22.9% | **+2.19** | 0.026 | 0.135 | G04 (WR below every profile), G07 |
| F09_g0.5_S20_TGT (gap-up fade to fill) | 323 | +10.05 | +0.17 | 1.33 | 32.5% | −0.46 | 0.0001 | **0.0009** | G04, G05 |
| F03_q0.75_S10_T120 (compression break) | 197 | +8.45 | +0.32 | 1.46 | 30.0% | −0.79 | 0.007 | 0.043 | G04, G05 |
| F15_OPEN2CLOSE_L30 (long day drift) | 1,767 | +5.98 | +0.06 | ~1.07 | ~52% | +0.19 | 0.042 | 0.202 | G04 |
| F01_k2.5_S20_T120 | **32** | +40.16 | — | — | — | — | — | 0.0017 | **G01** (n=32) |

The gap-fade family (F09, short side = fading gap-up opens toward the
prior close) is the one economically coherent near-miss: positive in
both management architectures, CI-positive in one, permutation-real,
n=323 days. It fails the frozen §8 floors on its 20–36% win rate (its
payoff ratio ≈ 3–5 does not clear the high-payoff row's 38% WR floor)
and fails BH in its CI-positive form. **Under the frozen protocol it
does not advance and cannot be rescued**; it is recorded for a possible
future preregistered study on future data only.

## Statistically real NEGATIVE results (knowledge)
37 cells reached BH q ≤ 0.05; most are significantly HARMFUL rules:
- **F07 VWAP-stretch fading loses in both directions** (8–16 cells,
  q ≤ 0.002): stretched markets keep going, net of costs.
- **F04 exhaustion-fading of 3-bar 15m runs loses** (q ≤ 0.001).
- F19 3m-run reversal at r=6 loses on shorts (q 0.034).
This mirrors the programme's standing result: fading strength on this
instrument destroys value after costs.

## Anomaly screen layer
2 of 162 cells at BH q ≤ 0.05: F08 VWAP-reclaim +1.28 pt at 3m;
F14 vol-expansion-with-new-extreme +1.34 pt at 1m. Both are ~1.5× base
cost gross at their best horizon, decayed at longer horizons, and their
strategy conversions failed the floors — consistent with real but
economically immaterial microstructure.

## Duration classes and strata
All four duration classes and all authorized strata were searched
(overnight and premarket via F15/F16 and the 9A study; RTH via
F01–F14, F17–F19). No stratum was pooled with another; no class
produced a passer.

## Verdict
Zero candidates advance. `MGSD_V1_FROZEN_CANDIDATES.json` is empty.
The robustness program (five-year durability, walk-forward, Monte
Carlo, execution stress, parameter stability, DSR/PBO/SPA, risk of
ruin, correlation) applies only to preliminary passers under the frozen
protocol; with zero passers it was **not executed for any variant**
(rescue prohibition), and its deliverable files record that state.
