# CCHC-V1 — DATA AND PROVENANCE AUDIT (Phase A)

Recorded 2026-08-27 UTC, before any CCHC-V1 trade outcome existed.

## Repository state
- Starting HEAD `be1fff683e28003cbe3ca7856758978828b713f2`
  (LPCC-V1 results commit), branch
  `claude/ninjatrader-mnq-automation-rqjzgg`, **clean tree**.
- Ancestry verified: **`eac54fe` IN ANCESTRY**, **`be1fff6` IN ANCESTRY**
  (it is HEAD). No reset, no history rewrite; LPCC-V1's failure and its
  full search burden are preserved untouched.
- Environment: Python 3.11.15, numpy 2.4.6.
- Source hashes (sha256, first 24): `wave4_run.py` c695937996f0fbd95c6658e2;
  `mgsd_lib.py` 8fdb21f8aa0622074dadc4ba; `lpcc_engine.py`
  5139e099b3cf0384c8aeec3c; `WAVE4_RAW.json` dd80b488acee43574e971f87.
- Data: canonical CLOSE-stamped 1m MNQ grid (hashes in
  `analysis/mgsd/MGSD_V1_DATA_MANIFEST.json`), ET wall clock with the
  proven exchange-calendar/DST treatment, `em` contiguity clock, no
  interpolation. DEV partition guard truncates at 2026-08-17.

## The Wave 4 closing VR30 cell — recovered and reproduced
- Cell ID: module B, **stratum `S9close`, q = 30**.
- Stratum definition (committed `wave4_run.py`): close stamps
  **931–960** = market interval **(15:30, 16:00] ET**, 30 bars/day.
- Bars are **CLOSE-stamped**: the bar stamped T covers (T−1min, T].
- Statistic: VR(q) = Var(non-overlapping q-bar sums) / (q · Var(1-bar)),
  q = 30, per-day blocks from the first stratum bar, global demeaning,
  1m log returns in bp with strict `em` contiguity (gap bars dropped,
  never bridged), day-clustered bootstrap 2,000 iterations,
  **committed seed 20260828 + q**.
- **Intervals contained in the published cell:** the stratum holds
  exactly 30 bars/day, so each eligible day contributes **exactly one**
  complete non-overlapping 30-bar interval (histogram: 1 window on
  1,767 days, 0 on 4). There is therefore no interval ambiguity; the
  frozen "chronologically final complete interval ending at the normal
  RTH close" **is** stamps 931–960 = **(15:30, 16:00] ET**. No interval
  returns were compared to make this selection.
- Published: VR30 = 1.269759, CI [1.083273, 1.469282], BH q 0.0320,
  1,767 windows, 1,771 days.
  **Reproduced 2026-08-27: VR30 = 1.269759, CI [1.083273, 1.469282],
  1,767 windows, 1,771 days — EXACT** (`cchc_provenance.py`,
  `provenance_vr.json`).

## Frozen close-stamp mapping (mechanical; interval unmoved)
- **Decision bar = stamp 930** (covers 15:29–15:30); all predictors end
  here.
- **Entry = open of stamp 931** (the 15:30:00 print) — the first
  executable price of the recovered interval.
- **Exit = open of stamp 961** (the 16:00:00 print) — the first causally
  executable open exactly 30 elapsed minutes after entry and the end of
  the recovered interval. This is a genuine traded price (MNQ trades to
  17:00 ET); it is **not** a closing-auction or settlement fill.
- Eligibility requires stamps 930…961 all present with
  `em[961] − em[930] = 31` (strict contiguity). **Early-close days fail
  this automatically and are excluded; the window is never shifted.**
- Anchor: **current RTH open = open of stamp 571** (the 09:30:00 print),
  known ~6 hours before the decision.

## Cost and execution model
Repository-approved MNQ models (frozen in MGSD-V1 §5): base **0.87 pt**
round turn; **stressed, RTH strata S5–S9: 1.305 pt** round turn;
stressed non-RTH: 1.740 pt. The CCHC interval is stratum **S9 (RTH)**,
so **1.305 is the session-appropriate binding stressed model**. This is
the repository's pre-existing frozen treatment, not a model selected to
help this test; because the exit prints at 16:00 the **1.740 non-RTH
model is additionally reported as a supplementary conservatism check**
and the result is stated under both. No authenticated commission
schedule exists; none invented; **exact-dollar and final cost gates
remain UNRESOLVED**; results reported in points/ticks (dollars at
$2/pt for scale only). Predeclared adverse slippage: 1, 2, 3 ticks per
side (2/side provisional base, 3/side stress).

## Exposure statement
All data through 2026-08-17 is exposed development history. The buffer
**2026-08-18 → 2026-08-31 is assigned no role and is untouched**; no
partition dated 2026-09-01 or later is inspected, summarized, or
hash-probed. CCHC-V1 is **exploratory historical feasibility only**;
a pass earns only the right to face genuinely future data.
