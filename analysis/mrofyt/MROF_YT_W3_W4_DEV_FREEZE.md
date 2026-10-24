# MROF_YT_W3_W4_DEV_FREEZE.md — waves three and four on DEV, frozen before any validation read

**Status: FROZEN 2026-10-24.** The operator's first complete wave-four
search (which also produced wave three's real-level report from the same
read) is committed here byte for byte. This commit is wave four's
hypothesis set (`MROF_YT_WAVE4_DISCOVERY_REGISTRATION.md` §5) and records
which wave-three pattern is carried to the December checkpoint
(`MROF_YT_WAVE3_BIGMOVE_REGISTRATION.md` §6). Nothing below changes a
threshold, feature, stop, target, limit, cooldown or rule.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** No order was placed.
Every number is a mid-to-mid first touch on recorded tape, before costs.

## 1. What was read

- DEV sessions `<= 20260918`, all already labelled `EXPOSED_PILOT_DEV`:
  20260901, 0902, 0903, 0904, 0905, 0908, 0909, 0910, 0911, 0913, 0914,
  0915, 0916, 0917, 0918 (15).
- **Refused, not read:** the 23 sessions 20260921 → 20261023 that were
  on the drive. Both reports list them. No event or fire in `w3.json`
  carries a session later than 20260918 (checked on the committed file).
  The validation sessions remain unexamined by waves three and four.
- Command (operator's machine, 2026-10-23/24):
  `python mrofyt_discover.py "D:\MLES_Capture" --out C:\MROF\reports\w4.json --nominated-out C:\MROF\reports\w4_nominated.json --w3-out C:\MROF\reports\w3.json`
  with `mrofyt_discover.py` 3500fcc3… on runner MROF-YT-RUNNER-1.2.2
  (package V24 or V25; Amendment 23 changed nothing a one-folder read
  sees).

## 2. Frozen files

```
88a7caf41cd48e4a5440f3d4c8cd3ffb2ee9f61988b07a3f892015bdd1a92dad  frozen_dev_20261024/w4_nominated.json
193ff50f5efc3dc96fac9ca15ee4305d9d84fb215d79a9c9e4913d4131e46252  frozen_dev_20261024/w4.json
d37309f75f55094c42f8568be4cccf5a597f546e5140e34f936ef0ddb192b67d  w3.json (uncompressed; 29 MB, so stored as below)
18a576a8e787dae311ef0737b56d314e8e0ca57b3bdd9eca102bf75fef6859ac  frozen_dev_20261024/w3.json.gz (gzip -9 -n of the file above)
```

`w4_nominated.json` is the file `--evaluate` reads at the checkpoint.
Its `nominated` list is identical to the one inside `w4.json`.

## 3. Carried to the December checkpoint

### Wave three — one pattern

Holm over the 24 NQ tests on DEV rejected exactly one:

| pattern | stop | NQ events | hit | matched base | lift (95 % interval) | p | expectancy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **L2 SWEEP_RECLAIM** | **60 ticks** | 116 | 0.4914 | 0.3368 | +0.1545 (+0.0624, +0.2482) | 0.001 | +5.00 pts |

L2 is carried forward at `S = 60` ticks, the only stop that survived
(§6). Its validation verdict is §6's table: 30+ NQ events, lift positive
with the 95 % interval excluding 0, and the placebo-level lift not
positive (so the checkpoint read uses `--both`).

Not carried forward: G1, G2, G3, L3 (did not survive Holm); L4 (29
resolved NQ events, under §5's 30); D1 (3); L1 (0, see §5 below).

### Wave four — five leads, no candidates

0 of 2 208 tests met §4 (best q = 0.377). The five nominees are all
**LEAD** (eligible under §5, not CANDIDATE):

| # | rule | stop | DEV n / sessions | lift | t | q | expectancy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `SS:trend30.top.q+dist_vwap.bottom.q:with:trend30` | 40 | 90 / 8 | +0.1515 | 4.704 | 0.804 | +5.92 |
| 2 | `US:dist_level.top.q+z_bi3.top.q:against:z_bi3` | 60 | 356 / 7 | +0.0519 | 4.596 | 0.804 | +1.63 |
| 3 | `U:range30.top.d:against:D60` | 80 | 551 / 13 | +0.0732 | 4.536 | 0.377 | +2.22 |
| 4 | `SS:z_d180.bottom.q+dist_vwap.bottom.q:with:z_d180` | 80 | 167 / 8 | +0.0614 | 3.421 | 1.000 | +0.62 |
| 5 | `SS:resp180.bottom.q+trend30.top.q:against:resp180` | 80 | 274 / 13 | +0.0553 | 3.359 | 0.821 | +2.88 |

Numeric cut-points, direction, target, limit and cooldown are in
`w4_nominated.json`. They are judged once, Holm over the five (§6).

## 4. Checkpoint commands — December, not before

First confirm the local copy is the frozen one:
`certutil -hashfile C:\MROF\reports\w4_nominated.json SHA256` must print
`88a7caf4…dad`; if it does not, use the committed copy.

```
python mrofyt_discover.py "D:\MLES_Capture;E:\MLES_Capture" --evaluate C:\MROF\reports\w4_nominated.json --unblind --out C:\MROF\reports\w4_validation.json
python mrofyt_bigmove.py "D:\MLES_Capture;E:\MLES_Capture" --both --unblind --out C:\MROF\reports\w3_validation.json
```

Each `--unblind` read writes the validation sessions to the exposure
ledger permanently.

## 5. Read after the run — descriptive, not tests

Computed here from the committed `w3.json` events. Nothing in this
section is a test, and nothing in it changes §3.

**L2 by session (NQ, stop 60).** Events fell on 6 of the 15 sessions:
20260909 (1), 0914 (10), 0915 (7), 0916 (55), 0917 (17), 0918 (26). The
level and flip inputs need history, which the first week lacks.
Expectancy was positive on all six. Leaving out any one session leaves
+4.68 to +5.38 points per event. 20260916, the FOMC decision day, holds
55 of the 116.

**One position at a time.** Overlapping events share a price path, so
116 events are not 116 trades. Taking an event only when the previous
taken one has resolved gives 57 NQ events: 30 targets, +6.76 points
each, +385.5 in total, of which +280.0 is on 20260916. MNQ, taken the
same way: 67 events, +1.54 each, with three of seven sessions negative.

Read: L2 is a lead worth its one judgement, not a finding. Its DEV
support is essentially one week (14–18 September) including an FOMC
day. The registered interval resamples events, not sessions, so it is
narrower than the session-to-session variation warrants.

**L1 never fired.** There were 0 events on 15 sessions. The function
matches §1 (suite `B3d`). Its conjunction (`clean_cross`, `held_5s`,
`persist_agree >= 3`, flow `z >= 1.5`, at four levels inside
09:30–10:00) is the held-break combination wave one's A6 needs, and A6
has never fired either. `clean_cross` with `held_5s` does occur at range
levels: it is L4's break memory, behind 151 raw L4 fires. So the binding
constraints are the window and the flow conditions. The read is that L1
is too strict for this tape, not broken. It is not changed (§9).
