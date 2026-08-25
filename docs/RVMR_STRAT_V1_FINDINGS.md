# RVMR-STRAT-V1 — FINDINGS

Pre-registered before results (`docs/RVMR_STRAT_PREREGISTRATION.md`).
**First gate — RVMR PARITY: PASS** (593,190 rows, 0 range, 0 volume, 0
timestamp mismatches, exact float equality). Nothing frozen was
modified. All results are EXPLORATORY-DERIVED on spent history.

## **HEADLINE**

> **RVMR REMAINS A STRONG MOVEMENT-REGIME TOOL BUT DOES NOT CURRENTLY
> IMPROVE STRATEGY SELECTION OR SETUP QUALITY.**

Track A: 16 populated interaction cells across ten unchanged canonical
strategies — **best BH q = 0.593, nothing survives**, signs scatter,
and the strongest raw cell shrinks under volatility/clock controls.
Track B: 8 pre-registered RVMR-native strategies — **none passes the
promotion gate**; the only q < 0.05 cell is *significantly losing*, and
one cell is void by my own specification error, disclosed below.

---

# TRACK A — existing strategies × RVMR (all unchanged)

Harvest (canonical implementations, hashes in the pre-registration):
OFH13 133 · OFH14 462 · sweep-reclaim 589 · accepted-brk 1,876 ·
rejected-brk 2,018 · V-recovery 995 · mean-rev 445 · open-drive 231 ·
overnight-reclaim 187 · G4 218.

## Final Track A table (EV points per event; n in parentheses)

| strategy | RANGE L / M / H | VOLUME L / M / H | best state | MFE/MAE | ff | tail preserved? | verdict |
|---|---|---|---|---|---|---|---|
| OFH13 | +6.5(12) / +13.9(67) / **+23.6(53)** | −16.5(1) / +3.7(18) / +19.5(113) | R-HIGH | 0.74→1.83 improves | 22→49% improves | **NO — 4/10 top winners, 46% winner P&L** | **RVMR CONTEXT ONLY** |
| OFH14 | −2.1(114) / −0.8(229) / **+11.3(116)** | −2.1 / −1.2 / +4.0 | R-HIGH | improves | improves | partial | **RVMR NONLINEAR INTERACTION** (p 0.037 raw, q 0.593 — not established) |
| sweep-reclaim | −2.1 / +4.7 / +2.6 | +3.4 / +1.7 / +2.2 | non-mono | flat | flat | — | NO RVMR INTERACTION |
| accepted-brk | −1.4 / −5.0 / +2.2 | −0.6 / −4.2 / −0.9 | non-mono | flat | flat | — | NO RVMR INTERACTION |
| rejected-brk | −1.3 / −1.9 / +0.4 | +0.4 / −1.2 / −1.5 | non-mono | flat | flat | — | NO RVMR INTERACTION |
| V-recovery | −2.8 / −1.3 / +0.1 | −4.4 / −3.5 / +0.6 | weak mono | flat | flat | — | NO RVMR INTERACTION (q 0.93) |
| mean-rev | +0.4 / −1.0 / **−5.7** | −1.9 / −0.1 / −2.7 | **R-LOW** | declines with HIGH | — | — | weak **RVMR LOW-REGIME BENEFIT** direction (p 0.39 — not established) |
| open-drive | +13.4(10) / +7.6 / +4.6 | −17.9(6) / +57.9(9) / +4.6 | LOW?? n=10 | — | — | — | NO RVMR INTERACTION (tiny LOW cells) |
| ovn-reclaim | +2.9(11) / +11.8 / +10.6 | −42.1(2) / −11.6(9) / +12.1 | MED/HIGH | flat | flat | — | RVMR NO SELECTIVITY (74–94% in M+H) |
| G4 | +11.5(26) / −0.3 / +5.0 | −1.8(8) / +4.0 / +3.4 | non-mono | LOW best M/M | — | — | NO RVMR INTERACTION |

**Family accounting (M=16 populated of 20 declared; at M=20 every q is
larger still): best q = 0.593.** The two seductive gradients (OFH13,
OFH14 on RANGE) fail sample, correction, and — decisively for OFH13 —
**tail preservation**: a trade-only-HIGH filter keeps 4 of the 10
biggest winners and 46% of winner P&L, cutting per-original-parent EV
from +17.26 to +9.39. The right tail *is* OFH13; no filter, no grades.

## OFH13 special analysis (certified states)

**VOLUME: 86% HIGH (113/131) — saturated. RVMR-VOLUME HAS LOW
SELECTIVITY FOR OFH13**, confirming (and sharpening) the earlier 83%
composite claim. **RANGE is not saturated** (9/51/40) and shows the
monotone-looking gradient above — but it is statistically unestablished
and tail-destructive as a filter. OFH13_PROSPECTIVE_V1 is untouched.

## Controls / incremental value

Every promising raw delta shrank inside ATR-tercile and hour strata
(e.g. G4 −6.5 → −2.4; OFH14's +13.4 raw was the only one to hold
magnitude, and it fails correction). **RVMR did not demonstrate
strategy-quality information beyond simple volatility/clock controls
in any Track A cell.**

## Structural geometry (diagnostic)

OFH13: HIGH-state entries sit *closer* to their FVG invalidation
(median 0.67 vs 0.79 ATR) with **P(risk ≤ 0.75 ATR ∧ MFE ≥ 2 ATR) =
35.8% vs 25.0% in LOW** — the "small legitimate risk, large excursion"
cell exists and is RVMR-tilted, but on 53 vs 12 events it is a hint,
not a finding.

---

# TRACK B — RVMR-native strategies (M = 8, five-year data)

2,503,622 bars, 2019-07 → 2026-08. Uniform frozen frame; direction
always from price; cooldown 30m; day-clustered stats.

| cell | n | EV | PF | M/M | p | q | verdict |
|---|---|---|---|---|---|---|---|
| B1 accepted breakout + R-HIGH | 2,905 | −1.16 | 0.93 | 0.98 | 0.24 | 0.95 | NO INCREMENTAL VALUE (control −1.06; delta −0.10) |
| B2 first pullback + R-HIGH | 3,159 | −0.04 | 1.00 | 1.00 | 0.97 | 1.00 | NO EDGE (control −0.48) |
| B3 sweep-reclaim levels + R-HIGH | 1,372 | −0.26 | 0.99 | 0.99 | 0.87 | 1.00 | NO INCREMENTAL VALUE — HIGH *underperforms* its control (+0.52) |
| B4 VWAP reversion + R-LOW | 6,966 | **−1.10** | 0.90 | 0.95 | **0.0051** | **0.041** | **FAILED — significantly NEGATIVE.** q<0.05 flags a losing cell; gate condition 1 kills it |
| B5 LOW→HIGH transition breakout | 3,461 | −0.18 | 0.99 | 0.97 | 0.82 | 1.00 | NO EDGE; ≈ MED→HIGH (−0.97) ≈ HIGH→HIGH (−0.54) |
| B6 HIGH→LOW exhaustion fade | 0 | — | — | — | 1.0 | 1.00 | **VOID — SPECIFICATION ERROR (mine)** |
| B7 opening drive + R-HIGH | 192 | +3.14 | 1.16 | 1.37 | 0.43 | 1.00 | NO INCREMENTAL VALUE — control (+5.43, n=375) beats the HIGH arm |
| B8 accepted gap + R-HIGH | 827 | +0.22 | 1.01 | 1.04 | 0.92 | 1.00 | NO EDGE |

**B6 disclosure:** the exhaustion test required the decision bar's close
to sit outside a 30-bar balance envelope **that included the decision
bar itself** — impossible by construction (the envelope's high ≥ the
bar's own high ≥ its close). B1 lagged its envelope correctly; B6 did
not. Zero events is the structural consequence. **Not re-run with a
corrected definition** — that requires a fresh pre-registration — and
M stays 8.

**Notable diagnostics (uncorrected, not promoted):**
- **B8 rejected-gap fade in R-HIGH: −9.91/trade (n=137, p=0.033)** —
  fading a rejected gap when high movement is available is distinctly
  bad. Directionally consistent with what RVMR measures (movement
  continues), and the closest thing to a *trade-avoidance* signal in
  the study; survives nothing formally.
- **B7's control** — the pure opening-drive continuation — is +5.43
  over 7 years (p=0.061), positive in 7 of 8 years; RVMR conditioning
  only dilutes it. An interesting non-RVMR object for some future
  pre-registration; explicitly not promoted here.
- B7's best state is MEDIUM (+9.40, p=0.041 uncorrected) — the
  non-monotone middle-bucket pattern this programme has repeatedly seen
  and repeatedly watched die; not pursued.

---

# FINAL ANSWERS

1. **Does RVMR improve quality classification of any existing
   strategy? NO** (best q 0.593; nothing passes the ten-condition gate).
2. **Which existing strategy benefits most from HIGH RVMR? NONE**
   established. (OFH14/RANGE is the best *unestablished* candidate,
   p 0.037 raw.)
3. **Which benefits most from LOW RVMR? NONE** established (mean
   reversion points that way, p 0.39).
4. **Does HIGH RVMR produce larger winners? STRATEGY-DEPENDENT** — yes
   for OFH13 (avg winner 107 vs 76) but on tiny LOW cells; no general
   pattern across strategies.
5. **Does HIGH RVMR also produce larger MAE? YES, generally** — losing
   MAE and median adverse excursion rise with state in most cells (the
   five-year symmetry result again).
6. **Does RVMR improve MFE/MAE rather than inflating both?
   STRATEGY-DEPENDENT and unestablished** — OFH13/OFH14 RANGE show
   ratio improvement (0.74→1.83); Track B shows ratios pinned at
   0.93–1.04 everywhere.
7. **Does RVMR predict 2R/3R+ opportunities? NO** — P(2R) moves 27–31%
   across states in Track B; small unstable shifts in Track A.
8. **Evidence for A+/A−/B+ grading? NO.** No strategy met the
   multi-metric monotone bar; grades were not constructed.
9. **HIGH RVMR + small structural risk + large MFE? YES, weakly** —
   OFH13 R-HIGH: 35.8% of events have risk ≤ 0.75 ATR with MFE ≥ 2 ATR
   (vs 25.0% in LOW). n=53; diagnostic only.
10. **LOW→HIGH better than HIGH→HIGH at expansion start? NO** (−0.18 vs
    −0.54, both ≈ 0, p 0.82).
11. **HIGH→LOW identifies exhaustion? INCONCLUSIVE — VOID** (my
    specification error; untested).
12. **Best new RVMR-native strategy? NONE.**
13. **Can RVMR be a strategy selector? NO** on this evidence — no
    strategy showed an established regime preference, so there is
    nothing to select between.
14. **Best current role for RVMR? MOVEMENT CONTEXT ONLY** — with one
    candidate secondary role worth a future pre-registration:
    *trade-avoidance for counter-movement setups* (the B8 rejected-gap
    fade loses 10 pts/trade in HIGH; A7 mean reversion is −5.7 in
    HIGH vs +0.4 in LOW — both uncorrected, same direction).

## Evidence ranking of RVMR applications

1. **Movement prediction** — certified, 70/70 cells (the only proven use)
2. **Loss avoidance for counter-movement trades** — two coherent
   uncorrected signals (B8-HIGH fade, A7-HIGH reversion); next-study
   candidate
3. Structural-risk geometry — one weak OFH13 diagnostic
4. Winner-size prediction — OFH13 only, unestablished
5. Transition detection — nothing (B5 flat, B6 void)
6. Strategy selection — nothing
7. Setup grading — nothing
8. Runner/target context — nothing (P(2R+) flat)

No survivor exists, so no freeze specs are written and no management
research is authorized. RVMR-C1 remains unauthorized.
**OFH13_PROSPECTIVE_V1 and all frozen infrastructure untouched.
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
