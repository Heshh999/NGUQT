# BRK-V1 — FINDINGS

Pre-registered at commit `e5054d6` **before any result existed**.
Reproduction gate PASS: 355,455 bars, 952 OFH6 signals, 133 OFH13.
Declared M = 3. OFH13_PROSPECTIVE_V1 untouched.

## **HEADLINE: NOTHING PROMOTED. All three cells failed, one of them
## because I specified it wrongly.**

| cell | p | BH q | verdict |
|---|---|---|---|
| BRK-H1 bracket | 0.0015 | 0.0045 | **NOT PROMOTED** — fails gate conditions 3 and 4 |
| BRK-H2 15s compression | — | — | **VOID** — gate unsatisfiable by construction (my error) |
| OVN-H1 overnight drift | 0.4130 | 0.6195 | NOT PROMOTED |

BRK-H1 is the reason the promotion gate was written with **four**
conditions instead of one. It clears q and it clears the CI, and it is
still not tradeable. Read the next section before believing any headline
q-value in this repo, including mine.

---

## BRK-H1 — magnitude-event bracket

```
SIGNAL brackets    n 952   mean  -4.16  med -24.51  win 23.9%  CI [-8.49, +0.60]
CONTROL brackets   n 4575  mean -12.82  med -23.75  win 20.4%  CI [-25.88, +4.89]
PAIRED delta       n 915   mean  +8.23  CI [+3.18, +13.56]  p 0.0015  (q 0.0045)
```

### Why this is not an edge, despite q = 0.0045

**1. Both sides lose money.** The signal bracket returns **−4.16 points
per signal** with a 23.9% win rate. The paired result says only that a
straddle at a signal minute bleeds *less* than a straddle at a matched
control minute. "Loses less than a control" is not a strategy.

**2. Gate condition 3 — sign stability: FAILED.**

| partition | n | mean Δ | CI | p |
|---|---|---|---|---|
| U | 132 | **−0.24** | [−5.79, +5.15] | 0.9266 |
| DEV | 361 | **−4.72** | [−11.80, +2.24] | 0.1835 |
| IR | 422 | **+21.96** | [+14.06, +31.59] | 0.0001 |

The entire effect lives in IR. It is nil in U and **negative** in DEV.
The pooled +8.23 is IR dominance, not a stable property.

**3. Gate condition 4 — tail domination: FAILED.**

| trades removed | mean Δ |
|---|---|
| none | +8.23 |
| top 1% (9 of 915) | +4.12 |
| top 5% (45 of 915) | **−3.79** |
| top 10% (91 of 915) | **−10.59** |

Forty-five trades out of 915 carry the whole result, and removing them
flips the sign.

**4. The effect is in the CONTROL, not the signal.** This is the finding
that actually matters:

| | U | DEV | IR |
|---|---|---|---|
| **signal** | −4.17 | −3.27 | −4.91 |
| **control** | −6.92 | **+1.46** | **−26.87** |

The signal side is remarkably *stable* across all three eras. It is the
control that swings 28 points. The paired delta is therefore measuring a
property of **my control construction under IR volatility** — controls
are drawn ≥ 60 min from any OFH6 signal, i.e. from quiet minutes, and a
0.5-ATR straddle placed in a quiet IR minute gets chopped to pieces. It
is not measuring a property of OFH6 signals.

**Verdict: NOT PROMOTED.** A significant q on an unstable,
tail-dominated, unprofitable cell whose effect traces to the control
arm is exactly the failure mode this family's gate was built to catch.

### The secondary result — the cleanest confirmation yet

**OFH6 direction matched the fill side on 460 of 952 brackets = 48.3%.**

This is the 61st independent confirmation that order flow does not
predict direction, and it is the cleanest instrument the programme has
produced: the bracket never chooses a side, so the market's own choice
is measured without any modelling in between. 48.3% against a 50% null.

Also notable: **fill rate was 100% (952/952)** — a ±0.5 ATR straddle is
touched within 30 minutes every single time, so bracket life is inert
(15, 30 and 60 minutes give byte-identical results). The structure has
no selectivity at all; it is simply "trade the first 0.5-ATR move."

Sensitivity (pre-declared, reported, never promoted): offsets 0.25/0.75
and ambiguity handling OPTIMISTIC/EXCLUDE all move the signal mean
between −10.41 and −0.16. **Every variant loses money.** No setting of
this structure is profitable.

---

## BRK-H2 — 15s compression → expansion: **VOID (my specification error)**

Zero events. This is not a bug and not a data problem — contiguity held
on 72,993 of 73,031 boxes and the ATR lookup resolved on 72,962.

```
boxes evaluated 72,962
range / ATR1m:  min 0.690   p01 1.111   median 2.080
gate demanded:  <= 0.350
```

**The minimum observed value is twice the threshold.** The cause is
dimensional: I compared a **5-minute** range (20 × 15s bars) against a
**1-minute** ATR and required the range to be a third of it. A 5-minute
range naturally runs about 2× a 1-minute ATR. The test was incoherent
from the moment I wrote it, and it was frozen that way.

**It was NOT re-run with a looser threshold.** Retuning a gate using the
data that exposed the error is precisely the overfitting this
methodology exists to prevent, and a "result" from it would be
worthless. BRK-H2 keeps p = 1.0 in the family accounting, and **M stays
at 3** — shrinking a declared family after a cell voids would flatter
the survivors.

A corrected form (compare the box range against `5 × ATR1m`, or against
the box-range distribution's own low quantile) requires a **fresh
pre-registration** and data not used to pick the threshold. The honest
descriptive fact for whoever writes it: 5-minute ranges run 0.69× to
2.08× the 1m ATR, so a meaningful compression gate sits near the 1.1
p01, not 0.35.

---

## OVN-H1 — overnight drift

```
n 260 nights   mean +10.24   med +18.00   win 55.8%
CI [-14.67, +34.44]   sign-flip p 0.4130   q 0.6195
by partition:  U +18.25   DEV -5.09   IR +22.18
top 1% 6.4%   top 10% 45.5%
```

**NOT PROMOTED.** The mean is positive and it is the *least*
tail-dependent cell in the family (top 10% carries 45.5%, versus 75.7%
for the bracket), but the CI is enormous and crosses zero, p = 0.41, and
DEV is negative. At n = 260 nights a +10 point mean with a 49-point-wide
CI is indistinguishable from noise.

The honest reading: MNQ plausibly carried overnight drift this year, but
one year of nights cannot demonstrate it, and this is the one cell where
more data would genuinely settle the question — the rule has **zero
fitted parameters**, so it cannot be overfit, and years of prior MNQ/NQ
history could test it without any of the multiple-comparison problems
that plague the rest of the programme.

**Implementation defect fixed mid-run** (disclosed): the first run
returned zero nights because no 1-minute bar *closes* at 18:00 — the
session opens then, so its first bar closes at 18:01. The rule now takes
the first bar at or after 18:00 and the last at or before 09:29, which
is a faithful reading of the pre-registered intent, not a spec change.

---

## REC-P1 — registered prospective, no backtest

Frozen in `analysis/brk/rec_p1_spec.py`, spec hash **`e6805d67e8930a9d`**,
lifted verbatim from `mrv_run.py::mr_h3` with `arm='RECLAIM'` — read
from source, not from memory.

**Deliberately NOT wired into the NT8 host.** Adding a candidate to
`V41FrozenCandidateEngine.cs` would invalidate the cand_spec / ofh6 /
ofht hashes and force a full parity re-verification while the
prospective ledger is mid-collection. That is not a cost worth paying
for a signal-only candidate. REC-P1 is evaluated offline from the same
1m order-flow capture the host already writes. The frozen engine is
untouched.

No backtest was run, by design: both prior tests (PRO-OF-H3 n=476,
MR-H3 n=581) spent the same 12 months, so no untouched history remains
and re-mining would produce a number with no evidential value.

---

## What this family actually bought

Three structural classes were opened and the prior — expect all three to
fail — held.

1. **Brackets do not monetize the magnitude effect.** The straddle fills
   100% of the time, has no selectivity, and loses money at every offset
   and every ambiguity convention tested. The magnitude signal is real
   but it is *symmetric round-trip* movement, not drift after a break —
   which is the specific question sixty directional tests could not
   isolate, and it is now answered.
2. **Sub-minute compression is untested**, because I mis-specified the
   gate. That is a real cost of this batch and it is mine.
3. **Overnight carry is unresolved** and is the only remaining thread
   with a clean path to resolution, because it has no free parameters.

The 48.3% fill-side result is the durable output: the cleanest
measurement yet of the programme's central claim, from an instrument
that cannot bias it.

**OFH13_PROSPECTIVE_V1 remains the best specification and remains
untouched. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
