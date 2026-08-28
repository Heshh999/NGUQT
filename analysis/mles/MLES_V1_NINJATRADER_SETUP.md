# MLES-V1 — NINJATRADER ACTIVATION (do this once, then leave it running)

Nothing below has been executed for you. **No claim is made that
capture succeeded** — that is only true once you run these steps and
send back the integrity output. THIS PROJECT DOES NOT AUTHORIZE LIVE
TRADING; the recorder is an Indicator and cannot place an order.

## 1. Install the file
1. Close NinjaTrader 8.
2. Copy `src/MlesV1CaptureHost.cs` to
   `Documents\NinjaTrader 8\bin\Custom\Indicators\`
3. Start NT8 → **New → NinjaScript Editor** → press **F5**.
   Expect **0 errors**. Screenshot any error and send it.

## 2. Confirm your data permissions
**Tools → Options → Market Data**, then check each instrument shows:
- **Level I** (bid/ask/last) — required.
- **Level II / market depth** — required for the depth stream. If you do
  not have it, capture still runs but `*_depth.csv` stays empty and the
  M3 family will remain `INSUFFICIENT DATA`. Tell me which you have.

## 3. Open three charts (one per instrument)
Front-month contracts: **NQ**, **ES**, **MNQ**. Any bar type — the
recorder listens to messages, not bars. Use 1-minute so the chart is
light.

## 4. Attach the recorder to each chart
Right-click chart → **Indicators** → `MlesV1CaptureHost` → Add.
- `CaptureFolder`: leave **blank** (defaults to
  `Documents\NinjaTrader 8\mles_capture\`). If you set one, it must not
  contain `analysis`, `docs` or `scratchpad` — the recorder refuses
  those and falls back to the default.
- Click OK. Repeat on all three charts.

## 5. Verify files appear
Within ~30 seconds `Documents\NinjaTrader 8\mles_capture\` should hold,
per instrument: `MLES_<INST>_<session>_quotes.csv`, `_trades.csv`,
`_depth.csv`, `_quality.csv`. Open `_quality.csv` — you should see
`SESSION_START` then `HEARTBEAT` rows every ~30s.

## 6. Fifteen-minute smoke capture
Leave all three attached for **15 minutes during RTH** (09:30–16:00 ET)
so there is real message traffic. Then, **without detaching**, run the
integrity checker.

## 7. Run the integrity checker
```
python3 analysis/mles/mles_integrity.py "C:\Users\<you>\Documents\NinjaTrader 8\mles_capture"
```
(or copy the folder to this machine and point at it).

## 8. Reading the result
- **PASS** (exit 0) — schema, sequences and clocks are clean. Send me
  the JSON output.
- **WARN** (exit 1) — usable but something needs noting: crossed quotes,
  a missing instrument, bounded exchange-clock reversals. Send it; I
  will tell you whether it matters.
- **FAIL** (exit 2) — duplicate sequence numbers, receive-clock
  reversals, header mismatch, or an outcome-bearing column. **Do not
  keep accumulating** until it is resolved; send the output.

## 9. Leaving it running safely
Keep NT8 connected with the three charts attached. The recorder is
crash-safe: it appends, flushes on every heartbeat, and writes each
session's manifest atomically at rollover. Restarts are safe — a new
`runId` is issued and files are appended, never truncated. Sessions roll
at **18:00 ET**, matching the futures session, not midnight.

## 10. What I need back before Mode B counts
The integrity JSON for the smoke test, plus which of Level I / Level II
you actually have per instrument. Then we accumulate 20 engineering days
before anything is called research data.
