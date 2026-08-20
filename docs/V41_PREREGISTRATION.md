# V4.1 Preregistration — Frozen Before Outcome Review

Preregistration timestamp: **2026-08-20** (before any feature→outcome
relationship on the full capture has been examined; see Phase 0 audit,
OOS/LOCKBOX INTEGRITY).

Data available at preregistration: full-capture STRUCTURE audit
(28,554 rows, PASSED), full ENTRIES files (72,403 rows, marginal
verification only), full ORDER-FLOW capture (281,214 bars, PASSED).
Structure CSVs not yet delivered; nothing conditional has been run.

## 1. Primary Class A market-edge hypotheses (8 of the 5–10 allowed)

H1–H6 were frozen in the engine registry at v4.1.0 and are embedded in
every audit printout; their definitions are unchanged. TR-H1-W and
TR-H2-M are added NOW, before outcome review, from the prompt's
candidate library; both are computable from already-captured columns.

| ID | Parent event | Direction | Source class |
|---|---|---|---|
| H1-VECTOR-SWEEP-REVERSAL | Confirmed 15m structural extreme swept by a 15m vector (RED\|VIOLET at low / GREEN\|BLUE at high), acceptance fails, LTF reclaims (ARCH-C) | Reversal, side = away from swept extreme | Registry v4.1.0 |
| H2-VECTOR-BREAK-CONTINUATION | 4H and 15m aligned; 15m vector closes beyond confirmed structure; LTF accepts (ARCH-B) | Continuation | Registry v4.1.0 |
| H3-LTF-TAKES-15M-WICK | 15m vector wick extreme taken by 1m/3m; BOTH branches (reclaim and acceptance) captured against the same parent | Either; branches pre-split | Registry v4.1.0 |
| H4-VECTOR-AT-LEVEL | Any vector while interacting with a tracked level (interaction ≠ NO_INTERACTION) | Rejection vs acceptance branches | Registry v4.1.0 |
| H5-UNRECOVERED-VECTOR-DESTINATION | Structure directional toward an older unrecovered 15m vector zone | Toward the zone; measures P(hit), time, path | Registry v4.1.0 |
| H6-OF-ABSORPTION-REVERSAL | New structural extreme; cumulative delta fails to confirm; absorption candidate at/near level (VOLUMETRIC WINDOW ONLY) | Reversal | Registry v4.1.0 |
| TR-H1-W | Causally confirmed W (formationType=W, secondLegConfirmed, not invalidated) with a GREEN\|BLUE vector while exiting (vectorExitsFormation) or break confirmed | Bullish | Library TR-H1, frozen 2026-08-20 |
| TR-H2-M | Mirror: confirmed M with RED\|VIOLET exit vector | Bearish | Library TR-H2, frozen 2026-08-20 |

Frozen for every primary:

- **Primary outcome**: mean *directional* net points at the 60-minute
  horizon (`y_net_60` signed by predicted side), minus base costs.
  Horizon 60m chosen for all eight, now, uniformly. 240m is a
  secondary descriptive horizon, never a substitute.
- **Baseline execution representation**: the hypothesis's registered
  architecture and stop family (H1/H3/H6: TIGHT; H2/H5: STRUCTURAL;
  H4/TR-H1/TR-H2: MEDIUM); management: registered family. This is a
  measurement vehicle, not an optimization target.
- **Expected relationship**: directional net > matched control and > 0
  net of base costs, in DEV and again in VAL.
- **Null / failure**: directional net ≤ 0 at base costs, or failure to
  replicate sign in VAL, or indistinguishable from its matched Class B
  ablation. A failed primary is reported, never rewritten.
- **Multiplicity**: Benjamini–Hochberg FDR q = 0.05 across the eight
  primaries (one-sided in the predicted direction). Day-block
  bootstrap CIs; clustering by thesisId.

**Mandatory matched comparisons for TR-H1/TR-H2** (frozen): W/M only;
W/M + vector anywhere; W/M + exit vector (the primary); primary +
EMA50-side confirmation — each vs matched CONTROL rows.

Not implemented / excluded, on the record: **VEC-H1** (no 1m vector
emission in the capture — NOT IMPLEMENTED, candidate for a future
event-window run); **TR-FIRSTVECTOR / TR-H14** (no verified public
mechanics; engine emits nothing for the family); **TR-PSY-H1**
(back-adjusted series fails price-integrity gate); **TR-PIVOT-H1**
(formula unverified; family not emitted). ADR/AWR and EMA-fan remain
context/ablation layers (Class B), not primaries.

## 2. Class B / C / D (unchanged from registry)

- B1 structure-vs-vector, B2 structure-vs-orderflow (OF window only),
  B3 structure-vs-level, B4 EMA-fan-addition — required around any
  Class A that shows credible information; also run for failed
  primaries as diagnostics.
- C1 ARCH-A/B/C comparison on identical parents. Signal-decay proxy:
  outcomes conditioned on `f_minsToEntry` bins {1–2, 3–5, 6–15, 16–60}
  — frozen now.
- D1 EMA9-vs-fixed-R on identical entries. Class C/D are
  decision-relevant only after a parent Class A survives.

## 3. Splits — frozen now, by calendar day (ET exchange day)

**Structure layer** (H1–H5, TR-H1/H2, B1/B3/B4, C1, D1):

| Split | Range | Role |
|---|---|---|
| DEV | 2019-07-01 → 2022-12-31 | discovery + confirmatory first look |
| VAL | 2023-01-01 → 2024-06-30 | replication; limited justified refinement |
| OOS | 2024-07-01 → 2025-09-30 | untouched until candidates frozen post-VAL |
| LOCKBOX | 2025-10-01 → 2026-08-19 | untouched until a full candidate is frozen |

**Order-flow layer** (H6, B2) — its data exists only inside
2025-11-02 → 2026-08-19, which overlaps the structure LOCKBOX. Frozen
resolution: OF-DEV 2025-11-02→2026-02-28, OF-VAL 2026-03-01→2026-05-31,
OF-OOS 2026-06-01→2026-08-19. Running H6/B2 there burns those rows for
structure-layer lockbox purposes; accepted and logged. H6's evidential
ceiling is correspondingly lower (~206 sessions total) and will be
reported as such.

Warm-up: rows are excluded per-row by `f_ema800Ready_15m` /
`f_hasEmaFan` (not by date). isWarmup rows excluded always.

## 4. Cost model — provisional, frozen; NET ranking pending user confirmation

Per contract, round turn, MNQ = $2/pt:

| Scenario | Commission | Slippage | Total (pts RT) |
|---|---|---|---|
| Gross | 0 | 0 | 0.00 |
| Commission-only | $0.74 RT | 0 | 0.37 |
| Base | $0.74 RT | 1 tick/side | 0.87 |
| Stressed | $0.74 RT | 2 ticks/side | 1.37 |

All four reported for every result. Promotion requires surviving Base
and being examined under Stressed. The user has not yet confirmed
actual costs — until then NET rankings are provisional by rule.

## 5. Controls — frozen

1. **Within-day shuffle permutation null** on directional outcomes
   (the V5 control that exposed the +16.6pt noise floor), ≥200 perms.
2. **Matched CONTROL rows** (engine-emitted placebo rows, no
   qualifying event) compared under identical measurement.
3. **Ablations** (Class B) for any surviving primary.
4. **Symmetry**: long and short measured separately; divergence is
   reported, not auto-rejected.
5. **Stability**: per-year table for every primary; rolling 6-month
   for survivors.
6. **Decay**: minsToEntry-bin conditioning (frozen above).
7. **Outlier dependence**: drop-top-1/top-3/top-5% for survivors.
8. **AMBIGUOUS races**: carried as bounds (both resolutions reported)
   wherever races enter a result.

## 6. Selection discipline

All eight primaries are reported with their failures. No direction,
horizon, metric, or membership change after outcomes are seen — a
changed idea becomes a NEW exploratory hypothesis requiring untouched
data. Exploratory discovery happens on DEV only, is labelled
EXPLORATORY — NOT YET CONFIRMED, is counted in the ledger, and
promotes only through frozen-rule → VAL → OOS.

## 7. Research ledger (opening state)

Prior programme history counted against multiplicity: V4 (8 hypotheses,
0 survived, Decision D), V5 (10 hypotheses, 0 survived, Decision D;
conjunction search: 8,329 conjunctions, best +20.6pt vs shuffled-null
best +26.1pt, retention −5.3%), V4.1 engine iterations (17 defects
fixed, no outcome analysis). This document opens the V4.1 outcome
ledger at zero tests run.
