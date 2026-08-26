# OFH13-MEMORY-V1 — FEASIBILITY RECORD — INSUFFICIENT FOR INTERACTION STUDY

Date: 2026-08-26 (UTC)
Directive: OFH13 × MEMORY-PRED interaction study — PREREGISTRATION ONLY.
Status: **NO PREREGISTRATION WAS FROZEN.** The directive's Step 2
counts-only feasibility gate failed before the freeze point. This
document is the permanent record of the source audit, the candidate
definitions as they stood BEFORE any count was computed, the counts,
and the verdict.

**VERDICT: OFH13-MEMORY-V1 INSUFFICIENT FOR INTERACTION STUDY.**

No interaction outcome was computed. No P&L, MFE, MAE, win rate,
favorable-first, or any other outcome statistic was touched during
feasibility. No p-value was generated; the programme multiplicity
ledger (M_cum = 8) is unchanged. Nothing frozen was modified. OFH13 V1
remains byte-for-byte unchanged. SUBMITS NO ORDERS.
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

---

## 1. Source audit (Step 1) — completed before any count

All sources read-only. Frozen-hash verification performed 2026-08-26:

| Source | Role | Verification |
|---|---|---|
| `analysis/v41/cand_spec.py` | frozen OFH13 event generator | sha256 `9bea8f1cafc2b6ea…59fe07e7` matches `analysis/v41/FROZEN_HASHES.txt` (frozen 2026-08-21) |
| `analysis/v41/ofh6_spec.py` | OFH6 parent signal | sha256 `e8145b7c493029de…b9d4be1b` matches FROZEN_HASHES |
| `analysis/v41/cand_mgmt.py` | frozen stop/target scorer | `stop_dist()` ATR1.5 = 1.5·atr; race same-bar-both-touch → ambiguous |
| `analysis/v41/prospective.py` line 47 | frozen OFH13 management | `'stop': 'ATR1.5', 'target': None, 'time_exit_min': 60` |
| `analysis/v41/cand_audit.py` lines 87–128 | existing favorable-first convention | `path()` + `ffpct()` — see §2.3 |
| `docs/PROSPECTIVE_REGISTRY.md` | OFH13_PROSPECTIVE_V1 authority | 133 events, UNSEEN 16 / DEV 57 / IR 60; ff@1ATR 49.6; G1 per-parent-EV trap precedent |
| `docs/MEMORY_PRED_V1_FINDINGS.md` (sha256 `641a3d2a…`, commit `db0233a`) | frozen MEMORY-PRED-V1 result | LOW −0.03340 bp / MEDIUM +0.01547 (CI includes 0) / HIGH +0.26674; Δ +0.30013 bp; SUB-COST |
| `analysis/rvmr/rvmr_spec.py`, `analysis/rvmr/rvmr_run.py` | frozen RVMR-V1 spec + canonical 1m loader | T1 1.270 / T2 2.335 / W 1440; STAMP_SHIFT 0, close-stamped |

Neither OFH13 nor MEMORY-PRED was reconstructed from the directive
text; both were taken verbatim from the frozen sources above, per the
directive's "Do NOT reconstruct either object from this prompt".

Stamp-convention audit: the order-flow grid is close-stamped
(`f_barCloseEt`, `cand_spec.py` line 92) and the rvmr 1m grid is
close-stamped (STAMP_SHIFT 0). Entry-bar mapping is therefore the
identity on the timestamp string — no shift, no interpolation.

Frozen reproduction check (run before counts): `load_merged()` +
`generate()` reproduce OFH13 exactly — 133 events, 16/57/60, 355,455
OF bars, 952 OFH6 parents. EXACT.

## 2. Candidate definitions as recorded BEFORE any count existed

These were drafted at audit time so that a failed feasibility could
never be quietly re-specified. They are recorded here for any future
V2; they were never frozen as a preregistration.

### 2.1 Causal MEMORY signal at OFH13 entry

Entry bar close time `e['et']` maps to rvmr index `t` with
`et[t] == e['et']`. Requires `em[t] − em[t−1] == 1` (frozen
contiguity clock; gaps are skipped, never bridged).

- `r[t] = log(c[t]/c[t−1])` — last completed 1m return at entry.
- `RB[t] = bucket(trailing_ratio(range)[t])` — numerator `rng[t]`
  and denominator window `t−1440..t−1` are all known at the close of
  bar t. Causal at entry.
- HIGH → predict `sign(r[t])` (continuation). LOW → predict
  `−sign(r[t])` (reversal). MEDIUM → **NEUTRAL**: the frozen
  MEMORY-PRED MEDIUM cell is +0.01547 bp with CI including 0 — the
  frozen source establishes no directional meaning for MEDIUM, and per
  the directive none was invented.
- `r[t] == 0` → NEUTRAL-zero. Missing grid bar / broken contiguity /
  unavailable state → NEUTRAL-unavailable.

**Causality note (declared, not discovered):** the frozen MEMORY-PRED
primary conditions on `RB[t] == RB[t+1]`; `RB[t+1]` requires bar
t+1's range, which does not exist at entry. The only deployable causal
signal is `RB[t]` alone. Any state-stability stratification could only
ever have been descriptive/non-promotable.

### 2.2 Interaction classes

ALIGNED = MEMORY-predicted direction equals OFH13 direction `d`;
OPPOSED = equals `−d`; all NEUTRAL-* excluded from the primary
contrast. Primary comparison: ALIGNED minus OPPOSED.

### 2.3 Intended primary endpoint (repository-consistent, chosen before counts)

The existing OFH13 favorable-first object, exactly as implemented in
`cand_audit.py`: per event over bars entry+1..entry+60,
`ff[1.0] = 1` if favorable excursion reaches 1.0·ATR before adverse
reaches 1.0·ATR, `2` if adverse first, `3` if both on the same bar
(excluded), `0` if neither (excluded); `ffpct = 100·f/(f+a)`
(registry baseline ff@1ATR = 49.6). Primary statistic would have been
mean FF-indicator(ALIGNED) − mean FF-indicator(OPPOSED), day-cluster
bootstrap 20,000, seed 20260826.

### 2.4 Binding rules that would have applied

- Expectancy per ORIGINAL parent (denominator 133, the G1 trap rule).
- Winner preservation: top-1/5/10 winner retention and winner-P&L
  retention ≥ trade retention.
- Controls: A state-only, B last-return-sign-only (essential),
  C day-respecting stratified label permutation.
- ABSOLUTE WIN-RATE RULE: a win-rate rise alone never promotes.
- Sample floors, drafted at audit time and BEFORE any count was run:
  **ALIGNED ≥ 20, OPPOSED ≥ 20, ≥ 15 unique days in each directional
  arm.** A day-clustered two-arm bootstrap below these floors is not
  interpretable.

## 3. Counts-only feasibility (Step 2) — result

Engine: `analysis/ofh13mem/feas_counts.py`; output:
`analysis/ofh13mem/FEAS_COUNTS_OUTPUT.txt`. Counts only — the script
computes no outcome of any kind.

```
TOTAL OFH13 events                  133   (LONG 55 / SHORT 78)
MEMORY-AVAILABLE                    130
  no rvmr bar at entry stamp          3   (entries 2026-08-18/19,
                                           past rvmr grid end 2026-08-17)
RB[t] among available:  LOW 12   MEDIUM 68   HIGH 50

ALIGNED                              10   unique days  10
OPPOSED                              52   unique days  48
NEUTRAL-medium                       68   unique days  61
NEUTRAL-zero                          0
NEUTRAL-unavailable                   3

CLASS x SIDE      ALIGNED  L 5 / S 5    OPPOSED  L 16 / S 36
CLASS x PARTITION ALIGNED  U 1 / D 3 / I 6
                  OPPOSED  U 9 / D 26 / I 17
STATE x PARTITION LOW  U 0 / D 4 / I 8    HIGH  U 10 / D 25 / I 15
```

## 4. Floor test and verdict

| Floor (set before counts) | Observed | Result |
|---|---|---|
| ALIGNED ≥ 20 | 10 | **FAIL** |
| OPPOSED ≥ 20 | 52 | pass |
| ALIGNED unique days ≥ 15 | 10 | **FAIL** |
| OPPOSED unique days ≥ 15 | 48 | pass |

**OFH13-MEMORY-V1 INSUFFICIENT FOR INTERACTION STUDY.** The ALIGNED
arm holds 10 events on 10 days — roughly one-third of the weakest
defensible floor, and 7.5% of the parent population. No choice of
endpoint, control, or inference machinery rescues a 10-event arm; the
study was therefore stopped BEFORE the preregistration freeze, before
any outcome was computed, and before any multiplicity was consumed.

### Why the ALIGNED arm is structurally starved (visible from counts alone)

OFH13 enters at the completed close of a mitigation bar — a pullback
into the FVG zone against the intended trade direction, confirmed by
opposing-side flow. The last 1-minute return at entry therefore tends
to point AGAINST the trade. 50 of the 62 directional-state entries sit
in RVMR HIGH, where MEMORY predicts continuation of that last return —
i.e. against the trade. Hence OPPOSED 52 vs ALIGNED 10 is not a sample
accident; it is the entry mechanism itself. At the OFH13 entry bar,
the causal MEMORY signal is largely a re-description of the pullback
that the entry logic already requires. A meaningful ALIGNED population
would require either LOW-state entries (n = 12 total) or entries where
the mitigation bar itself closed back in the trade direction — both
rare by construction.

## 5. What happens next

- **No overlay exists.** Nothing is shadow-logged; there is no
  prospective arm to start. OFH13_PROSPECTIVE_V1 continues exactly as
  frozen.
- **Accrual path:** ALIGNED accrued ~10 events per 12 months of
  capture. Reaching the n ≥ 20 / ≥ 15-day floors requires on the order
  of one to two additional years of order-flow capture. If revisited
  then, it must be a NEW preregistration (V2) against the definitions
  recorded in §2 — the directive's no-variant rule applies: this
  failure does not authorize same-window redesigns.
- The MEMORY-PRED-V1 Lane A prospective plan (start 2026-08-26
  00:00:00 ET) is untouched by this record.

## 6. Reproduction

- `analysis/ofh13mem/feas_counts.py` — deterministic, no RNG used.
- `analysis/ofh13mem/FEAS_COUNTS_OUTPUT.txt` — full counts output.
- Verified 2026-08-26: prereg-registry OFH13 reproduction EXACT
  (133 = 16/57/60); frozen source hashes match FROZEN_HASHES.txt.
