# RVMR-AVOID-V1 — PRE-REGISTRATION (FROZEN BEFORE RESULTS)

Committed before any state-split outcome of this study was computed.
Motivating leads (rejected-gap fade −9.91 in R-HIGH, p≈0.033; mean
reversion −5.7 HIGH vs +0.4 LOW) came from RVMR-STRAT-V1 and are
**motivation only — the gap-fade and session-extreme numbers were seen
there, so those two families cannot count as independent confirmation;
they are labelled MOTIVATING. The other families are the test.**
Nothing frozen is modified; no avoidance filter touches any live or
prospective system; every survivor is EXPLORATORY-DERIVED.

## Source of truth (read + hashed)

| file | sha256(16) | supplies |
|---|---|---|
| `analysis/rvmr/rvmr_spec.py` | `e348f035a9209540` | frozen RVMR-V1 |
| `analysis/rvmr/rvmr_prospective.py` | `7397ad3d4edeb2de` | certified states + parity |
| `analysis/rvmr_strat/tb_run.py` | `0eb0d0c92a874cc4` | 5y detectors: gap fade, VWAP reversion, level sweep-reclaim; uniform frame |
| `analysis/rvmr_strat/ta_run.py` | `5144910dc273d362` | canonical-year harvest + rich frame |
| `analysis/v41/mrv_run.py` | `497427a8261c8cf8` | mr_h2, v_h1 |
| `analysis/mag/mag_run.py` | `7024f7ccf2feb593` | mag_dir_h2, ovn h4 |

## First gate

`rvmr_prospective.py parity` re-run for this study; required 0/0/0.
Fail ⇒ `RVMR-AVOID-V1 FAIL — RVMR PARITY NOT ESTABLISHED`.

## Counter-movement definition (mechanical)

A family qualifies only if the entry trades **against a causally
measured directional move known at entry**. Registry, **M = 7 (Range
family; the Volume analysis over the same seven is the declared
secondary)** — frozen now:

| id | family | source (verbatim) | data | what is faded / how measured |
|---|---|---|---|---|
| F1 | rejected-gap fade | `tb_run.gap_events()` rej | 5y | the opening gap, \|open−priorClose\| ≥ 0.5 ATR, known at 09:44 decision — **MOTIVATING** (seen in STRAT-V1) |
| F2 | VWAP extension reversion | `tb_run.meanrev_events()` | 5y | distance to session VWAP ≥ 1.5 ATR at entry bar |
| F3 | session-extreme reversion | `mrv_run.mr_h2` | canonical yr | excursion beyond session extreme — **MOTIVATING** (A7 in STRAT-V1) |
| F4 | V-recovery after flush | `mrv_run.v_h1(FAST)` | canonical yr | the directional flush (`flushes()` dist), entry with 50% recovery against it |
| F5 | overnight sweep→reclaim | `mag_run.ovn_family h4 FULL_SWEEP_RECLAIM` | canonical yr | the sweep beyond the frozen ON extreme |
| F6 | failed-breakout return | `mag_run.mag_dir_h2 C_REENTRY_ANY` | canonical yr | the balance breakout being faded after re-entry |
| F7 | level sweep→reclaim | `tb_run.reclaim_events()` | 5y | the sweep beyond {ON H/L, PDH/L, PWH/L, OR15} (canonical-yr `mr_h3 RECLAIM` reported as replication echo) |

**Considered and EXCLUDED:** opening-drive failure (`mag OPEN-H2`,
n = 40) — canonical but cannot support a three-state split; declared
INSUFFICIENT DATA in advance rather than registered as a
guaranteed-uninformative slot. OFH13/OFH14 are **not**
counter-movement under this definition (they enter on FVG mitigation
in the direction of the originating signal) and are excluded; nothing
here touches OFH13_PROSPECTIVE_V1.

Every family is scored exactly as canonically registered — the
uniform frozen frame those studies used (1.5 ATR stop, no target,
60-min exit, 0.87 pt cost). Entries, directions, sessions untouched.
The only new variable is the RVMR state available at the decision-bar
close.

## Frozen statistics

- Primary per family: **Δ = EV(R-HIGH) − EV(R-LOW ∪ R-MED)**, two-sided
  day-clustered bootstrap p (20,000 day resamples). **BH at M = 7.**
- Pooled headline: same Δ over all seven families' events concatenated,
  day-clustered (one test, reported beside the family).
- Secondary: identical battery on VOLUME states, BH at M = 7, reported
  separately; Range and Volume are never combined.
- Avoidance economics: baseline vs **AVOID-HIGH** (drop R-HIGH events):
  per-**original**-opportunity EV, loser P&L avoided, winner P&L
  sacrificed, saved/sacrificed ratio, PF, top-10-winner retention,
  top-5% winner P&L retention, largest removed winner.
- Controls (mandatory): ATR terciles within family; time-of-day windows
  {09:30–10:30, 10:30–12:00, 12:00–13:30, 13:30–15:00}; Δ recomputed
  within strata, count-weighted.
- Extension buckets: uniform causal EXT = \|close(entry) −
  close(entry−15)\|/ATR, family terciles; states compared within
  buckets (diagnostic).
- Efficiency (diagnostic): frozen `mag_lib` EFF (5-bar net/path,
  terciles 0.119/0.264) splitting R-HIGH fades.
- Transitions (diagnostic): prior-state→state EV table, pooled.
- Temporal: per-year (5y families) / U-DEV-IR (canonical-year).
- Geometry grid: median/mean/p75/p90 MAE and MFE (ATR units), MFE/MAE,
  ff at ±0.25 and ±1.0 ATR (AMBIGUOUS never guessed), P(+xR before
  stop-hit) for x ∈ {0.5, 1, 2, 3} (5y frame) and {0.25…5} (canonical
  frame), stop-hit %, time-to-adverse diagnostics on the 5y frame.

## Promotion gate — the twelve declared conditions, all printed

Material HIGH deterioration; visible in raw geometry; worse
favourable-first; removes more losing than winning P&L;
per-original-opportunity EV improves; top winners preserved; effect in
**multiple independent** (non-MOTIVATING) families; temporal
stability; survives ATR and ToD controls; incremental beyond generic
volatility; adequate sample; not one-tail-event driven.

## Declared failure case

If HIGH inflates MFE and MAE symmetrically and avoidance sacrifices as
much winner as loser P&L: **"RVMR HIGH INDICATES MORE MOVEMENT, NOT BAD
FADE QUALITY — NO AVOIDANCE RULE."** No entry/stop/target/sizing
rescue of any kind; the only decision under study is trade vs avoid.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
