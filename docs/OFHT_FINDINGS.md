# OFH7-OFH10: Timing Entries on Frozen OFH6 Context

**Date:** 2026-08-21
**Spec (pre-registered, frozen before first run):** `analysis/v41/ofht_spec.py`
**Run:** `analysis/v41/ofht_run.py` - full output in the session scratchpad
(`ofht_out.txt`), per-entry diagnostics in `ofht_entries_*.csv`.
**Question:** after frozen OFH6 identifies direction, does a second causal
timing event (sweep-reclaim, opposing-vector failure, parent-wick defense,
liquidity trap) give a better ENTRY LOCATION - lower MAE, higher MFE/MAE,
favourable-first ordering?

Naming: the retired exploratory labels OFH7/OFH9 from `ofh.py` are
unrelated (x-OFH7 effort-result, x-OFH9 value reversion). This family is
the four timing hypotheses of the 2026-08-21 directive. Partitions are
DEV (<= 2026-03-31) and INTERNAL REPLICATION (IR, 2026-04+). Neither is
OOS. Family size M=4; every correction uses it. All excesses vs side- and
split-matched baselines; horizon 60m; cost 0.87 pt.

---

## Baseline and context decay

OFH6 immediate entry (n=783): excess +8.19, medMFE/medMAE **1.026**,
1-ATR favourable-first **48.1%**. The bar the timing events must beat.

Entering in the OFH6 direction Δ minutes after the signal:

| Δ | n | excess | ff1 |
|---|---|---|---|
| 0 | 783 | +8.19 | 48.1 |
| 15 | 783 | +8.74 | 49.3 |
| 30 | 783 | +8.02 | 52.5 |
| 45 | 769 | **+1.61** | 49.2 |
| 60 | 748 | **-0.02** | 50.5 |

**The OFH6 information is fully spent between 30 and 45 minutes.** This
is a clean, useful measurement: the 30-minute context life declared as
primary was the right one, and any timing event that waits longer than
~30 minutes is waiting past the edge.

## Results (primary configuration, L=30)

| | n | excess | medMFE/medMAE | ff1 (Δ vs 48.1) | DEV / IR excess | verdict input |
|---|---|---|---|---|---|---|
| OFH7 sweep+vector reclaim | 54 | +11.74 | 1.011 | 51.9 (+3.7pp, p=.30) | +14.8 / +9.1 | ordering hint, tiny n |
| OFH8 opposing-vector failure | 222 | +4.86 | 1.042 | 49.1 (+1.0pp, p=.40) | **+10.9 / -0.2** | mean does not replicate |
| OFH9 parent-wick defense | 25 | -6.38 | 1.181 | 44.0 | +35.8 / -39.5 | below MIN_N=40 |
| OFH10 vector trap | 48 | +14.39 | 0.967 | 45.8 (-2.3pp) | +28.7 / +1.2 | geometry WORSE |

Family statistics on the declared endpoint (ff1 improvement over OFH6,
day-clustered bootstrap, BH over M=4): **best q = 0.79**. Sign-flip
permutations: 0.43 / 0.64 / 0.74. Nothing approaches significance.

Ordering replication check (the criterion given the highest weight):
- OFH7 ff1: DEV 44.0 vs IR 58.6 - **not same-sign vs baseline across partitions**
- OFH8 ff1: DEV 49.0 / IR 49.2 - flat in both
- OFH10 ff1: DEV 52.2 / IR 40.0 - degrades

No hypothesis shows repeatable entry asymmetry.

## Control decomposition (the informative part)

OFH7's mandated controls separate the ingredients cleanly:

| variant | n | excess | ratio | ff1 |
|---|---|---|---|---|
| OFH6 + sweep + **vector** reclaim (primary) | 54 | +11.74 | 1.011 | 51.9 |
| OFH6 + sweep + **ordinary** reclaim | 204 | **+18.28** | **1.407** | 50.0 |
| sweep + vector reclaim, **no OFH6** | 404 | -4.42 | 0.949 | 51.1 |
| OFH6 + vector, **no sweep** | 839 | +6.26 | 1.052 | 48.7 |
| matched random | 54 | -8.18 | 1.009 | 57.7 |
| PM-context instead of OFH6 | 38 | +0.55 | 0.862 | 43.2 |

Reading: **OFH6 direction is the active ingredient** (+11.7 with it,
-4.4 without; price-momentum context +0.6 - it is the cumulative delta,
not momentum). **The sweep location helps. The VECTOR trigger hurts** -
the ordinary-reclaim control beats the vector-reclaim primary on mean
(+18.3 vs +11.7) and on geometry (ratio 1.407 vs 1.011). Waiting for a
climax-volume candle means entering after a burst, at a worse price.
Per the directive this control observation is RECORDED AND NOT ACTED ON:
no OFH11 is created from it, and OFH7 is not modified.

Elsewhere: OFH8's opposing-vector event without OFH6 is worthless
(+0.93, n=959), so its DEV-only mean was the context, not the event.
OFH10's mean is matched by its own PM-context control (+16.4 vs +14.4),
so it is not even delta-specific. OFH9's controls all sit at n<=140 with
sign disagreements - nothing interpretable at this frequency.

## Stop family

Gate (declared): only OFH8 qualified (marginally). Structural stop:
DEV +9.83 / IR **-2.76**; 1.0 ATR: +1.36 / -7.62; 1.5 ATR: +11.93 /
-5.18. Not replicated; no target testing justified. OFH7/OFH9/OFH10
failed the gate (ratio or ff1 below baseline, or n<40).

## Concentration and stability (primaries)

- OFH7: 17/28 weeks positive; top 2 trades = +419 of +587 total.
- OFH8: 22/42 weeks positive; top 11 trades = +2,397 of +887 total
  (the other 211 trades are net -1,510).
- OFH10: 13/26 weeks positive; ONE trade = +602 of +649 total.
- OFH9: 11/19 weeks positive; total negative.

## Final ranking

Weighted per the directive (repeatable entry asymmetry above raw points):

1. **OFH7** - the only positive ordering signal (+3.7pp ff1, ff05 57.7),
   context-specific by its controls, but n=54, p=0.30, ratio 1.011, and
   the ordering does not replicate across partitions.
2. **OFH8** - the only adequate sample (n=222), and with it a clean
   negative: geometry flat, DEV mean vanishes in IR.
3. **OFH10** - raw points high but geometry worse than baseline and the
   PM control matches it; one trade carries the total.
4. **OFH9** - n=25; nothing measurable.

## Verdicts

| hypothesis | verdict |
|---|---|
| OFH7 | **INTERESTING BUT INCONCLUSIVE** |
| OFH8 | **FAILED INTERNAL REPLICATION** |
| OFH9 | **INSUFFICIENT SAMPLE** |
| OFH10 | **NO MEASURABLE INCREMENTAL VALUE** |

## The answer

**DID ANY OFH6 TIMING METHOD CONVERT CUMULATIVE-DELTA DIRECTIONAL
INFORMATION INTO A MEANINGFULLY BETTER ENTRY LOCATION?**

# NO

- against the corrected family endpoint: best BH q = 0.79;
- against the decisive criterion: no hypothesis improved MFE/MAE or
  favourable-first ordering in a way that held across both partitions;
- with the caveat that OFH7/OFH9/OFH10 ran at n = 25-54, so for those
  three the power to detect a real geometry improvement was low - the
  answer for them is "no evidence", not "proven absent". OFH8, at
  n=222, is a genuine negative.

Two by-products stand regardless: the OFH6 context lifespan is now
measured (spent by ~45 minutes), and the OFH7 control decomposition
shows the context and the sweep location carry information while the
climax-vector trigger degrades the entry. Both are recorded; neither is
acted on. Per the directive: no OFH11, no re-tuning of these four.
2026-09+ capture months remain untouched prospective data for the
frozen OFH6 spec.

*THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.*
