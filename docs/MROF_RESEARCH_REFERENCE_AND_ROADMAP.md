# MROF research reference and roadmap — describing and forecasting NQ

Written 2026-11-28. This file holds **outside research and the plan
only**. It holds none of this project's results; those stay with the
operator. Where a registration in `analysis/mrofyt/` tests an idea, it
is named. **THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**

How the sources were read: the papers marked *(full)* were read in
full; everything else in abstracts and summaries only, and should be
read before anything is built on it. Vendor prices are as listed in
November 2026, were not verified, and nothing was bought or requested.

---

## 1. Two tools, one loop

- **The describing tool** says what the market is doing now: how wild
  it is, whether moves are continuing or giving back, what kind of day
  the calendar makes it.
- **The forecasting tool** turns a description into odds: how far the
  day is likely to go, and, where there is a reason, which way and for
  how long.

Neither is a strategy. A and B stay the trades; the two tools grade
them: take the signal or not, and at what size. The literature's name
for this is meta-labeling (López de Prado): a second model that only
decides whether to act on the first one.

The loop that keeps it honest:

1. **Describe** the state before the decision, from data known then.
2. **Forecast** as odds, written down before the outcome.
3. **Act** only through rules frozen beforehand.
4. **Score** every forecast against what happened (calibration: of the
   times it said 70 %, how many came true).
5. **Retire** a forecast whose score decays, by a rule fixed in
   advance.

A weather service works this way. What is better than a weather
forecast is one that also knows where it has no skill and says so: the
market's own odds (implied volatility) are the starting point, and a
forecast earns its place only by beating them on data it has not seen.

## 2. Which way

The plain finding across independent studies: direction from price,
volume or order flow, at minutes to hours, does not survive retail
costs. The exceptions are forced flows.

| Finding | Source |
| --- | --- |
| The last half hour follows the rest of the day in more than 60 futures, 1974–2020; on the S&P 500 only on days when option dealers are short gamma; it gives back over the next days | Baltussen, Da, Lammers, Martens 2021 *(full)* |
| The first half hour predicts the last on SPY, 1993–2013; stronger on volatile, high-volume and news days | Gao, Han, Li, Zhou 2018 |
| Leveraged funds rebalance at the close in the direction of the day; intraday momentum is stronger where that activity is intense. One study finds the fund effect larger than option hedging, quickly reverting, and shrinking over time | Concretum; Barbon, Beckmeyer, Buraschi, Moerke |
| The noise-area rule (this project's B) reproduces on its own sample; independent re-runs find it weaker since its 2024 publication. One of them reports the decline as highly significant while its own Welch test gives p = 0.26 | Zarattini, Aziz, Barbon *(full)*; Paz 2026 *(full)*; Delgado 2026 *(full)* |
| The opening-range breakout (this project's A) reproduces before costs in independent re-runs and is about the size of a wide spread; results bunch in 2020–2022 | Zarattini, Aziz; independent replications |
| The overnight drift (02:00–03:00 ET) was flat from 2021; the pre-FOMC drift is gone after 2015 | Boyarchenko, Larsen, Whelan; Kurov, Wolfe, Gilbert 2021 |
| Order flow predicts price for about a second on the E-mini; the sign of order flow is predictable while returns are not, because liquidity adjusts | Takahashi 2025; Lillo, Farmer 2004 |
| Deep learning on the order book forecasts about two price changes ahead, and accuracy does not become profit | Kolm, Turiel, Westray 2023; Briola, Bartolucci, Aste 2025 |
| Five frozen foundation models on NQ and ES, 5 to 120 minutes: none beats "no change" (pre-registered) | Upadhyay 2026 *(full)* |
| Fourteen price-and-volume signal families on MNQ five-minute bars: none passes after costs | Mesfin 2026 *(full)* |
| Published anomalies earn about a quarter less out of sample and more than half less after publication | McLean, Pontiff 2016 |

## 3. When: the dealers' side

The one "when" signal with a mechanism. Dealers who are short gamma
must buy rallies and sell drops, which extends moves; long gamma, they
do the opposite, which dampens them.

| Finding | Source |
| --- | --- |
| Short gamma raises volatility and the chance of large moves; long gamma dampens both. Dealer positions signed with exchange data that labels buyers and sellers | Ni, Pearson, Poteshman, White 2021 |
| Short gamma with a thin market gives momentum and flash crashes; long gamma gives reversal; the sign of gamma goes with the sign of intraday autocorrelation | Barbon, Buraschi, "Gamma Fragility" |
| On same-day-expiry days dealers are long gamma; higher dealer gamma predicts stronger reversals of E-mini order flow, fading within about an hour, and lower volatility | Dim, Eraker, Vilkov; Adams, Fontaine, Ornthanalai |
| Retail traders are net buyers of same-day options, which would leave dealers short them | Beckmeyer, Branger, Gayda |
| The measured net position is small and balanced (the exchange is an interested party) | Cboe |
| B's authors: the rule earned more after a five-day fall, read as dealers more likely short gamma (in sample, SPY) | Zarattini, Aziz, Barbon *(full)* |

**Open questions.** The studies disagree about which side dealers are
on in the same-day-options era. No published study measures Nasdaq-100
dealer gamma, which sits in QQQ options, NDX index options and options
on NQ futures. Free and cheap gamma figures assume dealers are short
calls and long puts; open interest does not say who holds what.

**Tested here without option data:** wave thirty-three
(`MROF_YT_WAVE33_DEALER_REGISTRATION.md`) reads the dealers' side from
price alone: a fall over five days, and whether the morning's
five-minute moves continue or give back.

## 4. For how long

| Finding | Source |
| --- | --- |
| Futures trend from a few hours to a few years, and revert at shorter and at much longer horizons (14 years of tick data) | Safari, Schmidhuber 2025 *(full)* |
| Stock returns: autocorrelation near zero under a minute, most negative around 15 minutes | Baule, Schlie, Zhou |
| Short-term trend following on daily data stopped paying around 2009 and collapsed on small-tick contracts; it is intact on large-tick ones; market makers pull liquidity ahead of predictable flow | Kurth, Eisler, Rej, Bouchaud 2026 *(full)* |
| Fast traders first trade against a large order, then with it if it keeps coming | van Kervel, Menkveld 2019 |
| Drift bursts, steep one-way runs over minutes, occur about weekly in futures, and most reverse | Christensen, Oomen, Renò |

**Tested here:** wave thirty-two (`MROF_YT_WAVE32_LATEDAY_REGISTRATION.md`)
measures B's result by time of day and by the age of its position.

## 5. How far

The most forecastable part.

| Finding | Source |
| --- | --- |
| Implied volatility (VIX, VXN) holds most of the information about coming volatility; past prices add a little | Giot; a large later literature |
| A one-day implied index, adjusted for its premium, beat HAR at one day (S&P) | Albers 2025 |
| HAR, a blend of the last day, week and month of realized volatility, is hard to beat; machine learning wins sometimes, not reliably | Corsi 2009; "HARd to Beat" 2024 |
| Volatility from falls predicts more than volatility from rises | Patton, Sheppard 2015 |
| News releases: the size of the reaction grows with the surprise and is absorbed within about a minute; no reliable drift after | LSEG; CME research |
| Volatility-managed sizing fails out of sample across about a hundred strategies | Cederburg and co-authors (via Alpha Architect) |

**Tested here:** wave thirty-four
(`MROF_YT_WAVE34_RANGE_REGISTRATION.md`) sets VIX, VXN and RVX against
HAR and a plain average range, with downside volatility, RVMR, expiry
days and event days reported beside. Wave thirty-one
(`MROF_YT_WAVE31_SIZING_REGISTRATION.md`) asks whether a range regime
used for size makes A and B steadier.

## 6. What a trade costs: market makers

| Finding | Source |
| --- | --- |
| A simple resting order was immediately losing on about two thirds of its fills in NQ and four fifths in ES: one is filled because the price is moving through | Market simulation under adverse selection 2024 *(full)* |
| Fast market makers hold tiny inventories and take liquidity under stress | Kirilenko, Kyle, Samadi, Tuzun (CFTC) |
| Fast-trader profits sit with a few firms and are earned from other traders; speed decides who wins | Baron, Brogaard, Kirilenko |
| Speed races between ES and SPY last milliseconds; a handful of firms win most | Budish, Cramton, Shim; Aquilina, Budish, O'Neill |
| Fading short moves pays more when the VIX is high | Nagel, "Evaporating Liquidity" |
| Stop orders cluster just past round numbers and set off cascades (currency data, not futures) | Osler (New York Fed) |
| Displayed depth misleads: depth can fall while volume rises | CME 2025 |
| Retail futures traders lose overall; a few large losses dominate | CFTC 2024 |

What follows for this project: market orders are the honest cost
model; resting orders to save the spread are filled mostly when wrong;
speed, queue position and market making are closed to a retail
account; book depth is not intent. CME's Trade at Marker Close (TMAC)
may suit an exit at 16:00; whether a given broker offers it is not
known here.

## 7. Building it without fooling ourselves

- **Freeze, then test.** Every rule, threshold and bar is written down
  and committed before the data is read; each window is read once.
- **Count the tries.** Many waves have now looked at the same bars. A
  result on them is weaker than its t says (deflated Sharpe; White's
  reality check). Unread data is the only clean test.
- **Start from the market's odds**, and from base rates, before any
  model.
- **Triple-barrier labels and meta-labeling** (López de Prado, chapters
  3, 7 and 12) fit A's structure and the grading of A and B.
- **Keep score forward.** A forecast written down before the fact and
  scored after is the only kind that accumulates evidence.
- **Lessons usually drawn from Renaissance** (from published accounts,
  not from the firm): many small edges, not one large one; costs
  modelled first; clean data; one system, not overridden by hand.

## 8. Data: what exists and what it costs

Buying is the operator's decision. Nothing here was bought, and
licensed data never goes into this repository.

**Free**

| Source | What |
| --- | --- |
| FRED (St. Louis Fed) | VXN since 2001, VIX since 1990, RVX since 2004, daily closes; Treasury yields |
| Federal Reserve | FOMC meeting dates, past and scheduled |
| Bureau of Labor Statistics | CPI and employment release dates (its pages refuse automated downloads; save them from a browser) |
| CME Daily Bulletin, section 40 | open interest by strike for NQ options, each day, no history: an archive has to be built by saving it daily |
| CFTC | weekly positioning report |

**Paid, raw option data (transparent, testable)**

| Source | Listed price | What |
| --- | --- | --- |
| ORATS | about $99 a month plus $599 once for history from 2007 | QQQ, NDX, SPY, SPX end-of-day with open interest and greeks |
| ThetaData | $40 to $160 a month | option history with open interest and greeks |
| Databento | pay per use, or $199 a month with live data | includes options on NQ futures |
| Cboe DataShop, Open-Close | on request | the data that labels buyers and sellers; Cboe's exchanges only, so not NDX |
| OptionMetrics | yearly licence | the academic standard since 1996 |

**Paid, ready-made gamma levels (method not disclosed):** SpotGamma
(about $99 to $299 a month), SqueezeMetrics (about $720 a month),
MenthorQ (ES and NQ futures options), Unusual Whales, FlashAlpha. Their
history is mostly not as it was known each day, so it cannot be tested
honestly; usable as a chart overlay.

**Order of spending, if any:** the free price-based readings first
(wave thirty-three). Only if they show something: raw history to
compute a QQQ and NDX gamma estimate as it stood each day; then data
that signs dealer positions.

## 9. Roadmap

**Frozen now, to be read once on ES, RTY and NQ**

| Wave | Question | Kind |
| --- | --- | --- |
| 31 | does a range regime, used for size, make A and B steadier? | judged |
| 32 | when in the day does B earn, and for how long? | reported; one rule judged |
| 33 | does B work when dealers are likely short gamma, read from price? | reported; two rules judged |
| 34 | does the options market's forecast of the range beat HAR? | judged |
| 35 | how often would the account plan lose the account, and at what size is that rare? | planning only |

**Next, after those reads**

1. **The state sheet:** one line a session, written before the open and
   at fixed times: expected range (wave thirty-four's forecast), RVMR,
   FALL, MODE, calendar and event flags.
2. **The odds tables:** for each state, how often A and B won and how
   far the day went, on data read so far; labelled as exposed.
3. **The forward log:** the sheet's forecasts written down before the
   fact on sessions from 2026-11-16, scored after; no orders.
4. **Decay rules:** fixed in advance, when a forecast or a rule is
   retired.
5. **The prop account's own rules** in place of wave twenty-six's
   account, once the firm is known.
6. **Event dates** for CPI and employment reports from the official
   archives, added to the events file.

**Later, and only on unread data**

- drift bursts on recordings from 2026-11-16;
- an archive of NQ option open interest from CME's daily bulletin;
- dealer gamma from bought option history, if wave thirty-three shows
  something and the operator decides to buy;
- slow trend on large-tick contracts, if the account's rules allow a
  position overnight.

**Not planned:** speed, market making, reading book depth as intent,
news sentiment, machine-learned direction, day-type lore without an
out-of-sample test.

## 10. Reading

Harris, *Trading and Exchanges*; Lebron, *The Laws of Trading*;
Bouchaud and co-authors, *Trades, Quotes and Prices*; López de Prado,
*Advances in Financial Machine Learning*; Chan, *Algorithmic Trading*
(chapter 7). Ongoing: Quantpedia, Alpha Architect, Concretum, the New
York Fed's Liberty Street Economics, BIS bulletins, CME research.

## Sources

- Baltussen, Da, Lammers, Martens, Hedging demand and market intraday momentum: https://academicweb.nd.edu/~zda/intramom.pdf
- Gao, Han, Li, Zhou, Market intraday momentum: https://econpapers.repec.org/RePEc:eee:jfinec:v:129:y:2018:i:2:p:394-414
- Zarattini, Aziz, Barbon, Beat the Market: https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content
- Paz, replication of Beat the Market: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7290621
- Delgado, replication of Beat the Market: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7323419
- Concretum, Do leveraged ETFs fuel intraday trends?: https://concretumgroup.substack.com/p/do-leveraged-etfs-fuel-intraday-trends
- Barbon, Beckmeyer, Buraschi, Moerke, Liquidity provision to leveraged ETFs: https://papers.ssrn.com/abstract=3925725
- Opening-range breakout on five indices (replication): https://www.mql5.com/en/blogs/post/776235
- Opening-range breakout on QQQ (replication): https://github.com/giovannibrusco/zarattini-2023-orb-qqq
- New York Fed, The disappearing overnight drift: https://libertystreeteconomics.newyorkfed.org/2026/07/the-disappearing-overnight-drift/
- Kurov, Wolfe, Gilbert, The disappearing pre-FOMC announcement drift: https://ideas.repec.org/a/eee/finlet/v40y2021ics1544612320315956.html
- Takahashi, order flow and price at one second: https://arxiv.org/abs/2508.06788
- Lillo, Farmer, The long memory of the efficient market: https://arxiv.org/abs/cond-mat/0311053
- Kolm, Turiel, Westray, Deep order flow imbalance: https://papers.ssrn.com/abstract=3900141
- Briola, Bartolucci, Aste, Deep limit order book forecasting: https://arxiv.org/abs/2403.09267
- Upadhyay, Do time-series foundation models forecast index-futures returns?: https://arxiv.org/abs/2611.12141
- Mesfin, OHLCV signals in MNQ, a falsification study: https://arxiv.org/abs/2605.04004
- McLean, Pontiff, Does academic research destroy stock return predictability?: https://ivey.uwo.ca/media/3775549/pontiff.pdf
- Ni, Pearson, Poteshman, White, Does option trading have a pervasive impact on underlying stock prices?: https://econpapers.repec.org/RePEc:oup:rfinst:v:34:y:2021:i:4:p:1952-1986.
- Barbon, Buraschi, Gamma Fragility: https://abarbon.com/papers/gamma-fragility
- Quantpedia, Do S&P 500 0DTE options increase market volatility? (Dim, Eraker, Vilkov; Adams, Fontaine, Ornthanalai): https://quantpedia.com/do-sp500-0dtes-options-increase-market-volatility/
- Beckmeyer, Branger, Gayda, Retail traders love 0DTE options (summary): https://www.cxoadvisory.com/individual-investing/retail-0dte-option-trader-performance
- Cboe, 0DTEs decoded: https://www.cboe.com/insights/posts/0-dt-es-decoded-positioning-trends-and-market-impact
- Glassnode, the problem with open-interest-based gamma: https://research.glassnode.com/gamma-exposure/
- Safari, Schmidhuber, Trends and reversion from minutes to decades: https://arxiv.org/abs/2501.16772
- Kurth, Eisler, Rej, Bouchaud, Is trend still your friend?: https://arxiv.org/abs/2607.01550
- Baule, Schlie, Zhou, return autocorrelation by horizon: https://www.fernuni-hagen.de/igas/docs/cesa_wp_14.pdf
- van Kervel, Menkveld, High-frequency trading around large institutional orders: https://ideas.repec.org/a/bla/jfinan/v74y2019i3p1091-1137.html
- Christensen, Oomen, Renò, The drift burst hypothesis: https://arxiv.org/abs/2601.08974
- Giot, implied volatility indexes and their information content: https://research.dial.uclouvain.be/bitstreams/e9598957-28ce-4552-a1b9-1bb4d353f721/download
- Albers, VIX1D next-day volatility forecasts: https://ideas.repec.org/a/wly/jfutmk/v45y2025i11p2092-2108.html
- HARd to Beat, HAR against machine learning: https://arxiv.org/html/2406.08041v1
- Patton, Sheppard, Good volatility, bad volatility: https://public.econ.duke.edu/~ap172/Patton_Sheppard_Realized_Semivariance_7oct11.pdf
- LSEG, How markets react to CPI surprises: https://www.lseg.com/content/dam/data-analytics/en_us/documents/ebooks/lseg-tick-history-research-paper-how-markets-react-to-cpi-surprises.pdf
- CME, How FX and equities trade economic data: https://www.cmegroup.com/insights/economic-research/2025/how-fx-equities-trade-economic-data-sets.html
- Alpha Architect, The performance of volatility-managed portfolios: https://alphaarchitect.com/the-performance-of-volatility-managed-portfolios/
- Market simulation under adverse selection (ES and NQ fills): https://arxiv.org/abs/2409.12721
- Kirilenko, Kyle, Samadi, Tuzun, The Flash Crash: https://www.cftc.gov/idc/groups/public/@economicanalysis/documents/file/oce_flashcrash0314.pdf
- Baron, Brogaard, Kirilenko, Risk and return in high-frequency trading: https://www.cftc.gov/idc/groups/public/@economicanalysis/documents/file/oce_riskandreturn0414.pdf
- Budish, Cramton, Shim, The high-frequency trading arms race: https://econpapers.repec.org/RePEc:oup:qjecon:v:130:y:2015:i:4:p:1547-1621
- Aquilina, Budish, O'Neill, Quantifying the high-frequency trading arms race: https://www.nber.org/papers/w29011
- Nagel, Evaporating liquidity: https://www.nber.org/papers/w17653
- Osler, Stop-loss orders and price cascades: https://www.newyorkfed.org/research/staff_reports/sr150.html
- CME, Reassessing liquidity beyond order book depth: https://www.cmegroup.com/articles/2025/reassessing-liquidity-beyond-order-book-depth.html
- CME, Trade Marker at Close FAQ: https://www.cmegroup.com/articles/faqs/faq-trade-marker-at-close-tmac.html
- CFTC, Retail traders in futures markets: https://www.cftc.gov/sites/default/files/2024-02/Retail_Traders_Futures_V2_website_ada.pdf
- López de Prado, Advances in Financial Machine Learning (contents): https://catalogimages.wiley.com/images/db/pdf/9781119482086.toc.pdf
- FRED, VXNCLS, VIXCLS, RVXCLS: https://fred.stlouisfed.org/series/VXNCLS
- Federal Reserve, FOMC calendars: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
- Bureau of Labor Statistics, CPI release archive: https://www.bls.gov/bls/news-release/cpi.htm
- Bureau of Labor Statistics, employment situation archive: https://www.bls.gov/bls/news-release/empsit.htm
- CME Daily Bulletin, section 40, Nasdaq-100 options: https://www.cmegroup.com/daily_bulletin/current/Section40_Nasdaq_100_And_E_Mini_Nasdaq_100_Options.pdf
- ORATS: https://orats.com/near-eod-data
- ThetaData pricing: https://thetadata.net/pricing
- Databento futures data: https://databento.com/futures
- Cboe DataShop Open-Close: https://datashop.cboe.com/volume-summary-data
- SpotGamma subscription cost: https://support.spotgamma.com/hc/en-us/articles/1500002666102-What-is-the-cost-of-a-SpotGamma-Subscription
- MenthorQ, gamma levels on futures options: https://menthorq.com/guide/gamma-levels-on-futures-options/
