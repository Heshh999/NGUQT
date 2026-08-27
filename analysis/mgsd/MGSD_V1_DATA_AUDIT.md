# MGSD-V1 — DATA AUDIT (Phase A)

Audited 2026-08-27 (UTC). Machine-readable facts: `MGSD_V1_DATA_MANIFEST.json`
(hashes, per-file inventory, stratum coverage). No signal, candidate outcome,
or conditional statistic was computed in this phase.

## Starting repository state
- Starting HEAD `70a0efc4d1d6519f5996b59fe849048e124c7ae1`, branch
  `claude/ninjatrader-mnq-automation-rqjzgg`, clean tree.
- Environment: Python 3.11.15, numpy 2.4.6, 4 cores.
- Isolated research directory: `analysis/mgsd/` (nothing outside it is
  modified by MGSD-V1).

## Required prior material (§2)
- `V4_1_BACKTEST_PROMPT_FINAL_FREEZE_V7_BROAD_DEV_DISCOVERY_VALIDATION.txt`
  — **NOT PRESENT** anywhere in the repository or scratchpad.
- `V3_V4_BACKTEST_PROMPT_WITH_HYPOTHESES_TARGETS_STOPS_ORDERFLOW.txt`
  — **NOT PRESENT**.
- `engine.txt` — **NOT PRESENT**.
- OFH13-POSTENTRY-V1 final report — PRESENT
  (`docs/OFH13_POSTENTRY_V1_FINDINGS.md`, closed at commit `70a0efc`).
The applicable research controls are therefore this repository's own frozen
programme discipline (preregistration-before-outcome, never-shrink
multiplicity, frozen-cost model, causal audits) — which is also the stricter
set. Conflict rule applied: strictest anti-leakage wins.

## PRIMARY DATASET — canonical 1-minute MNQ grid
- Loader: `analysis/rvmr/rvmr_run.py::load_bars()`, STAMP_SHIFT=0.
- **2,503,622 bars, 2019-07-04 18:25 → 2026-08-17 15:16 ET, 2,218 days.**
- CLOSE-stamped, ET wall clock (DST implicit); contiguity via the frozen
  `em` minute clock; **0 duplicates; 0 OHLC violations; 0 non-positive
  prices; 6,059 zero-volume bars (0.24%, retained, flagged)**;
  1,241,630 missing minutes = weekends/holidays/maintenance/halts —
  never bridged, never interpolated.
- Instrument: continuous MNQ/NQ-equivalent (V3 asset); roll stitching was
  audited in the frozen RVMR-V1 Phase 0; price basis consistent with the
  ph2 export (verified byte-equal on overlapping bars).
- OHLCV complete. **No executed bid/ask, no trade prints, no DOM/depth.**
- **Complete calendar years: 2020, 2021, 2022, 2023, 2024, 2025 (six).**
  2019 (155 days) and 2026 (196 days) are partial.
- Aggregation determinism: 1m→3m 50,000/50,000 consistent; 1m→15m
  50,000/50,000; 1m→60m 38,989/38,989. A higher-timeframe bar becomes
  available only after its close (grouping = stamps in (B−k, B]).
- Session-stratum coverage (see manifest): all nine frozen strata have
  ≥95% bar coverage on the overwhelming majority of days; Globex/premarket
  strata are genuinely populated (24h session data).

## 30-SECOND ARM DATASET (ph2 export)
- 20 monthly files `scratchpad/ph2/V3_30s_*.csv` (hashes in manifest).
  These are EVENT exports carrying mixed `1m` and `30s` rows plus
  precomputed feature and outcome columns from the old V3 scalp research.
- **ADMISSIBLE INPUT: raw OHLCV of `timeframe==30s` rows only.** Every
  other column (EMA/VWAP/levels/MFE/MAE/net/barTo-R races) is a
  **PROHIBITED input**: precomputed, previously exposed, unknown causal
  provenance.
- Proven facts (reproduced from raw rows, not assumed):
  - **34,944 unique 30s bars, 192 trading days, 2025-09-01 → 2026-05-29**
    (9 months). ⚠ The task statement claimed 147 days / 2025-11→2026-05;
    that claim FAILS reproduction — the proven coverage (192 days,
    2025-09 onward) matches the repository's own LTF record and governs.
  - **182-slot grid 09:30:00 → 11:00:30 ET — reproduced exactly.**
  - Stamp convention proven: all close-stamped;
    **1m[T] = 30s[T−30s] ∪ 30s[T]**.
  - Aggregation vs the canonical 1m grid: **17,190 of 17,190 pairs exact
    OHLC (100%)**; 17,186/17,190 also exact on volume (4 volume-only
    mismatches, recorded); 0 duplicate-key conflicts.
  - OHLCV only; no bid/ask, flow, DOM, depth. **No genuine 15s/10s/5s/tick
    history is admissible (5s/15s capture exists but is prohibited by the
    sub-30s exclusion).**
  - No 30s coverage outside 09:30:00–11:00:30 and none for 2026-06/07/08.
    **The 30s files contain no premarket.** Premarket research uses the
    1-minute grid.

## EXCLUDED / PROHIBITED datasets
| dataset | reason |
|---|---|
| 5s/15s LTF capture (192 days) | sub-30-second prohibited in MGSD-V1 |
| order-flow capture 2025-08→2026-08 | price-action first; order flow only as a later separately frozen incremental arm |
| OFH13 133-trade table and labels | prohibited discovery input |
| ph2 non-OHLCV columns | pre-computed, pre-exposed |
| cross-market (ES/YM/RTY/vol/rates) | **no genuine synchronized series exists in the repository → cross-market arm INSUFFICIENT DATA; nothing downloaded or substituted** |
| scheduled-macro calendar | no exact reproducible calendar exists in the repository → news-conditioned variants NOT RUN, reported insufficient |

## Causal reconstructability
Every admissible field (OHLCV at close-stamped minutes / 30s slots) is
reconstructable at its stamp. All derived features used later are computed
from completed bars only and are covered by the software tests.
