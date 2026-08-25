# XMARKET-V1 — PRE-REGISTRATION (FROZEN BEFORE ANY ES DATA EXISTS)

**Status: FROZEN, NOT RUN.** The data audit (below) found **zero ES/MES
bars** in this project. Per the directive's critical data rule the
backtest was not started and nothing was synthesized.

This document is committed anyway, and that is the point: every rule
below is frozen at a moment when **not a single ES bar has ever been
observed by anyone on this project.** When synchronized ES history
arrives, the study runs against a specification written in provable
ignorance of the data. That is the strongest pre-registration this
programme has ever been able to make.

Nothing frozen is modified. No live/prospective system may use
XMARKET-V1. Every future survivor is EXPLORATORY-DERIVED.

---

# 1. NQ data audit (what exists)

| item | status |
|---|---|
| NQ/MNQ 1m OHLCV | **MULTI-YEAR AVAILABLE** — 2,503,622 bars, 2019-07-04 → 2026-08-17, 0 duplicate stamps, strictly monotonic (`scratchpad/rvmr_1m`, Phase-0 audited) |
| NQ order flow (bid/ask vol, delta, imbalance) | **AVAILABLE (limited)** — 355,455 bars, 2025-08-18 → 2026-08-19 |
| NQ 30s | AVAILABLE (partial) — 192 days ph2 + 70 days capture |
| NQ 15s / 5s | AVAILABLE (partial) — 70 days, 2026-06-02 → 2026-08-21 |
| session / timezone | close-stamped ET, RTH 09:30–16:00 (`V4SessionMap` 570/960), DST-consistent |
| contract | MNQ, continuous; roll behaviour audited — largest session-reopen jumps are weekend gaps, not rolls |

# 2. ES data audit — **NONE**

Searched exhaustively: all 46 scratchpad data directories, 268 uploaded
archives, and the repository source.

- **Filenames:** zero matches for ES / MES / SPX / SP500 / emini.
- **Instrument fields:** every dataset carrying an instrument column
  reports `MNQ` (or `MNQ SEP26`). No other instrument appears anywhere.
- **Price-range sweep** (decisive — ES trades ~2,000–7,000, NQ
  ~10,000–31,000): every file in every directory has closes in
  **10,948 – 31,052**. No file is in ES territory.
- **Repository:** no ES/MES instrument reference in `src/`, `analysis/`
  or `docs/`.

**Verdict: INSUFFICIENT DATA.** Not "limited" — *absent*.

*(Note: `scratchpad/synthdrop/` contains a file explicitly named
`..._SYNTH.csv`. It is MNQ, it is synthetic, and it is not a substitute
for anything. The directive forbids synthesized ES, SPY/QQQ
substitution, and inferring order flow from OHLCV; none was used.)*

# 3. Synchronized overlap audit

| | |
|---|---|
| eligible NQ timestamps | 2,503,622 |
| eligible ES timestamps | **0** |
| matched timestamps | **0** |
| overlap window | **none** |

# 4–5. Contract/roll and timestamp/causality audits

Not performable — they are two-market audits and only one market exists.
The NQ-side facts they will be run against are recorded in §1. Both
audits are **required gates before any hypothesis runs** (§8).

---

# 6. FROZEN NORMALIZATION

Never compare raw points. Each market is normalized by **its own**
volatility.

```
ATR_X(t)      = SMA(20) of True Range on market X, ending at bar t
                (the definition Phase-0 verified exact, and the one
                 RVMR-V1 already uses)
Z_X(t, w)     = (close_X(t) - close_X(t-w)) / ATR_X(t)
PRIMARY w     = 5 minutes
REL_STRENGTH(t) = Z_NQ(t,5) - Z_ES(t,5)
```

**Exactly one declared diagnostic alternative:** `ZV_X(t,w)` using
causal realized volatility — stdev of the last 20 one-minute returns —
in place of ATR. Reported for robustness only; never the primary. No
optimized weights, no third variant.

# 7. FROZEN CLASSIFICATIONS (price-based, no delta)

```
ES STATE at NQ decision bar t, for NQ direction d ∈ {+1,-1}:
  CONFIRMING  sign(Z_ES(t,5)) == d  AND |Z_ES(t,5)| >= 0.5
  OPPOSING    sign(Z_ES(t,5)) == -d AND |Z_ES(t,5)| >= 0.5
  NEUTRAL     otherwise

ES BALANCE   30-bar high/low envelope of ES (identical construction to
             the frozen NQ balance, mag_lib.balance)
ES ACCEPTANCE 2 consecutive completed ES closes beyond its own edge
             (identical rule to the frozen NQ acceptance)

LEADERSHIP at t:
  NQ-LEADS  |Z_NQ(t,5)| >= 1.0  AND  |Z_ES(t,5)| <= 0.5
  ES-LEADS  |Z_ES(t,5)| >= 1.0  AND  |Z_NQ(t,5)| <= 0.5
CATCH-UP window: bars t+1..t+3 (PRIMARY). Declared secondary windows:
  1 and 5 bars — reported, never promoted. No other window is tested.
  CATCH-UP occurs if, for some k ≤ 3, sign(Z_lag(t+k,3)) == d and
  |Z_lag(t+k,3)| >= 0.5.  REFUSAL = no catch-up within the window.

DIVERGENCE buckets: terciles of |REL_STRENGTH| computed on the FIRST
  FULL YEAR of overlap ONLY, then applied unchanged to all later data
  (causal; no look-ahead; never recalibrated per era).
```

# 8. GATES THAT MUST PASS BEFORE ANY HYPOTHESIS RUNS

1. **Synchronization gate** — deterministic NQ↔ES matching on identical
   close-stamped ET minutes. Report matched / missing-NQ / missing-ES /
   duplicates / **max clock discrepancy, which must be 0** (exact minute
   equality; no fuzzy joining).
2. **Roll gate** — pre/post-roll diagnostics for *both* markets. Any bar
   within ±1 session of **either** market's roll is excluded from
   REL_STRENGTH and leadership events, so a roll discontinuity can never
   manufacture divergence, lead/lag, or confirmation.
3. **Causality gate** — `ES_available_time <= NQ_decision_time`, with
   equality permitted only when both bars complete on the same minute
   boundary. A bar is used only once complete. No same-bar ES high/low
   or future ES reaction may justify an earlier NQ entry.
4. **Resolution honesty** — at 1m data, no sub-minute lead/lag claim of
   any kind is permitted. Sub-minute leadership requires synchronized
   5s/15s data and is a separate future study.

If any gate fails: **STOP**, report the failure, run nothing.

---

# THE EIGHT HYPOTHESES — M = 8, frozen, no H9

Direction always comes from **NQ price structure**; ES never triggers a
trade by itself. NQ constructs are reused verbatim from frozen sources
(`mag_lib.balance`, the 2-close acceptance, `tb_run` detectors) — no new
optimized NQ breakout is created. Uniform frozen measurement frame
throughout: **1.5 × ATR_NQ stop, no target, 60-min time exit, 0.87 pt
cost**, identical across all arms so it cannot create an interaction.

**XMK-H1 — NQ breakout + ES confirmation.** Frozen NQ accepted
breakout; classify ES at the same causal bar. Arms: NQ alone ·
+CONFIRMING · +NEUTRAL · +OPPOSING. *Primary comparison: CONFIRMING vs
NQ-alone.*

**XMK-H2 — NQ breakout + ES refusal + NQ failure.** NQ breaks, ES does
not confirm, **and NQ itself then loses acceptance** (close back inside
within 5 bars) → reversal geometry. ES refusal alone never triggers.
Compared against NQ failed-breakout alone.

**XMK-H3 — NQ leads → ES catch-up.** NQ-LEADS parent; ES catches up
within 3 bars; measure subsequent NQ continuation. Compared against
NQ-LEADS with no ES condition.

**XMK-H4 — NQ leads → ES refusal.** Same parent, ES refuses. Split by
NQ's own state: (A) NQ stays price-efficient, (B) NQ efficiency
deteriorates, (C) NQ loses acceptance. Primary: **refusal + (B or C)** →
NQ mean reversion. Refusal alone never triggers.

**XMK-H5 — relative-strength extreme.** |REL_STRENGTH| buckets →
classify first resolution within 30 bars: divergence continues /
converges via NQ / converges via ES / both reverse / unresolved. An
information study first; becomes a trade only if geometry supports it.

**XMK-H6 — ES leads → NQ catch-up.** Mirror of H3. Directly answers
whether ES→NQ leadership is more informative than NQ→ES.

**XMK-H7 — cross-market acceptance agreement.** NQ accepts beyond its
balance **and** ES accepts beyond its own, same direction, same causal
bar. Arms: NQ-only · ES-only · both · disagreement. *Primary: both vs
NQ-only.*

**XMK-H8 — disagreement resolution.** NQ beyond its balance while ES
inside its own (or the mirror). Observe the **first** resolution over 10
bars → A) ES joins NQ, B) NQ returns toward ES, C) both reverse, D)
persists. Question: does the *manner of resolution* predict NQ better
than the initial disagreement?

---

# ANALYSIS PLAN (frozen)

**Raw geometry first** — N, frequency, returns at 5/10/15/30/60m,
median, MFE, MAE, MFE/MAE, absolute movement. **Favourable-first** at
±0.25, ±0.5, ±1.0, +1.5/−1.0, +2.0/−1.0 ATR, with **AMBIGUOUS never
guessed**.

**Matched controls (mandatory)** — every hypothesis compared against
NQ-equivalent events matched/controlled on NQ ATR, time of day, NQ
recent return, NQ recent range, NQ volume, RVMR state, direction, and
year. *The central question: does ES add information beyond what NQ
already showed?*

**Incremental-information test** — every survivor compared against
NQ-only momentum, NQ-only acceptance, NQ-only path efficiency, NQ RVMR
context, time of day, ATR. If ES merely restates NQ momentum →
**NO INCREMENTAL VALUE**.

**RVMR** is a *predeclared diagnostic only*. Results are reported by
LOW/MEDIUM/HIGH after the primary analysis. **No hypothesis may survive
because one RVMR slice looked good**; the cross-market edge must exist
independently first.

**Order-flow track** — only if synchronized ES *and* NQ order flow both
exist; strictly SECONDARY and outside M=8; the longer OHLCV price result
takes precedence over any short order-flow window.

Reported throughout: long/short separately, NQ-leads/ES-leads
separately, year-by-year with sign inversions flagged, month stability,
volatility era, broad time-of-day windows (no narrow-time optimization),
and tail analysis (largest winner/loser, top 1%, top 5%, mean excluding
top 1%, median, plus a **drop-top-5% destruction test**).

**Statistics** — raw p, day-clustered bootstrap CI, sign-flip/permutation
p, **BH at M = 8**, family-wise (Holm) alongside. Promotion never on q
alone.

**Promotion gate — all fourteen printed explicitly:** positive economic
directional geometry · adequate N · matched-control advantage · **ES
adds incremental information beyond NQ-only variables** · MFE/MAE
improves · favourable-first improves · credible median · year/partition
stability · long/short not catastrophically asymmetric without
explanation · low/moderate tail dependence · no roll artifact · no
synchronization artifact · no time-of-day construction artifact ·
plausible costs/slippage.

# Prohibitions (binding)

No management rescue (no stop/target/trailing/breakeven/size
optimization before raw geometry survives). No machine learning of any
kind. No new optimized NQ breakout definition. No synthesized,
interpolated, or substituted ES. No sub-minute claims at 1m resolution.
No searching additional ES filters to rescue a failed result — **a clean
failure is the declared valid outcome**, reported as: *ES DOES NOT ADD
MATERIAL INCREMENTAL INFORMATION TO NQ AT THIS RESOLUTION.*

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
