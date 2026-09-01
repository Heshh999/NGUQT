# RECORDER_DEPLOYMENT.md — MROF capture deployment (v01.2)

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. The recorder is an
indicator; it submits no orders (grep-tested at MLES Freeze A).

## 1. Package audit (performed before any deployment claim)

`MROF_V1_Engine.zip` — **PRESENT and AUDITED**:

- SHA-256 `f4658e9b68f131aa6b568d7034e9a77c5b3171e799c2056cc10bd629571f7ec2`,
  28,659 bytes, 13 files.
- `1_NinjaTrader_Recorder/MlesV1CaptureHost.cs` — **byte-identical** to
  the committed `src/MlesV1CaptureHost.cs` (MLES Freeze A `c40f39a`).
- `2_Analysis_Engine/mles_integrity.py` — byte-identical to
  `analysis/mles/mles_integrity.py`.
- Also contains `mrof_engine.py`, `tests_mrof.py` (42/42), the capture
  spec + machine schema, the state/readiness report, the setup
  walkthrough, and README.

The zip does NOT yet contain the v01/v01.1/v01.2 wave modules — those
live in `MROF_YT_TapeScalp_Wave.zip` and in the repository; they are
analysis-side and are not needed inside NinjaTrader.

## 2. Deployment steps (user-side; the only unautomatable part)

1. NinjaTrader 8 with your live futures connection (Level I required;
   enable Level II / market depth if your subscription has it).
2. Import `MlesV1CaptureHost.cs` per `SETUP_WALKTHROUGH.md`
   (NinjaScript Editor → new Indicator → paste → compile).
3. Attach one instance each to **NQ front contract** and **MNQ front
   contract** (ES optional). Charts stay open during the session.
4. Output lands as
   `MLES_<inst>_<session>_{quotes,trades,depth,quality}.csv` plus an
   atomic `..._manifest.json` per session (18:00 ET roll).
5. At a contract roll week, run instances on BOTH the old and new
   contract; the parser refuses silent mixing, and v01.2 zone logic
   retires zones at rolls automatically.

## 3. Verification (any machine with Python 3)

```
python3 2_Analysis_Engine/tests_mrof.py            # expect 42/42
python3 2_Analysis_Engine/mles_integrity.py <capture folder>
```

## 4. Honest completion status

**Deployment is NOT complete.** The package is delivered and audited;
the recorder has never been attached in the user's NinjaTrader, and
captured sessions = 0. Completion requires the user-side steps above —
there is no server-side action that can substitute for them.
