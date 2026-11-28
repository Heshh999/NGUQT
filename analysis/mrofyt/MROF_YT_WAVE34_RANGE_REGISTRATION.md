# MROF_YT_WAVE34_RANGE_REGISTRATION.md — how far: the options market's forecast of the day's range

**Status: FROZEN on 2026-11-28, before the tool was written, before any
forecast below was computed on any bar, and before any ES or RTY bar,
or any NQ bar after 2026-06-11, was read by anything.** What had been
seen beforehand is listed in §0.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on historical bars and public index values. No order
is placed.

---

## 0. Where this comes from, and what was already seen

How far the market will move is the part of the forecast that the
research finds most predictable. RVMR (the frozen range regime) held in
70 of 70 checks on five years. The literature adds two things this file
tests:

- **The options market's own forecast.** Implied volatility (VIX for
  the S&P 500, VXN for the Nasdaq-100, RVX for the Russell 2000) holds
  most of the forecasting information; past prices add a little.
  VIX1D, adjusted for its premium, beat HAR one day ahead (Albers,
  Journal of Futures Markets, 2025). The idea, borrowed from betting
  markets: start from the market's own odds and add only what you know
  beyond them.
- **HAR**, which blends the last day, week and month of volatility,
  reliably beats GARCH-type models; volatility from falls predicts more
  than volatility from rises (Patton and Sheppard, 2015).

**Seen beforehand:** RVMR's replications; the size of NQ's cash ranges
as any chart shows them; the dates of the three index files' first and
last values when they were downloaded from FRED on 2026-11-28 (VXN from
2001-02-02, VIX from 1990-01-02, RVX from 2004-01-02).

**Not seen:** any forecast below, or any error of one, on any bar of any
market; any ES or RTY bar; any NQ bar after 2026-06-11.

## 1. The quantity forecast

For each eligible session (wave twenty-four's), the **cash range**
R = (the highest high − the lowest low of the 390 minutes from 09:30) ÷
the open, on the front contract. Every forecast is of **log R**, made
before the session opens.

## 2. The four forecasts

All four are linear in their inputs, fitted by least squares on log R:

| name | inputs (each known at the previous close) |
| --- | --- |
| **ATR** | log of the mean R of the 14 previous eligible sessions |
| **HAR** | log R of the previous session; log of the mean R of the previous 5; log of the mean R of the previous 22 |
| **IMPLIED** | log of the index's close on the trading day before the session: VXN for NQ, VIX for ES, RVX for RTY |
| **HAR+IMPLIED** | HAR's three and IMPLIED's one |

The index value for a session is its last value dated **before** the
session's date; when that is more than 5 calendar days before, the
session has no IMPLIED input. Sessions are compared only where all four
forecasts exist.

**Walk-forward:** each calendar year is forecast with the coefficients
fitted on every session before that year; the first forecast year is
the third calendar year of the market's sessions. Only forecast years
are scored.

## 3. The verdict

For each scored session, the loss of a forecast is the squared error of
log R. **d** = HAR's loss − HAR+IMPLIED's loss (above 0 when the
options market's forecast helps). **IMPLIED ADDS** when:

- the mean of d is above 0 on ES and above 0 on RTY; and
- over ES and RTY together (a session's d is the average of the markets
  that have it; weeks are ISO weeks) the mean of d is above 0 with a
  **weekly t of 2.5 or more** (wave twenty-eight's statistic).

Otherwise **DOES NOT ADD**. NQ is reported, never judged. What it leads
to: when it adds, the describing tool's expected range starts from the
options market's forecast (HAR+IMPLIED); when it does not, from HAR.
Nothing about trading changes by this file.

## 4. Reported beside, never judged

- For each forecast and market: the mean loss and the out-of-sample R²
  against the scored sessions' mean of log R; HAR against ATR, as d is
  for IMPLIED.
- **Downside volatility:** HAR+IMPLIED with two more inputs, the log of
  the previous session's realized variance from falling minutes and
  from rising minutes (one-minute log changes of the 390 closes).
- **RVMR at 09:35:** the mean error of HAR+IMPLIED (log R less the
  forecast) on sessions whose RVMR state at 09:35 is HIGH and on the
  others, with the frozen `analysis/rvmr/rvmr_spec.py` as wave
  thirty-one reads it.
- **Calendar days:** the mean error of HAR+IMPLIED and the mean log R
  less the overall mean on each kind of day: option-expiry Fridays (the
  third Friday of a month), the quarterly ones (March, June, September,
  December), the last session of a month and of a quarter.
- **Event days**, only when an events file is given: the same for each
  kind it holds (FOMC, FOMC_UNSCHEDULED, CPI, NFP). Its dates come only
  from the official calendars (the Federal Reserve's FOMC pages; the
  Bureau of Labor Statistics' release archives), never from memory.
  Kinds the file does not hold are not reported.

## 5. Reads

- NQ's ten years (already read), ES and RTY (wave twenty-five's 2a
  exports), each read by this wave's own command **once**, recorded
  before any result is shown. The index files are the operator's
  copies of FRED's VXNCLS, VIXCLS and RVXCLS; the tool stops when a
  file's series is not the market's.
- NQ's later months are not read by this wave. Sessions from 2026-07-01
  are never read.

## Explicitly NOT registered

- other inputs, horizons, windows or fitting schemes; machine-learned
  models; the range of the night session
- the forecasts used for sizing, stops or targets: a later file
- markets other than NQ, ES and RTY
- live, paper or simulated order placement

## Expected beforehand (written 2026-11-28, before anything was computed)

Implied volatility is the most consistently useful single input in the
research, and it reacts to news before the bars do. **IMPLIED ADDS:**
about two chances in three. HAR better than ATR: about three in four.
Downside volatility adding a little more: about one in two. RVMR HIGH at
09:35 marking days wilder than the pre-open forecast: about one in two.
Event and expiry days wider than the forecast: likely for FOMC and CPI,
unclear for expiries.
