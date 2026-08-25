# RVMR-STRAT-V1 — PRE-REGISTRATION (FROZEN BEFORE RESULTS)

Committed before any strategy × regime outcome was computed. RVMR-V1,
OFH13_PROSPECTIVE_V1, prospective.py, the NT8 engine, and the RVMR
forward logger are not modified. Every discovery here is
**EXPLORATORY-DERIVED** (spent history). No new prospective RVMR
outcome is used for discovery.

## Source of truth (read + hashed, never reconstructed from prompt)

| file | sha256(16) | supplies |
|---|---|---|
| `analysis/rvmr/rvmr_spec.py` | `e348f035a9209540` | frozen RVMR-V1 (thresholds 1.270/2.335 from source) |
| `analysis/rvmr/rvmr_prospective.py` | `7397ad3d4edeb2de` | certified state pipeline |
| `analysis/v41/cand_spec.py` | `9bea8f1cafc2b6ea` | OFH13/OFH14/G4/G3/G1 |
| `analysis/v41/prospective.py` | `240189f3d4179198` | frozen management registry |
| `analysis/v41/mrv_run.py` | `497427a8261c8cf8` | mr_h2, mr_h3(RECLAIM), v_h1 |
| `analysis/v41/pro_run.py` | `7b6ed1447f3bcc54` | (reference) |
| `analysis/mag/mag_run.py` | `7024f7ccf2feb593` | balance/accept/reject, ovn, open families |
| `analysis/mag/mag_lib.py` | `c1b2a961cb2cd464` | balance()/acceptance frozen defs |
| `analysis/v41/red_lib.py` | `87bcf35674e3534c` | swings, levels, entry_ok |

## First gate

`rvmr_prospective.py parity` re-run for this study. Required: 0 range,
0 volume, 0 timestamp mismatches. Fail ⇒ stop with
`RVMR-STRAT-V1 FAIL — RVMR PARITY NOT ESTABLISHED`.

## RVMR snapshot rule (both tracks)

State of the completed decision bar (available exactly at that close —
the certified availability rule). Range and Volume are examined
**separately**; RVMR-C1 remains unauthorized; 3×3 tables are
descriptive only.

---

## TRACK A — existing strategies, completely unchanged

Harvest from canonical implementations only; entries, directions,
management untouched; events tagged with the causally-available state.

| id | strategy | canonical source | management frame |
|---|---|---|---|
| A1 | OFH13 | `cand_spec` EV (133) | frozen 1.5 ATR / 60m (its own) |
| A2 | OFH14 | `cand_spec` EV (462) | frozen STRUCT stop (`struct_ref`) / 60m; R < 2 pt reported separately |
| A3 | sweep→reclaim | `mrv_run.mr_h3, arm='RECLAIM'` (REC-P1 spec) | uniform frame |
| A4 | accepted breakout | `mag_run.mag_dir_h1 → C_ACCEPT_ANY` | uniform frame |
| A5 | rejected breakout | `mag_run.mag_dir_h2 → C_REENTRY_ANY` | uniform frame |
| A6 | V-recovery | `mrv_run.v_h1(FAST)` | uniform frame |
| A7 | mean reversion | `mrv_run.mr_h2` | uniform frame |
| A8 | opening drive | `mag_run.open_family → C_DRIVE_ONLY` | uniform frame |
| A9 | overnight sweep/reclaim | `mag_run.ovn_family → FULL_SWEEP_RECLAIM` | uniform frame |
| A10 | G4 (canonical candidate) | `cand_spec` EV (218) | uniform frame |

Uniform measurement frame = frozen OFH13 management (1.5×ATR stop, no
target, 60-min time exit, 0.87 pt cost) — a **measurement frame** for
signal-only candidates, identical across states, so it cannot create an
interaction. Data: the canonical capture year (these detectors need it).

**Interaction statistic (frozen):** Δ = EV(HIGH) − EV(LOW), per tool.
p = two-sided **day-clustered bootstrap** (20,000 day resamples;
fraction of resampled Δ crossing 0, doubled, +1 correction).
**Family = 10 strategies × 2 tools = 20 tests, BH at M=20.** Promotion
requires the ten Track-A gate conditions, not q alone.

**Controls (simple, pre-declared):** Δ re-computed inside ATR-tercile
strata and inside hour-of-day strata (count-weighted); RVMR must add
separation *within* volatility and clock strata to claim incremental
value.

Per cell: N, EV pts, EV R, WR, PF, median R, avg win/lose, MFE, MAE,
MFE/MAE, ff@0.25/1 ATR, stop-hit %, time-to-MFE/MAE, P(0.25R..5R)
diagnostics (no targets introduced), winner-only size stats, loser-only
severity stats, largest win/loss. Tail preservation for any implied
filter: top-10 winners retained, top-5% contribution, per-original-
parent EV. Selectivity (%L/%M/%H) per strategy; ≥90% in one state ⇒
"RVMR NO SELECTIVITY" stated plainly.

**OFH13 special:** verify the 83%-HIGH claim with certified RANGE and
VOLUME states separately; no filtering of the prospective strategy
under any outcome.

**Grades:** only if a strategy shows monotone ordering across
expectancy, PF, median R, MFE/MAE, ff, and winner MFE, stable across
partitions. Otherwise **no grades** — and a negative-expectancy state is
never labelled B+.

---

## TRACK B — new RVMR-native strategies, M = 8 (frozen; no B9)

Data: the RVMR-certified V3 extract (2019-07 → 2026-08-17) — these
detectors are pure OHLCV, so the full history powers them; calendar
years are the stability partitions, with the overlap year carrying the
canonical U/DEV/IR labels. Uniform frozen frame: 1.5×ATR(20) stop, no
target, 60-min time exit, 0.87 cost. Eligibility: RTH stamp 09:30–15:00,
ATR>0, 60 contiguous forward minutes. Cooldown 30 min per cell.
Direction always from PRICE structure; RVMR alone never triggers.

Frozen constructs (reused from certified code wherever it exists):
BALANCE = 30-bar high/low envelope (`mag_lib.balance`);
ACCEPTANCE = 2 consecutive closes beyond the edge;
REJECTION = close beyond then a close back inside within 5 bars;
ON_HI/ON_LO frozen at 09:29; OR15 = 09:30–09:44 range; PDH/PDL =
prior-day RTH extremes; PWH/PWL = prior-week RTH extremes;
session VWAP = RTH cumulative typical-price×volume (proxy, labelled);
opening drive = |close(09:44) − open(09:30)| ≥ 1.0 ATR.

- **B1** HIGH-RVMR accepted breakout: acceptance events (as MAG frozen);
  arms: alone / +HIGH range / +HIGH volume.
- **B2** HIGH-RVMR first pullback: expansion = |close_j − close_{j−10}|
  ≥ 1.5 ATR with acceptance beyond the balance edge; leg origin O =
  close_{j−10}, extreme X; first pullback = first close retracing ≥ ⅓
  of the leg (invalid if close crosses O); entry = first close beyond
  the pullback bar's extreme within 15 bars. Arms: alone / +HIGH.
- **B3** sweep→reclaim over the level union {ON H/L, PDH/PDL, PWH/PWL,
  OR15 H/L}, single reclaim rule (close back through within 5 bars), no
  per-level tuning; arms: alone / +HIGH.
- **B4** LOW-RVMR mean reversion: |close − VWAP| ≥ 1.5 ATR, direction
  toward VWAP, entry at extension bar close; arms: alone / +LOW (range;
  volume reported).
- **B5** LOW→HIGH transition: state(j−1)=LOW, state(j)=HIGH
  (consecutive RTH bars); require a balance-edge breakout close within
  5 bars; direction = breakout side. Compared against MED→HIGH and
  HIGH→HIGH under the identical breakout requirement.
- **B6** HIGH→LOW exhaustion: ≥3 HIGH among last 10 states, now LOW;
  price must show failed continuation: a close back INSIDE the balance
  within 5 bars after having been outside; fade toward the balance mid.
- **B7** opening drive continuation (MAG frozen construction:
  `FULL_OPEN_CONT`) with an RVMR-HIGH arm at the 09:44 decision bar.
- **B8** gap × RVMR: gap = first RTH open − prior RTH close, |gap| ≥
  0.5 ATR; ACCEPTED (close(09:44) still beyond prior close, gap side) →
  continuation at 09:44; REJECTED (back through) → fade at 09:44;
  each × L/M/H states.

Statistics: sign-flip-by-day p (directional cells), day-clustered
bootstrap CI, **BH at M=8** on the primary arm of each cell; matched
comparison = the no-RVMR arm of the same construction. Ten-condition
Track-B gate; **no management rescue** — a failed raw edge dies
untuned.

## Structural-stop geometry (diagnostic only)

Where a legitimate structural reference exists (sweep extreme, balance
edge, ON extreme, OR edge, FVG invalidation for OFH13), report
dist/ATR at entry by state, and P(dist ≤ 0.75 ATR AND MFE60 ≥ 2 ATR) —
the "small legitimate risk, large favourable excursion" cell. Stops are
never actually tightened; HIGH-RVMR ⇒ smaller stop is forbidden.

## Absolute rules

HIGH is not assumed good; LOW is not assumed bad; HIGH ≠ A+. If nothing
improves, the declared valid result is: *RVMR remains a strong
movement-regime tool but does not currently improve strategy selection
or setup quality.* **THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
