# Order-Flow Setup Grading (A+ / A- / B+ / B-) — Findings

Date 2026-08-20. Volumetric window only: OF-DEV 2025-11-02..2026-02-28
(n=1,295 events, 102 days), OF-VAL 2026-03-01..2026-05-31 (n=1,038, 79
days). OF-OOS (Jun–Aug 2026) NOT READ. Scripts: analysis/v41/of_grade.py,
of_grade2.py.

Population: non-control structure BREAK events joined to the 1m
volumetric bar closing at the event minute (99.7% join, 3,285/3,294).
Outcome: probe-side signed net at 60m; also reported in R against the
event's own stop.

## Standing-order note
The programme prompt defers grading until a strategy survives. Nothing
has survived, so this is not a tradeable grading system. It is the
pre-registered B2 ablation (STRUCTURE vs STRUCTURE+ORDERFLOW) expressed
as a grade: *does order flow at the event stratify forward outcomes?*

## Two defects found and fixed during this pass

1. **`f_ofCumDeltaSlope` is an exact alias of `f_ofBarDelta`.** The
   engine sets `CumDeltaSlope = CumDeltaChange = cumDelta − prevCumDelta`,
   which is the bar delta by construction
   (MnqV41OrderFlowResearchHost.cs:277). Two columns, one number. The
   first score version counted delta agreement twice.
2. **`f_deltaFailsBreak` = bullish OR bearish divergence**, so it
   overlaps the side-oriented divergence term; the failure side was also
   counted twice.

Double-counting both tails mechanically widens the grade spread. It is
the entire reason v1 looked promising:

| | v1 (double-counted) | v2 (corrected) |
|---|---|---|
| OF-DEV monotone | No | No |
| OF-DEV spread / perm p | +13.9 pt / 0.086 | +9.3 pt / **0.365** |
| OF-VAL monotone | Yes | Yes |
| OF-VAL spread / perm p | +18.4 pt / 0.040 | +66.3 pt / 0.003 |

The corrected OF-VAL "p=0.003" is an artifact of a **16-event B- bin**
averaging −62 pt with mean |net| 88 vs ~49 elsewhere — 16 outliers in
extreme-volatility conditions, not a grade. The same bin is **+1.63 in
OF-DEV (n=29)**. Sign flip on tiny bins is the definition of noise.

## The one contrast that held: A+ vs B+

Chosen *after* seeing the v2 table — a search over contrasts, counted
and labelled EXPLORATORY. Six tests total in this study (v1×2, v2×2,
contrast×2).

| | OF-DEV | OF-VAL |
|---|---|---|
| A+ net R/trade @base | +0.127 (n=124) | +0.048 (n=122) |
| B+ net R/trade @base | +0.006 (n=552) | −0.054 (n=416) |
| difference | +0.121 R | +0.102 R |
| bootstrap 95% CI on diff | [−0.116, +0.357] | [−0.131, +0.343] |
| P(diff ≤ 0) | 0.158 | 0.179 |
| permutation p | 0.120 | 0.130 |

The **difference is remarkably stable** (+0.121 → +0.102 R, 84%
retention). It is also **not statistically distinguishable from zero in
either split**, by two independent methods that agree with each other.

**Confound partly ruled out:** A+ mean ATR ≈ B+ mean ATR (37.1 vs 38.9;
44.5 vs 45.0), so the grade is not simply selecting quiet regimes. But
A+ carries a **50% wider stop** (74 vs 48 pt DEV; 81 vs 56 pt VAL) — the
grade concentrates on wider-structure events, so in R terms it is
partly a stop-size effect. ATR-matched, the edge is not uniform: DEV
low/mid +0.155/+0.154 but high +0.018; VAL low +0.107, mid **−0.018**,
high +0.217. No stable volatility pocket.

**Per-month A+ (net R):** DEV +0.084, −0.045, +0.379, +0.066;
VAL −0.022, −0.057, +0.254. Two of seven months carry the entire
result; five are flat-to-negative.

## Single-ingredient reads (OF-DEV, points, descriptive)
`deltaFailsBreak` TRUE −7.01 vs FALSE +2.27 (n=175) is the strongest
single separator; divergence-against −6.10 vs +1.53 (n=86);
delta-agrees +2.72 vs −0.64 (n=639). Direction is as the H-OF library
predicts — order flow that *contradicts* a break is the informative
side, not order flow that confirms it.

## VERDICT

**WEAK / INCONCLUSIVE — order flow does not currently support an
A+/A-/B+ grading system.**

- The full four-grade ladder is **not monotone in OF-DEV** and its
  OF-VAL monotonicity rests on 16 outlier events.
- The one stable contrast (A+ vs B+, ≈ +0.11 R both splits) fails
  significance in both splits (p ≈ 0.12–0.13, CIs spanning zero) and is
  partly a stop-size artifact.
- Seven months of volumetric history is the binding constraint: A+
  yields ~122 events per split, and two months carry the result.

**This is the most persistent signal the programme has produced** — it
is the only contrast that kept its sign, magnitude and direction across
a split boundary, where the entire structure/vector family flipped. It
is not evidence of an edge, and it must not be traded. It is a reason
to keep capturing volumetric data.

## What would settle it
1. Keep Run B going. At the current rate, ~12 more months roughly
   doubles A+ events per split and would move p≈0.12 to a decisive
   answer either way.
2. Freeze the v2 six-ingredient score and the A+/B+ contrast **exactly
   as written here**, then test once on OF-OOS (Jun–Aug 2026, still
   untouched) — as a genuinely new preregistration, not a rescue.
3. Fix the engine's alias column (`f_ofCumDeltaSlope`) so no future
   analysis double-counts it.

---

# ADDENDUM — $1,000 Account Feasibility (2026-08-20)

**LEDGER: OF-OOS IS SPENT.** June–July 2026 were opened at the user's
explicit direction, after the cost was stated, to illustrate P&L. They
may never again be described as untouched or used as confirmatory
evidence. Script: analysis/v41/acct1000.py.

Not a strategy backtest. Nothing survived validation; the A+ rule below
is a searched cell reported WEAK/INCONCLUSIVE above. The point of this
addendum is that the account-size conclusion holds **whether or not the
edge is real**.

## The asked-for window looks excellent

A+ events, 2R exit, 1 MNQ contract, $2/pt, 0.87 pt round-turn cost:

| period | n | end equity | peak | max DD |
|---|---|---|---|---|
| May–Jul 2026 | 124 | **$4,977** | $5,572 | $2,375 |
| Nov 2025–Apr 2026 (prior) | 209 | $3,022 | $4,003 | $2,623 |
| Nov 2025–Jul 2026 | 333 | $5,999 | $6,594 | $2,623 |

May–Jul returns +298% on $1,000. Taken alone it is the best three-month
stretch in the window.

## Month by month, $1,000 reset each month, 2R

| month | n | end | month | n | end |
|---|---|---|---|---|---|
| 2025-11 | 18 | −45% | 2026-04 | 48 | −63% |
| 2025-12 | 34 | +115% | 2026-05 | 37 | +105% |
| 2026-01 | 35 | +230% | 2026-06 | 41 | +141% |
| **2026-02** | **37** | **−219%** | 2026-07 | 46 | +51% |
| 2026-03 | 37 | +84% | | | |

**February 2026 ends at −$1,189 — the account is destroyed and left in
debit.** The continuous Nov→Jul run "survives" February only because it
entered with ~$4,000 of prior profit. Start date decides everything,
which is the signature of a luck-dependent curve, not an edge.

## Monte Carlo — 5,000 random orderings of the same 333 trades

| account | probability of ruin | median end |
|---|---|---|
| **$1,000** | **50.7%** | **$0** |
| $2,500 | 12.6% | $6,499 |
| $5,000 | 0.4% | $8,999 |
| $10,000 | 0.0% | $13,999 |
| $25,000 | 0.0% | $28,999 |

Same trades, same edge, only the order changed: **a $1,000 account is a
coin flip to be wiped out.** The median outcome is zero.

## Why — the arithmetic

- Median A+ stop over May–Jul: **97 pt = $193 = 19.3% of $1,000** per
  trade, on the smallest position that exists (1 MNQ; there is no
  fraction of a contract).
- Prudent risk of 1–2% on $1,000 is $10–20 = **5–10 MNQ points**. The
  setups need 10–20× that.
- Single worst trade in the pool: **−$650 (65% of the account).**
  Ten worst: −650, −606, −590, −517, −500, −472, −404, −400, −389, −387.
- Longest consecutive stop run: 6 = $1,158 = 116% of the account.
- Account required for 1 contract at these stops: **$9,650 at 2% risk,
  $19,300 at 1%.**

## Verdict

$1,000 cannot trade this. The binding constraint is **account size, not
strategy** — and it would still bind if the edge were fully validated,
because one MNQ contract at a 97-point stop is an irreducible ~$193 of
risk. The honest minimum for this event class is roughly **$10,000**,
and that buys the right to trade an edge that has not been shown to
exist.
