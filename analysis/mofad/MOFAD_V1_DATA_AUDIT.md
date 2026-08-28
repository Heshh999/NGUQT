# MOFAD-V1 — MANDATORY DATA-READINESS AUDIT

Facts below were computed by `phase_a_facts.py` (output frozen in
`phase_a_facts.json`) plus the previously committed audits cited inline.
No forward return, outcome, or P&L was computed. All hashes are SHA-256
over sorted file contents. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

**Headline: no quote, depth, tick/message, fill, or authenticated-event
data exist anywhere in this repository or its configured feeds.** The only
genuine microstructure asset is the NinjaTrader V4.1 order-flow capture of
**1-minute bar-aggregate** aggressor-split volume, full session, 12.0
months. It was already exposed by the OFH/OF-N/OFFVG/PROOF/V5-P3 programs.

---

## 1. Stream-by-stream audit

### 1.1 MNQ 1m OHLCV (price backbone)
| field | value |
|---|---|
| source / ownership | user's NT8 export, RVMR-certified extract (`rvmr_1m/`, 8 files) |
| symbol / contract | MNQ continuous (no roll discontinuity — proven, `docs/ES_NQ_DATA_V1_AUDIT.md` §3) |
| timezone / stamping | US/Eastern, **close-stamped (proven)** |
| resolution | 1 minute; no exchange/receive split; no sequence numbers |
| coverage | 2,503,622 bars, 2019-07-04 → 2026-08-17, 2,218 days, full session |
| missingness / dups | 0 duplicates; 312 classified gaps (0.0125%) |
| sha256 | `0ae4a6cb…a4a6b83a49` (`phase_a_facts.json`) |
| prior exposure | FULLY EXPOSED (every price program) |

### 1.2 MNQ 1m order-flow capture (the one genuine flow asset)
| field | value |
|---|---|
| source / ownership | user's NT8 V4.1 order-flow engine capture (`ofnew/` 4 files + `of2/` 10 files) |
| schema | 108 columns incl. `f_ofBidVolume`, `f_ofAskVolume`, `f_ofBarDelta`, `f_ofCumDelta`, min/max delta, 2x/3x/4x imbalance + stacked levels, absorption candidates, `f_volumePerUpTick/DownTick`, bar profile POC/VAH/VAL |
| aggressor side | **directly observed by NT8 at trade level, but stored only as per-1m-bar aggregates** — no per-trade records survive |
| resolution | 1-minute bar aggregates, close-stamped ET; no exchange/receive split |
| coverage | 381,982 rows, 315 days 2025-08-18 → 2026-08-19; **DEV-eligible 313 days 2025-08-18 → 2026-08-17 (exactly 12.0 months), all 24 hours covered**; 2 buffer days (2026-08-18/19) present and EXCLUDED from research |
| depth | `f_depthHistoryAvailable = FALSE` in the capture itself |
| sha256 | ofnew `6d426732…ca0ed53a`; of2 `baf4ac59…6305a950` |
| prior exposure | EXPOSED (OFH1–14, OF-N1–12, OFFVG, OF-grading/targets, PROOF, V5-P3) |

### 1.3 MNQ/NQ quote data (§5.1)
**ABSENT.** No best bid/ask prices, no displayed sizes, no quote updates,
no exchange or receive timestamps, no sequence numbers, no locked/crossed
records, no level-2/depth in any form (market-by-price or market-by-order).
Spread, microprice, OFI, queue, replenishment, and absorption research at
message level is **not possible** from existing data, and inferring these
from OHLCV is prohibited.

### 1.4 Executed trade data (§5.2)
**ABSENT at message level.** No trade-by-trade prices/sizes, no timestamps,
no sequence, no condition/bust flags. Aggressor side exists **only** as the
per-bar bid/ask-volume split of §1.2 (direct at collection time, aggregate
at rest). No classification rule is needed or permitted — there are no
trades to classify.

### 1.5 30-second and tick data (§5.3)
Raw ticks/messages: **ABSENT**. Genuine 30s OHLCV: morning window
09:30–11:00 only, 34,944 bars, 192 days 2025-09-01 → 2026-05-29
(proven, `analysis/mgsd/MGSD_V1_DATA_AUDIT.md`; aggregation to 1m proven
exact 17,190/17,190). The `ph2/` exports additionally contain 20 scattered
month files (201912…202605, sha256 `67a51eb4…be91dcfb`) of *event/feature*
rows, not contiguous full-session bars. **Full-session 30s coverage does
not exist; temporal durability at 30s is insufficient; nothing is
extrapolated to the close or overnight.**

### 1.6 ES data (§5.5 inputs)
- `es_pilot/`: 42 files, 837,249 rows, 2026-06-30 → 2026-08-17, ES 1m
  OHLCV certified clean (`docs/ES_NQ_DATA_V1_AUDIT.md` addendum). The
  schema carries bidVolume/askVolume/delta columns but they are populated
  in **0 of 837,249 rows** — no ES order flow exists. sha256
  `caece995…07fcec9a2`.
- `es_full/`: 174 CSVs (87 entries + 87 structure months, 2019-06→) of
  **v4.1 engine event/feature outputs computed on ES**, not continuous ES
  bars; unusable for lead/lag or flow research. sha256 `f74f1f77…5831b42d`.
- Genuine continuous ES history remains **42 session days (1.86% of the NQ
  span)**.

### 1.7 Fill/latency records (§5.4)
**ABSENT** — see `MOFAD_V1_EXECUTION_DATA_AUDIT.md`.

### 1.8 Economic-event data (§5.6)
**ABSENT** — see `MOFAD_V1_EVENT_DATA_AUDIT.md`.

---

## 2. Partitions (preserved exactly)

DEV ≤ 2026-08-17 · buffer 2026-08-18→31 untouched · VALIDATION
2026-09-01→2027-02-28 · OOS 2027-03-01→2027-08-31 · LOCKBOX 2027-09-01+.
No future file was opened; the buffer days present inside the OF capture
files are excluded by the loader-side date cap recorded above. No
retrospective microstructure data arrived, so no `HISTORICAL_MICRO_DEV`
set exists to label.

## 3. Readiness decisions

See `MOFAD_V1_DATA_READINESS_MATRIX.csv`. Summary:

- **READY_FOR_DISCOVERY**: F03 (aggressive-volume imbalance — bar-level,
  subject to the spent-fingerprint screen), F08 (price impact/decay —
  bar-level λ), F12 (session-transition inventory with real order flow).
  All capped at 12.0 months genuine coverage → **any survivor is
  provisional-only; the five-year durability line is already determined:**
  `FIVE-YEAR MICROSTRUCTURE DURABILITY: INSUFFICIENT DATA.`
- **CAPTURE_ONLY**: F01, F02, F04, F05, F06, F07, F10 (required
  quote/depth/message/ES-flow streams do not exist).
- **INSUFFICIENT_DATA**: F09 (42 ES days; 1m-resolution cross-market price
  mechanisms already spent by XMARKET-V1 0/8; no sub-minute sync provable),
  F11 (no authenticated event source; downloading substitutes prohibited).
- **PROHIBITED_BY_INTEGRITY_FAILURE**: none — no stream failed integrity;
  the missing streams are absent, not corrupt.
