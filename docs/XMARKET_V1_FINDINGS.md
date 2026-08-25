# XMARKET-V1 — FINDINGS

## **FINAL VERDICT**

> **XMARKET-V1 FAILED TO FIND MATERIAL INCREMENTAL ES INFORMATION AT
> 1-MINUTE RESOLUTION.**
>
> **ES IS HIGHLY RELATED TO NQ BUT DOES NOT ADD ENOUGH INFORMATION
> BEYOND NQ'S OWN PRICE/STATE VARIABLES UNDER THE TESTED MECHANISMS.**

Zero of eight hypotheses passed the promotion gate. No ES filter was
created to rescue the family. Nothing frozen was modified.
`OFH13_PROSPECTIVE_V1` remains untouched.

Raw output: `analysis/xmarket/XMK_OUTPUT.txt`.

---

## 1. Result-blindness audit

| | |
|---|---|
| H4 result seen before addendum freeze? | **NO** |
| H5 result seen before addendum freeze? | **NO** |
| H8 result seen before addendum freeze? | **NO** |

No P&L, mean, median, MFE, MAE, MFE/MAE, favourable-first, p, q, year,
era, time-of-day, RVMR slice, tail table or matched-control figure for
H4, H5, H6, H7 or H8 was ever displayed before the addendum was frozen
and pushed. The numeric definitions were committed at `0910732` before
any run produced a hypothesis result; a later run was terminated
mid-write at 355 lines, but the highest line ever read was **140** and
the H4 section begins at line **179**.

**H4, H5 and H8 remain PRE-REGISTERED.** No `EXPLORATORY-DERIVED`
designation is triggered.

**Disclosed permanently:** H1, H2 and H3 results *were* seen before the
addendum document existed. H1/H2 derive entirely from the original
frozen document. H3 depends on the catch-up timing choice, frozen in
source and committed before H3 produced output, transcribed unchanged.

## 2–3. Addendum

| | |
|---|---|
| path | `docs/XMARKET_V1_PREREGISTRATION_ADDENDUM.md` |
| sha256 | `e74182e9360f14ca42c05517d609eca44a924a043fee1b402b5efae80423b0b6` |
| commit | `a2baab01d4b30327b65ac39b2a9afeb272596c75` |
| timestamp | 2026-08-25T07:41:25+00:00 |
| pushed before execution | **yes** |

## 4. Original pre-registration

| | |
|---|---|
| path | `docs/XMARKET_V1_PREREGISTRATION.md` |
| commit | `36aaa28378dbaa359e011579ae3dc96f5e2418e7` |
| sha256 | `314262cbfe3782f07ac81c795f01dc553382fa5d11ef1f6cf14cfd3bebb8c786` |
| byte-identical to frozen commit | **yes** |
| **M** | **8 — NOT shrunk** |

## 5–7. Data gates and universe

**Gate 1 PASS · Gate 2 PASS** (`docs/ES_NQ_DATA_V1_GATE2.md`, `0910732`).
Corrected conservative quarantine, all three anchors ±2 days.

| | |
|---|---|
| MATCHED | **2,243,394** |
| ROLL_QUARANTINED | 258,873 |
| NQ_ONLY | 1,355 |
| ES_ONLY | 40,157 |
| usable decision bars | 529,629 |

## 8. Normalization (frozen, unchanged)

`Z_X(t,w) = (close_X(t) − close_X(t−w)) / ATR_X(t)`, primary w = 5;
`REL_STRENGTH = Z_NQ(t,5) − Z_ES(t,5)`. Divergence terciles calibrated
on **2019-07-04 → 2020-07-04 only** (n = 303,178): LOW < 0.2142 ≤ MID ≤
0.5154 < HIGH. Uniform frame everywhere: 1.5 × ATR_NQ stop, no target,
60-minute exit, 0.87 pt cost.

---

## 9–16. THE EIGHT HYPOTHESES

### Primary comparisons

| family | n | signal | control | raw Δ | **matched Δ** | p | BH q | Holm |
|---|---|---|---|---|---|---|---|---|
| XMK-H1 | 10,137 | −1.028 | −0.909 | −0.119 | **+0.021** | 0.2306 | 0.3839 | 1.0000 |
| XMK-H2 | 514 | −3.883 | −0.797 | −3.086 | −2.293 | 0.0916 | 0.3666 | 0.6415 |
| XMK-H3 | 3,673 | −0.611 | −0.575 | −0.036 | +0.032 | 0.9363 | 1.0000 | 1.0000 |
| XMK-H4 | 2,990 | −0.633 | −0.832 | +0.139 | +0.200 | 0.7524 | 1.0000 | 1.0000 |
| XMK-H5 | 6,356 | −0.565 | −1.544 | +0.980 | +0.327 | 0.1433 | 0.3823 | 0.8601 |
| XMK-H6 | 3,665 | −1.061 | −0.100 | −0.961 | −0.478 | **0.0185** | 0.1484 | 0.1484 |
| XMK-H7 | 5,411 | −0.466 | −1.324 | +0.858 | **+2.022** | 0.2399 | 0.3839 | 1.0000 |
| XMK-H8 | **0** | — | — | — | — | — | — | — |

**Every signal arm has a negative mean.** Not one is economically
positive, so no comparison can promote regardless of its delta — the
BRK-H1 rule.

### H1 — NQ breakout + ES confirmation

| arm | n | mean | median | MFE | MAE | MFE/MAE | ff@0.25 |
|---|---|---|---|---|---|---|---|
| NQ alone | 11,065 | −0.909 | −12.120 | 24.75 | 25.00 | 0.990 | 47.2% |
| **+ CONFIRMING** | **10,137** | **−1.028** | −12.364 | 24.75 | 25.25 | 0.980 | 46.9% |
| + NEUTRAL | 772 | +1.038 | −10.179 | 24.50 | 20.50 | 1.195 | — |
| + OPPOSING | 156 | −2.825 | −9.814 | 29.88 | 25.12 | 1.189 | — |

**The decisive number is 10,137 / 11,065 = 91.6%.** ES already confirms
nine NQ breakouts in ten. At +0.85 one-minute correlation, "ES agrees"
is very nearly a constant, and a constant cannot discriminate. Matched
Δ = **+0.021** — indistinguishable from zero. MFE/MAE 0.980 vs 0.990 and
favourable-first 46.9% vs 47.2% are the same distribution.

**ES confirmation is decorative.**

### H2 — NQ breakout + ES refusal + NQ failed acceptance

| arm | n | mean | MFE/MAE | ff@0.25 |
|---|---|---|---|---|
| NQ failed alone | 5,005 | −0.797 | 0.913 | — |
| **+ ES refusal** | **514** | **−3.883** | 0.751 | 45.5% |
| + ES confirmed | 4,491 | −0.444 | 0.932 | — |

ES refusal makes the pre-registered *reversal* trade **markedly worse**
(matched Δ −2.293), with MFE/MAE falling 0.913 → 0.751.

**Sign inversion, recorded but NOT exploited.** Signed by the reversal
direction the path runs −0.79 → −2.35 → −2.24 → −2.97 over 5/10/15/60
minutes; flipped, that says NQ tends to *resume the original breakout
direction*. Inverting a hypothesis after seeing its results is retuning.
**H2 is reported FAILED, not promoted in reverse.** Year signs flip
twice (2021 +0.46, 2026 +7.97 on n = 43 with median −20.28); MFE/MAE
ranges 0.414 → 1.569.

### H3 — NQ leads → ES catch-up

| arm | n | mean | MFE/MAE |
|---|---|---|---|
| parent, no ES condition | 6,675 | −0.575 | 0.953 |
| **catch-up** | **3,673** | **−0.611** | 0.909 |
| refusal | 3,002 | −0.531 | 1.012 |

ES splits the parents almost evenly (3,673 / 3,002) — so unlike H1 this
is *not* a near-constant — **and the split still tells you nothing.**
Raw Δ −0.036, p = 0.9363. The three arms are one distribution.

### H4 — NQ leads → ES refusal, split by NQ's own state

| arm | n | mean | MFE/MAE |
|---|---|---|---|
| all parents (reversal dir.) | 6,675 | −0.772 | 0.988 |
| refusal, all | 3,002 | −0.650 | 0.950 |
| A_EFFICIENT | **12** | −5.068 | 0.164 |
| B_DETERIORATES | **12** | +4.706 | 0.320 |
| C_LOST_ACCEPTANCE | 2,978 | −0.654 | 0.975 |
| **PRIMARY (B or C)** | **2,990** | **−0.633** | 0.975 |

Matched Δ +0.200, p = 0.7524 — null.

**Structural finding: the A/B/C split is degenerate.** 2,978 of 2,990
land in C. When NQ leads and ES refuses, **NQ loses acceptance within
three bars 99.6% of the time**, leaving A and B with 12 events each. The
efficiency refinement had nothing to refine. This is reported, not
repaired — the primary arm (B or C) is well populated and the hypothesis
is scored as frozen.

### H5 — Relative-strength extreme

**Resolution within 30 bars (information study):**

| bucket | n | converged via NQ | converged via ES | widened | unresolved |
|---|---|---|---|---|---|
| LOW | 6,583 | 9.2% | 9.9% | 81.0% | 0.0% |
| MID | 6,277 | 26.4% | 29.1% | 44.4% | 0.0% |
| HIGH | 6,356 | **37.0%** | **39.1%** | 23.9% | 0.0% |

Two things matter here. First, the LOW→HIGH gradient is **mechanical**:
with multiplicative 0.5×/1.5× thresholds, a small divergence has far
more proportional room to widen than to halve. It is a property of the
measure, not information about the market. Second — and this is the
direct answer to *which market wins the disagreement* — **convergence is
almost perfectly symmetric: 37.0% via NQ vs 39.1% via ES.** Neither
market systematically drags the other back.

| arm | n | mean | MFE/MAE | ff@0.25 |
|---|---|---|---|---|
| RS LOW | 6,583 | −1.544 | 0.953 | — |
| RS MID | 6,277 | −1.584 | 0.971 | — |
| **RS HIGH** | **6,356** | **−0.565** | 1.023 | 49.6% |

Raw Δ +0.980 (p = 0.1433), matched Δ +0.327. HIGH is still negative.
Year signs flip four times (2019 +, 2020–21 −, 2022 +, 2023–24 −, 2025 +,
2026 −).

### H6 — ES leads → NQ catch-up (mirror of H3)

| arm | n | mean | MFE/MAE |
|---|---|---|---|
| parent, no NQ condition | 6,729 | −0.100 | 1.036 |
| **catch-up** | **3,665** | **−1.061** | 1.012 |
| refusal | 3,064 | **+1.050** | 1.061 |

**The only nominally significant primary in the family — and it points
the wrong way.** Raw Δ −0.961, p = 0.0185, matched Δ −0.478. When ES
leads and NQ *does* catch up, subsequent NQ geometry is **worse**; when
NQ refuses to follow ES, it is better (+1.050). BH q = 0.1484, so it
does not survive correction at M = 8 in either direction. Year signs
flip; 2026 is −3.288.

### H7 — Cross-market acceptance agreement

| arm | n | mean | median | MFE/MAE | ff@0.25 |
|---|---|---|---|---|---|
| NQ any | 11,064 | −0.908 | −12.120 | 0.990 | — |
| **BOTH accept** | **5,411** | **−0.466** | −13.245 | 1.009 | 47.7% |
| NQ only | 5,647 | −1.324 | −11.295 | 0.968 | — |
| ES only | 26,775 | −0.143 | −13.076 | 1.028 | — |
| disagreement | **6** | −7.739 | −8.211 | 0.765 | — |

**H7 carries the family's largest matched-control advantage: +2.022
pts/trade** (signal −0.450 vs control −2.472, n matched 5,215). It still
fails, for reasons that are not close:

- BOTH_ACCEPT **loses money** (−0.466). Condition 1 fails outright.
- p = 0.2399, sign-flip p = 0.4162, BH q = 0.3839.
- Median −13.245, **worse** than NQ_ONLY's −11.295.
- Six of eight years negative.
- Top-1% share −5.062; mean ex-top-5% = **−7.982**. Tail-dependent.

Genuine cross-market *disagreement* on acceptance occurs **6 times in
seven years** — the two markets essentially never accept in opposite
directions at the same minute.

*Limitation, disclosed:* the ES_ONLY arm has no cooldown applied while
the NQ-anchored arms do, inflating its N. It is not part of the primary
comparison (BOTH vs NQ_ONLY) and does not affect any statistic above.

### H8 — Disagreement resolution — **VOID, SPECIFICATION ERROR (mine)**

**n = 0. Zero events in seven years, and the cause is my defect, not the
data.**

`nq_balance(j)` returns `max(high[j−29 … j])` — a window that **includes
the decision bar**. Therefore `close[j] > balance_high` is impossible by
construction, since `close[j] ≤ high[j] ≤ max`. The same holds on the low
side, and `es_beyond` carries the identical flaw. H7 works because its
detector calls `nq_balance(j−2)`; H8 called `nq_balance(j)`.

**This is the B6 defect from RVMR-STRAT-V1 repeating** — a balance
envelope containing its own decision bar. Per the standing rule, a void
hypothesis is **not retuned and not re-run**, and **M is not shrunk**.
H8 counts as a full member of the family of 8. The question it was built
to ask — *which market wins the disagreement?* — is answered indirectly
by H5's resolution table (37.0% NQ vs 39.1% ES: neither).

---

## 17–18. Matched controls and incremental information

Every signal arm was matched cell-by-cell against NQ-equivalent events on
**NQ ATR · time of day · NQ recent normalized return · NQ recent range ·
NQ volume · RVMR range state · direction · year**. Cells lacking a
counterpart were dropped **symmetrically from both sides**, so missing
control coverage can never flatter the signal.

**The destruction test — can the result be explained by NQ alone?**

| family | raw Δ | matched Δ | survives NQ-only explanation? |
|---|---|---|---|
| H1 | −0.119 | +0.021 | **NO — collapses to zero** |
| H2 | −3.086 | −2.293 | NO — wrong sign |
| H3 | −0.036 | +0.032 | **NO — zero either way** |
| H4 | +0.139 | +0.200 | NO — p 0.75 |
| H5 | +0.980 | +0.327 | **NO — two-thirds absorbed by NQ controls** |
| H6 | −0.961 | −0.478 | NO — wrong sign |
| H7 | +0.858 | +2.022 | delta survives, but signal is loss-making |
| H8 | — | — | VOID |

## 19–21. Geometry, favourable-first, long/short

**MFE/MAE across every arm sits in 0.87–1.20, clustered on ~1.00.**
Favourable-first at ±0.25 ATR sits in 45.5–49.6% across all eight — never
distinguishable from a coin flip, with AMBIGUOUS preserved as its own
class throughout (e.g. H1 CONFIRMING: 3,814 FAV / 4,326 ADV / **1,997
AMBIGUOUS**) and never resolved by guessing.

Long/short asymmetry is consistent and unexplained by ES: longs
outperform shorts in every family (H1 −0.564 vs −1.563; H4 +0.570 vs
−1.717; H7 +0.308 vs −1.316). This is an **NQ drift** property, present
in all arms including the controls, and is not an ES effect.

## 22. NQ-lead vs ES-lead — the asymmetry question

| direction | parent n | catch-up mean | refusal mean | matched Δ |
|---|---|---|---|---|
| **NQ leads → ES** (H3) | 6,675 | −0.611 | −0.531 | +0.032 |
| **ES leads → NQ** (H6) | 6,729 | −1.061 | **+1.050** | −0.478 |

The two leadership states occur almost equally often (6,675 vs 6,729) —
**neither market is the leader.** The only asymmetry is that ES→NQ
catch-up is actively *harmful* to subsequent NQ geometry while NQ→ES
catch-up is inert. Neither survives BH at M = 8.

## 23–25. Stability

- **Year:** no family holds a sign across 2019–2026. H1 is negative in
  7 of 8 years; H5 flips four times; H7 is negative in 6 of 8.
- **Volatility era:** COVID-2020 is the worst era for nearly every arm
  (H1 −2.468, H4 −2.502, H6 −2.122, H7 −2.649); 2023–24 is the best.
  Direction of the *delta* does not persist across eras.
- **Time of day:** H4 (+1.061) and H7 (+1.164) are positive only in
  09:30–11:00 and negative after 13:30. Consistent with the pre-registered
  observation that the largest cross-market extremes cluster at the cash
  open. **No tighter window was tested or optimized.** Since neither
  family survives its primary test, this is labelled but not pursued.

## 26. RVMR diagnostic (post-primary, never a promoter)

Reported after the primary in every family. Range-HIGH is the worst
state in H1 (−1.577), H2 (−8.278), H5 (−2.658) and H6 (−3.606) — the
same symmetric-magnitude behaviour RVMR-V1 was certified for. **No
ES + RVMR combination was constructed.**

## 27. Tail destruction

| family | max | min | top-1% share | mean | ex-top-1% | ex-top-5% |
|---|---|---|---|---|---|---|
| H1 | +541.88 | −226.49 | −2.108 | −1.028 | −3.228 | **−7.983** |
| H2 | +543.88 | −56.26 | −0.692 | −3.883 | −6.635 | **−10.590** |
| H4 | +352.38 | −74.18 | −2.880 | −0.633 | −2.479 | **−6.453** |
| H5 | +407.63 | −85.58 | −3.364 | −0.565 | −2.490 | **−6.567** |
| H6 | +495.88 | −83.91 | −1.788 | −1.061 | −2.987 | **−6.926** |
| H7 | +541.88 | −206.93 | −5.062 | −0.466 | −2.851 | **−7.982** |

Every family degrades sharply once the top 5% is removed. All are
**TAIL-DEPENDENT**, and all were already loss-making before the test.

## 28. Multiple testing

BH and Holm at the **frozen M = 8** (table in §9). Lowest raw p is
H6 at 0.0185, wrong-signed; its BH q is 0.1484. **No family reaches
q < 0.05.** M was not shrunk for the void H8 or for any failing family.

## 29. Promotion gate

All fourteen conditions printed for every family in
`analysis/xmarket/XMK_OUTPUT.txt`. Summary of condition 1 — *positive
economic directional geometry* — which alone is disqualifying:

| family | signal mean | cond. 1 | BH q < 0.05 | promoted |
|---|---|---|---|---|
| H1 | −1.028 | FAIL | FAIL | **NO** |
| H2 | −3.883 | FAIL | FAIL | **NO** |
| H3 | −0.611 | FAIL | FAIL | **NO** |
| H4 | −0.633 | FAIL | FAIL | **NO** |
| H5 | −0.565 | FAIL | FAIL | **NO** |
| H6 | −1.061 | FAIL | FAIL | **NO** |
| H7 | −0.466 | FAIL | FAIL | **NO** |
| H8 | VOID | — | — | **NO** |

## 30. Survivor freeze

**None.** No `XMARKET-[ID]-CANDIDATE-V1` is created.

## 31. Final classification

| family | classification |
|---|---|
| XMK-H1 | **REDUNDANT WITH NQ PRICE** (91.6% base rate; matched Δ +0.021) |
| XMK-H2 | **NO INCREMENTAL VALUE** (wrong sign; year-unstable) |
| XMK-H3 | **NO INCREMENTAL VALUE** (p 0.94) |
| XMK-H4 | **NO INCREMENTAL VALUE** (p 0.75; A/B split degenerate) |
| XMK-H5 | **REDUNDANT WITH NQ PRICE** (2/3 of Δ absorbed by NQ controls) |
| XMK-H6 | **NO INCREMENTAL VALUE** (significant wrong-signed; q 0.148) |
| XMK-H7 | **TAIL-DEPENDENT** (largest matched Δ, but loss-making, q 0.38, ex-top-5% −7.98) |
| XMK-H8 | **VOID — SPECIFICATION ERROR** |

---

## FINAL QUESTIONS

1. **DOES ES ADD MATERIAL INFORMATION BEYOND NQ?** — **NO**
2. **STRONGEST ES USE?** — **NONE**
3. **DOES ES CONFIRMATION IMPROVE MATCHED NQ BREAKOUTS?** — **NO** (+0.021)
4. **DOES ES REFUSAL IMPROVE MATCHED NQ FAILED-BREAKOUT DETECTION?** — **NO** (−2.293, wrong sign)
5. **WHICH MARKET LEADS MORE USEFULLY?** — **NEITHER** (6,675 vs 6,729 parents; both inert or harmful)
6. **IS CROSS-MARKET DISAGREEMENT ITSELF USEFUL?** — **NO** (acceptance disagreement occurs 6 times in 7 years)
7. **IS DISAGREEMENT RESOLUTION USEFUL?** — **NO** (H8 VOID; H5 shows convergence 37.0% NQ vs 39.1% ES — symmetric)
8. **DID ANY HYPOTHESIS SURVIVE ALL PROMOTION GATES?** — **NO**

---

## What this closes

The programme's central recurring finding now extends to a second
market. Across ~100 hypotheses, order flow predicted magnitude and not
direction; here a seven-year, 2.24-million-minute synchronized ES↔NQ
universe — the highest-quality dataset this project has ever held —
shows that **a second correlated index future adds nothing directional
that NQ's own price and state variables did not already contain.**

The reason is visible in H1's base rate: at +0.85 one-minute correlation,
ES agrees with NQ 91.6% of the time. High correlation is precisely what
makes ES uninformative — it repeats NQ rather than adding to it.

**XMARKET-V1 IS KILLED.** No new ES filters were created. The next
mechanism must be genuinely different from a correlated index future.

**OFH13_PROSPECTIVE_V1 REMAINS THE BEST SPECIFICATION AND REMAINS
UNTOUCHED. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
