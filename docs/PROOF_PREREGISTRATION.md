# PRO-OF-V1 — PRE-REGISTRATION (professional order-flow family)

**Committed before any PRO-OF outcome was computed.** Track A: M = 8
hypotheses testable on existing data. Track B: 7 concepts requiring data
we do not have — capture specifications only, never backtested on
proxies. All Track-A rules are **EXPLORATORY-DERIVED**; no true
historical OOS remains. Frozen shelf untouched; no prospective OFH13
outcomes used.

## Data audit (the gating deliverable)

| field | status |
|---|---|
| 1m OHLCV, total/bid/ask volume, delta, delta%, cum delta, min/max delta | **AVAILABLE** |
| imbalance counts, stacked summaries (2x/3x/4x) | AVAILABLE |
| volume per up/down tick, price-progress ticks | AVAILABLE |
| absorption candidate flags + strength | AVAILABLE (bar-level proxy, capture's own) |
| relVolume (standardized participation) | AVAILABLE (capture-native) |
| developing profile POC/VAH/VAL, insideValueArea | AVAILABLE, verified causal |
| HVN/LVN **counts** | AVAILABLE |
| HVN/LVN **price locations** | NOT AVAILABLE — **PROXY ONLY** derivable by smearing 1m volume across bar ranges; declared for H7 below, in advance |
| developing VWAP | NOT AVAILABLE |
| 3m/15m swings, prior-day H/L, session H/L | DERIVABLE CAUSALLY (established machinery) |
| 30-second OHLCV | AVAILABLE 2025-09→2026-05, ~09:30–11:00 ET only |
| footprint-at-price ladder | **NOT AVAILABLE** (MODE1_SUMMARY) |
| tick-by-tick trades / time & sales / trade timestamps | **NOT AVAILABLE** |
| Level-2 / MBP depth, MBO, DOM snapshots | **NOT AVAILABLE** (`f_depthHistoryAvailable = FALSE`) |
| add/cancel/modify, icebergs, queue/replenishment | **NOT AVAILABLE** |
| synchronized ES order flow | **NOT AVAILABLE** (no ES capture exists) |

**Consequence:** PRO-OF-H9…H15 are **CAPTURE REQUIRED — NOT
HISTORICALLY TESTABLE**. They receive frozen capture specifications
only. No iceberg, pulling/stacking, sweep, tape-speed, ES-lead or DOM
aggregation claim will be made from bar-level data.

## Frozen constants (set before results)

| quantity | value | provenance |
|---|---|---|
| aggression | opposing/aligned \|delta\| ≥ 511 | long-frozen Q_BD75 |
| balance width cut | 30-bar range/ATR ≤ **5.283** | DEV median, frozen now |
| extreme-flow bar | \|delta\| ≥ **1293** | DEV q99, frozen now |
| CVD margin | 586 | RED-phase freeze, reused |
| elevated participation | relVolume ≥ 2.0 | capture-native standardization |
| acceptance window | 5 bars; acceptance = ≥4 of 5 closes beyond the boundary | fixed |
| rejection window | reclaim close within 10 bars | fixed |
| entry gate / cooldown / costs / partitions / outcomes / ff / controls | identical to RED / V4.2 phases | established |

## Track A rules (LONG stated; SHORT mirror)

**H1 — auction breakout acceptance.** Balance = the prior 30 consecutive
bars with range/ATR ≤ 5.283; boundary = that window's high. Breakout bar
= first close above the boundary. Aggression = breakout-bar delta ≥ +511.
**Acceptance** = during the next 5 bars, ≥ 4 closes above the boundary
and no close back below. Entry at the 5th bar's close (after acceptance
is knowable). Ablation: breakout only · +delta · +acceptance · full.

**H2 — headfake.** Same balance. Price closes below the balance low,
volume/participation elevated outside (relVol ≥ 2.0 or |delta| ≥ 511 on
an outside bar), then within 10 bars a completed close back **inside**
the balance. Entry at the reclaim close, target direction = interior.
Controls: excursion only · outside-volume only · reclaim only · full.
Also reported: excursion distance, bars outside, delta outside.

**H3 — stop-run resolution, two arms.** Extreme = confirmed 15m swing
(primary; 3m and prior-day reported separately). Excursion bar trades
beyond the extreme with relVol ≥ 2.0. **ARM A accepted:** 3 consecutive
closes beyond the old extreme within 10 bars → enter WITH the run at the
3rd close. **ARM B rejected:** a close back through the old extreme
within 5 bars, without 3-closes-beyond first → enter AGAINST the run at
the reclaim close. Primary question: do the two arms' forward
distributions genuinely differ (and from matched controls)?

**H4 — low-participation pullback.** Impulse = 5 consecutive bars moving
≥ 1.5 ATR with aligned delta sum ≥ 511. Pullback = the following bars
retracing ≤ 61.8% of the impulse. **Participation contraction** =
pullback median relVolume ≤ 0.5 × impulse median relVolume AND pullback
opposing-delta sum magnitude ≤ 0.5 × impulse delta. Resumption = close
beyond the impulse extreme within 20 bars of the impulse end. Entry
there. Control: identical price shape with participation ratio > 1.0
(noisy pullback).

**H5 — extreme flow bar: reaction, not the bar.** Extreme bar =
|delta| ≥ 1293. Classification at bar+5 (fixed): **ACCEPTED** = last
close beyond the extreme bar's high (bullish case); **REJECTED** = last
close below the extreme bar's open (full retrace); else NEUTRAL. Two
tested arms, both entered at the classification close: ACCEPTED →
continuation WITH the bar; REJECTED → reversal AGAINST the bar. The
bar-alone control is entry at the extreme bar's own close.

**H6 — value-area edge auction response.** Developing profile ready;
price touches VAH from inside. **REJECTION** = within 3 bars a close
back inside by ≥ 0.25 ATR → enter toward POC (short at VAH, long at
VAL). **ACCEPTANCE** = 3 consecutive closes outside within 5 bars →
enter away from value at the 3rd close. The two states are never
pooled. Diagnostics: volume/delta/time outside, re-entry rate.

**H7 — LVN traversal (PROXY ONLY, declared).** Causal volume-at-price
histogram per session built by smearing each completed 1m bar's volume
uniformly across its range (25-tick bins); LVN = any bin below 25% of
the session's running median bin volume, HVN = above 200%, both
knowable only from completed bars. Entry: a close crossing into an LVN
band moving away from the nearest HVN, with aligned delta ≥ +511;
continuation target = traversal. Control: equal-width non-LVN zones,
matched entries. This tests the *concept's proxy*, and is labelled so.

**H8 — persistent CVD divergence as continuation.** Window = 30
consecutive bars: price change ≥ +1 ATR while cumDelta change ≤ −586.
Arms: **fade** (short, the classic interpretation) vs **continuation**
(long, the absorption interpretation) — same events, opposite sides —
vs ordinary momentum control (price ≥ +1 ATR with cumDelta ≥ +586) vs
divergence + structure failure (price also closed below the latest 3m
swing low → fade only). Entry at window-end close.

## Track B capture specifications

Written as deliverables 24–31 in the findings document: exact NT8
fields for MBO/depth (H9–H12, H15), tick/T&S for equal-volume bars
(H13), and a synchronized ES Volumetric capture (H14). No historical
claims will be made for any of them.

## Gates

Raw-geometry gate; survivor-only management (structural / 1 / 1.5 / 2
ATR stops; 15/30/45/60 m; 0.5–3 R plateaus); matched controls
(direction, hour, ATR quintile, partition); sign-flip-by-day p,
day-clustered CI, BH q at M = 8; monotonicity over cherry-picked cells;
tail-concentration downgrade; long/short and DEV→IR splits mandatory.
"NO ROBUST ORDER-FLOW EDGE FOUND IN CURRENT BAR-LEVEL DATA" is an
acceptable and useful outcome, and if it occurs the recommendation is
Track-B capture, not variant generation.
