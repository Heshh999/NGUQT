# RVMR-V1 — PERMANENT FROZEN SPECIFICATION

**Status: FROZEN CONTEXT TOOL.** Answers one question only: *how much
movement is the current market environment likely to offer?* It never
answers long/short, buy/sell, size, stop, target, or trade/no-trade.

## Registry entry

| field | value |
|---|---|
| status | **FROZEN CONTEXT TOOL** |
| purpose | MOVEMENT REGIME |
| data | OHLCV (1m), nothing else |
| directional | **NO** |
| trade control | **NO** |
| position sizing | **NO** |
| prospective logging | **YES** (companion module, outside NT8) |
| certified historical replication | **YES** — `docs/RVMR_V1_5Y_REPLICATION.md` |
| combined RVMR-C1 | **NOT YET AUTHORIZED** |
| strategy grading (A+/A−/B+) | **NOT YET AUTHORIZED** |

*(Recorded here, not in `PROSPECTIVE_REGISTRY.md`, which is on the
protected do-not-modify list.)*

## Source of truth

| file | sha256(16) | role |
|---|---|---|
| `analysis/rvmr/rvmr_spec.py` | `e348f035a9209540` | frozen formulas/thresholds |
| `analysis/rvmr/rvmr_run.py` | `8743161d6fb5b04e` | certified replication engine |
| `analysis/rvmr/rvmr_extract.py` | `b1160ccf377af345` | V3 extraction |
| `analysis/mag/mag_lib.py` | `c1b2a961cb2cd464` | original discovery formulas |
| certification commits | `84933d2` (freeze), `8534fda` (5-year result) | |

## Exact frozen definition

```
score(x)_t = x_t / mean(x_{t-1440 .. t-1})
   RANGE-REGIME-V1:  x = high - low        (completed 1m bar)
   VOLUME-REGIME-V1: x = bar volume
window   = 1440 BARS over the full merged series incl. overnight;
           the current bar is EXCLUDED from its own normaliser
buckets  = LOW < 1.270   MEDIUM 1.270..2.335   HIGH > 2.335
           (identical numeric thresholds for both tools, verbatim from
            the certified implementation; never recalibrated)
stamping = 1m bars CLOSE-stamped, US/Eastern
availability = a state exists at, and not before, the close of its bar;
           rvmrAvailableTime == bar close time
warmup   = 1440 prior bars required, else UNAVAILABLE
           (reason INSUFFICIENT_WARMUP)
missing bars = the window slides over the bars that EXIST (NinjaTrader
           prints no bar when nothing trades); nothing is interpolated
           or carried forward
certified research universe = RTH stamps 09:30..15:00 (the >=60-min-to-
           close requirement of the certified labels); the logger also
           records 15:01..16:00 states flagged inCertifiedUniverse=FALSE
```

## Canonical output (per eligible stamp)

`rvmrVersion, rvmrAvailableTime, rvmrRangeScore, rvmrRangeRegime,
rvmrVolumeScore, rvmrVolumeRegime` — labels only from
{LOW, MEDIUM, HIGH, UNAVAILABLE}. No combined score, no grades, no
bullish/bearish reading exists in this version, deliberately.

## Certification summary

- Five-year backward replication: monotone LOW<MED<HIGH in **70/70**
  year×horizon cells; **74/74** months positive; day-level Spearman
  +0.397/+0.448, permutation p 0.00005; effect survives time-of-day
  matching (84–104%) and within-era slicing; full report in
  `docs/RVMR_V1_5Y_REPLICATION.md`.
- Implementation parity: **593,190 rows, 0 score mismatches, 0 regime
  mismatches, 0 timestamp mismatches** (exact float equality) between
  the certified engine and the production logger.
- Cross-feed determinism: 13 forward-most sessions computed from two
  independent data paths (prospective capture vs Strategy-Analyzer
  tick-built): **5,083 rows, 0 regime mismatches.**

## Known limitations (documented, not repaired)

1. **Scores are feed-relative near feed defects.** Comparing the
   capture feed against the V3 export over 202 days produced 84 label
   flips in 154,924 comparisons (0.054%), fully classified: 57 from a
   V3-asset day outage (2026-01-23) contaminating the next session's
   trailing window; 6 at 16:00 close bars (outside the certified
   universe); 4 at/after LTF-quarantined violent minutes where feeds
   genuinely disagree on a bar; 17 with scores within ≤0.013 of a
   frozen boundary. Within one feed the tool is exactly deterministic.
2. A feed outage day contaminates trailing normalisers for roughly one
   session afterwards. The window-over-existing-bars rule is the
   certified behavior and is preserved.
3. Near-threshold states can differ across imperfect feed copies; the
   canonical forward feed (below) is therefore the single source of
   truth for logged states.
4. HIGH is symmetric information: MFE/MAE ≈ 1.00 and favourable-first
   ≈ 50% in every bucket over five years. **RVMR carries no directional
   content whatsoever** — measured, not assumed.

## Permitted uses

calculate · display · log · attach as context to research events ·
backfill historical research datasets (labelled
`RETROACTIVE_CONTEXT_BACKFILL`) · later analysis under pre-registered
hypotheses.

## Forbidden uses

select/reject/block trades · choose direction · alter entries, exits,
stops, targets, runners · change size or risk · grade setups (A+/A−/B+)
· modify OFH13 or any frozen strategy · construct RVMR-C1 or any
combined/weighted score. There is deliberately **no**
`EnableRvmrTradingFilter` switch, and no code path by which RVMR can
reach an order API (it does not run inside NinjaTrader at all).

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
