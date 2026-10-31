# MROF_YT_W6_W7_DEV_FREEZE.md — waves five, six and seven on DEV; the frozen cuts, committed before any held-out read

**Committed 2026-10-31, before any replay holdout or validation session
was read by wave six or wave seven.** The operator ran the three tools
on 2026-10-30/31 against the old drive (`D:\MLES_Capture`, newest
recording 2026-10-22 21:19). This file pins the two frozen-cut files
those runs wrote and records, from the operator's screenshots, what the
DEV runs showed. DEV sessions were seen before every registration
involved: **everything below describes; nothing here is a verdict.**

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** No order was placed.

## Sessions

- **Read (DEV, 15):** 20260901, 0902, 0903, 0904, 0905, 0908, 0909,
  0910, 0911, 0913, 0914, 0915, 0916, 0917, 0918.
- **Refused unread (validation, 23):** 20260921, 0922, 0923, 0924, 0925,
  0929, 0930, 1005, 1006, 1007, 1008, 1009, 1011, 1012, 1013, 1014,
  1015, 1016, 1019, 1020, 1021, 1022, 1023. They stay blind until the
  checkpoint.

## Frozen files

```
d09cef66ac9d84a2f3df2713973990a19b6bd0ed8cfa8dd5d1426faee71d5689  frozen_dev_20261031/w6_frozen.json (wave six, registration A4: trapped cut NQ 0.0, MNQ 0.0)
030ee8bb3f7815ec6bd560a551615298060d812abb33101451eb32685cf798d3  frozen_dev_20261031/w7_frozen.json (wave seven, §3-§4: trapped median NQ FAILED 17, NQ HELD 103, MNQ FAILED 90, MNQ HELD 358; 90th percentile of |D| NQ 33, MNQ 135)
```

These are the files `--evaluate … --holdout` and `--evaluate …
--unblind` read. They are not changed after this commit.

**Recorded consequence, not a change.** Wave six's trapped cut is the
DEV median (A4), and the median L2 event had no aggressive contracts a
tick or more beyond the level, so the cut is 0 on both instruments and
T5 keeps every L2 event: T5 is identical to T1 as registered. By A4
and "Explicitly NOT registered" the cut stays as frozen; T5 still
counts in Holm's five. The likely reason (pending the event list in
`w6.json`) is that the frozen L2 detector's `returned_through_level`
is the runner's `ap.returned`, which is also set when an approach ends
by retreating, so many L2 events are rejections near a level that never
traded through it.

## What the DEV runs showed (NQ; MNQ beside where it matters)

**Wave six** (L2 at the six daily range levels; every event, not one
position at a time; target 25 points, 30 min):

| test | n | hit | net points | net R |
| --- | --- | --- | --- | --- |
| T1 L2, fixed 15-point stop | 116 | 0.491 | +4.38 | +0.292 |
| T2 L2, STRUCTURAL stop (mean 5.1 points) | 116 | 0.233 | +1.86 | +0.234 |
| T3 L2, FLOW-INVALIDATION | 116 | 0.328 | +3.01 | +0.151 |
| T4 L4, fixed | 29 | 0.517 | +6.14 | +0.409 |
| T5 = T1 (cut 0) | 116 | 0.491 | +4.38 | +0.292 |

MNQ: T1 +1.89, T2 −0.89, T3 +0.05, T4 +3.57 net points; none
separates from zero.

**Wave seven** (order-flow levels; grade A or A+; one position at a
time; net after costs):

| test | n | win | net R | net points |
| --- | --- | --- | --- | --- |
| F1 FAILED, E1 next level | 18 | 28 % | −0.177 | +0.25 |
| F2 FAILED, E2 tape | 124 | 29 % | −0.033 | −0.59 |
| F3 FAILED, E3 hybrid | 18 | 28 % | −0.484 | −1.56 |
| F4 FAILED, E4 25 / 15 | 100 | 37 % | −0.061 | −0.91 |
| H1–H4 HELD | 0–5 | — | — | — |
| G grade slope (E4, every event) | 265 | — | +0.017 per point | p 0.86 |

Events NQ: FAILED A+ 18, A 117, B 92, skip 12; HELD A+ 1, A 4, B 12,
skip 9. E4 net R by grade: FAILED A+ −0.156, A +0.094, B −0.321, skip
+0.292. MNQ: F2 −1.14 net points, F4 −0.49; G +0.182 (p 0.12). On
DEV, the levels the tape builds all day produce many more setups than
the daily levels and no edge after costs, and the grade does not order
them.

**Wave five** (exit study): no sign met the nomination rule on either
instrument (`w5_nominated.json` holds 0 signs), so wave five has
nothing to validate. Holding a 20-point run with the 10-point trail is
worth about zero (NQ +0.01, MNQ −0.04 points). Half-life, descriptive:
L2 on NQ moves +0.39 / +1.83 / +1.26 / +0.52 / +0.84 points beyond its
hour's baseline at 5 s / 30 s / 1 min / 2 min / 5 min, then −2.15 /
−7.70 / −8.75 at 10 min / 30 min / 1 h.

## What happens next

The replay holdout (NinjaTrader Market Replay sessions before
2026-09-01, once a replay recording exists) and then the checkpoint
read these frozen files. No setting above is changed in light of these
DEV numbers. Any idea they suggest, such as a shorter L2 hold, needs its
own registration before the sessions that judge it are read.
