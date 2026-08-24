# MAG-AUC-V1 — FINDINGS

Pre-registered at `c9c4bfe` **before any outcome existed**. Canonical
reproduction PASS on all seven counts. M = 15, never shrunk. Every
result below is **EXPLORATORY-DERIVED** — already-spent history.
OFH13_PROSPECTIVE_V1 and all frozen artefacts untouched.

## **HEADLINE**

> **ORDER FLOW APPEARS MORE USEFUL AS A MAGNITUDE / REGIME FEATURE THAN
> AS A DIRECTIONAL SIGNAL.**

MAG-H3 is the only cell that survives family correction (q = 0.0008).
All eleven directional cells fail. But the magnitude result carries a
sting the pre-registration was built to expose: **the order-flow
composite is beaten by plain volume and plain bar range.**

---

# 1. Source audit

Canonical implementations read directly: `cand_spec` (OFH6/OFH13/OFH14/
G1/G3/G4, ATR, bar delta, cumulative delta, volume, bid/ask volume,
developing profile POC/VAH/VAL, imbalance and stacked counts),
`red_lib` (3m/15m swings, FVG, prior-day levels, MFE/MAE, favourable-
first, forward labels), `prospective` (frozen registry).

**Audit finding that changed the design:** `ofMinDelta` / `ofMaxDelta`
are **session-running cumulative-delta extremes, not intrabar
excursion** — verified constant across consecutive bars. A per-bar
"delta range" **does not exist** in this data. It was dropped from
MAG_SCORE rather than fabricated.

# 2. Data audit

| item | class |
|---|---|
| 1m OHLCV; bid/ask volume; bar delta; delta %; cumulative delta; total volume; volume per tick; imbalance & stacked counts; ATR; developing POC/VAH/VAL | **AVAILABLE** (100% coverage, 355,455 bars, 315 days) |
| rolling delta (`dsum15` 98.9%); causal balance/range; overnight high/low/midpoint; RTH opening range; 3m/15m structure; prior-day H/L | **CAUSALLY DERIVABLE** |
| VWAP, overnight VWAP | **PROXY ONLY** — no tick VWAP; typical-price×volume accumulation, labelled as proxy wherever used |
| **per-bar delta range** | **NOT AVAILABLE** — see above |
| 30s | **AVAILABLE (partial)** — 192 days ph2 + 70 days capture |
| 15s / 5s | **AVAILABLE (partial)** — 70 days, 2026-06-02 → 2026-08-21 |

# 3. Canonical reproduction — PASS

355,455 bars · 952 OFH6 · 133 OFH13 · 462 OFH14 · 218 G4 · 477 G3 ·
845 G1. All seven exact.

# 4. Exact MAG_SCORE

```
a = |ofBarDelta|                             / trailingMean(·,1440)
b = ofTotalVolume                            / trailingMean(·,1440)
c = (buyImbalance_3x + sellImbalance_3x)     / trailingMean(·,1440)
MAG_SCORE = (a + b + c) / 3
```
Trailing window excludes the current bar. Imbalance counts summed so
sign cancels. **Bar range deliberately excluded** (it would make MAG-H3
a volatility-persistence tautology). Buckets are **U-partition
terciles applied unchanged to DEV/IR**: LOW < 1.270, HIGH > 2.335.

# 5. MAG-H3 — the one survivor

Median future movement, 83,596 eligible bars:

| bucket | n | \|ret\| 5m | 10m | 15m | 30m | 60m |
|---|---|---|---|---|---|---|
| LOW | 29,115 | 10.0 | 13.8 | 16.8 | 23.2 | 32.8 |
| MEDIUM | 28,393 | 13.2 | 18.5 | 22.2 | 30.8 | 43.5 |
| HIGH | 26,088 | 18.0 | 24.8 | 30.0 | **40.8** | **56.0** |

**Monotone LOW < MEDIUM < HIGH at 5 of 5 horizons, and in all three
partitions separately** (U 15.5/20.0/27.5 · DEV 22.8/31.8/41.3 · IR
29.3/38.3/50.0). Same monotonicity in true range and MFE+MAE.

Day-clustered inference (258 days): **Spearman +0.3122, permutation
p = 0.00005**, HIGH−LOW mean |ret|@30m **+23.20** with non-overlapping
CIs (HIGH [54.20, 62.11], LOW [32.42, 37.43]). **BH q = 0.0008** at
M = 15.

### The sting — the pre-registered skeptical benchmark wins

| score | day Spearman | HIGH−LOW |ret|@30m |
|---|---|---|
| **MAG_ALT_RNG** (trailing-normalised bar range) | **+0.3917** | **+33.41** |
| **MAG_ALT_VOL** (volume alone) | +0.3790 | +28.26 |
| MAG_SCORE (order-flow composite) | +0.3122 | +23.20 |

**Plain bar range and plain volume each predict future absolute movement
BETTER than the order-flow composite.** The order-flow-specific
ingredients (|delta|, imbalance counts) **dilute** rather than add.
Neither benchmark needs order-flow data at all. This comparison was
pre-registered precisely so the magnitude result could not be reported
as an order-flow win.

**Verdict: PROMISING MAGNITUDE / REGIME FEATURE.**

# 6–7. MAG-DIR-H1 / H2 — magnitude + accepted / rejected breakout

| arm | n | mean | PF | MFE/MAE | ff@1ATR |
|---|---|---|---|---|---|
| C_BREAKOUT_ONLY | 2112 | −2.13 | 0.89 | 0.93 | 47.8% |
| C_ACCEPT_NOMAG | 1765 | −2.23 | 0.89 | 0.93 | 47.9% |
| **FULL_MAG_ACCEPT** | 1511 | **−0.34** | 0.98 | 0.97 | 49.2% |
| C_REENTRY_ANY | 2005 | −1.11 | 0.95 | 0.94 | 50.0% |
| **FULL_MAG_REJECT** | 1630 | **−1.95** | — | — | — |

Magnitude **does** improve an accepted breakout — by +1.89 pts over
`C_ACCEPT_NOMAG` — and the control audit says **MATCHED** (no field
differs >25%), so unlike BRK-H1 this is not a control artifact. **But
both arms lose money**, so gate 2 kills it. This is the BRK-H1 trap
recognised and refused. MFE/MAE ≈ 0.93–0.98 and ff ≈ 47–50%: the
symmetric geometry seen in every directional family to date.

**Verdicts: NO INCREMENTAL VALUE (both).**

# 8. MAG-OFH13-H1 — the informative diagnostic

| bucket | n | mean | WR | PF | MFE | MAE | MFE/MAE | avg winner |
|---|---|---|---|---|---|---|---|---|
| LOW | **4** | +30.74 | 50.0% | 3.51 | 2.46 | 1.87 | 1.32 | 86.00 |
| MEDIUM | 19 | −10.18 | 21.1% | 0.61 | 1.47 | 2.97 | 0.50 | 76.69 |
| HIGH | **110** | +21.51 | 38.2% | 2.02 | 2.70 | 1.80 | **1.50** | **111.72** |

**Not monotone** (LOW n=4 is meaningless). The real finding is the
distribution: **110 of 133 OFH13 events (83%) already occur in HIGH
magnitude states.** OFH13 is *already* a high-magnitude strategy, which
is precisely why a magnitude filter cannot improve it — there is almost
nothing to filter out. HIGH does carry the best MFE/MAE (1.50) and the
biggest average winner (111.72), consistent with OFH13's tail-dependent
economics. **OFH13_PROSPECTIVE_V1 WAS NOT FILTERED OR MODIFIED.**

**Verdict: NO INCREMENTAL VALUE** (the state is already saturated).

# 9–11. Overnight family

**OVN-H2** — extension → reversion. FULL +2.60 (n=125) but median
−22.58, U −2.89 / DEV +5.24 / IR +3.19, and the *control*
(`C_REENTRY_ONLY`, +3.41) beats it. Control audit MATCHED. Gates: 2 of
8. **Verdict: NO INCREMENTAL VALUE.**

**OVN-H3 — VOID, SPECIFICATION ERROR (mine).** The FULL arm produced
**zero events**. Diagnosed, not retuned: of 247 strong-overnight days,
the RTH open cleared the overnight extreme **0 times**; the maximum
(open − extreme)/ATR is **−0.030**, the median **−5.44**. MNQ trades
continuously into 09:30, so the open *is* essentially the last overnight
price and lies inside the overnight range **by construction** — clearing
the extreme would require an opening gap a continuous future does not
produce. The control arm still answers the underlying question:
`C_ONMOVE_ONLY` n=246, mean **+0.38**, U +8.20 / DEV +8.51 / **IR
−12.38** — unstable and economically nil. **Not re-run with a looser
threshold. M stays 15.**

**OVN-H4 — the best cell in the family.**

| arm | n | mean | PF | MFE/MAE | ff@1ATR | U / DEV / IR |
|---|---|---|---|---|---|---|
| C_SWEEP_ONLY | 256 | +5.72 | 1.25 | 1.22 | 53.7% | −9.91 / +14.11 / +5.66 |
| **FULL_SWEEP_RECLAIM** | 187 | **+10.42** | **1.42** | **1.29** | **57.1%** | +4.82 / +20.64 / +2.37 |
| **+ HIGH magnitude** | 172 | **+12.07** | **1.49** | 1.26 | **58.6%** | +5.31 / +22.86 / +4.27 |

**Passes 7 of 8 gates** — positive expectancy, profitable on its own,
sign-stable across all three partitions, matched-control advantage,
credible geometry (MFE/MAE 1.29, the only cell meaningfully above 1),
adequate sample, control audit MATCHED.

**It fails condition 4:** removing the top 5% of 187 trades takes the
mean to **−2.47**. And `p = 0.0894 → BH q = 0.4470` at M=15. And
adding the HIGH-magnitude condition *does* improve it (+10.42 → +12.07,
PF 1.42 → 1.49) — the one place magnitude adds something to a
price-structure setup.

**Verdict: INTERESTING BUT INCONCLUSIVE.** Not promoted. This is the
programme's third independent sighting of the same object — a swept
liquidity extreme that is reclaimed (PRO-OF-H3, MR-H3, now OVN-H4 at
the overnight level). It has never cleared family correction.

# 12–13. Opening family

**OPEN-H1** FULL +4.61 (n=55) — but the control `C_DRIVE_ONLY` (+6.67,
n=229) is **better**, control audit **MISMATCHED on volume**, and n=55
fails the sample gate. Gates: 3 of 8. A striking sub-result:
`C_DRIVE_ORIGIN_RECLAIMED` (n=11) is **−41.46, WR 0.0%, MFE/MAE 0.03,
p=0.0008** — when an opening drive's origin is reclaimed, the day is
over. Tiny n, but the cleanest destruction signal seen.
**Verdict: NO INCREMENTAL VALUE.**

**OPEN-H2** ARM_A_50 −9.08 (n=40), ARM_B_100 +8.81 (n=26). MFE/MAE 0.65
and 0.60 — the worst geometry in the family. **Verdict: POOR ENTRY
GEOMETRY.**

# 14–15. BAL family — the corrected compression

The dimensionally coherent gate **works** where BRK-H2's did not: ratio
spans 0.460–2.434 (median 0.943), and the U-p25 cut at 0.784 produced
1,082–1,209 events. The specification error is fixed; the hypothesis
still fails.

| arm | n | mean | PF | MFE/MAE |
|---|---|---|---|---|
| C_SHOCK_BREAKOUT | 1209 | −3.35 | 0.84 | 0.90 |
| FULL_BAL_ACCEPT | 1082 | −2.20 | 0.89 | 0.90 |
| FULL_BAL_FALSEBREAK | 830 | −0.15 | 0.99 | **1.07** |

The false break has better geometry than the accepted break — the only
directional hint in the family — but it is still not profitable.
**Verdicts: NO INCREMENTAL VALUE (BAL-H1), INTERESTING BUT
INCONCLUSIVE (BAL-H2).**

# 16. RANGE-H1 — persistence CONFIRMED

Mean 1m range per minute in the window *after* the state:

| bucket | n | +3m | +5m | +10m | +15m | +30m |
|---|---|---|---|---|---|---|
| LOW | 29,333 | 11.33 | 11.45 | 11.55 | 11.60 | 11.62 |
| MEDIUM | 28,453 | 15.17 | 15.30 | 15.30 | 15.28 | 15.04 |
| **HIGH** | 26,140 | **20.67** | 20.65 | 20.45 | 20.20 | **19.50** |

HIGH decays only 5.7% from +3m to +30m and the HIGH/LOW ratio stays
≈1.7–1.8× throughout. **The state marks a genuinely persistent
elevated-volatility regime, not one large bar.**
**Verdict: PROMISING MAGNITUDE / REGIME FEATURE.**

# 17. RANGE-H2 — no interaction

| family | LOW | MEDIUM | HIGH |
|---|---|---|---|
| OFH13 | +30.74 (n4) | −10.18 (n19) | +21.51 (n110) |
| ACCEPTED-BREAKOUT | +0.90 | −7.21 | +1.07 |
| REJECTED-BREAKOUT | −1.55 | +0.89 | −2.38 |

**Non-monotone in every family.** The pre-registered expectation — LOW
favours mean reversion, HIGH favours continuation — **does not appear.**
**Verdict: NO INCREMENTAL VALUE.**

# 18. ASYM-H1 — the crispest answer in the family

Identical 2,609 bars, four arms:

| arm | mean | PF | MFE/MAE | U / DEV / IR | p |
|---|---|---|---|---|---|
| **A follow DELTA SIGN** | **−3.44** | 0.83 | 0.85 | −2.02 / −3.41 / −4.24 | **0.0011** |
| B follow PRICE | −1.94 | 0.91 | 0.90 | −0.63 / −1.64 / −2.96 | 0.0844 |
| C price if \|delta\| extreme | −1.94 | 0.91 | 0.90 | same as B | 0.0844 |
| D price UNCONDITIONAL (n2993) | **−1.44** | 0.93 | 0.95 | −1.84 / −2.16 / −0.48 | 0.1885 |

Two clean readings. **Following delta sign is 1.50 pts/trade worse than
following price on the very same bars, and is significantly negative
(p=0.0011), consistently in all three partitions.** And **conditioning
on extreme |delta| makes the price model worse, not better** (C −1.94 vs
D −1.44). **Verdict: NO INCREMENTAL VALUE** — absolute intensity does
not rescue a price-direction model, and delta sign is actively harmful.

# 19. ASYM-H2 — activity × efficiency

| arm | n | mean | PF | MFE/MAE |
|---|---|---|---|---|
| STATE_A HIACT+HIEFF → continuation | 2102 | −1.16 | 0.94 | 0.97 |
| STATE_B HIACT+LOEFF → reversion | 1473 | **−3.94** | 0.83 | 0.88 |
| C_RAW_DELTA_SIGN | 2990 | +0.25 | 1.01 | 1.00 |
| C_PRICE_MOMENTUM | 2993 | −1.44 | 0.93 | 0.95 |

Both hypothesised states lose, and STATE_B (the "rejection" state) loses
**most**. Control audit **MISMATCHED on volume and range** — STATE_A is
drawn from far more active bars than `C_PRICE_MOMENTUM`, so that
comparison is flagged and not relied on. **Price efficiency does not
separate continuation from rejection.**
**Verdict: NO INCREMENTAL VALUE.**

# 20. Control-construction audit

Run on every paired comparison. **MATCHED:** MAG-DIR-H1, BAL-H1, OVN-H2,
OVN-H4, ASYM-H1 (exact — same bars). **MISMATCHED:** OPEN-H1 (volume),
ASYM-H2 (volume and range). Every mismatched pairing is flagged in place
and its paired difference is treated as suspect. No cell's verdict rests
on a mismatched control.

# 34. Multiple testing — M = 15

| hypothesis | n | mean | p | BH q | Holm |
|---|---|---|---|---|---|
| **MAG-H3** | — | — | **0.0001** | **0.0008** | **0.0008** |
| ASYM-H1 | 2609 | −1.94 | 0.0844 | 0.4470 | 1.0000 |
| OVN-H4 | 187 | +10.42 | 0.0894 | 0.4470 | 1.0000 |
| MAG-DIR-H2 | 1630 | −1.95 | 0.1603 | 0.6011 | 1.0000 |
| BAL-H1 | 1082 | −2.20 | 0.2171 | 0.6514 | 1.0000 |
| ASYM-H2 | 2102 | −1.16 | 0.4638 | 1.0000 | 1.0000 |
| OPEN-H2 | 40 | −9.08 | 0.5020 | 1.0000 | 1.0000 |
| OPEN-H1 | 55 | +4.61 | 0.6777 | 1.0000 | 1.0000 |
| OVN-H2 | 125 | +2.60 | 0.7229 | 1.0000 | 1.0000 |
| MAG-DIR-H1 | 1511 | −0.34 | 0.8635 | 1.0000 | 1.0000 |
| BAL-H2 | 830 | −0.15 | 0.9432 | 1.0000 | 1.0000 |
| MAG-OFH13-H1 / OVN-H3 / RANGE-H1 / RANGE-H2 | diagnostics or void — entered at p=1.0 (conservative) |

**Exactly one cell survives correction.**

# 35. Promotion gate — full table

| cell | 1 exp | 2 self | 3 sign | 4 tail | 5 ctrl | 6 geom | 7 n | 8 artifact | result |
|---|---|---|---|---|---|---|---|---|---|
| **OVN-H4** | PASS | PASS | PASS | **FAIL** | PASS | PASS | PASS | PASS | **7/8 — NOT PROMOTED** |
| OVN-H2 | PASS | PASS | FAIL | FAIL | FAIL | FAIL | PASS | PASS | 4/8 |
| OPEN-H1 | PASS | PASS | FAIL | FAIL | FAIL | PASS | FAIL | PASS | 4/8 |
| MAG-DIR-H1 | FAIL | FAIL | FAIL | FAIL | PASS | FAIL | PASS | FAIL | 2/8 |
| BAL-H1 | FAIL | FAIL | FAIL | FAIL | PASS | FAIL | PASS | FAIL | 2/8 |
| BAL-H2 | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | PASS | PASS | 3/8 |
| ASYM-H1 | FAIL | FAIL | PASS | FAIL | PASS | FAIL | PASS | FAIL | 3/8 |
| ASYM-H2 | FAIL | FAIL | FAIL | FAIL | PASS | FAIL | PASS | FAIL | 2/8 |
| OPEN-H2 | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | 1/8 |

**Self-caught defect in my own gate, disclosed:** condition 2 was
originally implemented as `mean > 0 AND median > −|mean|`. The median
clause is **not in the directive** and is wrong for a no-target /
1.5-ATR-stop strategy, whose median is negative by construction. It
would have rejected **OFH13_PROSPECTIVE_V1 itself** (36.1% WR, negative
median), which proves the clause invalid. Corrected to the directive's
actual meaning — profitable on its own, not merely less bad than control
— and the family was **re-run**. The fix moved OVN-H4 from 5/8 to 7/8.

# 36. Ranking (by the ten declared criteria, not mean P&L)

1. **MAG-H3** — only cell surviving correction; monotone at 5/5 horizons
   in 3/3 partitions; regime feature, not a trade
2. **RANGE-H1** — persistence confirmed; 1.7–1.8× range ratio held to
   +30m; regime feature
3. **OVN-H4** — best MFE/MAE (1.29), best ff@1ATR (57.1%), sign-stable,
   7/8 gates; killed by tail dependence and q = 0.4470
4. **MAG-OFH13-H1** — informative (83% of OFH13 already in HIGH) but no
   incremental value
5. **BAL-H2** — MFE/MAE 1.07, the only other geometry above 1
6. **ASYM-H1** — decisive negative result, high evidential value
7–11. MAG-DIR-H1/H2, OVN-H2, OPEN-H1, ASYM-H2 — no incremental value
12. **OPEN-H2** — poor entry geometry
13. **OVN-H3** — void, specification error
14–15. RANGE-H2, and the void's control — no incremental value

# 37. Freeze specs for survivors

**MAG_SCORE is frozen as specified in §4** and is registered as a
**REGIME FEATURE ONLY** — not a signal, not a filter, and explicitly
**not** applied to OFH13. Honest caveat attached: `MAG_ALT_RNG` and
`MAG_ALT_VOL` both outperform it, so if a regime feature is ever used,
**trailing-normalised bar range is the better and simpler choice.**

No directional survivor exists, so no directional freeze spec is
written, and **no management study was run** — the directive's "no
management rescue" rule binds, because no cell demonstrated credible raw
directional geometry.

---

# SPECIAL QUESTIONS

**1. DOES ORDER-FLOW MAGNITUDE PREDICT FUTURE ABSOLUTE MOVEMENT?**
**YES.** Monotone at 5/5 horizons in 3/3 partitions, Spearman +0.3122,
p = 0.00005, q = 0.0008. *But plain volume and plain bar range predict
it better.*

**2. DOES ORDER-FLOW SIGN PREDICT DIRECTION ONCE PRICE STRUCTURE IS
CONTROLLED?** **NO.** ASYM-H1: on identical bars, delta sign returns
−3.44 vs price direction −1.94; delta sign is significantly negative
(p = 0.0011) in all three partitions.

**3. DOES HIGH MAGNITUDE + PRICE ACCEPTANCE BEAT ACCEPTANCE ALONE?**
**NO.** +1.89 pts of improvement (−2.23 → −0.34) with a MATCHED control,
but **both lose money**, so there is nothing to improve upon.

**4. DOES HIGH MAGNITUDE + FAILED ACCEPTANCE BEAT REJECTION ALONE?**
**NO.** FULL_MAG_REJECT −1.95 is *worse* than C_REENTRY_ANY −1.11.

**5. DOES OFH13 PERFORM BETTER IN HIGH EXPECTED-MOVEMENT STATES?**
**INCONCLUSIVE.** HIGH (+21.51, n=110) beats MEDIUM (−10.18, n=19) but
LOW (n=4) is unusable and the relation is non-monotone. The meaningful
finding is that **83% of OFH13 events already occur in HIGH states**, so
there is nothing to select.

**6. DOES THE RTH OPEN DETERMINE WHETHER OVERNIGHT INVENTORY CONTINUES
OR REVERTS?** **INCONCLUSIVE**, and partly unanswerable as specified —
OVN-H3's acceptance arm is void because a continuous future has no
opening gap. What *did* answer: OVN-H4, the overnight *level* sweep and
reclaim, is the strongest cell in the family (7/8 gates).

**7. IS ABSOLUTE ORDER-FLOW INTENSITY MORE USEFUL THAN DELTA SIGN?**
**YES — but only in the weak sense that sign is actively harmful.**
Intensity as a *condition* also hurts (C −1.94 vs D −1.44). Intensity is
useful for **magnitude**, not for direction.

**8. DOES PRICE EFFICIENCY SEPARATE CONTINUATION FROM REJECTION?**
**NO.** STATE_A −1.16, STATE_B −3.94; both lose, the rejection state
worst.

**9. BEST ROLE FOR ORDER FLOW BASED ON THIS RESEARCH?**
**VOLATILITY REGIME.** (Secondarily MOVEMENT MAGNITUDE — the same
finding.) Explicitly **not** DIRECTION, not BREAKOUT QUALITY, not
REJECTION QUALITY, not OFH13 CONTEXT. With the honest caveat that
trailing bar range and volume both fill the volatility-regime role
better than the order-flow composite does.

---

**OFH13_PROSPECTIVE_V1 REMAINS THE BEST SPECIFICATION AND IS UNTOUCHED.
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
