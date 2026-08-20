# V4 PRE-REGISTRATION — frozen before any outcome was examined

Frozen: 2026-08-19. Data available at freezing: v4_structure (196,799 rows,
2019-09-01 to 2026-08-18), v4_entries (994,692 rows), v4_orderflow (279,834
rows, 2025-11-02 to 2026-08-18, audit PASSED).

Inspected before freezing: schema, column names, dtypes, coverage, row counts,
duplicate checks, causal-timestamp checks, feature-side distributions, label
integrity (non-negativity, monotonicity). **No feature-to-outcome relationship
was examined.**

## SPLIT — declared now, before any result

| Split | Range | Months |
|---|---|---|
| DEV | 2019-09 → 2022-12 | 40 |
| VAL | 2023-01 → 2024-12 | 24 |
| OOS | 2025-01 → 2026-08 | 20 |

Chronological, no shuffling. OOS overlaps the order-flow window (2025-11+),
which is where the V4 incremental test will run if it is warranted at all.

## PRIMARY METRIC — declared now

`net_240m / tfAtr` — forward return at 240 minutes, signed by break direction,
normalised by the event timeframe's ATR.

240m is chosen BEFORE seeing results, for one stated reason: cost is a fixed
number of points, so the longest horizon has the most favourable cost ratio.
That is the entire structural argument for V4 over V3 and it must not be
re-chosen afterwards.

Inference: means clustered by session day; bootstrap over session days, not
over events. Multiple testing: Benjamini-Hochberg across the 8-hypothesis
family below.

Cost: **ASSUMED, NOT MEASURED.** 1.5 points round trip (commission + 1 tick
slippage each side) on MNQ at $2/point. Net figures are provisional and
labelled as such until a measured cost model is supplied.

## THE EIGHT HYPOTHESES

**H1 — DISPLACEMENT CONTINUATION.** 60m breaks classified
CLOSED_BEYOND_DISPLACEMENT show higher forward return in the break direction
than CLOSED_BEYOND_WEAK. *Direction: continuation. Fails if displacement <=
weak, or the CI spans zero.* Rationale: displacement is the observable
signature of participation; a decisive break should carry further than a
marginal one, or "break of structure" carries no information about magnitude.

**H2 — WICK REJECTION REVERSAL.** WICKED_BEYOND on 60m or 15m is followed by
movement AGAINST the break direction. *Direction: reversal. Primary outcome
net_60m signed against the break. Fails if <= 0.* Rationale: a level that
repels price on first touch has defenders; failing to close beyond is the
observable trace.

**H3 — HTF ALIGNMENT IMPROVES CONTINUATION.** For 15m breaks, mean forward
return rises monotonically with `alignAgree` (0-4 across 1d/4h/60m/15m).
*Direction: continuation. Fails if not monotone, or top bucket not above
bottom.* Rationale: the brief's central HTF-to-LTF claim, stated as a testable
gradient rather than assumed.

**H4 — CONFLICT MARKS MEAN REVERSION.** Breaks with `alignOppose >= 3` are
followed by movement against the break. *Direction: mean reversion. Fails if
<= 0.* Rationale: the brief forbids discarding conflict automatically;
conflicting structure may identify range conditions where breaks fail.

**H5 — STRUCTURE PLUS LOCATION.** Breaks with `atLocation == TRUE` show higher
forward return than breaks away from any tracked level. *Direction:
continuation, stronger at location. Fails if no difference or reversed.*
Rationale: the brief's STRUCTURE + LOCATION question, tested as an interaction
rather than assumed.

**H6 — PRIOR FAILURE POISONS THE LEVEL.** Breaks on a timeframe that has
already produced a failed break earlier the same session
(`priorFailedBreakThisTf == TRUE`) underperform those that have not.
*Direction: weaker continuation. Fails if no difference.* Rationale: a level
that has already rejected price once today has demonstrated defenders. Note
this is the causal, before-the-fact version; `failedBreak` itself is a label
and is not usable as an input.

**H7 — COMPRESSION PRECEDES EXPANSION.** Breaks from the lowest tercile of
`tfCompression` produce larger continuation distance (`contMaxAtr`) than
breaks from the highest tercile. *Direction: volatility expansion. Primary
outcome contMaxAtr. Fails if no difference or reversed.* Rationale: energy
released from a coiled range travels further than a break from a range already
extended.

**H8 — BREAKS INTO OPEN SPACE ARE WORSE.** Breaks where the nearest tracked
location is more than 2 ATR away underperform breaks near a level. *Direction:
worse — an avoidance signal, not a selection signal. Fails if no difference.*
Rationale: **carried over from prior V3 research**, where it was the single
largest replicating effect (DEV -0.1353 t=-5.63, VAL -0.2197 t=-6.05). Source
is prior research, not new theory, and it is declared as such. This is a
replication attempt on new event definitions.

## RULES BINDING THIS SET

- All eight are reported, including failures. None is dropped silently.
- No predicted direction or primary horizon is changed after seeing a result.
- Anything discovered after this point is EXPLORATORY and labelled as such.
- A large DEV number that fails VAL is not a finding.
