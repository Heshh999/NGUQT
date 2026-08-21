# VEC-H1 Findings — Confirmatory Verdict

Date 2026-08-21. Executes docs/VECH1_PREREGISTRATION.md, which was
frozen on 2026-08-20 BEFORE the capture existed. This is the first
hypothesis in the programme tested under a preregistration that
predates its own data. Script: analysis/v41/vech1_confirm.py.

**The HOLD (2024-07 onward) was never opened.** VEC-H1 failed DEV and
VAL, so under the frozen rules the holdout stays sealed — still clean
for whatever is preregistered next.

## Capture integrity (all 18,913 rows, 7.1 years)

Zero entries at or before their parent close; delays all within the
one-candle window [1,14] min; zero arm-definition violations; zero
duplicate arms; every stop exactly 1.5 × parent ATR; wick, colour and
proximity rules satisfied on every row; 15,764 qualifying parents;
sides balanced (9,372 long / 9,541 short); stable yearly counts. The
audit's "LOOKAHEAD REJECTED 15754" is the boundary-bar counter from
the pre-fix build (one same-stamp bar per parent, correctly excluded);
the CSV proves the actual violation count is 0.

## Step 0 — the mandated symmetry check

| split | arm | medMFE | medMAE | ratio |
|---|---|---|---|---|
| DEV | C_FULL | 1.529 R | 1.700 R | **0.899** |
| VAL | C_FULL | 1.926 R | 1.936 R | **0.995** |

The known prior held: the C arm's adverse excursion equals or exceeds
its favorable excursion. There was no asymmetry to harvest before a
single expectancy number was computed.

## The gates (mean net points at 60m)

| split | C n | C gross | C @base | A | B | verdict |
|---|---|---|---|---|---|---|
| DEV | 1,248 | **−0.440** | −1.310 | −0.396 | +1.901 | FAIL — every gate |
| VAL | 614 | **−1.176** | −2.046 | +0.855 | −0.740 | FAIL — every gate |

All p-values 0.51–0.94. C is negative in both splits, worse than A in
both splits, negative in 5 of 6 years (only 2022 +0.50), and both
sides lose. Win rate at 1R: 44.5% in both splits — a coin flip minus
costs.

**The arm contrasts did exactly the job they were built for.** The
hypothesis says the 1m vector AT the parent's extreme is the signal.
The data says the full conjunction is the WORST of the three arms:
location-without-vector (A) beats it in both splits, and
vector-away-from-location (B) swings +1.9 → −0.7 between splits —
regime noise. Had only "1m vector follows 15m vector" been tested
without the matched arms, DEV would have looked promising at +1.9 and
VAL would have destroyed it. The control structure prevented that
story from ever being told.

## Verdict

**VEC-H1 FAILS.** Per the preregistration's own text: the base
hypothesis will NOT be rescued by adding EMA, time-of-day, level,
order-flow, wick-size or proximity filters. It is recorded on the
ledger as tested and rejected.

Programme ledger after this test: V4 0/8, V5 0/10, V4.1 0/8,
TR-H1 management pass negative, pattern/asymmetry scans negative,
VEC-H1 0/1 — across five distinct hypothesis classes on
causally-clean, independently verified data, with the last test
preregistered before its data existed.

The structure HOLD remains the one untouched resource. It should be
spent only on a hypothesis with a genuinely different information
source than 15m/1m OHLCV — everything derivable from that source has
now been tested and has failed symmetrically.
