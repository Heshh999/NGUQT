# NVQ-V1 — FINDINGS

**Verdict: 1 of 16 cells survives BH — D_STREAK3_DN, next-day reversal
after exactly three consecutive down days. It passes every destruction
its sample size permits, is positive in all 8 years, and is frozen
prospectively. It cannot be a full-gate candidate on this sample
(n = 84 < 200 floor) and is registered exploratory.**

Freeze commit `7c4cad4` (before outcomes). DEV 2019-07-04→2026-08-17
(exposed; exploratory ceiling). Seeds per protocol.
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

## 1. The dead cells (15 of 16)

- **Volume-clock sampling (all 6 cells): null.** First-ever event-time
  test here: AC(1), AC(2) and VR(6) at 5m- and 15m-equivalent volume
  bars all include zero/one. Re-measuring NQ on a volume clock does not
  reveal structure the time clock hid. Class `VOLUME_CLOCK_STRUCTURE`
  spent.
- **Day-type taxonomy mostly null:** NR7, WR7, inside, outside,
  trend-up, inside∧NR7, streak-3-up, streak-4+ — none survives.
  Notably: up-streaks do NOT reverse (−6.6 bp reversal = mild
  continuation). TREND_DN (+31.9 bp, q 0.067) just misses and agrees
  in direction with the survivor.

## 2. The survivor — D_STREAK3_DN

**Signal:** RTH close marks the third consecutive down close, with the
day before the streak up or flat (exactly 3). n = **84** over 7.1 years
(~12/year). **Outcome:** next-day close-to-close **+44.8 bp**
(CI [+21.1, +68.6], p 0.00022, **BH q 0.0035**) ≈ +84 pts at current
prices, versus +5.7 bp unconditional and +12.8 bp after any single down
day — monotone in streak depth, 8× drift.

Destruction battery:
- **Positive in all 8 calendar years** (2019 +63 → 2026 +126 bp);
  second half (+55) *stronger* than first (+35) — no decay.
- Drop best day +40.8; drop best 3 +33.8; median +32.6; win 63%.
- Positive in both volatility halves (+58 high, +31 low).
- Decomposition: overnight **+30.7*** + next-day RTH **+14.1*** — both
  legs independently significant; not a gap artifact, not an RTH
  artifact.
- Asymmetry is mechanistically coherent (documented index-futures
  short-horizon reversion: panic selling reverts; buying doesn't).

**Frozen translation** (pre-declared: next-session open → close, RTH
only, no overnight): base **+23.3 pt/trade PF 1.335**, stressed
**+22.8 pt PF 1.328** — passes the PF floors. Informational only, since
the anomaly's larger half lives in the overnight gap: close-to-close at
the 1.740 pt overnight cost would have been +86.6 pt/trade, PF 2.63,
win 63%. That variant was *not* pre-frozen and is **not** promotable
from this run.

**Why it is not a candidate:** G01 requires ≥200 effective events;
84 exists. ~12 signals/year means the floor cannot be met on this
history. Multiplicity candor: q = 0.0035 within this 16-cell family;
programme-wide ~700 tests — the strongest independent support is the
8/8 year sign consistency (≈ p 0.004 on its own) and the absence of
decay.

## 3. Disposition

- 15 dead/null cells → registry (`VOLUME_CLOCK_STRUCTURE` spent;
  `DAY_TYPE_TAXONOMY` cells dead).
- **D_STREAK3_DN → `PASSED_HISTORICAL_EXPLORATORY`**, protected class
  `DAY_TYPE_TAXONOMY` — derivative mining prohibited while its
  prospective arm runs.
- **Prospective freeze:** `NVQ_V1_PROSPECTIVE_FREEZE.md` — the
  close-to-close object is frozen for forward scoring on VALIDATION
  data (2026-09-01+), alongside OFH13/OFH14. No VALIDATION outcome was
  opened; the freeze precedes the data. `docs/PROSPECTIVE_REGISTRY.md`
  is hash-protected (MLES audit) and is deliberately NOT modified; this
  freeze stands alone.
