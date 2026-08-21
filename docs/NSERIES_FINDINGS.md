# N-Series — 12 New Hypotheses, the Noise Floor, and the Autopsy

Date 2026-08-21. Twelve new event-class hypotheses, directions and
mechanisms declared before the run, all twelve reported. Scripts:
analysis/v41/nseries.py, nseries2.py. HOLD (2024-07 onward) NOT read.

## The result that frames everything else

The identical 12-way search was re-run on **within-day-shuffled
outcomes** — same events, same rules, relationships destroyed:

| | real data | pure noise |
|---|---|---|
| best DEV mean of the 12 | **+1.509** (N7) | median **+1.485**, p90 +3.30, max +6.45 |
| hypotheses positive every year, both splits | **0 of 12** | ≥1 in **4%** of shuffles |

**The best of twelve real hypotheses landed exactly at the median of
what randomness produces**, and the real data failed the
"positive every year" test that noise passes 4% of the time. Twelve
tries was not enough tries to beat chance — it was enough to measure
chance, and we lost to it.

## The twelve (net pts/trade @ 0.87 cost, 60m)

| id | event class | dir | DEV | VAL |
|---|---|---|---|---|
| N1 | equal-high/low sweep (liquidity pool) | fade | −2.77 | +0.15 |
| N2 | ≥3 pushes, poor progress | fade | +0.81 | −2.42 |
| N3 | tightest compression + break | follow | −1.58 | −1.18 |
| N4 | widest compression + break | fade | −1.04 | +1.19 |
| N5 | quiet tape >4h + break | follow | −1.50 | −0.92 |
| N6 | W/M neckline break + retest | follow | +0.57 | −1.67 |
| N7 | day's first 09:30–10:30 break | fade | **+1.51** | −4.75 |
| N8 | ADR ≥100% consumed | fade | −0.84 | +1.04 |
| N9 | 4H range regime + break | fade | −0.13 | −0.37 |
| N10 | ≥2 ATR from VWAP | fade | −3.15 | −1.66 |
| N11 | wicked beyond but no close beyond | fade | −1.09 | −0.63 |
| N12 | EMA fan aligned + break with it | follow | +0.49 | −0.68 |

Not one is positive in both splits at 60m. Every DEV winner inverts.

## Autopsy — why the best five lose

Median excursion **in the traded direction** (fades measured on the
fade's own favourable/adverse):

| id | DEV ratio | VAL ratio |
|---|---|---|
| N7 | 1.045 | 0.940 |
| N2 | 0.973 | 0.956 |
| N6 | 1.027 | 1.106 |
| N12 | 1.055 | 1.082 |
| N9 | 1.060 | 1.022 |

All within a few percent of 1.0. **The losing mechanism is the same
one found everywhere else in this programme**: these entries have no
location advantage, so the trade is a coin flip and cost decides it.

A 5 × 5 stop × horizon grid (none / 1.0 / 1.5 / 2.0 / 3.0 ATR ×
15 / 30 / 60 / 120 / 240 min) was run on each. For N7, N2 and N9 —
**no cell of 25 is positive in both splits.** Better stops do not
repair them, exactly as the earlier stop-family study predicted:
with symmetric excursion the stop moves variance, not the mean.

Two cells did survive. One is a spike, one is a plateau:

- **N6** at no-stop / 240m: +3.22 / +2.29 — but the adjacent 1.0 ATR
  cell is −2.26 / −1.59. A sign flip from one neighbouring cell is
  fragility, not an edge. Rejected.
- **N12** at 1.0 ATR / 240m: +0.95 / +0.98, and the surrounding cells
  (1.0–2.0 ATR × 120–240m) are positive in both splits too. A real
  plateau, n=7,099. That one earned a proper test.

## N12 dissected — and why it is beta, not edge

"EMA fan aligned + break in the fan's direction, hold 4h, 1.0 ATR stop":

| | DEV | VAL | by year |
|---|---|---|---|
| N12 all | +0.945 | +0.981 | −0.10, +0.29, +1.45, +1.55, +0.27, +2.41 |
| **N12 LONG only** | **+2.467** | **+2.821** | −0.48, +3.65, +2.63, +2.49, +1.85, +4.67 |
| **N12 SHORT only** | **−1.611** | **−2.224** | +1.02, −8.02, −0.81, +0.74, −2.35, −1.95 |

The long side carries everything; the short side loses in both splits
and in 4 of 6 years. That is the signature of **directional drift, not
predictive information** — and the matched baseline confirms it:

| | DEV | VAL |
|---|---|---|
| all breaks, LONG | −0.21 | **+1.03** |
| all breaks, SHORT | −1.49 | −2.68 |

**Every long-biased rule on this instrument prints money in
2019–2024 because NQ went up.** N12's long edge over the unconditional
long baseline is +2.47 vs −0.21 (DEV) and +2.82 vs +1.03 (VAL) — the
DEV gap does not survive into VAL at anything like the same size, and
the short side, where drift cannot help, is decisively negative. A
rule that only works on the side the market was already going is not
an edge; it is leveraged exposure with extra commission.

Also worth stating plainly: 7,099 trades, ~1,290/year, **+$2,468/year
gross on one contract with a $4,702 max drawdown** — before slippage
on 1,290 round turns, and it needs an account several times that
drawdown to survive.

## Answer to the question asked

**No — there is no hypothesis here with positive EV and good
risk-to-reward that would have been profitable every year.** Twelve
new event classes, 125 stop × horizon cells, and a formal noise floor
say the same thing, and the noise floor says something sharper: the
best result we produced is indistinguishable from what shuffled
outcomes produce, and "profitable every year" is a bar that *noise
clears 4% of the time* while our real hypotheses cleared it 0%.

The one plateau that survived is long-only market drift.

**On the specific request**: selecting for "positive every year" on
data we have already seen is the single most reliable way to
manufacture a curve fit — it is a filter with roughly 2^6 = 64-to-1
selectivity applied to a set we can enumerate cheaply. The noise
floor above is what that filter yields on data with no signal at all.
That is why I ran the control before reporting any winner, and why
the two cells that passed got dissected rather than promoted.
