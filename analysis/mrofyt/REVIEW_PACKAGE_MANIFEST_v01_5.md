# REVIEW_PACKAGE_MANIFEST_v01_5.md — independent-verification package

Additive; the v01.4 `REVIEW_PACKAGE_MANIFEST.md` stays unchanged and
hash-pinned. Every claim below is independently re-runnable.

## Recorders (read-only proof targets)

```
dab3abec22e16255cd27d198200125c5cd6a44192e7ff07d53ce798c755dd63d  src/MlesV1CaptureHost.cs
17a8c347d39e7187f81d7ca1fd6c7161440a8d1bfdc49823f23d1553c419815e  src/MlesV11CaptureHost.cs
f4658e9b68f131aa6b568d7034e9a77c5b3171e799c2056cc10bd629571f7ec2  MROF_V1_Engine.zip (delivered artifact; recorder inside byte-identical to src/MlesV1CaptureHost.cs)
```

Read-only proof (both recorders are `Indicator` classes with no order
API in code):

```
grep -nE "SubmitOrder|ChangeOrder|CancelOrder|Account\.|EnterLong|EnterShort" src/MlesV11CaptureHost.cs
# -> no matches outside the header comment documenting the prohibition
```

C# syntax verification actually performed here:

```
mcs -target:library -out:/dev/null nt8_stubs.cs src/MlesV11CaptureHost.cs   # exit 0
```

The NinjaTrader **F5 compile** and the **five-minute NQ+MNQ Market
Replay smoke test** were **NOT run** — no NinjaTrader, Windows runtime,
data feed or replay database exists in this environment. They remain
user-side (`RECORDER_DEPLOYMENT_v01_3.md` §2, §5, §7).

## Engine + ingestion (42/42 and the v01.5 chain)

```
d38b653707cbd31fba3d11e82ee3b6d3373cb534bba10357e1fc2809f4027538  analysis/mrof/mrof_engine.py
86048409233d7b563348f6174337b00d354a337b799af5ae109d382f8340bf9f  analysis/mrof/tests_mrof.py
ae74a5ece5199efed2586bf71cad2d4ceff3627eb3cdcf5f789a3521eab9e053  analysis/mles/mles_integrity.py
4ce2f94200334dc4597f7c2d79995158b8954e3d523e626dba5657855e53b8e1  analysis/mrofyt/mles_v11_adapter.py
a4aed25eedc161e5c31db4b2144c9393408cdedc4d515229a5d9b2afc5efcbb9  analysis/mrofyt/mles_v11_audit.py
e3da36cd63a18a22935124e852ce8f8b785e96df136d98944f7e88654b1c6847  analysis/mrofyt/mrofyt_engine_v015.py
```

## Test files (all counts claimed in the freezes)

```
c1ce10249dff41f437c6a21b629305b8bc4ac0453d0087475dfb2ea6dfa10e34  analysis/mrofyt/tests_mrofyt.py
30e858e87d7fa81fc2c5ca1466e5f3afc2d14ef3cef6a1bbda4fb41eb467e776  analysis/mrofyt/tests_mrofyt_v01_1.py
ea3770f5e0772d2f46a35f55c3c89d08c5b6ce831bd0c6aaaaa549c45bdb8560  analysis/mrofyt/tests_mrofyt_v01_2.py
788248f531afc7e56ad793fb9a9a8828cdc180d605987c7ca36ab1104a18f971  analysis/mrofyt/tests_mrofyt_v01_3.py
d71e919549e8537d10e42cbc492206bf3a1ee4f8602e703204a27c14f4ba11c0  analysis/mrofyt/tests_mrofyt_v01_4.py
89cb51f4f18d45c1e2c7b1f2a449f763d04b08e5703907f1e5d002f177b78330  analysis/mrofyt/tests_mles_v11.py
2f4c26df78246d739cb8bd3d1efec2cf283c2f7777b0710e37eff33f4c8bdebb  analysis/mrofyt/tests_mrofyt_v01_5.py
ed861c3ea75f87a42f3a8348d9581d0d9a31814f09822408df96e737a977c0a2  analysis/mofad/tests_closure.py
aa90aeeba1f9eb8d11d48c9020b869a4093cc2236abe0e2e3e9def5608ab246e  analysis/mofad/similarity_screen.py
```

## Commands and expected counts

```
cd analysis/mrofyt
python3 tests_mrofyt.py        59/59      python3 tests_mrofyt_v01_3.py  32/32
python3 tests_mrofyt_v01_1.py  56/56      python3 tests_mrofyt_v01_4.py  25/25
python3 tests_mrofyt_v01_2.py  31/31      python3 tests_mles_v11.py      29/29
python3 tests_mrofyt_v01_5.py  36/36
cd ../mrof  && python3 tests_mrof.py     42/42
cd ../mofad && python3 tests_closure.py  15/15
TOTAL 325/325
```

Synthetic fixtures demonstrate implementation behavior only. They are
not, and are never presented as, evidence of positive expected value.
