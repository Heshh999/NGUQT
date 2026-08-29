# RNVP-V1 — ROUND-NUMBER GRID + VOLUME PARTICIPATION — FINDINGS

Protocol frozen at `87b81d8` before any outcome; engine + 19/19 unit
tests committed before the run (`38dbe1a`). One-shot run, no reruns,
no corrections. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

## Verdict

**0 / 8 confirmatory cells pass the full frozen gate battery.**

`NO VERIFIED NEW HIGH-OPPORTUNITY-FREQUENCY EDGE FOUND UNDER THE
FROZEN SEARCH AND AVAILABLE GENUINE DATA.`

Monte Carlo not run (no passer; MC never rescues). All results are
`EXPLORATORY DEV EVIDENCE — NOT INDEPENDENT CONFIRMATION`.

## Family RNL — the 100-point grid (2,232 first-interaction events)

| cell | n | stressed | perm p | freq/wk | first binding failures |
|---|---|---|---|---|---|
| R1 fade first upper touch (S) | 769 | +0.592 | 0.195 | 2.07 | PF, p/q, years 4/8, dom 1.86, tails |
| R2 fade first lower touch (L) | 784 | +1.302 | 0.142 | 2.11 | PF, p/q, dom 0.82, tails |
| R3 upside break continuation (L) | 205 | +1.781 | 0.293 | 0.55 | PF, p/q, frequency, tails |
| R4 downside break continuation (S) | 317 | +3.941 | 0.166 | 0.85 | PF, p/q, dom 0.61, frequency, tails |

The honest surprise: **all four cells are positive after stressed
costs, in both mechanism arms (fade the touch AND trade the break)** —
the only wave ever to put every confirmatory cell above water. But
none is close to significance (BH q ≥ 0.52), profit factors top out at
1.14, single years dominate (R1's 2025 is 186% of its total; R3's
2019 is 209%), and every cell fails top-1%-removal — the profit lives
in a few outsized winners. R4 (stop-cascade continuation through a
breaking level) is the family's best face: +3.94 stressed, delay
+2.71, all four neighbors positive — and still p 0.166 with CI
[−6.3, +15.3]. A weak grid effect may genuinely exist; at MNQ costs
on 7 years of data it is **not resolvable from noise**, and the gates
correctly refused it.

## Family VTP — volume participation timing: dead, informatively

- V1/V2 (heavy-morning continuation): −0.44 / −2.28 stressed, p ≥
  0.46. High-participation mornings do NOT persist into the afternoon.
- V3/V4 (light-morning reversion): **−7.6 / −6.7 stressed** (p 0.85 /
  0.74), every neighbor negative. Fading a quiet morning is one of the
  worst trades tested in this entire programme — the index drifts on
  regardless of participation.

Raw volume, the last untouched field in the data, carries no
afternoon-direction information at day scale. The information-vs-noise
participation dichotomy is empirically false on MNQ.

## Frequency mandate check (directive §7)

RNL touch cells ran at 2.1 trades/week with 85% of weeks active —
comfortably inside the mandate; the break cells (0.55–0.85/wk) and
both VTP strategies (V-HI 1.45/wk 65.5% active, V-LO 1.41/wk 67.1%)
were reported at cell and strategy level as frozen. Frequency was
never the binding failure for the family — significance was.

## Ledger

- `RNVP-RNL` (R1–R4) → DEAD_FROZEN, new class `ROUND_NUMBER_GRID`.
- `RNVP-VTP` (V1–V4) → DEAD_FROZEN, new class
  `VOLUME_TIME_PARTICIPATION`.
- Raw statistics `RNVP_V1_RAW.json`; console `RNVP_RUN_OUTPUT.txt`;
  reproduce `python3 analysis/rnvp/rnvp_run.py` (~116 s), seeds
  20260930/31/32 frozen in protocol.

Registry stands at 90 hypotheses / 30 mechanism classes. The two
classes tested here were the last obvious virgin axes in pure
OHLCV: exogenous price levels and raw-volume states. What remains
untested is combinations of dead components (prohibited without a new
interaction mechanism) and data that does not exist yet (VALIDATION
opens 2026-09-01; MLES capture at 0 days).
