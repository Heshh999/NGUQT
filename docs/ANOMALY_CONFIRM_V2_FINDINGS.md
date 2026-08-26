# ANOMALY-CONFIRM-V2 — FINDINGS (ONE-SHOT HYPOTHESIS-SPECIFIC HISTORICAL CONFIRMATION)

# H1 ORDINAL-V-TURN: PARTIALLY CONFIRMED (13/14). H2 HALF-SESSION-LOW: FAILED (8/14).

Executed once against the preregistration frozen at
`e6f3f06ca54dc6e14e46a5fe1910086436a4d851`
(sha256 `0d7bae634c58d835bcc09577881564a037e828b1249cec8ffb3c7123ddef8ac8`,
2026-08-26T11:10:11+00:00). No threshold, motif, window or definition
was changed. No strategy simulated, no order submitted, nothing frozen
modified.

**Epistemic status:** hypothesis-specific *unexamined* historical
confirmation — **not** globally pristine OOS, **not** prospective. The
ceiling label is CONFIRMED (hypothesis-specific historical); nothing
here is prospectively validated.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**

---

## 1–6. PROVENANCE, WINDOW, FIREWALL, FAMILY

Phase 0: prereg sha256 **matches**; RVMR spec unchanged (1.270/2.335/
1440); Wave-3 lineage (menu `b054a00`, engine/findings `0ba46c1`) as
recorded in the prereg. **Confirmation window 2024-01-01 … 2026-08-17**;
820 confirmation exchange days, 1,398 discovery days. **Prospective
firewall: 0 rows ≥ 2026-08-26 consumed** (asserted; data ends
2026-08-17). MEMORY-PRED-V1 Lane A untouched. **M_binding = 2**;
RUN-AGE-HAZARD non-promotable; **M_cum = 8** (six prior promotable tests
+ these two).

**Contamination confirmed clean at runtime:** the H1 primary is a
within-last-leg contrast, and the engine reports the pooled turnAligned
(= the 2024+-exposed lag-1 MEMORY-PRED marginal) as **−0.0102 bp** while
Δturn is **+0.0314 bp** — the marginal cancels out of the contrast by
construction, so the tested object is genuinely the unexamined
second-order path-shape structure.

---

## 7–8. H1 COUNTS

848,395 confirmation motif events: 012 → 217,432 · 021 → 108,213 · 102 →
105,362 · 120 → 106,842 · 201 → 103,561 · 210 → 206,985. Each of the four
primary motifs ≥ 20,000 → minimum-n precondition PASS.

## 9–14. H1 PRIMARY, SIDES, MAGNITUDE MATCH, RVMR

| quantity | value |
|---|---|
| **Δturn (holdout)** | **+0.0314 bp**, CI [+0.0150, +0.0478], boot p 0.00005 |
| discovery anchor | +0.0792 bp → **retention 39.6%** (floor ⅓ = +0.0264) |
| **VT6 V-up vs est-up** | **+0.0199 bp** (PASS) |
| **VT7 V-dn vs est-dn** | **+0.0434 bp** (PASS) |
| **VT8 final-leg magnitude match** | **matched +0.0336 bp = 107% of raw** (PASS) — 1,606 cells |
| VT-amp RVMR (secondary) | LOW +0.0403, MED +0.0057, HIGH +0.0265 bp — **HIGH > LOW: FALSE** |

**The decisive scientific result (VT8): path shape is NOT redundant with
the final leg.** Matching on `|x2−x1| × ATR × ToD` *raised* the contrast
to 107% of raw — the V-turn-vs-established difference is not an artifact
of the fresh reversal having a larger last leg. Combined with the
incremental check (§1–6), **this confirms genuine second-order path-shape
information, distinct from the already-known lag-1 effect.** Both
directional sides pass.

**Honest correction to the discovery story (VT-amp, secondary,
non-gating):** the discovery-suggested RVMR-HIGH amplification **did not
replicate** — on 2024+, LOW carries the largest contrast (+0.0403) and
HIGH (+0.0265) is not distinguishable from zero. The effect is real but
**not** state-amplified out of sample. Because RVMR amplification was
frozen as a *secondary* per the Wave-3 protocol, this does not change the
verdict; it corrects the mechanism narrative.

## 15. RUN-AGE-HAZARD diagnostic (non-promotable)

h(k) by state on the confirmation window: POOL 0.4954 → 0.4819 → 0.4757
(k=1,3,5). The monotone early decay replicates (fresh runs carry more
continuation than aged ones), corroborating the mechanism. The k=9+
uptick and the loss of the discovery HIGH-steepness are noted; this is a
diagnostic and gates nothing.

## 16–17. H1 STABILITY

**Years (VT11): 3/3 positive** — 2024 +0.0480, 2025 +0.0167, 2026 +0.0297
bp (matched: +0.0486 / +0.0243 / +0.0219). **Months (VT12): 24/32
positive**, median +0.0363, worst 2025-04 −0.0999, best 2024-09 +0.1149.

**Time-of-day (VT10): 1/3 — FAIL.** The entire effect is **OVERNIGHT
+0.0534 bp** (CI excludes 0); RTH_AM −0.0278 and RTH_PM −0.0012 are
negative/null. This is the single failing gate and the reason the
verdict is PARTIALLY, not fully, CONFIRMED.

## 18. H1 TAIL DESTRUCTION

Within-group trims leave Δturn at **+0.0374 (1%)** and **+0.0361 (5%)** —
robust; not carried by a few extreme next-minute returns.

## 19–20. H1 INFERENCE AND BH

Day-clustered bootstrap 20,000/seed 20260826: Δturn CI [+0.0150,
+0.0478], p 0.00005. Motif-id rotation permutation (r[t+1] outcome
preserved, FFT-exact): **p 0.00285**. BH q at M=2: **0.00010**. M_cum=8
non-binding: 0.00013.

## 21. VT1–VT14

| # | measured | | # | measured | |
|---|---|---|---|---|---|
| VT1 | 0 rows ≥ bound | PASS | VT8 | matched +0.0336 (107%) | **PASS** |
| VT2 | motifs verbatim | PASS | VT9 | 3/3 ATR | PASS |
| VT3 | +0.0314 bp | PASS | VT10 | **1/3 ToD** | **FAIL** |
| VT4 | CI [+0.0150,+0.0478] | PASS | VT11 | 3/3 years | PASS |
| VT5 | q 0.00010, perm 0.00285 | PASS | VT12 | 24/32 months | PASS |
| VT6 | +0.0199 | PASS | VT13 | +0.0374/+0.0361 | PASS |
| VT7 | +0.0434 | PASS | VT14 | 39.6% retention | PASS |

**VT PASSED 13 / 14.**

## 22. H1 VERDICT

> ## PARTIALLY CONFIRMED (hypothesis-specific historical)

Frozen precedence: all of sign (VT3), CI (VT4), permutation and BH (VT5)
pass; year (VT11) and month (VT12) stability pass (so not UNSTABLE); VT8
passes (so not PATH-SHAPE REDUNDANT); **one condition — time-of-day
stability (VT10) — fails**, which maps to PARTIALLY CONFIRMED.

**What is confirmed:** a fresh directional reversal carries genuinely
different next-minute information than an aged run of the same final
direction, and that difference is *incremental to the final leg itself*
(VT8 107%) and *not* the known lag-1 effect (it cancels from the
contrast). This is the first confirmed **second-order path-shape**
result in the programme.

**What is not:** the effect is confined to the overnight session (VT10),
its RVMR-HIGH amplification did not replicate, and it is **economically
negligible** — Δturn ≈ +0.031 bp ≈ 0.06 NQ pts, and dissection shows the
contrast is driven by *established runs reverting* (012 −0.020, 210
−0.039 bp) more than by V-turns continuing (the V-up arm mean ≈ 0). In
plain terms the confirmed content is close to "aged 3-bar runs
mean-revert overnight" — the run-age-hazard mechanism again — not a
tradeable fresh-continuation edge. **No strategy is authorized.**

---

## 23–29. H2 — HALF-SESSION-LOW

**649 eligible confirmation days** (LOW 366, MED 244, HIGH 39). Pooled
+3.527 bp (CONTEXT ONLY, non-supporting, as frozen).

| noon state | n | aligned (bp) | P(match) |
|---|---|---|---|
| **LOW** | 366 | **+3.980** | 0.5027 |
| MEDIUM | 244 | +2.394 | 0.5041 |
| HIGH | 39 | +6.360 | 0.4872 |

| gate/quantity | value | verdict |
|---|---|---|
| **HS3/HS4** LOW mean, retention | +3.980 bp, **47.8%** of +8.32, ≥ +2.77 | PASS |
| **HS5** CI | **[−3.542, +12.586]** includes 0 | **FAIL** |
| **HS6** BH q / perm | q 0.33190 / perm 0.35393 | **FAIL** |
| HS7 both morning signs | am>0 +2.176, am<0 +7.502 | PASS |
| HS8 morning-magnitude both halves | +0.856 / +7.105 | PASS |
| **HS9** LOW-specificity vs non-LOW | **+1.040, CI [−8.986, +11.998]** | **FAIL** |
| **HS10** ATR both halves | lowvol **−3.214** / highvol +11.175 | **FAIL** |
| HS11 years | 2/3 | PASS |
| **HS12** months | **15/32** positive | **FAIL** |
| **HS13** tails | ex-1% **−1.123**, ex-5% **−6.054** | **FAIL** |
| HS14 no subgroup rescue | pooled not used | PASS |

## 30–36. H2 DESTRUCTION DETAIL

- **Not distinguishable from zero** (HS5, HS6): the point estimate +3.98
  bp is less than half its own CI half-width; the day sign-flip
  permutation gives p 0.354.
- **Not LOW-specific** (HS9): LOW is +1.04 bp above non-LOW with a CI
  from −9 to +12 — and HIGH (+6.36) actually exceeds LOW. The state does
  not identify anything special.
- **Entirely volatility-driven** (HS10): in low-ATR mornings the LOW
  effect is **−3.21 bp**; the whole thing lives in high-ATR mornings
  (+11.18). It is "big-morning drift," not a quiet-regime persistence.
- **Tail-dependent** (HS13): removing the top 1% (4 days) turns it
  **negative** (−1.12); top 5% → −6.05. The five largest LOW days are
  **+991.8, +434.7, +224.0, +213.1, +182.6 bp** — a handful of monster
  afternoons carry the entire mean. Median is only +0.585 bp.
- **Years (HS11):** 2/3, but 2024 was −0.56 bp; **months (HS12):** only
  15/32 positive.

Bootstrap 20,000/seed 20260826; day sign-flip permutation p 0.354; BH q
at M=2 **0.33190**.

## 38. H2 VERDICT

> ## FAILED (failing gates: HS5, HS6, HS9, HS10, HS12, HS13)

The frozen precedence selects FAILED rather than TAIL-DEPENDENT because
TAIL-DEPENDENT requires the CI (HS5) and support (HS6) to *pass* first;
here they fail, so the effect is not even established before the tail
question arises. The discovery lead was a **subgroup of a pooled null**,
and under the strict destruction the preregistration demanded of exactly
that situation, it collapsed: not significant, not LOW-specific, entirely
volatility-driven, and carried by five extreme days. This is the
preregistration's HS14 discipline working as designed — pooled
performance was never allowed to prop it up.

---

## 39. DEFECTS / DISCLOSURES

- **No spec defect.** One implementation performance choice (FFT-exact
  rotation permutation, verified at offset 0) and one display artifact
  (numpy scalar wrappers in the raw month prints) — neither touches a
  statistic; every gated number is correct as printed.
- The background shell wrapper reported exit-1, but the engine printed
  `EXECUTION COMPLETE` and all gates; the exit code is a harness artifact
  of the launch wrapper, not a script error.

## 40. FINAL INTERPRETATION

- **1 of 2 candidates confirmed — partially.** ORDINAL-V-TURN is the
  programme's first confirmed *second-order path-shape* structure:
  incremental to the final leg (VT8 107%), distinct from the exposed
  lag-1 effect (cancels from the contrast), significant and permutation-
  robust — but overnight-only, non-amplified by RVMR out of sample, and
  economically negligible. Frozen as a mathematical claim, not an edge.
- **HALF-SESSION-LOW is dead.** A textbook subgroup-of-a-null that failed
  every destruction test. No retuning; the branch is closed.
- **RVMR's role weakened, not strengthened, here.** The one confirmed
  structure does not depend on RVMR state (LOW ≈ HIGH), and the RVMR-
  conditioned half-session lead failed. Consistent with the programme
  ledger: RVMR is a certified *magnitude/activity* tool whose *directional*
  conditioning keeps not surviving strict confirmation.
- **M_cum = 8 sensitivity:** non-binding, changed no verdict (H1 q 0.00013,
  H2 q 0.41234).

## 41–43. HASHES, COMMIT, TREE

| artifact | sha256 |
|---|---|
| `docs/ANOMALY_CONFIRM_V2_PREREGISTRATION.md` | `0d7bae634c58d835bcc09577881564a037e828b1249cec8ffb3c7123ddef8ac8` |
| `analysis/anomaly/scan3_run.py` | `b8495516a9dcf9ada3ac287e304292fedd9ba3a8ac4a446bef858ad7dba73135` |
| `analysis/rvmr/rvmr_spec.py` | `e348f035a920954054a2b3e76ac0f0363b5502ccb2c872a2276d6236a152cd62` |

Engine `analysis/confirm2/confirm2_run.py` + raw output
`CONFIRM2_OUTPUT.txt` committed with this document. Working tree clean at
execution start (HEAD `e6f3f06…`).

---

## FROZEN KNOWLEDGE OBJECT (H1 only, as authorized)

```
ORDINAL-V-TURN-V2   STATUS: PARTIALLY CONFIRMED (hypothesis-specific historical)
  claim   at a fixed final-leg direction, a fresh 3-bar reversal (motif
          102/201) carries different next-minute return than an aged
          run (012/210); the contrast Δturn = +0.0314 bp (CI [+0.0150,
          +0.0478], p 0.00005, perm 0.00285) is incremental to the final
          leg (magnitude-matched 107%) and distinct from the lag-1 effect.
  limits  overnight-only (VT10 fail); RVMR-HIGH amplification did NOT
          replicate; economically negligible; V-turn arm ≈ 0 (contrast
          driven by aged-run reversal). NOT an edge, NOT a strategy.
  next    a predictive/trading hypothesis would require its own
          preregistration and prospective (post-2026-08-26) evidence.
```

No object is frozen for HALF-SESSION-LOW. RVMR-V1's certificate is
unchanged. Both candidates' family slots are spent (M_cum = 8).

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
