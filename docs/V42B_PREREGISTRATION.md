# V4.2-B MECHANISM EXPANSION — PRE-REGISTRATION (H-NEW1 … H-NEW15)

**Committed before any H-NEW outcome was computed.** M = 15. Nothing
added after results. Frozen shelf untouched; no prospective OFH13 data
used for discovery. Canonical reproduction re-verified immediately
before this commit (355,455 bars; 952 signals; 133/462/218/477/845).

**All fifteen are EXPLORATORY-DERIVED.** The 12-month history has been
examined many times; **no true historical OOS remains**. DEV/IR are
internal partitions. Confirmation requires future data.

## Shared frozen machinery (reused, never refit)

| piece | value | provenance |
|---|---|---|
| FVG | canonical `cand_spec.build_fvg` (displacement-embedded) | canonical |
| mitigation semantics | canonical `_mitigate` (far-side close invalidates; touch = wick; trigger = close beyond midpoint) | canonical |
| aggression / "attack" | opposing `\|delta\| ≥ 511` (Q_BD75) | frozen long ago |
| FVG life | formation + 30 min (studies needing longer observation state it) | V4.2 convention |
| entry gate | RTH, ≥60 min to close, valid ATR | canonical |
| cooldown | 30 min chronological per arm | canonical convention |
| costs | 0.87 pt RT; sensitivity +1/+2 ticks | frozen |
| partitions | U ≤ 2025-11-01 · DEV ≤ 2026-03-31 · IR → 2026-08-19 | established |

## Effort / result / efficiency framework (ONE primary, frozen)

Per bar, on the opposing side of a candidate long/short:

- `effort = |opposing delta| / rolling-median |delta| (60 bars, causal)`
- `result = adverse tick progress × 0.25 / ATR`
- `efficiency = result / max(effort, ε)`
- `failure  = effort / max(result, ε)`  ← **this is E2**

**E2 is the frozen primary and its failure cut is the already-frozen
DEV q75 = 15.9608 from the RED phase — reused, not refit.** Buy-side
efficiency uses positive delta and upside tick progress symmetrically.
No further formulations are searched in this batch.

## Shared episode record

One pass over every canonical FVG extracts, per mitigation episode:
touch bar; every attack bar (opposing |delta| ≥ 511) with its effort,
result, efficiency and E2; the running adverse extreme; the trigger bar
(close beyond midpoint) with mitigation depth
`(zHi − ext)/(zHi − zLo)`; reclaim speed `trigger − last attack`;
distance from entry to the zone's far side in ATR; and the count of
bars under elevated opposing pressure. All fifteen FVG-based studies are
filters or bucketings of this one record set, so they are mutually
consistent by construction.

## The fifteen rules (LONG stated; SHORT = exact mirror)

**H-NEW1 Persistent failed aggression.** ≥2 distinct failed attacks
(each E2 ≥ 15.9608), separated by ≥1 non-attack bar, inside one episode,
then the trigger. Control: exactly 1 failed attack.

**H-NEW2 Failure speed.** On events with ≥1 failed attack + trigger:
`speed = trigger_j − last_attack_j`. Buckets **FAST 1–2 · MEDIUM 3–5 ·
SLOW 6+**. Success = monotone FAST > MEDIUM > SLOW.

**H-NEW3 FVG depth.** `depth = (zHi − ext)/(zHi − zLo)` at trigger.
Bins **SHALLOW <1/3 · MIDDLE 1/3–2/3 · DEEP >2/3**. Tested for depth
alone (all mitigations), failed aggression alone, and both.

**H-NEW4 Weakening second attack.** ≥2 attacks; `r = effort₂/effort₁`.
**WEAKER ≤0.75 · EQUAL 0.75–1.25 · STRONGER >1.25**.

**H-NEW5 Deteriorating price result.** ≥2 attacks with effort maintained
(`effort₂ ≥ 0.9 × effort₁`); bucket `result₂/result₁`:
**NONE ≥1.0 · MODERATE 0.5–1.0 · STRONG <0.5**.

**H-NEW6 Displacement → FVG → failed opposing flow → re-expansion**
(continuation). Impulse delta over the three formation bars aligned
(≥ +511 long). First touch episode; ≥1 failed attack; trigger =
completed close **above the zone high** within 10 bars. Controls:
displacement only · displacement+FVG · FVG+weak pullback · FVG+failed
aggression · full.

**H-NEW7 Proximity to structural invalidation.** On the failed-aggression
event set, distance from entry to (a) FVG far side, (b) nearest
confirmed 3m swing, (c) 15m swing, (d) sweep extreme, (e) displacement
origin — **each reported separately, never pooled**. Bins **NEAR <0.5
ATR · MID 0.5–1.5 · FAR >1.5**.

**H-NEW8 Failed aggression after a sweep.** A causally-known low was
traded through within 15 bars before the attack. Reported separately for
3m, 15m, prior-day, plus a no-sweep control and an FVG+sweep+failure arm.

**H-NEW9 Delta acceleration × price deceleration.** Across the first two
attacks: `Δeffort = effort₂ − effort₁`, `Δresult = result₂ − result₁`.
States **A** accel+accel · **B** accel+flat (|Δresult| ≤ 0.1) ·
**C** accel+decel · **D** weaken+decel. Pre-declared prediction: **C is
strongest**.

**H-NEW10 Aggression-efficiency flip.** A failed sell attack (E2 ≥ cut),
then within the episode a buy-aggression bar (`delta ≥ +511`) whose buy
efficiency ≥ **2.0 ×** the failed attack's sell efficiency, then the
trigger. Controls: delta sign flip only · failed aggression only ·
opposite aggression only · full flip.

**H-NEW11 Relative buy/sell efficiency (continuous, non-FVG).** At every
entry-ok bar, rolling 15-bar buy and sell efficiency; ratio
`buy_eff / max(sell_eff, ε)`. Quintiles → forward geometry. Compared
head-to-head with quintiles of raw delta, rolling delta, and price
momentum on the same bars.

**H-NEW12 Confirmed parent → 30s micro-pullback → re-expansion**
(execution). Canonical OFH13 parents, unchanged, restricted to genuine
30s coverage (2025-09→2026-05, ~09:30–11:00 ET, **OHLCV only — no 30s
delta will be invented**). Arm A = canonical 1m entry. Arm B = after the
1m trigger, first 30s bar closing against direction (micro-pullback, no
parent invalidation), then enter on the first 30s bar closing back with
direction. **Per-parent EV is primary**; unfilled parents count as 0.

**H-NEW13 Setup quality score (diagnostic only).** Five pre-declared
binary dimensions: ≥2 failed attacks · FAST reclaim · DEEP mitigation ·
NEAR invalidation · efficiency flip present. Each is first tested
individually; the score is built **on DEV only** from those that are
monotone there, then evaluated on IR. Score = count of satisfied
dimensions (0/1 each, **no fitted weights**). **Never used to filter or
size OFH13 or any prospective trade.**

**H-NEW14 Failed breakdown of an FVG.** Bullish FVG; a completed close
**below zLo** (apparent invalidation); within 10 bars a failed sell
attack (E2 ≥ cut); then a completed close back **above zHi** (full
reclaim). Entry at that close. Controls: ordinary mitigation · ordinary
failed aggression · breakdown without reclaim · full.

**H-NEW15 Time under pressure.** Within an episode, count bars where
opposing |delta| exceeds the rolling median while the adverse extreme
has not extended more than 0.25 ATR beyond the initial touch extreme.
Bins **1 · 2–3 · 4–5 · 6+**, reported **within ATR terciles** to control
for volatility.

## Gates, statistics, verdicts

Raw-geometry gate before any management (MFE/MAE, favourable-first, MAE,
median, matched-control advantage). Survivors only: broad mechanical
stops (structure / FVG invalidation / sweep extreme / 1 / 1.5 / 2 ATR)
and plateau-seeking exits (15/30/45/60 m; 0.5–3 R). Matched controls on
direction, hour, ATR quintile, partition. Statistics: sign-flip-by-day p,
day-clustered bootstrap CI, BH q at **M = 15**. Bucket studies are judged
on **monotonicity**, not on a single cell's p-value; a single winning
extreme bucket is called fragile. Small samples stay visibly small
regardless of p. Verdict vocabulary as specified. **"None survived" is a
successful result.**
