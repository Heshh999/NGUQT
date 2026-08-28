# MLES-V1 — DATA READINESS

Machine-readable: `MLES_V1_READINESS_STATUS.json`.
**Every gate is currently BLOCKED. No gate has been claimed passed.**

## Current genuine data
| Asset | Status |
|---|---|
| MNQ 1m OHLCV, 2019-07→2026-08-17 | present, **fully exposed**, not message data |
| MNQ 1m order-flow **bar aggregates**, 315 days | present, exposed; **not raw messages** (§1) |
| 30s OHLCV, 192 days, 09:30–11:00 only | present, exposed; **OHLCV only** — no quotes, depth, queue, or event ordering (§1) |
| ES 1m OHLCV, 42 days | present; **too short and insufficiently synchronized** for lead/lag (§1) |
| Quotes / depth / raw trades / latency / queue / fills | **DO NOT EXIST** |

Captured message files today: **quotes 0, trades 0, depth 0.** The
recorder has never been attached.

## Gates (all frozen now, none reducible later)

**Engineering readiness** — ≥20 outcome-blind capture days; ≥95% session
coverage per instrument; ≥99.9% parse success; zero unexplained
timestamp reversals; bounded/flagged sequence and reconnect gaps;
verified contract mappings and rolls; no persistent crossed book outside
documented feed states; deterministic replay; verifying manifests.
**Have: 0 days.**

**Research readiness (general)** — ≥12 calendar months after the last
material schema change; ≥200 eligible days; ≥1,000 raw triggers; ≥500
effective independent events after clustering and purging; ≥100
effective events per binding subgroup. **Have: 0 of each.**

**OFH13/OFH14 overlay readiness** — ≥100 parent signals; ≥40 unique
parent days; every parent recorded whether or not an overlay would
approve it; complete immutable control ledger. **Have: 0.**

**Cross-market lead/lag readiness** — ≥120 concurrent NQ+ES days; no
unresolved contract/session mismatch; measured cross-stream timing
uncertainty < ⅓ of the claimed median lead; causal opportunity surviving
p99 latency. **Have: 0 days, and clock uncertainty is unmeasured →
currently `NOT IDENTIFIABLE`.**

**Fill-model readiness** — actual BBO at each decision and exit;
measured processing/feed latency distribution; shadow-order
acknowledgements. **Have: none.** Depth is MBP without queue identity,
so **passive fills are `NOT IDENTIFIABLE`** regardless of how much data
accumulates on this feed.

## Honest timeline
20 engineering days ≈ 4 trading weeks. The 12-month/200-day research
floor means **roughly a year of continuous capture** before any general
message-level family can be tested. That is the real cost, and it is not
negotiable downward: large raw message counts never substitute for
unique days, independent episodes, or calendar duration (§9).

`FIVE-YEAR MESSAGE-LEVEL DURABILITY: INSUFFICIENT DATA.`

---
Freeze A commit: `c40f39a18a3741836b7849d0e2ab3c758c0e67e5`
