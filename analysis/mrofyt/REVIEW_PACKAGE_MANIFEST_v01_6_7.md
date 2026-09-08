# REVIEW_PACKAGE_MANIFEST_v01_6_7.md — independent-verification package

Additive. `REVIEW_PACKAGE_MANIFEST.md` (v01.4),
`REVIEW_PACKAGE_MANIFEST_v01_5.md` and `REVIEW_PACKAGE_MANIFEST_v12.md`
stay unchanged and hash-pinned. Every claim below is independently
re-runnable. **THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**

## New in this delivery

```
cb1ac7fa10b59955a467d140e7c17b9318eea525adb29b42c07cb15f64de1057  mrofyt_swings_v016.py
001d80630f0561749899f2ea46707bc339dd91435e082bad6da963c394d8b9de  mrofyt_engine_v016.py
84a0ca89b93eea041a82da37e5afb87c91072d3c8ed75ff77ced17706126b963  tests_mrofyt_v01_6.py
2b1f9f9159fcda2b76d5f9ac16e53771f473278bf7009b98de51cec37c95e17b  MROF_YT_OF01_6_SUCCESSOR_FREEZE.md
b6bd0b05f48a6e26871df69c97fde97112a19d3f4b17da7edf280caa5bdc354d  mrofyt_exits_v017.py
0df5357cce0d0c77c6f38759c757086a067ea90aef8efc1d373a766bbc8fe7f9  tests_mrofyt_v01_7.py
cbd25e6df806db216cf480a3445f1628fc56dff95ea0d903dc197b91ac7b4791  MROF_YT_OF01_7_EXIT_FREEZE.md
a6504d0f991271b6fe9af7f8ddf1d2686700bd91669792bfd0f89079d5ebe3d9  mrofyt_pilot.py
acf033b6bb49367fe347f1a133c5821d98c24c73f8941bdcdb421a763e9a459c  tests_mrofyt_pilot.py
8ab588facfbade92b6be20943dc1888cff2e52f7333f7291f85ed73684e2dd7c  MROF_YT_PILOT_DIAGNOSTIC_FINDINGS.md
50d0ddc78814725011714faf01b1da0d45053d3612cb08095230496ac641c1a2  MROF_ACTUAL_STATE_INVENTORY.md
```

Modified (one file, additively — a skip path, an observation hook and a
run-id field):

```
8332ca65df963d02e6d27786e9569d04590330bb5e8c71f16a369dab2fd359a2  mrofyt_runner.py
```

Archived source directive:

```
55d598a3c2e5453b9c47675f76932455dca8689084fddfd4535e5b4907def942  ../../docs/prompts/MROF_ONE_COMPLETE_CLAUDE_PROMPT_1.md
```

Delivered package (93 files, repo layout preserved so every suite runs
from inside it unchanged):

```
0db8de7a90c2ee43d764e83b31d48b99dddf4dbd2b7c64aff2c29ad46b158069  MROF_V1_Engine_v01_6_7.zip
```

```
cd analysis/mrofyt && for f in tests_*.py; do python3 "$f" | tail -1; done
# run from inside the unzipped package: 370/370, identical to the repo
```

## Predecessors — reverified unmodified

```
74ff9a99e468e22326dad9e01e4ee4dc7ab90c8da7e330a6b5f9e70e9eecb91b  MROF_YT_OF01_FINAL_SOURCE_PROMPT.md
b753a09cc077267a935df37f9b531f2179d920b8f76dc6ee5788628c264f7194  MROF_YT_OF01_5_SUCCESSOR_FREEZE.md
e3da36cd63a18a22935124e852ce8f8b785e96df136d98944f7e88654b1c6847  mrofyt_engine_v015.py
```

Reverified in-suite by `tests_mrofyt_v01_6.py::B19` and
`tests_mrofyt_v01_7.py::C12`, so a predecessor edit breaks the build.

## Reproduce everything

```
cd analysis/mrofyt
for f in tests_*.py; do python3 "$f" | tail -1; done
```

| suite | result |
| --- | --- |
| `tests_mles_v11.py` | 29/29 |
| `tests_mles_v12.py` | 37/37 |
| `tests_mrofyt.py` | 59/59 |
| `tests_mrofyt_pilot.py` | 18/18 |
| `tests_mrofyt_runner.py` | 11/11 |
| `tests_mrofyt_v01_1.py` | 56/56 |
| `tests_mrofyt_v01_2.py` | 31/31 |
| `tests_mrofyt_v01_3.py` | 32/32 |
| `tests_mrofyt_v01_4.py` | 25/25 |
| `tests_mrofyt_v01_5.py` | 36/36 |
| `tests_mrofyt_v01_6.py` | 21/21 |
| `tests_mrofyt_v01_7.py` | 15/15 |
| **total** | **370/370** |

## Runnable research commands

```
python3 mles_v12_audit.py  "<capture folder>"                      # integrity
python3 mrofyt_runner.py   "<capture folder>" --out ledger.json     # outcome-blind
python3 mrofyt_pilot.py    "<capture folder>" --out pilot.json      # §8A diagnostic
```

All three stream at flat memory. `mrofyt_runner.py --outcomes` and
`mrofyt_exits_v017.research_driver()` both raise `STATE-C LOCKED`.

## Read-only no-order proof

```
grep -nE "SubmitOrder|ChangeOrder|CancelOrder|EnterLong|EnterShort|ExitLong|ExitShort" \
     mrofyt_swings_v016.py mrofyt_engine_v016.py mrofyt_exits_v017.py mrofyt_pilot.py
# -> no matches outside header comments documenting the prohibition
```

Enforced in-suite by `B18` and `C12`, which strip comments before
scanning.

## NOT performed here

Real NinjaTrader F5 compilation; Market Replay or live smoke testing;
any market-outcome study. This environment has no NT8, Windows or live
feed. **A stub compile is not an API validation.**

Classification: **`IMPLEMENTATION_COMPLETE` / `INSUFFICIENT_DATA` /
`MARKET_RESEARCH_NOT_RUN` / `PROSPECTIVE_VALIDATION_NOT_STARTED`.**
