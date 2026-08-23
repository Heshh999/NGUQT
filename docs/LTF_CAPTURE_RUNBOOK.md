# LTF CAPTURE RUNBOOK — producing genuine 5s / 15s / 30s MNQ data

The engine that **tests** 5s/15s data is `analysis/ltf_exec/ltf_engine.py`.
It is finished and already proven on genuine 30s bars. It cannot test 5s
or 15s because **no genuine 5s or 15s history exists in this project** —
and nothing will ever be interpolated to invent it.

This document covers the other half: the engine that **produces** that
data, `src/MnqV41LtfCaptureHost.cs`. It records real bars as NinjaTrader
closes them. It submits no orders.

## What it captures

| series | how it is obtained | delta columns |
|---|---|---|
| 1m | chart primary | filled **only** if the chart is Order Flow Volumetric |
| 30s | `AddDataSeries(Second, 30)` | EMPTY by design |
| 15s | `AddDataSeries(Second, 15)` | EMPTY by design |
| 5s | `AddDataSeries(Second, 5)` | EMPTY by design |

NinjaTrader standard Second series carry no per-price bid/ask, so the
`bidVolume/askVolume/delta/deltaPercent` columns are written EMPTY for
them rather than inherited from the 1m bar. That is the data rule, not a
limitation to be worked around.

If the primary chart **is** Volumetric, the frozen
`V41FrozenCandidateEngine` runs on it and every lower-timeframe row
carries the live frozen parent state (`parentCandidate, parentEventId,
parentDirection, parentAvailableTime, parentEntryTime, parentEntryPrice,
parentATR, fvgLow, fvgHigh, structuralInvalidation, parentStillValid`).
If it is not Volumetric the capture still runs — those columns are left
empty and the backtester regenerates parents from frozen `cand_spec`
anyway.

## Install (once)

1. NinjaTrader → **New → NinjaScript Editor**
2. Strategies → right-click → **New Strategy** → name it
   `MnqV41LtfCaptureHost` → Finish
3. Select **all** the generated text and paste the contents of
   `src/MnqV41LtfCaptureHost.cs` over it
4. **F5** (Compile). It must say *0 errors*.

## Capture a day

1. **Control Center → Connections → Playback**
2. **Control Center → Tools → Historical Data → Download → Get Market
   Replay data** — pick the date, instrument `MNQ`. A day you have not
   downloaded cannot be replayed.
3. Open an **MNQ 1 Minute** chart. Order Flow **Volumetric** preferred
   (gives parent state); plain 1 Minute also works.
4. Chart → **Strategies** tab → add `MnqV41LtfCaptureHost`
   - **Output folder** = `C:\V41`
   - **Calculate** = `On bar close`
   - **Maximum bars look back** = `Infinite`
   - **Enabled** = ✓ → OK
5. Playback control bar: load the replay date, set speed to **max**,
   press **▶**. Let it run the whole session (09:30 → 16:00 ET at
   minimum; the full 24h is better).
6. When the day finishes, **untick Enabled**. The shutdown summary
   prints in the **Output** window (New → Output):

```
LTF CAPTURE COMPLETE
  1m  bars 390
  30s bars 780
  15s bars 1560
  5s  bars 4680
  day files 1
  parent state RECORDED (volumetric primary)
  files in C:\V41\V41_ltf
```

Those counts are the RTH-only expectation for one session. A full 24h
replay is roughly 3.5× larger. **If 5s or 15s shows 0 bars**, the replay
data for that day has no ticks — redownload it.

7. Repeat for every day you want. Files land in
   `C:\V41\V41_ltf\V41_LTF_MNQ_YYYYMMDD.csv`, one per ET calendar day.
   Re-replaying a day appends to that day's file; the backtester
   deduplicates first-wins.

Send back the whole `V41_ltf` folder.

## Test the captured data

```
python3 analysis/ltf_exec/ltf_engine.py inventory <folder>   # what really exists
python3 analysis/ltf_exec/ltf_engine.py validate <folder>    # aggregation gates
python3 analysis/ltf_exec/ltf_engine.py run      <folder>    # all 8 arms
```

`validate` checks 5s→15s, 15s→30s, 30s→1m, 15s→1m and 5s→1m aggregate
**exactly**. It refuses to backtest if any pair mismatches — that gate
is what caught the 45,587 duplicated rows in the 30s export. Only after
it passes does `run` produce per-parent results; the 15s and 5s columns
populate automatically and ARM4 / ARM7 become testable for the first
time.

## Expectation, set before the data arrives

OFH13 parents occur at roughly **0.5 per day**. N replayed days yields
about N/2 parents. To get out of the "very low sample" label at all you
need several weeks of replayed days; to say anything confirmatory you
need far more. The honest prior from the genuine 30s work is that
lower-timeframe entry does **not** improve OFH13 economics — every one
of the eight arms lost to the plain 1m entry by skipping 6–10 of the ten
largest winners. Capture is worth doing because 5s/15s is the last
untested door, not because the door is expected to open.

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. This strategy submits no
orders.
