# ODMC-V1 — DATA AND PROVENANCE AUDIT (Phase A)

Recorded 2026-08-27 UTC, before any ODMC-V1 trade outcome existed.

## Repository state
- Starting HEAD `963009d20bd11528da9728801645e38d3d5f6163` (CCHC-V1
  results), branch `claude/ninjatrader-mnq-automation-rqjzgg`,
  **clean tree**.
- Ancestry verified: **`eac54fe`, `be1fff6`, `963009d` all IN ANCESTRY**.
  No reset, no history rewrite. LPCC-V1 and CCHC-V1 failures and their
  full search burden are preserved untouched.
- Environment: Python 3.11.15, numpy 2.4.6.
- Hashes (sha256, first 24): `wave4_run.py` c695937996f0fbd95c6658e2;
  `mgsd_lib.py` 8fdb21f8aa0622074dadc4ba; `WAVE4_RAW.json`
  dd80b488acee43574e971f87; `MGSD_V1_SUBMIN_30S_LEDGER.csv`
  62ea9797c4080acdbabbf9d4.
- Data: canonical CLOSE-stamped 1m MNQ grid (hashes in
  `analysis/mgsd/MGSD_V1_DATA_MANIFEST.json`), ET wall clock with the
  proven exchange-calendar/DST treatment, `em` contiguity clock, no
  interpolation. DEV partition guard truncates at 2026-08-17.

## 3.1 The Wave 4 opening-drive VR10 cell — reproduced EXACT
- Cell: module B, **stratum `S5open`, q = 10**.
- Stratum (committed `wave4_run.py`): close stamps **571–600** =
  market window **[09:30, 10:00)**, 30 bars/day. Bars CLOSE-stamped
  (bar T covers (T−1min, T]).
- Statistic: VR(q) = Var(non-overlapping q-bar sums)/(q·Var(1-bar)),
  q = 10, per-day blocks from the first stratum bar, global demeaning,
  1m log returns in bp, strict `em` contiguity (gap bars dropped, never
  bridged), day-clustered bootstrap 2,000 iterations, **committed seed
  20260828 + q**.
- **Blocks contained in the published cell:** 30 bars/day ⇒ **three**
  non-overlapping 10-minute blocks/day — stamps **571–580**, **581–590**,
  **591–600** (histogram: 3 blocks on 1,822 days, 2 on 8, 1 on 3).
- Published: VR10 = 1.081912, CI [1.029336, 1.140243], BH q 0.0320,
  5,485 blocks, 1,833 days. **Reproduced 2026-08-27: VR10 = 1.081912,
  CI [1.029336, 1.140243], 5,485 blocks, 1,833 days — EXACT**
  (`odmc_provenance.py`, `provenance.json`).

## 3.2 Mechanical block selection (no return comparison)
The **chronologically earliest complete block beginning at/after the
09:30 RTH open** is stamps **571–580** = market block
**[T0, T10] = [09:30, 09:40)**, midpoint **T5 = 09:35**. The other two
blocks exist in the cell and are NOT used.

## Frozen close-stamp mapping (interval unmoved)
| element | stamp | wall clock |
|---|---|---|
| `P0` block traded open | **open of stamp 571** | 09:30:00 print |
| signal half `[T0,T5]` | completed stamps **571–575** | five completed bars |
| `P5` midpoint close | **close of stamp 575** | 09:35:00 |
| decision | after stamp 575 completes | 09:35 |
| entry | **open of stamp 576** | 09:35:00 print |
| trade half `(T5,T10]` | stamps **576–580** | five bars |
| exit | **open of stamp 581** | 09:40:00 print |
Eligibility: stamps 571…581 present with `em[581] − em[571] = 10`.
No entry inside the signal half, no late entry, no scanning, no re-entry.

## 3.3 Prior 30-second observation — reproduced (provenance only)
From the committed `MGSD_V1_SUBMIN_30S_LEDGER.csv`:
`S30A_n10_t1.0_s20_e30` — **n 28 events / 28 days**, stressed EV
+48.9879 pt, WR 0.750, PF 4.2432, CI [+18.4845, +78.8718], p 0.0020,
BH q 0.0400. **First binding failure: sample floors (28 events / 28 days
vs ≥100 / ≥40)**, with visible regime concentration (2026 EV +83.5 vs
2025 +14.5 on 14 trades each). Genuine 30s coverage: 34,944 bars,
192 days, 2025-09-01→2026-05-29, 182 slots 09:30:00–11:00:30;
30s→1m aggregation 17,190/17,190 exact. **Its favorable parameters are
not used to alter ODMC-V1 in any way.**

## 3.4 Costs
Repository-approved models: base **0.87 pt** RT; stressed **RTH 1.305**,
non-RTH 1.740. The repository has **no opening-specific stress model**,
so the frozen fallback applies for the stress side: adverse slippage
1/2/3/4 ticks per side, with **4 ticks/side = 2.00 pt round turn
designated BINDING STRESS** (the strategy executes in the most volatile
minutes of the day) and 2 ticks/side = 1.00 pt as provisional base.
Base-cost gates use the repository's approved **0.87** model (which
exists and is the §4.7-item-3 "frozen base"); every scenario is
reported. **No commissions invented; exact-dollar and final commission
gates UNRESOLVED**; results in points/ticks (dollars at $2/pt for scale
only). Market execution, one contract, no compounding, no favorable
limit fills.

## Exposure statement
All data through 2026-08-17 is exposed development history. The buffer
**2026-08-18 → 2026-08-31 has no role and is untouched**; nothing dated
2026-09-01 or later is inspected, summarized, or hash-probed. ODMC-V1 is
**exploratory historical feasibility only**.
