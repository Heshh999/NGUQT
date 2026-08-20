# V4.1 External-Evidence / Practitioner Review

Date: 2026-08-20. Performed BEFORE outcome review, per the prompt.
Purpose: source and tier the evidence behind the hypothesis library.
Nothing here is evidence of positive expectancy in MNQ; it justifies
plausibility and documents source fidelity.

## Practitioner evidence table

| Practitioner | Market | Method / indicator | Method evidence | Performance evidence | Tier | Justifies hypothesis? | Supports profitability claim? |
|---|---|---|---|---|---|---|---|
| Traders Reality / Tino | FX, indices (incl. ES examples) | PVSRA vector candles, unrecovered vector zones, W/M formations, EMA fan (5/13/50/200/800), 50% vector recovery, trigger candles, dealer/MM framing | STRONG: open-source TradingView scripts publish the exact candle rules; site carries "Vector Candle Basics" and a masterclass list including "50% Vector Recovery" (Session 80) | NONE FOUND independently verified | **C** | YES (H1–H5, TR-H1/H2 translations) | **NO** |
| Nour Atta / Nour Trades / Stock Hours | US equities/options | 5-minute chart, support/resistance, volume, price action; live-streamed order fills; self-published broker statements | Public; consistent across sources | Self-published, not independently broker-synced | **B** (transparency) / method **does not include** footprint/delta per available sources | NOT for order-flow hypotheses — per the prompt, footprint/delta usage is NOT attributed to him; recorded honestly | NO (not independently verified) |
| Morad Askar / FuturesTrader71 | ES/futures | Volume profile, order flow, auction framing, DOM; 20+ yrs; founder of Edge Clear brokerage, co-founder Convergent Trading | STRONG public methodology history (webinars, interviews) | NONE FOUND independently verified | **C** | YES (H6, B2, profile layers) | NO |
| Tier-A search (broker-synced, e.g. Kinfo) | futures | order-flow features | Kinfo provides read-only broker-synced verification (incl. futures) — the *channel* exists | No specific trader found jointly satisfying verified long-run performance AND documented use of our exact order-flow features | — | — | — |

**Formal result, as the prompt requires:** NO PUBLIC SOURCE FOUND THAT
JOINTLY VERIFIES BOTH THE TRADER'S LONG-RUN PERFORMANCE AND USE OF
THIS SPECIFIC INDICATOR. That is an acceptable result. No practitioner
evidence above Tier C exists for any vector or footprint hypothesis in
this programme; all such hypotheses rest on method-plausibility plus
our own confirmatory testing.

**Source-fidelity note (vector definition).** The engine's PVSRA
translation — 10-bar lookback; climax = vol ≥ 200% of average OR
vol×spread ≥ 10-bar high; elevated = vol ≥ 150% — matches the public
Traders Reality TradingView script family. `vectorSourceVerified=TRUE`
in the audits is corroborated by primary public sources.
TR-H1/TR-H2's "vector must exit the W/M" remains ADAPTED (public
material supports vector location around formations as a clue, not a
mandatory rule), and is labelled ADAPTED in all reporting. The
first-vector strategy and any exact TR stop rule remain unverified —
NOT IMPLEMENTED rather than invented.

## Academic / microstructure evidence

| Work | Market | Finding | Relevance |
|---|---|---|---|
| Cont, Kukanov & Stoikov — *The Price Impact of Order Book Events* | US equities (TAQ, 50 stocks) | Short-horizon price changes are driven mainly by order-flow imbalance at the best quotes; near-linear relation, slope ∝ 1/depth; robust across stocks and intraday scales | Justifies plausibility of H6/B2 (executed-flow features carrying short-horizon information). Not MNQ; not a profitability claim |
| Generalized OFI / cross-impact literature (arXiv 2112.02947; Quantitative Finance 2023) | equities | OFI generalizations retain predictive content; cross-asset impact exists | Same, weaker |
| Fed note (2025) — OFI in US Treasuries | UST | Order-flow imbalances amplify price moves | Effect exists outside equities |
| Short-horizon order-flow filtration studies (arXiv 2507.22712) | various | Directional association of filtered order flow with short-horizon returns | Horizon caution: effects live at seconds-to-minutes; our 1m bars sit at the coarse edge |

Limitations recorded: all of the above concern *quote-level* or
tick-level flow in other instruments; our features are 1-minute
aggregated executed volume. The literature justifies WHY the
hypothesis family is plausible; it says nothing about whether our MNQ
implementation clears costs. That is what the confirmatory pass
measures.

## Sources

- https://tradersreality.com/shorts-vector-candle-basics/
- https://tradersreality.com/masterclasses-2/
- https://www.tradingview.com/script/UcbR9FIH-Traders-Reality-PVSRA-Volume-Suite/
- https://www.tradingview.com/script/I604sNNd-Traders-Reality-Vector-Candle-Zones/
- https://whop.com/blog/stock-hours-review/
- https://ippei.com/stock-hours/
- https://www.moneyshow.com/expert/52250087f39943ab9a26a909ea02b619/
- https://bookmap.com/blog/trading-depth-interview-ft71
- https://kinfo.com/trader-verification
- https://arxiv.org/pdf/1011.6402
- https://arxiv.org/pdf/2112.02947
- https://www.tandfonline.com/doi/full/10.1080/14697688.2023.2236159
- https://www.federalreserve.gov/econres/notes/feds-notes/order-flow-imbalances-and-amplification-of-price-movements-evidence-from-u-s-treasury-markets-20251103.html
- https://arxiv.org/html/2507.22712v2
