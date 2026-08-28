# NMAE-V1 — ANCESTRY, EXPOSURE AND MECHANISM ONTOLOGY

Read-only (§3). No prior research was reset, rewritten, squashed,
deleted or hidden. No unrelated file was modified.

## 1. Repository state

- Branch `claude/ninjatrader-mnq-automation-rqjzgg`
- Starting HEAD `9c75fff743294a092b75c9502144edbfe716da8f`
- Tree clean at audit start
- Python 3.11.15 · numpy 2.4.6 · x86_64 Linux · mono/mcs for NT8 hosts

**All 15 prior freeze and results commits verified in ancestry (15/15):**
`eac54fe` Wave-4 · `f08396b`/`be1fff6` LPCC · `5133c51`/`963009d` CCHC ·
`9072bd3`/`9fec078` ODMC · `7062e67`/`bb6986b` MGSD ·
`7c8a854`/`643343f`/`e628b9d`/`938382b` MOFAD · `8dfc2de`/`537a662` VTBS.

## 2. Exposure status (binding, per §2)

- The MNQ 1m price span 2019-07-04→2026-08-17 is **fully exposed**.
- The MNQ 1m order-flow capture 2025-08-18→2026-08-19 is **exposed**.
- The 30s morning window and the 42-day ES pilot are **exposed**.
- Any positive result on this history would be exploratory DEV evidence
  only — never independent confirmation.
- Protected partitions **remain unopened**: buffer 2026-08-18→31,
  VALIDATION 2026-09-01→2027-02-28, OOS 2027-03-01→2027-08-31,
  FINAL LOCKBOX 2027-09-01+.

## 3. Mechanism ontology (reconciled aliases)

The existing spent registry (`analysis/mofad/MOFAD_V1_SPENT_HYPOTHESIS_REGISTRY.csv`,
78 rows) and its 23 fingerprint classes are carried forward unchanged as
the canonical ontology. Summary of dispositions:

| Disposition | Count | Meaning |
|---|---:|---|
| `DEAD_FROZEN` | 59 | tested, failed a binding gate — rescue prohibited |
| `DESCRIPTIVE_ONLY_SPENT` | 10 | maps that never became valid strategies |
| `INSUFFICIENT_DATA` | 2 | unproven, not false; untradeable |
| `PASSED_HISTORICAL_EXPLORATORY` | 2 | OFH13, OFH14 — prospective-protected |
| `RESERVED_UNTOUCHED` | 5 | future partitions + MEMORY-PRED prospective |

**No new spent entries were added by NMAE-V1.** Nothing was tested, so
nothing became spent. In particular, the message-level mechanisms that
MLES-V1 would have covered remain **RESERVED_UNTOUCHED** and are
explicitly *not* imported to the registry (§1 forbids classifying them
dead when MLES did not complete).

## 4. Derivative-blocking screen

The deterministic screen (`analysis/mofad/similarity_screen.py`, rules
R1 mechanism-class match, R2 ≥0.80 token Jaccard at equal granularity,
R3 management/filter/execution variant) is inherited and remains the
gate any future NMAE proposal must clear, alongside §4's R4 (spent
component combination), R5 (protected-parent contamination) and R6
(unexecutable mechanism).

**Zero NMAE proposals were screened**, because §8 forbids defining
candidates before the precondition passes. `NMAE_V1_DERIVATIVE_SCREEN.csv`
therefore contains a header and no rows — an honest empty ledger, not a
fabricated one.
