# LPCC-V1 — DATA AND PROVENANCE AUDIT (Phase A)

Recorded 2026-08-27 UTC, before any LPCC trade outcome existed.

## Repository state
- Starting HEAD `eac54fe420eab5c5d1df20e6bd6c77471ee02c38`, branch
  `claude/ninjatrader-mnq-automation-rqjzgg`, clean tree.
- `eac54fe` (Wave 4) verified IN ANCESTRY of HEAD (it IS HEAD).
- Environment: Python 3.11.15, numpy 2.4.6.
- Committed source hashes:
  `analysis/wave4/wave4_run.py` sha256 `c695937996f0fbd9…0878ec47`;
  `analysis/mgsd/mgsd_lib.py` sha256 `8fdb21f8aa062207…00ad7aa1`
  (grid loader + DEV partition guard, truncates at 2026-08-17).
- Data: canonical close-stamped 1m MNQ grid (hashes in
  `analysis/mgsd/MGSD_V1_DATA_MANIFEST.json`), ET wall clock,
  exchange-calendar sessions, no interpolation, `em` contiguity clock.

## The Wave 4 late-premarket VR30 cell — recovered and reproduced
- Stratum: S4latePM = close stamps **08:01–09:29 ET** (mod 481–569,
  89 bars/day), CLOSE-stamped (bar stamped T covers (T−1min, T]).
- Statistic: VR(q)=Var(non-overlapping q-bar sums)/(q·Var(1-bar)),
  q = 30, per-day blocks starting at the FIRST stratum bar, global
  demeaning, day-clustered bootstrap (2,000, seed 20260828+q), 1m
  returns in bp with strict contiguity (gap bars excluded, never
  bridged).
- Non-overlap: 89 bars/day → 2 complete 30-bar windows/day
  (stamps 481–510 and 511–540); last 29 bars unused. Histogram over
  1,835 eligible days: {2 windows: 1,829, 1: 3, 0: 3}.
- Published: VR30 = 1.3239, CI [1.1404, 1.5211], BH q 0.032,
  3,661 windows. **Reproduced 2026-08-27: VR30 = 1.323901,
  CI [1.140421, 1.521117], 3,661 windows, 1,835 days — EXACT**
  (`lpcc_provenance.py`, `provenance_vr.json`).

## Mechanical single-window mapping (documented, not moved)
The VR cell aggregates TWO 30-minute windows per day. LPCC-V1 requires
one. The mechanical resolution — fixed by the committed construction,
not by results — is the **first** non-overlapping window of the cell:
- **[T0, T1] = (08:00, 08:30] ET market time** = close stamps 08:01–08:30.
- Decision bar: the completed bar stamped **08:00** (mod 480).
- Entry: **open of the bar stamped 08:01** (first executable price of
  the window; requires em-contiguity with the decision bar).
- Time exit: **open of the bar stamped 08:31** — the first executable
  open exactly 30 elapsed minutes after entry, the end of the recovered
  interval.
The second window (08:31–09:00) exists in the VR cell and is NOT used:
one event per day, no scanning, frozen.

## Cost and fill model
Repository-approved MNQ model: base 0.87 pt round turn; MGSD-V1
premarket stressed model **1.740 pt** round turn (non-RTH entries).
No authenticated commission schedule exists; none invented; the
exact-dollar cost gate remains **UNRESOLVED**; results reported in
points/ticks (dollars shown at the MNQ $2/pt multiplier for scale
only). Predeclared adverse-slippage matrix: 1, 2, 3 ticks per side
(2/side provisional slippage base, 3/side slippage stress), reported
alongside the frozen repository models.

## Exposure statement
All data through 2026-08-17 is exposed development history (MGSD
exposure ledger inherited). 2026-08-18→31 remains an unused buffer.
No partition after 2026-08-31 is touched. This test is EXPLORATORY
HISTORICAL FEASIBILITY only; a pass is not validation; a failure kills
LPCC-V1 as frozen.
