# MROF-YT-OF-01.1 — SUCCESSOR FREEZE (H1 ZONES + WALL HOLD/FLUSH ENGINE)

Frozen and committed **before any outcome is computed or computable**.
Successor source prompt archived as `MROF_YT_OF01_1_SOURCE_PROMPT.md`
(SHA-256 `76624b8235982a48c4b0c2fc82468ce5c24ea685e3e0537598e2742899235e3c`);
its full text governs verbatim wherever this freeze does not narrow it.
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.

## 1. Predecessor immutability (binding)

The predecessor wave MROF-YT-OF-01 (commit `f99c521`) is **immutable**.
No outcome was ever opened under it (0 captured sessions), the recorder
remains unattached, and A1–A6, the level hierarchy, and the execution
rules are unchanged. Pinned predecessor hashes (verified by the
successor test suite on every run):

```
881d6df8e9acb8fb5c597e55cfc8646f0a9b4f0ceab35604697051299d18ae48  MROF_YT_OF01_WAVE_FREEZE.md
3c094d0280a7571aa1e7aed5fc59fa432722759bc8131d37115ee08bd03bc702  mrofyt_levels.py
06ce854a40717a2398231eb8c5120d8e709c18fd8f7cb8d1ac2cc4ecc640a8e1  mrofyt_signals.py
c1ce10249dff41f437c6a21b629305b8bc4ac0453d0087475dfb2ea6dfa10e34  tests_mrofyt.py
```

The new modules are **additive files** that the predecessor engine does
not import; disabling them (not calling them) reproduces the
predecessor bit-for-bit by construction, and the suite asserts the new
modules never monkey-patch predecessor functions. All predecessor
referent decisions (150 ms latency, 09:30–11:30 window, VWAP ± 2σ_w
bands, ADR `UNVERIFIED_CONTEXT`, `PSY_NQ_UNVERIFIED` on continuous
data, NQ-signal/MNQ-execution topology, Romano-Wolf α=0.05) carry
forward unchanged.

## 2. Data verdict — binding classification

Required raw data unchanged (trades + BBO + 10-level depth, plus
certified unadjusted front-contract hourly bars for the zone module).
Available: **0 sessions**. Classification:

**`INSUFFICIENT_DATA`**

No outcome, markout, probability fit, zone touch statistic, or P&L was
computed. The successor wave is FROZEN-AWAITING-DATA and runs exactly
as frozen when MROF State-C readiness passes.

## 3. What this revision adds (frozen by reference + narrowings)

**Nour Trades transcript transfer** (`4r_3DNeE8_U`, SHA-256 pinned in
the source): the eight accepted concepts enter only as the features
and modules below; every rejected transfer (stock share thresholds,
×100 display multipliers, same-participant inference from equal-size
prints, ECN/option logic, candle-volume-as-wall-fuel, wall-defined
levels, retrospective attempt selection) is enforced by tests.

**Causal one-hour supply/demand-zone context module** (context only,
never a seventh entry family): certified hourly bars from the 18:00 ET
session start; compact base = `TR_z ≤ 0.0` and `body_fraction ≤ 0.60`
(most recent ≤3, ≥1 required); displacement = `TR_z ≥ 2.0`,
`body_fraction ≥ 0.60`, close ≥1 tick beyond both the base extreme and
the prior five-bar swing (exact mirror for supply); zone bounds from
base wick/body extrema; available only at displacement close;
lifecycle FRESH → TOUCHED (independent touch = re-entry after a
retreat ≥ max(zone width, 4 ticks)) → INVALIDATED (completed hourly
close ≥1 tick beyond distal; intrabar breaches recorded separately) /
ROLLED_OFF (contract change; zones never cross rolls or come from
continuous prices). One `H1_SUPPLY_DEMAND` family vote regardless of
overlaps; excluded from both base clustering counts;
`h1_zone_experimental_present` reported separately. Event labels
evaluated CONFLICT-first, then ALIGNED / OPPOSING / NO_H1_ZONE.
`Available_R_H1` is a diagnostic; the base `Available_R` and 0.70R
gate remain primary. On the historical continuous 1m asset the module
is **`H1_ZONE_UNVERIFIED_CONTEXT`** (no contract identity) — it
certifies only on capture data.

**Key-level wall hold-versus-flush decision engine** (state/forecast
overlay, never a seventh entry family): wall = largest causally
standardized blocking-side display within 2 ticks of the active level,
`z ≥ 2.0`, tie to the nearer price, frozen per episode; event
accounting `initial + added − executed − nontrade_removed = remaining
+ error` with a frozen tolerance (breach ⇒ `UNCERTAIN_NO_TRADE`);
nine causal states (NO_QUALIFYING_WALL, WALL_OBSERVED, HOLD_ARMED,
HOLD_CONFIRMED→A1, FLUSH_ARMED_EXECUTION, FLUSH_ARMED_WITHDRAWAL→A3
timing, FLUSH_CONFIRMED→A2/A6, FAILED_FLUSH_RECLAIM→A4,
UNCERTAIN_NO_TRADE); armed states can never enter; confirmed states
fill only at the first executable quote after confirmation + latency,
never backdated. Probability snapshots at precontact and first
contact (contact = primary) for `P_FLUSH / P_HOLD_OR_RECLAIM /
P_UNRESOLVED` at 5s/10s/30s — plumbing and session-blocked empirical
baseline delivered now; any fitted model lives inside future training
folds and is charged to multiplicity. All probabilities are
shadow-only; A1–A4/A6 remain the sole entry authority. MBP wording is
enforced: `REFILLING_LIQUIDITY_ESTIMATE`, never iceberg/participant/
spoof labels.

**New frozen features (24–29)**: H1 zone state; wall episode state;
clearance dynamics `V_exec_w`, `V_all_w` (kept separate), right-
censored `T_clear_exec_w`, `WALL_BURDEN_10`, repeated-approach memory
(120 s, 2-tick retreat separation, never a same-participant claim);
`POST_CLEAR_RESERVE_5` (equal weights, unavailable before its 5 s
window completes, forbidden from precontact/contact forecasts);
futures-native `QUOTE_MIGRATION_SCORE` (event-sequenced buyer-led
up-steps vs seller-led down-steps plus concessions, exact long/short
mirror, one-tick spreads handled); adverse-large-print share
(`z ≥ 2.0` size only) and participant-neutral equal-size clustering.

**New ablations 19–28** frozen by reference (H1 context four-way,
H1 geometry, zone-vs-five-bar-swing baseline, wall-at-level vs
matched wall-off-level, probability model vs base rates vs
momentum baseline, L1 vs L1+L2, initial-size vs chipping dynamics,
first-cross vs 5 s acceptance, ± quote migration, B1/B2 large-print
diagnostic). Descriptive subgroups can never rescue a pooled parent.

## 4. Deliverables in this commit

- `mrofyt_h1zones.py` — hourly-bar certification, base/displacement
  detection, zone construction and lifecycle, context labeling,
  clustering extension, `Available_R_H1`.
- `mrofyt_wall_engine.py` — wall selection, episode accounting and
  reconciliation, clearance dynamics, state machine and A-family
  authorization map, quote-migration score, large-print/equal-size
  diagnostics, post-clear reserve, snapshot causality guards,
  empirical probability baseline, shadow-record formatter.
- `tests_mrofyt_v01_1.py` — the required deterministic suites for
  both modules (including the 12 zone proofs and 20 wall proofs from
  the source), predecessor-hash immutability, and no-monkey-patch
  checks.

## 5. Close-out (required form)

Classification: **`INSUFFICIENT_DATA`** — 0 sessions of required
event data. Nothing tested, nothing failed, nothing passed; the
registry row for this wave is `RESERVED_UNTOUCHED`. The single
advancing action remains attaching the MLES recorder.
