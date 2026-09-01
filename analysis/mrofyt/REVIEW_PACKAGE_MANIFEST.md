# REVIEW_PACKAGE_MANIFEST.md — v01.4 independent-verification package

Everything a reviewer needs to re-run the claimed suites and the
read-only recorder proof, with pinned hashes (requirement 10).
Verified by `tests_mrofyt_v01_4.py` on every run.

## Recorder (read-only proof target)

```
dab3abec22e16255cd27d198200125c5cd6a44192e7ff07d53ce798c755dd63d  src/MlesV1CaptureHost.cs
f4658e9b68f131aa6b568d7034e9a77c5b3171e799c2056cc10bd629571f7ec2  MROF_V1_Engine.zip (scratchpad delivery; recorder inside is byte-identical to src/)
```

Read-only proof: the class is `Indicator` in namespace
`NinjaTrader.NinjaScript.Indicators`; the MLES freeze test greps the
source for every order/account API. Reviewers re-run:
`grep -cE "SubmitOrder|ChangeOrder|CancelOrder|Account\." src/MlesV1CaptureHost.cs` → expect 0 matches on API calls
(the only hit is the comment documenting this prohibition).

## Engine integration files (42/42 claim)

```
d38b653707cbd31fba3d11e82ee3b6d3373cb534bba10357e1fc2809f4027538  analysis/mrof/mrof_engine.py
86048409233d7b563348f6174337b00d354a337b799af5ae109d382f8340bf9f  analysis/mrof/tests_mrof.py
ae74a5ece5199efed2586bf71cad2d4ceff3627eb3cdcf5f789a3521eab9e053  analysis/mles/mles_integrity.py
```

Command: `python3 analysis/mrof/tests_mrof.py` → **42/42**.

## Registry closure (15/15 claim)

```
ed861c3ea75f87a42f3a8348d9581d0d9a31814f09822408df96e737a977c0a2  analysis/mofad/tests_closure.py
aa90aeeba1f9eb8d11d48c9020b869a4093cc2236abe0e2e3e9def5608ab246e  analysis/mofad/similarity_screen.py
```

Command: `python3 analysis/mofad/tests_closure.py` → **15/15**.
(The registry CSV and fingerprints JSON evolve by design as waves are
registered; the closure suite validates their mutual consistency.)

## Wave suites

```
python3 analysis/mrofyt/tests_mrofyt.py          →  59/59
python3 analysis/mrofyt/tests_mrofyt_v01_1.py    →  56/56
python3 analysis/mrofyt/tests_mrofyt_v01_2.py    →  31/31
python3 analysis/mrofyt/tests_mrofyt_v01_3.py    →  32/32
python3 analysis/mrofyt/tests_mrofyt_v01_4.py    →  (this wave)
```
