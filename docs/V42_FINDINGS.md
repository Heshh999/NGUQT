# V4.2 FVG + ORDER-FLOW FAILURE FAMILY — RESULTS

Pre-registered in `docs/V42_PREREGISTRATION.md` (committed before any
outcome). M = 10, nothing added after results. Canonical reproduction
gate passed first (952 / 133 / 462 / 218 / 477 / 845). Mirror walker
verified against canonical `_mitigate` on all 38,767 FVGs: 0 mismatches.
Frozen shelf untouched; no prospective OFH13 data used.

**Headline: 9 of 10 fail. One raw-gate survivor — G4-FVG — with strong
but small-sample evidence (n = 27), frozen as an exploratory candidate.
Nothing is promoted to the prospective shelf.**

## 1–3. Source, data, reproduction audits

Canonical sources read and reused directly (`build_fvg`, `_mitigate`
semantics, Q_BD75 = 511, entry gate, G4 events from `cand_spec.generate`).
Data: as RED audit; additionally genuine 30s OHLCV for 2025-09→2026-05,
192 days, ~09:30–11:00 ET only, **no 30s bid/ask** — nothing fabricated.
E2 failure cut 15.961 reused from the RED freeze, not refit.

## 4–13. Exact definitions

As pre-registered, unchanged. Shared: canonical displacement-FVGs;
mitigation walk = far-side close invalidates, touch = wick into zone,
trigger = completed close beyond midpoint; aggression = opposing
|delta| ≥ 511 during mitigation; failure = E2 ≥ 15.961 on the first
aggression bar; FVG life formation+30 (observation studies +120); entry
gate RTH/≥60-to-close/ATR; 30-min cooldown; costs 0.87 pt.

## 14. Causality audit

All levels/FVGs/swings carry known-time indices; episodes and walks are
strictly forward; outcomes need complete consecutive windows; the
walker's fidelity to canonical `_mitigate` was asserted, not assumed.

## 15–23. Results (60 m horizon; MFE/MAE in ATR medians; ff at ±1 ATR)

| study | n | mean | med | MFE/MAE | ff | ctl ΔR | ctl Δff | U→DEV→IR mean |
|---|---|---|---|---|---|---|---|---|
| FVG-F1 FULL | 115 | +2.46 | +12.63 | 1.35 | 47.8% | +0.36 | −0.7 | +35 / −6.8 / −4.2 |
| FVG-F2 ep1 | 114 | +1.62 | +12.63 | 1.30 | 48.2% | +0.15 | −3.6 | +34 / −2.0 / −8.5 |
| FVG-F3 | 77 | +3.02 | +12.63 | 1.35 | 44.2% | +0.47 | −5.1 | +48 / −20 / −4.7 |
| FVG-F4 | 67 | +3.07 | +2.63 | 1.26 | 46.3% | +0.27 | −4.6 | −1.8 / +21.6 / −8.4 |
| **G4-FVG** | **27** | **+64.12** | **+46.13** | **3.21** | 51.9% | **+2.37** | **+7.1** | **+153 / +117 / +23** |
| G4-SWEEP | 109 | +16.13 | +18.38 | 1.33 | 44.4% | +0.27 | −5.9 | +37 / +0.8 / +18 |
| FVG-WEAK-PB | 1695 | −4.08 | −0.62 | 0.98 | 49.7% | +0.00 | −0.6 | +0.6 / +4.1 / −14.3 |
| FVG-ER | study | — | — | non-monotonic | — | — | — | — |
| FVG-DISCOUNT | exec | — | — | — | — | — | — | — |
| OFH13-30S | exec | — | — | — | — | — | — | — |

Long/short: F4 is +27.3 long / −20.5 short (unstable); F1/F2/F3 carry a
long-side mean with sub-50% long ordering; G4-FVG is positive both sides
(+64.8 long n11 / +63.7 short n16). WEAK-PB fails everywhere.

Tail concentration: **F1's entire +283 total is one +300 trade
(top-1-trade = 106% of total P&L); F2 162%, F3 122%, F4 116%.** These
four are single-trade artifacts at the mean level; their positive
medians with ~48% ordering are magnitude-without-direction again.
G4-FVG is the exception: top trade 32.8%, top-5% 32.8%, maxDD 353 pt
against +1731 total.

## 24. Effort/result analysis (FVG-ER)

DEV-frozen terciles of the E2 score on F1-B events: LOW R 1.41 →
MED 0.98 → HIGH 1.29. **U-shaped, not monotonic — fails the
pre-declared test.** Raw |delta| bucketing is also non-monotonic
(MED best). Effort-vs-result is NOT the information carrier here, and
neither is raw aggression size.

## 25–26. Concentration & costs

See above. All candidates are cost-insensitive at ±2 ticks relative to
their effect sizes; G4-FVG: +64.12 / +63.87 / +63.62.

## 27. Statistics (sign-flip-by-day; day-clustered CI; BH across the 7 primary rules)

| study | p | 95% CI | BH q |
|---|---|---|---|
| FVG-F1 | 0.368 | [−17.4, +23.9] | 0.472 |
| FVG-F2 | 0.405 | [−18.9, +22.7] | 0.472 |
| FVG-F3 | 0.393 | [−20.3, +26.1] | 0.472 |
| FVG-F4 | 0.385 | [−21.1, +26.2] | 0.472 |
| **G4-FVG** | **0.014** | **[+8.8, +124.8]** | **0.098** |
| G4-SWEEP | 0.068 | [−4.8, +39.5] | 0.238 |
| FVG-WEAK-PB | 0.928 | [−8.4, +0.1] | 0.928 |

Only G4-FVG's CI excludes zero. Its BH q of 0.098 does **not** clear
0.05 at family accounting — stated plainly.

## 28. Survivor management (G4-FVG only; n = 27 — read with that caveat)

Every cell of the small mechanical family is positive with a broad
plateau and no isolated maximum:

| stop \ exit | 15 m | 30 m | 60 m |
|---|---|---|---|
| STRUCT (attack extreme) | +28.9 | +41.7 | +56.6 |
| 1.0 ATR | +22.7 | +37.2 | +52.6 |
| 1.5 ATR | +23.3 | +38.5 | +53.7 |
| 2.0 ATR | +29.1 | +44.4 | +58.2 |
| none | +28.3 | +46.3 | +64.1 |

Stops cost little because the finding IS the low MAE (median 1.49 ATR
vs ~2.9 for control).

## 29. Ranking (pre-declared criteria)

1. **G4-FVG** — only study passing the raw gate on every axis: control
   ΔR +2.37, Δff +7.1 pp, MAE 1.49 vs 2.9, median +46, all partitions
   positive, both directions positive, low concentration.
2. G4-SWEEP — real mean, but ordering −5.9 pp vs control and U-partition
   R 0.94: fails the gate.
3. FVG-F1 / F2 / F3 (jointly) — R ≈ 1.3 but ~48% ordering, means carried
   by one trade, U→IR decay.
4. FVG-F4 — direction-unstable.
5. FVG-ER — non-monotonic; mechanism refuted as tested.
6. FVG-WEAK-PB — dead flat, negative IR.

## 30. The ten special comparisons

- **A (F1 vs OFH13):** Removing OFH6 does NOT preserve OFH13's
  behaviour. F1-FULL: median positive but ordering 47.8%, mean = one
  trade, DEV/IR means negative. The OFH6 context is doing real work in
  OFH13.
- **B (freshness):** ep1 R 1.30, ep2 0.93, ep3+ 1.48 — **non-monotonic;
  freshness is not confirmed** (the pre-declared preference).
- **C (sweep incremental):** F3 ≈ F1 with fewer events and *worse*
  ordering (44.2%). The sweep adds nothing at the FVG.
- **D (iFVG vs FVG):** F4 similar magnitude profile, worse stability,
  long/short split. No advantage over ordinary FVGs.
- **E (does FVG fix G4?):** **Yes, on this history** — the FVG split
  inside canonical G4 is dramatic: at-FVG R 3.21 / MAE 1.49 / +64.1 vs
  not-at-FVG R 0.99 / +6.5. This is the family's one positive answer.
- **F (does sweep fix G4?):** Partially (R 1.33) but ordering worsens;
  inferior to the FVG split on every gate axis.
- **G (continuation vs reversal):** Continuation (WEAK-PB) fails
  outright; weak pullbacks did *worse* than strong ones. The
  failure/reversal frame survives, the continuation frame does not.
- **H (is effort/result the carrier?):** No — non-monotonic buckets;
  raw delta no better. The carrier among tested pieces is the *presence*
  of opposing aggression at a location (the flow flag), not its
  effort/result magnitude.
- **I (location-preserving discount):** 0.25 ATR: fill 80%, per-parent
  +4.04 vs +2.44 — direction right but inside noise (parent CI spans
  zero); 0.50 ATR: fill 64%, per-parent **−4.28** — harmful. No reliable
  improvement claim.
- **J (30s execution):** 57/133 parents in genuine 30s coverage; the 30s
  trigger always fired and always earlier, median entry price **1.50 pt
  worse**, per-parent EV +20.77 vs +19.87 — a wash. No geometric
  improvement; earlier ≠ better, confirmed empirically.

## 31. Freeze spec — survivor

**G4FVG_EXPLORATORY_V1** (frozen at commit; EXPLORATORY-DERIVED, NOT
validated, NOT promoted to the prospective shelf, NOT for Sim/live):

- Parent: canonical G4 event, rule byte-identical to `cand_spec`.
- Qualifier: at the G4 entry bar, a live same-direction canonical
  displacement-FVG exists — formed within the prior 120 minutes, no
  far-side close since formation — and the entry bar touches its zone.
- Scoring: entry at G4 entry close (canonical D4), no target, 60 m time
  exit, no stop (consistent with G4's signal-only registry status);
  stop plateau documented above.
- Frequency ≈ 2/month. Expected wait for n=20 forward events ≈ 10
  months. Verdict caveats: n=27, U partition holds only 2 events,
  IR mean (+23) is a third of DEV's, ordering only 51.9%, and BH q
  0.098 fails the 0.05 line. The MAE reduction is the substantive
  finding.
- Validation path: prospective only, alongside (never inside) the OFH13
  stream.

## 32. Final verdicts

| study | verdict |
|---|---|
| FVG-F1 | NO INCREMENTAL VALUE (single-trade mean; ordering < control) |
| FVG-F2 | INTERESTING BUT INCONCLUSIVE (non-monotonic freshness) |
| FVG-F3 | NO INCREMENTAL VALUE (sweep adds nothing) |
| FVG-F4 | INTERESTING BUT INCONCLUSIVE (direction-unstable) |
| **G4-FVG** | **PROMISING EXPLORATORY CANDIDATE** |
| G4-SWEEP | DIRECTIONAL DRIFT ONLY |
| FVG-WEAK-PB | POOR ENTRY GEOMETRY |
| FVG-ER | NO INCREMENTAL VALUE (mechanism refuted as tested) |
| FVG-DISCOUNT | EXECUTION IMPROVEMENT ONLY — and not reliably that |
| OFH13-30S | NO INCREMENTAL VALUE (honest wash on 57 parents) |

### DID THIS FAMILY IDENTIFY A REPEATABLE FVG + ORDER-FLOW-FAILURE ENTRY-LOCATION ADVANTAGE BEYOND OFH13?

**INCONCLUSIVE — one candidate, not a confirmed advantage.** G4-FVG is
the only study that passed every pre-declared gate, with a CI excluding
zero and genuinely different geometry (MAE halved), but on 27 events,
q = 0.098, and exploratory-derived data. Everything else failed, mostly
reproducing the programme's recurring signature: magnitude asymmetry
with coin-flip ordering.

### WHICH MECHANISM CARRIES THE MOST INFORMATION?

**G4 FAILURE — conditional on FVG LOCATION (combination; the components
are separable and individually weak).** FVG location alone: F1-A is flat.
G4 failure alone: R 0.99 away from FVGs. Effort/result magnitude:
refuted. Freshness: not confirmed. Sweep: nothing. Weak pullback:
inverted. The one strong cell is canonical G4 attack-failure occurring
*at* an FVG — and with n = 27 the honest label is COMBINATION /
CANNOT fully ISOLATE.
