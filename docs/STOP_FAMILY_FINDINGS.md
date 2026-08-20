# Stop Family Re-Test — "Forget the Tight Stops"

Date 2026-08-20. Class D. Entry definitions frozen and unchanged; only
the stop varies. Script: analysis/v41/stopfamily.py.
Structure OOS/LOCKBOX (2024-07 onward) NOT READ.

Method is exact rather than approximated: with a **stop + time exit**
there is no stop-vs-target race, so a stop of size S is hit within the
horizon iff `y_mae_60m >= S`. The capture records adverse excursion at
every horizon, so all eight stops resolve without ordering assumptions
and without the AMBIGUOUS problem. Metric is **net points** — R is not
comparable across stop families because the unit itself changes.

## First: "the stop at the end of the candle" is already in the data

`CANDLE_1M` — the completed 1m entry candle low (long) or high (short),
±1 tick — is exactly the stop that has been called TIGHT throughout this
programme. Measured over 46,081 probes:

- **median distance 4.75 pt = $10 per MNQ contract**
- **hit on 82% of trades** (88–90% on H1)

At that distance it is not an invalidation level, it is a coin flip
paid for with commission. That is why it performs worst or near-worst
almost everywhere.

## The result: the stop barely matters

**ALL-BREAKS, 33,929 DEV / 15,215 VAL probes:**

| stop | median dist | DEV net | stopped | VAL net | stopped |
|---|---|---|---|---|---|
| NONE (time exit only) | — | −1.347 | 0% | −0.762 | 0% |
| CANDLE_1M | 4.75 pt | −0.940 | 82.1% | −1.236 | 82.5% |
| CANDLE_15M | 20.50 pt | −1.151 | 40.7% | −1.272 | 41.6% |
| C15 + 0.25 ATR | 25.45 pt | −1.199 | 31.4% | −1.360 | 31.8% |
| ATR 1.0 | 18.38 pt | −0.756 | 43.8% | −1.033 | 45.0% |
| ATR 1.5 | 27.56 pt | −0.824 | 27.9% | −0.963 | 29.9% |
| ATR 2.0 | 36.75 pt | −0.970 | 18.1% | −0.924 | 20.4% |
| STRUCTURAL | 43.25 pt | −0.982 | 14.1% | −1.253 | 15.0% |

**The entire spread across all eight stop choices is 0.59 pt (DEV) and
0.60 pt (VAL) — smaller than the 0.87 pt cost of trading.** Choosing
the stop matters less than the commission.

This is the direct consequence of the symmetric-excursion result
(medMFE ≈ medMAE). With no drift, expectancy ≈ −cost whatever the stop:
a stop relocates variance, not the mean.

## 64 hypothesis × stop cells: 3 positive in both splits

All three are TR-H1, the candidate already killed on other grounds:

| cell | DEV | VAL |
|---|---|---|
| TRH1 / NONE | +0.337 | +2.119 |
| TRH1 / ATR 1.5 | +0.884 | +0.961 |
| TRH1 / ATR 2.0 | +0.812 | +1.444 |

Three of 64 is *below* what chance alone would produce, and TR-H1's
n is 299/131 with p ≈ 0.31/0.17. Wider stops flatter it slightly; they
do not resurrect it.

Every large-n DEV winner inverts in VAL — H3 ATR 1.5 +0.826 → −3.091,
H4 ATR 1.5 +0.773 → −2.123, H1 ATR 1.0 −0.685 → −2.166.

## Which stop makes the most sense, if an edge is ever found

Mean rank across the eight hypotheses (1 = best of 8):

| stop | DEV rank | VAL rank |
|---|---|---|
| ATR 1.5 | **1.5** | 3.4 |
| ATR 1.0 | 2.9 | 3.8 |
| ATR 2.0 | 3.8 | 3.5 |
| NONE | 4.9 | 2.1 |
| CANDLE_1M | 5.6 | 4.0 |
| STRUCTURAL | 5.2 | 6.0 |
| CANDLE_15M | 6.2 | 5.8 |
| C15 + 0.25 ATR | 5.9 | 7.5 |

**ATR-scaled stops in the 1.0–2.0 range are the only family that ranks
well in both splits** — best average rank, most stable, 18–45% hit
rates that behave like invalidation rather than noise. Median 18–37 pt
= $37–74 per contract.

Candle-based stops rank poorly at both ends: the 1m candle is too tight
(82% hit), and the 15m candle is oddly the *worst* family in DEV
despite being wider — because it scales with the event bar's own range,
which is largest exactly when the break is most likely to fail.

**Recommendation: 1.5 × ATR.** Not because it made money — it did not —
but because it is the most stable-ranking, structurally defensible
choice, and it sizes with volatility instead of with an arbitrary
candle.

## Verdict

Changing the stop does not rescue any hypothesis. The stop was never
the problem; the entries carry no directional information, and the
excursion is symmetric, so every stop converges on −cost. Re-testing
the same entries with a ninth or tenth stop would be searching, and is
not warranted.
