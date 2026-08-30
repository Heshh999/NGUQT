# MROF-YT-OF-01 — TAPE-SCALPING WAVE FREEZE AND DATA VERDICT

Frozen and committed **before any outcome is computed or computable**.
Source directive archived as `MROF_YT_OF01_SOURCE_PROMPT.md`
(SHA-256 `7b710b1d794674195d23a12e26fe67c41e566f6206f4314c9979673cfe99cf64`);
its full text governs verbatim wherever this freeze does not narrow it.
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.

## 1. Governing gate

Operates under MROF-V1 (`analysis/mrof/MROF_V1_STATE_AND_READINESS.md`,
commit `31cd0cd`). Current state: **MROF-V1 STATE A — NO GENUINE
ORDER-FLOW DATA** (MLES recorder never attached; 0 captured sessions;
no trades-with-BBO or depth history exists anywhere in the repo; the
V4.1 volumetric asset is 1m bar aggregates and cannot support any of
this wave's event-level features). OFH13/OFH14/STREAK3DN protections,
all partitions, and the 90-hypothesis spent registry remain intact and
untouched. The video material is hypothesis inspiration only; the
transcript audit in the source directive is preserved as-is.

## 2. Data verdict — binding classification

Required raw data (source §Required raw data): synchronized raw
trades + BBO + ten-level depth. Available: **none (0 sessions)**.

Per the source directive ("If data readiness is insufficient, write
and freeze the candidate mathematics and return `INSUFFICIENT_DATA`
without opening outcomes"), this wave's classification is:

**`INSUFFICIENT_DATA`**

No outcome, markout, P&L, event study, fold, or grade was computed.
The wave is FROZEN-AWAITING-DATA: when captured sessions satisfy the
MROF State-C readiness gates, this wave runs **exactly as frozen here**
— no re-specification at open time.

## 3. Frozen wave content (by reference + narrowing decisions)

The six Wave A families (A1 replenishing-wall absorption reversal, A2
displayed-wall depletion continuation, A3 non-trade-withdrawal vacuum
continuation, A4 ten-second expected-response-failure reversal, A5
pullback absorption trend resumption, A6 cash-open control
continuation), the four conditional Wave B management comparisons, the
23-entry causal feature dictionary, the level hierarchy (active pool /
context-only / 9-family clustering / Available_R geometry with
REJECT_GEOMETRY < 0.70 and A+ eligibility ≥ 2.00), the grading
procedure, the PSY module branches, the required controls/ablations,
the nested chronological estimation, the positive-EV promotion gate,
and the three-way close-out classification are frozen **verbatim from
the archived source prompt**. Every threshold named there (z ≥ 2.0 /
1.5 / 1.0 gates, 3-of-4 persistence, 60%/20% vacuum, RR < 0.25,
1.5× executed-vs-displayed, 2-tick retreat, 120s touch window, 50%
pause-volume rule, 30-minute cap, 2R target) is frozen as written; no
alternative may be searched.

Referent-gap and environment decisions, resolved NOW (pre-outcome):

1. **Trading window**: no frozen MROF window existed → the source
   default governs: 09:30:00–11:30:00 ET (A6 restricted to
   09:30–09:45 as specified).
2. **Latency**: none previously frozen → 150 ms base; 300 ms and
   500 ms as non-rescuing stresses.
3. **Session-VWAP bands**: the source references an "already-frozen
   session-VWAP band formula"; **no such formula exists in this
   repository** (RVMR bands are day-range forecast bands, a different
   object). Frozen here: upper/lower band = session VWAP ± 2.0 ×
   σ_w(t), where σ_w(t) is the causal volume-weighted standard
   deviation of traded price around the running VWAP within the
   session. One pair, no k search.
4. **ADR module**: the required certification against the saved
   TradingView indicator (≥100 causal timestamps) is impossible here
   (no TradingView export supplied) → all ADR features are
   **`UNVERIFIED_CONTEXT`**: computed, stored, and barred from
   affecting entry, grading, or promotion until certified.
5. **PSY-NQ-01**: the construction requires raw **unadjusted
   front-contract** NQ/MNQ Sunday-session data with contract
   identity. The historical 1m asset is a continuous contract and
   fails that identity requirement → status **`PSY_NQ_UNVERIFIED`**
   on historical data. The construction and its audit are implemented
   and unit-tested; the branch becomes auditable on MLES capture data
   (which stamps contract identity on every row). PSY-FX-01 is not
   opened (no FX data or authorization).
6. **Aggressor classification**: the capture's frozen `QUOTE_TEST_v1`
   (with confidence field) is the frozen method; classification
   uncertainty is reported, never forced.
7. **Level precedence**: none previously frozen → the source default
   governs (label with every overlapping level; nearest-level
   distance for eligibility; no post-hoc label selection).
8. **Multiplicity**: no cross-wave FDR procedure being live at event
   tier → the source's preregistered dependence-aware Romano-Wolf
   step-down at α=0.05 governs all promotional comparisons of this
   programme's event-tier waves, cumulative from this wave forward.
9. **Deployment topology**: primary = **NQ signal / MNQ execution
   with causal synchronization** — chosen now, before any data.
   NQ-only and MNQ-only are charged comparisons if ever run.
10. **Registry**: one row `MROF-YT-OF01-WAVE` is appended to the
    spent-hypothesis registry as `RESERVED_UNTOUCHED` (class `-`)
    so the cumulative burden records the wave's existence at freeze.
    Event-tier novelty screening versus the spent bar-aggregate OF_*
    classes happens at State-C open using the frozen screen's
    new-causal-source rule (the event stream did not exist for any
    spent hypothesis); nothing is tested until then.

## 4. Engine delivered with this freeze (State-A-legal)

`mrofyt_levels.py` — level engine: prior-session/weekly extremes,
Globex vs 09:30 opens (not interchangeable), overnight extremes fixed
at 09:30, session VWAP + the frozen band pair, PP/S1/R1/M2/M3 (S1/R1
intermediate only), ADR14 lines + ADR_USED (UNVERIFIED_CONTEXT), PSY
8-hour weekly construction with availability timestamp and audit,
9-family one-count clustering, and transparent Available_R geometry
with the frozen role gates.

`mrofyt_signals.py` — event-tier feature and execution engine on top
of `analysis/mrof/mrof_engine.py`: MBP book reconstruction; causal
robust baselines (median/MAD, previous 20 sessions, same 5-minute
bucket, current session excluded); aggressor delta / intensity +
acceleration / price response / flow-response efficiency / K-level
book imbalance (k=3 primary) / replenishment and depletion ratios /
non-trade withdrawal inference with matched-execution subtraction /
book resiliency with 30 s right-censoring / equal-weight control
score / 4×2.5 s persistence / sweep + 5 s reclaim / level-test
sequence / spread-response dominance / pause quality / multi-horizon
alignment / cash-open shock metrics; the A1–A6 detectors composing
exactly the frozen thresholds; and the execution state machine
(first executable quote after latency, structural stop = event-window
extreme + max(2 ticks, 0.10×ATR20-1m), 2R target, 10 s
early-invalidation, later control-loss exit, 30-minute hard cap, one
position, Y_j dollar accounting with commissions/fees/slippage).

`tests_mrofyt.py` — deterministic fixtures for all of the above.
Synthetic events are software fixtures only, never market evidence.

The engine computes **no outcome ranking**: the MROF State-C hard
lock (`research_unlocked()`) still governs; nothing here opens P&L.

## 5. Close-out (required form)

Classification: **`INSUFFICIENT_DATA`** — zero qualifying sessions of
the required raw data exist. Nothing was tested; nothing failed;
nothing passed. The single action that advances this wave is capture:
attach the MLES recorder (NQ + MNQ), accumulate sessions, pass the
State-C readiness gates, then run this wave exactly as frozen.
