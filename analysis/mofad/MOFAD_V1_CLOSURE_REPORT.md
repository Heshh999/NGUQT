# MOFAD-V1 — FAILED-HYPOTHESIS CLOSURE REPORT

**Committed BEFORE any MOFAD outcome analysis**, per the master prompt §2.
"Kill" = permanently classified as spent and protected from rescue. No code,
report, ledger, or evidence was deleted.

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

---

## 1. Scope of the closure sweep

Every prior formal program in this repository was inspected via its
committed findings/ledger artifacts (all of `docs/*_FINDINGS.md`, the
MGSD/LPCC/CCHC/ODMC ledgers under `analysis/`, and the ODMC cumulative
exposure ledger, which itself aggregates 571 prior formal tests). The
registry (`MOFAD_V1_SPENT_HYPOTHESIS_REGISTRY.csv`, **72 rows**) records one
row per named hypothesis or per bounded hypothesis family; where a family's
own committed ledger already enumerates its variants (e.g. MGSD's 244
strategy variants), the registry row points at that ledger rather than
duplicating it — the ledger remains the variant-level record and is equally
frozen.

## 2. Status counts

| status | rows | notes |
|---|---:|---|
| `DEAD_FROZEN` | **53** | tested, failed at least one binding gate; rescue prohibited |
| `DESCRIPTIVE_ONLY_SPENT` | **10** | maps/anomaly descriptions that never became a valid strategy (Wave-4 VR cells, anchor field, RVMR battery, MGSD screens, MAG, NSERIES, ANOMALY-SCAN, HARU, RVMR-VALIDATION, ANOMALY-CONFIRM maps) |
| `INSUFFICIENT_DATA` | **2** | OFH13-MEMORY (ALIGNED n=10 < 20 frozen floor); S30A n=28 observation |
| `PASSED_HISTORICAL_EXPLORATORY` | **2** | OFH13, OFH14 — passed their stated historical gates; prospective arms frozen; **derivative mining prohibited** while prospective runs |
| `RESERVED_UNTOUCHED` | **5** | VALIDATION / OOS / LOCKBOX partitions, 2026-08-18..31 buffer, MEMORY-PRED prospective Lane A |

No prior hypothesis was granted `PASSED_HISTORICAL_EXPLORATORY` from gross
P&L alone: OFH13/OFH14 are the only members and each passed its program's
full stated historical gate set (BH q = 0.061 exploratory threshold of that
program) before being frozen for prospective scoring.

## 3. ODMC failure — verified, not taken on report

The master prompt says ODMC "user reports failed; verify the committed
final report and result hash before registering it." Verified directly:

- `analysis/odmc/ODMC_V1_RESULTS.md` at HEAD `9fec0784f4027877b62f1fde7c9b5411a1af54f6`
  states **"ODMC-V1 HISTORICAL FEASIBILITY FAILED; HYPOTHESIS KILLED."**
- The results file records protocol-freeze commit
  `9072bd3d8ef244eb6b87a6c56f9e983849e526a8` (v1.0.1 test correction
  `93acc65` committed before outcomes).
- Binding failures: gross PF 1.272 < 1.30 floor; day-blocked permutation
  p = 0.5891 vs familywise 0.0166667; D10 volatility residualization left
  ≈ 0 residual effect.
- Registered as `DEAD_FROZEN`; the three-arm continuation family
  (LPCC + CCHC + ODMC) is registered closed as a family row.

## 4. How close derivatives are automatically blocked

`similarity_screen.py` + `MOFAD_V1_SPENT_HYPOTHESIS_FINGERPRINTS.json`
implement a **deterministic** screen, frozen before outcomes:

- Every registry row carries a `fingerprint_class` (20 classes). Each class
  has a frozen information-set token list and trigger granularity.
- **R1** — a proposal declaring any spent mechanism class is rejected
  outright. This blocks re-parameterization, inversion (fade↔continuation
  inside the same class), renaming, and session-shifting of a dead rule.
- **R2** — a proposal whose information-set token Jaccard ≥ 0.80 against a
  spent class at the same trigger granularity is rejected even under a new
  class name. This blocks rescues that relabel the same data driving the
  same decision.
- **R3** — any management/filter/execution variant of an existing strategy
  is rejected as not-a-new-mechanism.
- `PASSED` classes are **protected**: FVG_FLOW_MITIGATION derivatives are
  rejected identically, so OFH13/OFH14 cannot be strip-mined while their
  prospective arms run.
- Acceptance additionally requires a written distinctness justification
  naming the *new causal information source*. Every screen decision for
  every MOFAD proposal (accepted or rejected) is recorded in the hypothesis
  ledger; rejected proposals cannot be resubmitted with parameter changes.

Dead hypotheses remain in all multiplicity accounting: the cumulative
exposure ledger lineage (571 prior formal tests at CCHC time, extended by
ODMC and this program) carries forward into the MOFAD multiplicity plan.

## 5. Distinctions preserved

Descriptive maps (variance-ratio cells, anchor fields, regime batteries)
are classified `DESCRIPTIVE_ONLY_SPENT`, not `DEAD_FROZEN` — except where a
specific strategy translation of the map was actually tested and failed
(LPCC/CCHC/ODMC translate Wave-4 cells; those translations are dead, while
the cells themselves remain descriptive-spent). `INSUFFICIENT_DATA`
verdicts (OFH13-MEMORY, S30A) are recorded as unproven-not-false and remain
untradeable and unpromotable without new data.
