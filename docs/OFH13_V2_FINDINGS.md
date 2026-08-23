# OFH13-V2 IMPROVEMENT RESEARCH — RESULTS

Canonical reproduction PASS (133 events, 48W/85L, every baseline figure
matched before research began). OFH13_PROSPECTIVE_V1 untouched. All
work on already-spent history; every observation below is
EXPLORATORY-DERIVED. Research ledger: ~25 distinct tests (12 feature
tercile scans × monotonicity, 2 partition-stability checks, 3
long/short matched splits, 3 early-exit rules, 4 stop variants, winner
development + time-to-progress) — treated as one exploratory sweep, not
25 independent hypotheses.

**HEADLINE: OFH13_PROSPECTIVE_V1 REMAINS THE BEST SPECIFICATION.
Every proposed improvement was destroyed by its own gate.**

## Study 1–2: winner/loser causal features (48 vs 85)

Twelve entry-time features scanned (FVG width/ATR, mitigation depth,
distance-to-invalidation, signal→entry minutes, extension past signal,
extension past FVG mid, entry-bar range, VWAP distance, 3m/15m swing
distance, hour, ATR). Median differences are small; only two features
showed tercile monotonicity on the pooled sample:

| feature | LOW | MID | HIGH | reading |
|---|---|---|---|---|
| **ext_mid** (ATR paid beyond FVG mid) | **+0.88R / PF 2.60** | +0.27R | +0.09R / PF 1.22 | cheaper entries better |
| **inv** (ATR to invalidation) | **+0.72R / PF 2.22** | +0.37R | +0.15R / PF 1.36 | closer invalidation better |

Both are the same mechanism (price paid relative to the zone) — and
**both REVERSE on IR**:

```
ext_mid  U: LOW +1.86 … HIGH −0.49     DEV: LOW +1.33 … HIGH −0.19
         IR: LOW +0.21   MID −0.14   HIGH +0.53   ← inverted
inv      IR: LOW −0.09 … HIGH +0.39                ← inverted
```

**Verdict: FRAGILE / THRESHOLD DEPENDENT (partition-unstable).** No
causal entry feature separates losers stably. (Reclaim speed could not
even be tested — the canonical trigger fires on the attack bar 99% of
the time, so speed has no variance; documented in V4.2-B.)

## Study 3/4/6: extension, FVG quality, geometry

Extension past the *signal* is non-monotone; extension past the *mid*
is the IR-unstable feature above. FVG width, age, depth: no stable
relationship (depth's best bin is MIDDLE — not monotone). Entry
geometry: profitable events *were* concentrated near invalidation on
U/DEV — and not on IR. Nothing usable.

## Study 7: long vs short

| | n | WR | PF | meanR | ext_mid | inv | fvgW | MAE |
|---|---|---|---|---|---|---|---|---|
| LONG | 55 | 32.7% | 1.33 | +0.13 | 0.36 | 0.77 | 0.63 | 33.8 |
| SHORT | 78 | 38.5% | 2.15 | +0.60 | 0.34 | 0.64 | 0.62 | 32.8 |

Feature medians are nearly identical — **the short advantage is not
explained by any measured entry condition**, and inside ext_mid bins it
flips sign at HIGH (short −0.18 vs long +0.39). Most plausible reading:
a 12-month directional-regime effect, not a structural one.
**Verdict: DIRECTION-SPECIFIC EFFECT — NEEDS VALIDATION. Longs stay.**

## Studies 8–9: winner development (the informative result)

Medians in R (of the 1.5 ATR stop):

| t | winners ur / MFE / MAE | losers ur / MFE / MAE |
|---|---|---|
| 3m | +0.32 / 0.62 / 0.35 | −0.29 / 0.36 / 0.62 |
| 5m | +0.71 / 0.97 / 0.35 | −0.35 / 0.39 / 0.91 |
| 10m | +1.10 / 1.65 / 0.40 | −0.30 / 0.62 / 1.20 |
| 60m | +2.36 / 3.48 / 0.51 | −0.45 / 1.37 / 2.36 |

**Winners announce themselves immediately** — median winner is +0.71R
in five minutes and its *final* median MAE is only 0.51R. **But the
converse fails: 76/85 losers ALSO reach +0.25R (median 2 m) and 66/85
reach +0.5R.** Early favourable progress is nearly universal; what
separates the populations is early ADVERSE depth — and cutting on that
is just a tighter stop (tested below). 59% of losers even touch +1R
before dying, which is why profit-taking pressure exists and why the
registry rejected targets.

## Study 10: early-failure exits — vacuous, not wrong

| rule | fires | Δexp | verdict |
|---|---|---|---|
| no +0.25R by 10m → exit | **2/133** | +0.33 | NO INCREMENTAL VALUE |
| no +0.25R by 15m → exit | 1/133 | +0.03 | NO INCREMENTAL VALUE |
| no +0.5R by 20m → exit | 1/133 | +0.08 | NO INCREMENTAL VALUE |

The rules barely ever trigger because almost every trade shows early
progress. Nothing to gain, nothing destroyed. Answer to Q4: winners DO
announce early — but a defensive exit built on that announcement is
empty, because losers announce too.

## Study 11: stop family — the frozen stop wins outright

Full replay, per-parent, all 133:

| stop | exp | PF | WR | maxDD | top-10 kept | winner P&L lost |
|---|---|---|---|---|---|---|
| **1.5 ATR (frozen)** | **+17.26** | **1.80** | 36.1% | **333** | 10/10 | 0 |
| 1.25 ATR | +13.62 | 1.65 | 29.3% | 439 | 10/10 | 920 |
| 1.0 ATR | +12.29 | 1.67 | 24.1% | 348 | 9/10 | 1,556 |
| FVG-invalidation (STRUCT) | +10.83 | 1.80 | 20.3% | 444 | **6/10** | 2,253 |

Tighter risk is uniformly worse — expectancy down 21–37%, drawdown UP
(more stop-outs cluster), and the structural stop deletes four of the
ten biggest winners. The reason is in Study 8: winners routinely draw
down ~0.5R (≈0.76 ATR) before working, so anything tighter than ~1.5
ATR clips winners. **Verdict: TOO MANY LARGE WINNERS REMOVED (all
tighter variants).** The frozen stop sits on the plateau.

## Studies 12–14

- **5s/15s overlay: INSUFFICIENT DATA** — no genuine LTF history; the
  capture host is delivered and waiting (LTF-EXEC-BACKTEST-V1). At 30s,
  measured twice: no improvement.
- **Quality score / A+A−B+ grading: UNSUPPORTED.** The score requires
  3–5 dimensions with monotone, partition-stable behaviour; zero
  dimensions survived the IR check, so no score was constructed and no
  grades exist. Answer to Q5: NO.

## Studies 15–16: tail preservation / filter efficiency

Applied to every proposal above (columns in the tables). The pattern is
absolute: every change that "improved" anything did it by taxing the
right tail, and the right tail IS the strategy (top 10 trades ≈ 100% of
net P&L). Filter efficiency was < 1 for every filter candidate implied
by the U/DEV features once IR was included.

## Final answers

1. **CAN HISTORICAL EXPECTANCY BE IMPROVED WITHOUT DESTROYING THE
   TAIL? NO** — on this history, nothing beat the baseline robustly.
2. **BIGGEST IMPROVEMENT OPPORTUNITY: NO CLEAR IMPROVEMENT.** (The
   only untested door left is execution capture — 5s/15s — and the 30s
   evidence says expect nothing.)
3. **CAN LOSERS BE IDENTIFIED CAUSALLY PRE-ENTRY? NO** — the two
   monotone candidates invert on IR.
4. **DO WINNERS ANNOUNCE EARLY ENOUGH FOR A DEFENSIVE EXIT? NO** —
   they announce, but so do losers; the exit rules fire on 1–2% of
   trades.
5. **DOES A+/A−/B+ HAVE A MONOTONIC BASIS? NO.**
6. **BEST PROPOSED OFH13-V2: NONE.**

## **OFH13_PROSPECTIVE_V1 REMAINS THE BEST SPECIFICATION.**

That is the result. The baseline's numbers (36.1% WR, PF 1.80, +0.41R,
3.18:1 realized, 33 pt median stop, 333 pt maxDD, shorts > longs) stand
unimproved by 25 destruction attempts. The honest interpretation of
this phase: the strategy's edge — if it survives forward — lives in the
event selection already frozen, not in any refinement this exhausted
history can reveal. The forward ledger is the only instrument that can
say more.
