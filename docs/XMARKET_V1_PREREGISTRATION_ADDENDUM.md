# XMARKET-V1 — PRE-REGISTRATION ADDENDUM

**Purpose.** The frozen pre-registration
(`docs/XMARKET_V1_PREREGISTRATION.md`, commit
`36aaa28378dbaa359e011579ae3dc96f5e2418e7`, sha256
`314262cbfe3782f07ac81c795f01dc553382fa5d11ef1f6cf14cfd3bebb8c786`)
names four constructs conceptually but leaves them numerically
incomplete. This addendum records the exact numeric forms **already
implemented**, verbatim and unaltered, so that provenance is explicit
before any performance result for the affected hypotheses is read.

**This addendum changes nothing.** It transcribes what
`analysis/xmarket/xmk_lib.py` and `analysis/xmarket/xmk_run.py` already
contain. No threshold, window, control, normalization, acceptance rule,
matching variable, cost, evaluation frame or hypothesis definition is
modified. **M remains 8.**

---

## 1. RESULT-BLINDNESS AUDIT

The numeric definitions below were written into source and committed at
`0910732` **before any run produced a single hypothesis result.** The
first execution attempt was terminated during the universe build, having
printed only the header and bar counts.

| question | answer |
|---|---|
| **H4 RESULT SEEN BEFORE FREEZE?** | **NO** |
| **H5 RESULT SEEN BEFORE FREEZE?** | **NO** |
| **H8 RESULT SEEN BEFORE FREEZE?** | **NO** |

For H4, H5 and H8, **no** P&L, mean return, median, MFE, MAE, MFE/MAE,
favourable-first, p-value, q-value, year breakdown, era breakdown,
time-of-day breakdown, RVMR slice, tail table or matched-control result
was visible at any point. The second run was terminated while writing;
its output reached 355 lines, but the highest line ever read was **140**,
and the H4 section begins at line **179**. H4, H5, H6, H7 and H8 results
were never displayed. The only inspection performed after termination
was a `grep` of section-header text, which returned no numbers.

**Therefore H4, H5 and H8 remain PRE-REGISTERED.** No
`EXPLORATORY-DERIVED` designation is triggered.

### Full disclosure on the fourth construct

The catch-up entry-timing choice (§5 below) governs **H3, H4 and H6**.
H4 and H6 results were never seen. **H3 results WERE seen** — its arm
geometry and primary comparison — before this document was created,
though after the timing choice was frozen in source and committed, and
the choice is transcribed here unchanged.

H1 and H2 results were also seen. Both are defined entirely by the
original frozen pre-registration and are unaffected by this addendum.

This is recorded permanently rather than tidied away. Nothing here is
altered in response to anything observed.

---

## 2. H4 — NQ PATH EFFICIENCY (frozen numeric form)

Source: `xmk_lib.py`, `Universe.__init__`, `EFF_W = 5`.

```
eff(t) = |c(t) - c(t-5)|  /  SUM_{i = t-4 .. t} |c(i) - c(i-1)|
```

**Exact indexing.** The numerator spans 5 minutes, `c(t-5) -> c(t)`. The
denominator sums the **five** one-minute increments covering that same
span: `i` runs `t-4` through `t` inclusive, each term `|c(i) - c(i-1)|`,
so the first term is `|c(t-4) - c(t-5)|` and the last is
`|c(t) - c(t-1)|`. Numerator and denominator therefore cover an
identical interval, and `eff` is bounded in `[0, 1]`.

**Causality.** Only completed bars are used. `eff(t)` requires the five
minutes to be genuinely consecutive: `em(t) - em(t-5) == 5` on the NQ
epoch-minute clock. A session boundary or data hole leaves `eff`
undefined; nothing is bridged or interpolated.

**Epsilon handling.** There is no epsilon. The guard is a strict
`den > 0`; if the denominator is exactly zero (five identical closes)
`eff` is set to `None` — **undefined**, not zero and not one. An event
whose `eff(t)` or `eff(t+3)` is `None` is classified `UNDEFINED` and
**dropped from every H4 arm**, including the control.

**The A / B / C split**, evaluated at the entry bar `t+3`:

| state | rule |
|---|---|
| **C — LOST ACCEPTANCE** | NQ closes back inside its 30-bar balance measured at `t`, at any of `t+1, t+2, t+3` |
| **B — DETERIORATES** | not C, and `eff(t+3) < eff(t)` |
| **A — EFFICIENT** | not C, and `eff(t+3) >= eff(t)` |

**C is tested first and wins ties.** The PRIMARY arm is
`refusal AND (B OR C)`, traded in the mean-reversion direction `-d`, as
the original pre-registration specifies. Refusal alone never triggers.

---

## 3. H5 — RELATIVE-STRENGTH RESOLUTION (frozen numeric form)

Source: `xmk_run.H5`, `H5_CONVERGE = 0.5`, `H5_WIDEN = 1.5`,
`H5_WINDOW = 30`.

Let `v = |RS(t)|` where `RS(t) = Z_NQ(t,5) - Z_ES(t,5)` is the frozen
relative-strength measure from the original pre-registration §6.

Scanning `k = 1 .. 30` and taking the **first** condition met:

| outcome | rule |
|---|---|
| **CONVERGED** | `\|RS(t+k)\| <= 0.5 * v` |
| **WIDENED** | `\|RS(t+k)\| >= 1.5 * v` |
| **UNRESOLVED** | neither occurs within 30 bars |

**Mathematical interpretation.** The thresholds are **multiplicative on
the event's own initial divergence**, not absolute levels. A divergence
resolves when it has halved, and widens when it has grown by half again.
Both are therefore scale-free in `v` and inherit the ATR normalization of
`Z`, so no raw-point comparison occurs anywhere.

**Causality.** The scan stops at a session boundary or data hole
(`em(t+k) - em(t) != k`), leaving the event `UNRESOLVED`. `RS(t+k)`
values that are undefined are skipped without advancing the outcome.

**Convergence attribution.** At the resolving bar `kk`, each market's
move is measured **in its own ATR units**:

```
dn = |c_NQ(t+kk) - c_NQ(t)| / ATR_NQ(t)
de = |c_ES(t+kk) - c_ES(t)| / ATR_ES(t)
CONVERGED_VIA_NQ  if dn >= de   else  CONVERGED_VIA_ES
```

**Epsilon handling.** The implementation guards a missing or zero ATR
with `(ATR or 1e9)`, which drives that market's normalized move to
approximately zero rather than raising; and a missing ES close sets
`de = 0.0`. Both guards are recorded here as implemented. Ties
(`dn == de`) are attributed to NQ.

Buckets `LOW / MID / HIGH` are terciles of `|RS|` calibrated on the
**first full year of overlap only** and then applied unchanged, exactly
as the original pre-registration requires.

---

## 4. H8 — "BEYOND BALANCE" (frozen numeric form)

Source: `xmk_run.es_beyond`, `xmk_run.H8`, `H8_WINDOW = 10`.

**BEYOND = ONE completed close beyond the causal balance boundary.**

```
beyond(market, t) = +1 if close(t) > balance_high(t)
                    -1 if close(t) < balance_low(t)
                     0 otherwise
```

where `balance` is the same causal 30-bar high/low envelope used
everywhere in this study, computed on each market's **own** timeline and
voided by any gap in that market's own bars.

**This is deliberately weaker than H7's ACCEPTANCE rule**, which
requires **two** consecutive completed closes beyond the edge. The
distinction is the point of the two hypotheses: H7 tests agreement of
*accepted* auction structure, H8 tests resolution of *provisional*
disagreement.

A disagreement event at `t` requires NQ beyond its own envelope in
direction `d` while ES is **not** beyond its own envelope in that same
direction (ES inside, or ES beyond the opposite edge).

Resolution scans `k = 1 .. 10`, first match wins:

| outcome | rule |
|---|---|
| **ES_JOINS_NQ** | ES beyond its own edge in direction `d` |
| **BOTH_REVERSE** | NQ back inside its envelope **and** ES beyond the opposite edge |
| **NQ_RETURNS_TO_ES** | NQ back inside its envelope |
| **PERSISTS** | none of the above within 10 bars; entry anchored at `t+10` |

Forward geometry is measured from the **resolution bar** and signed by
the original NQ direction `d`, so a negative mean means NQ reverted.

---

## 5. CATCH-UP TIMING (frozen, governs H3 / H4 / H6)

Source: `xmk_run.lead_family`, `xmk_run.H4`, `CATCHUP_BARS = 3`.

Catch-up is decided over `t+1 .. t+3`, so the earliest fully causal
decision point is `t+3`. **Every arm of H3, H4 and H6 — including the
no-ES-condition control — is entered at `t+3`.** Signal and control
therefore share an identical entry lag, and the comparison cannot be a
timing artifact.

Declared secondary windows **1 and 5** are reported for robustness and
**may never be promoted**, exactly as the original pre-registration
states. No other window is tested.

---

## 6. WHAT IS *NOT* CHANGED

Unchanged and taken verbatim from the original frozen document:
`Z_X(t,w)` and `REL_STRENGTH`; the primary `w = 5`; CONFIRMING /
OPPOSING / NEUTRAL at `|Z_ES| >= 0.5`; NQ-LEADS / ES-LEADS at
`1.0 / 0.5`; catch-up at `|Z_lag(t+k,3)| >= 0.5`; the 30-bar balance;
the two-close acceptance rule; the NQ accepted-breakout detector reused
from `tb_run.accept_events`; the uniform frame of 1.5 × ATR_NQ stop, no
target, 60-minute time exit and 0.87 pt cost; the favourable-first
ladder with AMBIGUOUS never guessed; the matched-control variable set;
BH and Holm at **M = 8**; and the fourteen promotion conditions.

**M IS NOT SHRUNK FOR VOID OR FAILING HYPOTHESES.**

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
