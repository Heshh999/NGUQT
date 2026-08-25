# 4H-DVT-V1 — HISTORICAL FINDINGS

## **FINAL VERDICT**

> **4H-DVT-V1 FAILED PROMOTION**

**7 of 15 promotion conditions FAIL.** The decisive finding is not that
the setup is merely weak — it is that **every one of its four components
subtracts value**. Vectors, the second test and the EMA9 trigger each
make the result *worse* than the simpler control, and the 4H filter is
null.

The strategy's `BH q = 0.0120` **passes** condition 12 — and it does so
**in the wrong direction**: the primary is *significantly worse* than the
ordinary-double-wick control. That is exactly why the gate has fifteen
conditions rather than one.

All results are **HISTORICAL DISCOVERY** — never OOS, never prospective,
never validated. Raw output: `analysis/dvt/DVT_OUTPUT.txt`.

---

## 1–2. Freeze verification and source hashes

| check | result |
|---|---|
| prereg sha256 at `19c60b9` | `c6526a09f1c13c34961c470ed3ff2d4ba17cc36dfc001870827d577fb1adcad0` — **match** |
| working-tree prereg | byte-identical (0-line diff) |
| `dvt_spec.py` at `19c60b9` | `2adf8b37d88d0676d22cb014768d8a996a6415ea2a59608c4af14718d06928d6` — **match** |
| HEAD at execution | `19c60b917f5655c9ba51804116e4f29de5218249`, tree clean |
| pre-existing DVT performance artifact | **none** — only `dvt_spec.py` and the counts-only `feasibility.py` were tracked |

Upstream: `rvmr_spec.py` `e348f035a9209540` · `rvmr_run.py`
`8743161d6fb5b04e` · `MnqTwoStrategiesShared.cs` `3f32ed177e972516`.

## 3. Implementation parity

1m bars 2,503,622 (2019-07-04 → 2026-08-17) · 15m intervals **169,639** ·
4H bars **10,956** · vector classes reproduced exactly (GREEN 11,629 ·
BLUE 5,699 · VIOLET 5,672 · RED 13,043 · REGULAR 133,586). Session VWAP,
bands, EMA9 and the vector classifier are transcriptions of the frozen
source, and the 15m/4H grids are the frozen 18:00-ET buckets.

**One sign error was found and fixed before any result was produced:** the
stopped-out economic-reference net was written `(px − stop) × side`,
which yields a *positive* number on a losing stop. Corrected to
`(stop − px) × side` and verified on worked examples (SHORT px 100 / stop
105 → −5; LONG px 100 / stop 95 → −5) *before* the scoring run.

## 4. Causal audit — PASS

Every entry satisfies the frozen availability table: 4H context from the
prior **completed** 4H bar; first vector from a **completed** 15m bar;
VWAP band per 1m bar with data through that bar; vector lookback from the
previous **10 completed** 15m bars; developing 15m OHLCV from completed
1m bars **through the trigger bar only**; EMA9 from completed 1m closes;
structural stop from the second interval's bars through the trigger.
**No completed-second-candle information can leak backward** — the
developing volume at bar *t* physically cannot contain later volume.

## 5. Parent reconciliation — fully reason-coded

| | count |
|---|---|
| rebuilt parents | **1,415** (SHORT 463 · LONG 952) |
| pre-registered feasibility | 765 (SHORT 250 · LONG 515) |

**Reason for the difference, stated plainly:** the counts-only
`feasibility.py` applied the entry-window filter at the **parent** stage
(requiring the second interval's last bar inside 09:30–15:00). The frozen
pre-registration §12 restricts only the **entry bar**. `dvt_run.py`
follows the pre-registration; the feasibility script was over-restrictive.
No rule was changed — the engine is the faithful one.

**Parent-level reconciliation is exact:**

```
1,415 parents  =  617 entries  +  798 no-trigger        (verified exact)
```

A further 2,108 *candidate bars* (not parents) were rejected as outside
the entry window or lacking a full 60-minute horizon.

## 6–8. Primary results

| arm | n | days | fwd5 | fwd15 | fwd30 | fwd60 | MFE | MAE | MFE/MAE | net | R |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **PRIMARY all** | **617** | 453 | +4.041 | **+2.956** | +1.878 | **−0.740** | 3.471 | 3.393 | **1.023** | **+0.395** | +0.013 |
| PRIMARY LONG | 415 | 302 | +2.532 | +3.784 | +1.297 | −2.340 | 3.453 | 3.827 | **0.902** | −0.337 | −0.031 |
| PRIMARY SHORT | 202 | 151 | +7.140 | +1.255 | +3.071 | +2.548 | 3.508 | 2.500 | **1.403** | +1.899 | +0.104 |

Economic reference **net +0.395**, day-clustered 95% CI
**[−4.937, +5.826]** — indistinguishable from zero. Median net **−18.620**:
the mean is carried by a minority of large winners.

**Sides diverge sharply.** SHORT has the better geometry (MFE/MAE 1.403,
net +1.899) on 202 events; LONG is the larger sample and is
**loss-making** (MFE/MAE 0.902, net −0.337). Neither side is deleted —
that would be V2.

## 9–17. Raw geometry and favourable-first

Forward returns decay monotonically from +4.041 at 5m to **−0.740 at 60m**
— whatever edge exists is short-lived and gone by the frozen horizon.

| ladder | FAV | ADV | AMBIGUOUS | NEITHER | fav% of decided |
|---|---|---|---|---|---|
| ±0.25 ATR | 255 | 202 | **160** | 0 | 55.80% |
| ±0.5 ATR | 325 | 252 | 40 | 0 | **56.33%** |
| ±1.0 ATR | 335 | 276 | 6 | 0 | 54.83% |
| +1.5/−1.0 | 274 | 339 | 2 | 2 | 44.70% |
| +2.0/−1.0 | 229 | 385 | 0 | 3 | 37.30% |

AMBIGUOUS preserved as its own class throughout and never resolved.
Favourable-first is above 50% at symmetric thresholds but **below the
ordinary-wick control at every one of them** (56.33% vs 59.69% at ±0.5).

## 18–22. Controls (identical measurement frame)

| arm | n | fwd15 | MFE/MAE | net |
|---|---|---|---|---|
| **PRIMARY** | 617 | **+2.956** | **1.023** | **+0.395** |
| **A** ordinary double wick | 2,097 | **+6.575** | **1.141** | +1.139 |
| **B** single vector | 1,683 | **+6.957** | **1.186** | +2.725 |
| **C** no EMA9 entry | 699 | **+6.955** | 1.147 | +1.635 |
| **D** no 4H alignment | 1,200 | +4.352 | 1.133 | +2.600 |
| **SECONDARY** completed-15m | 708 | **−2.750** | **0.798** | **−4.907** |

**Every control beats the primary on fwd15 and MFE/MAE.** The secondary
completed-15m reference is far worse than the developing version, so the
fast entry is the better of the two promotable tests — both fail.

## 23–27. THE DECOMPOSITION — every component subtracts

| component | raw fwd15 | 95% CI | p | matched | matched p |
|---|---|---|---|---|---|
| **A — vector value** (vs ordinary wick) | **−3.620** | [−6.444, −0.741] | **0.0120** | **−4.102** | **0.0357** |
| **B — double-test value** (vs single) | **−4.001** | [−6.747, −1.259] | **0.0040** | unavailable* | — |
| **C — EMA9 value** (vs no-EMA9) | **−3.999** | [−5.959, −1.971] | **0.0003** | −0.688 | 0.7580 |
| **D — 4H value** (vs no-4H) | −1.396 | [−3.873, +1.147] | 0.2714 | +0.725 | 0.6984 |

**A. Vectors make it worse.** Requiring GREEN/BLUE/VIOLET/RED instead of
allowing REGULAR costs **−3.620 raw and −4.102 matched**, both with CIs
excluding zero. Vector participation at a VWAP band is not a filter for
quality here; it selects a worse subset.

**B. The second test makes it worse.** −4.001, CI excluding zero. One
vector rejection outperforms two.

**C. The EMA9 trigger is expensive.** Execution detail across the 617
parents present in both arms: entry price is **−4.6159 points worse**,
the trigger costs **0.99 bars of delay**, risk rises 2.132 → 2.465 ATR,
and fwd15 falls **+8.552 → +2.956**. The matched comparison is null
(−0.688, p 0.758), so most of the raw damage is condition selection — but
the raw execution cost is real and large.

**D. The 4H filter does nothing.** −1.396 raw (p 0.271), +0.725 matched
(p 0.698). It reduces frequency (1,415 → 1,200 parents without it) without
improving direction.

**\*Disclosed control-construction defect:** the matched comparison for
Control B returned **matched n = 0**. Control B is single-test, so
`k1 == k2` and its first-to-second-test gap is always 0, while the
primary's gap is always ≥ 1 — and gap tercile is one of the frozen
matching variables. The two populations therefore share no cell **by
construction of my matching implementation**, not because of the data.
The **raw** B comparison stands and is what gate condition 6 uses; the
matched B figure is simply unavailable. I am recording this rather than
letting "matched n 0" pass silently.

## 28. Year destruction

| year | n | fwd15 | median | MFE/MAE | ff0.5 | net | **vs Control A** |
|---|---|---|---|---|---|---|---|
| 2019 | 36 | +3.694 | +3.000 | 1.935 | 58.82% | +2.179 | **+0.896** |
| 2020 | 81 | +3.318 | +3.250 | 0.959 | 54.93% | +2.411 | −4.833 |
| 2021 | 88 | +3.895 | +3.750 | 0.909 | 66.27% | −6.995 | −4.198 |
| 2022 | 76 | +0.293 | +8.750 | 1.165 | 48.65% | +2.327 | −8.824 |
| 2023 | 105 | +6.338 | +5.000 | 0.953 | 51.02% | −2.206 | −1.853 |
| 2024 | 89 | +0.022 | +5.750 | 1.065 | 59.26% | +9.681 | −3.148 |
| 2025 | 91 | +10.755 | +10.000 | 1.007 | 58.82% | +10.201 | **+2.751** |
| 2026 | 51 | −11.554 | −15.250 | 0.790 | 52.94% | **−22.546** | **−12.228** |

**2 of 8 years beat Control A** (gate needs ≥70%), and with the best year
removed the advantage is **−4.723**. 2026 is severely negative on both
measures.

## 29. Time-of-day destruction

| bucket | n | fwd15 | MFE/MAE | net | vs A |
|---|---|---|---|---|---|
| OPEN | **537** | +3.988 | 1.055 | +1.432 | −4.608 |
| MIDMORN | 56 | **−7.040** | 0.737 | −11.205 | −13.732 |
| AFTERNOON | 20 | +3.562 | 1.016 | +14.167 | −0.589 |

**87% of entries occur in the 09:30–10:30 bucket**, a structural
consequence of the entry window and VWAP-band dynamics. MIDMORN is
negative, so condition 10 fails. MIDDAY produced fewer than 10 entries.

## 30–32. Diagnostics (leads only, never rules)

**RVMR (context only):** LOW n 23 fwd15 +9.554 · MEDIUM n 188 +0.711 ·
HIGH n 406 +3.621. No filter was constructed.

**Vector colour (lead only):** `GREEN → GREEN` n 102, fwd15 **+18.809**,
net +11.640 is the standout cell; `GREEN → BLUE` n 28 is −7.402. **No
colour rule was created and none may be** — this is recorded as a future
research lead requiring its own pre-registration.

**Second-test extreme (never a filter):** FAILED_SHORT_OF n 354 (+1.303) ·
SWEPT n 256 (+5.104) · EQUAL n 7. No sweep filter was applied.

## 33. Tail destruction

Largest winner **+360.88**, largest loser −188.62. Top-1% share **6.306**,
top-5% share **21.282**. Mean +0.395 → **ex-top-1% −2.114 →
ex-top-5% −8.412**, median-ex-5% **−20.620**. The advantage versus
Control A remains negative after both removals (−4.150 / −3.533).
**The economic result is entirely tail-carried and negative without it.**

## 34–35. Inference and multiplicity

Day-clustered bootstrap, **20,000 iterations, seed 20260825**, throughout.
**M = 2, frozen and unchanged.**

| promotable test | p (vs A) | BH q |
|---|---|---|
| PRIMARY developing | 0.0120 | **0.0120** |
| SECONDARY completed-15m | 0.0000 | **0.0001** |

Both are significant **in the wrong direction** — both are significantly
*worse* than the ordinary-wick control.

## 36. Promotion gate — 7 of 15 FAIL

| # | condition | result |
|---|---|---|
| 1 | sufficient N | PASS n617 d453 L415 S202 |
| 2 | useful raw geometry | PASS fwd15 +2.956, net +0.395 |
| 3 | MFE/MAE > control | **FAIL** 1.023 vs 1.141 |
| 4 | favourable-first > control | **FAIL** 56.33 vs 59.69 |
| 5 | beats ordinary wick | **FAIL** −3.620, CI [−6.444, −0.741] |
| 6 | 2nd test adds value | **FAIL** −4.001 |
| 7 | EMA9 improves or no harm | **FAIL** −3.999 |
| 8 | long/short transparency | PASS |
| 9 | year stability ≥70% | **FAIL** 2/8, ex-best −4.723 |
| 10 | time-of-day stability | **FAIL** MIDMORN −7.040 |
| 11 | tail robustness | **FAIL** ex-top-5% net −8.412 |
| 12 | corrected support | PASS q 0.0120 *(wrong direction)* |
| 13 | no lookahead | PASS |
| 14 | no data artifact | PASS |
| 15 | no control artifact | PASS |

## 37–38. Verdict and candidate

**4H-DVT-V1 FAILED PROMOTION. No candidate is frozen.** No
`4H-DVT-CANDIDATE-V1` is created. No orders, no OFH13 combination, no
stop/target optimization.

---

## FINAL QUESTIONS

1. **Useful historical directional geometry?** — **NO** (net +0.395, CI spanning zero, median −18.620, fwd60 negative)
2. **Two vector tests beat two ordinary wicks?** — **NO** (−3.620 raw, −4.102 matched, both CIs exclude zero)
3. **Second vector adds information?** — **NO** (−4.001, CI excludes zero)
4. **1m EMA9 improves execution?** — **NO** (−4.62 pts entry price, +0.99 bars delay, fwd15 +8.552 → +2.956)
5. **4H EMA20/50 alignment adds value?** — **NO** (raw −1.396 p 0.271, matched +0.725 p 0.698)
6. **Which side is stronger?** — **SHORT** (MFE/MAE 1.403, net +1.899 vs LONG 0.902, −0.337) — but on 202 events and inside a failed family
7. **Survives year destruction?** — **NO** (2/8, best-year-removed −4.723)
8. **Survives time-of-day destruction?** — **NO** (MIDMORN −7.040; 87% of entries in one bucket)
9. **Survives tail removal?** — **NO** (ex-top-5% net −8.412)
10. **Incremental to matched NQ conditions?** — **NO** (matched vector value −4.102)
11. **Developing-vector fast entry passed the causal audit?** — **YES**
12. **Either promotable test survived corrected testing?** — **NO** — both significant, both **wrong-signed**
13. **Passed all 15 conditions?** — **NO** (7 fail)
14. **Freeze 4H-DVT-CANDIDATE-V1?** — **NO**
15. **Run stop/target optimization now?** — **NO**

---

## Why it failed

The setup is a **stack of four filters, three of which actively destroy
the base phenomenon.** A single ordinary VWAP-band rejection with a 4H
context (Control A, n = 2,097, fwd15 +6.575, MFE/MAE 1.141) is
**materially better** than the full construction, and adding vector
status, a second test and an EMA9 trigger reduces it step by step to
fwd15 +2.956 with MFE/MAE 1.023.

The one genuinely positive observation — that the developing fast entry
beats waiting for the 15m candle to complete (+2.956 vs −2.750) — means
the *causal architecture* was worth building even though the *strategy*
was not.

**Recorded as future research leads only, requiring their own
pre-registrations — none may modify V1:** the `GREEN → GREEN` colour cell
(n 102, fwd15 +18.809), and the fact that the simplest arm in the family
is the strongest, which points away from filter-stacking altogether.

**Per the frozen no-rescue rule, none of the following was tested and
none will be: 8/4/32-bar spacing, Band 2, other VWAP multipliers, EMA13,
fresh 4H crossovers, colour-only rules, sweep requirements, other entry
hours, stops or targets.** Any of those is **4H-DVT-V2** and needs a new
pre-registration.

**NO ORDERS PLACED. OFH13_PROSPECTIVE_V1 UNTOUCHED.
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
