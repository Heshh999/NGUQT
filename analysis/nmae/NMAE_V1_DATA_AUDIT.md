# NMAE-V1 — DATA-AVAILABILITY AUDIT (Mode A, read-only)

Performed under §8 Mode A, which is authorized even when the precondition
fails. Nothing was downloaded, purchased, scraped or authenticated. No
outcome was computed. Field-level manifest: `NMAE_V1_DATA_MANIFEST.json`.

**Headline: 4 of 29 required data classes exist. 0 of 6 NMAE families
are data-ready.**

## 1. What exists

| Class | Status | Coverage | Exposure |
|---|---|---|---|
| MNQ 1m OHLCV | present | 2,503,622 bars, 2019-07-04→2026-08-17, close-stamped ET | **fully exposed** |
| MNQ 1m order flow (bar aggregates) | present | 315 days, 2025-08-18→2026-08-19, full session | **exposed** (OFH/OF-N/OFFVG/MOFAD) |
| MNQ 30s OHLCV | present | 192 days, **09:30–11:00 only** | exposed; §2 forbids using it as a quote substitute |
| ES 1m OHLCV | present | **42 session days**, 2026-06-30→2026-08-17 | exposed (XMARKET-V1) |

## 2. What is absent (25 classes)

**Cross-index futures:** MES, YM, MYM, RTY, M2K — no files, no feed.
ES order flow: schema columns exist but are populated in **0 of 837,249
rows**.

**Cash / ETF basis inputs:** NDX cash index, QQQ bid/ask, risk-free /
financing rate at decision time, expected dividends, ETF borrow —
**none**.

**Options and volatility:** NQ or QQQ option chains, option bid/ask,
greeks/IV source, VXN, VIX spot or futures curve — **none**. §5 forbids
substituting model values for market prices, so nothing can stand in.

**Authenticated economic events:** licensed release timestamps,
pre-release consensus, first-release actual, revision history — **none**.
§5 and the standing authorization both forbid an unauthenticated
substitute calendar.

**Cross-asset regime inputs:** treasury futures/yields, dollar index,
semiconductor/tech ETF — **none**.

**Message and execution layer:** BBO quotes, L2 depth, raw trade
messages, broker/shadow fill records, latency distributions — **none**.
(This is also why MLES-V1 could not have run.)

## 3. Family readiness (§7 / §19 floors)

| Family | Status | First binding shortfall |
|---|---|---|
| N1 hedged equity-index relative value | `INSUFFICIENT_DATA` | YM and RTY absent entirely; ES span 42 days vs floors of 200 unique days and 5 years |
| N2 cash/futures basis and fair value | `INSUFFICIENT_DATA` | no cash index, no ETF quotes, no rates, no dividends — all four fair-value inputs missing |
| N3 realized vs option-implied | `INSUFFICIENT_DATA` | no option chains; executable bid/ask required and unavailable |
| N4 volatility term structure / VRP | `INSUFFICIENT_DATA` | no VXN/VIX or option term-structure data of any kind |
| N5 authenticated economic surprise | `INSUFFICIENT_DATA` | no authenticated release/consensus/revision source |
| N6 cross-asset regime transition | `INSUFFICIENT_DATA` | 4 of 5 asset classes absent; ES span far below the 200-day floor |

**READY_FOR_DISCOVERY: 0 of 6.**

Per §5, these are reported as `INSUFFICIENT DATA` rather than filled with
proxies. Specifically **not** done: no candle close used as fair value,
no spread inferred from OHLCV range, no model price used where a quote
is required, no scraped calendar, no interpolated chain.

## 4. Standing conclusion

Even if the MLES-V1 precondition had passed, NMAE would have stopped at
Mode A with `INSUFFICIENT OR UNUSABLE NEW DATA`, because every one of the
six frozen families requires an information class this repository does
not hold. The precondition gate is simply the earlier of the two stops.

## 5. What would unlock which family (no authority requested here)

- **N1 / N6** — genuine YM, RTY (and full-span ES) futures history at
  synchronized timestamps.
- **N2** — QQQ or NDX quotes + a rate curve + dividend estimates.
- **N3 / N4** — NQ or QQQ option chains with real bid/ask, plus VXN/VIX.
- **N5** — a licensed economic calendar with first-print and revision
  fields.
- All message-level work (and MLES-V1 itself) — the capture program
  already committed at `e628b9d` (`MofadV1MicroCaptureHost`), which
  records quotes, depth and trades once attached in NinjaTrader.

Each of these requires **explicit separate authorization** to acquire.
None was sought or used.
