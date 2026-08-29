# MROF-V1 — GOVERNING STATE, DATA TIERS, RECORDER DISPOSITION, READINESS

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.
Subordinate to every existing partition guard, spent-class prohibition,
protected-parent rule and freeze; stricter rule controls.

## A. Governing-state report

- Lineage verified: V4.1 → MGSD → MOFAD → MLES → MTF → NVQ → RMA →
  MTNAD → RNVP. Latest completed wave RNVP-V1 (freeze `87b81d8`,
  results `36f846a`). Working tree clean at MROF start; unrelated work
  preserved.
- Protected candidates intact and untouched: **OFH13, OFH14**
  (docs/PROSPECTIVE_REGISTRY.md) and **STREAK3DN**
  (analysis/nvq/NVQ_V1_PROSPECTIVE_FREEZE.md), all frozen for
  VALIDATION (2026-09-01 → 2027-02-28). Buffer 2026-08-18→31 unused;
  OOS and FINAL LOCKBOX untouched. Nothing in MROF-V1 opens, filters,
  or re-derives from them.
- Cumulative registry: 90 hypotheses / 30 mechanism classes
  (`analysis/mofad/MOFAD_V1_SPENT_HYPOTHESIS_REGISTRY.CSV` lineage,
  closure tests 15/15). MROF-V1 adds **no** hypothesis rows: no
  outcome was computed.

**Declared state:**

`MROF-V1 STATE A — NO GENUINE ORDER-FLOW DATA.`
(No event-level order-flow history exists; see tier table. The
recorder has never been attached; MLES capture days = 0.)

`NO OUTCOME TEST RUN — GENUINE ORDER-FLOW HISTORY REMAINS INSUFFICIENT.`

## B. Data-tier classification (verified against the repository)

| dataset | fields | tier | coverage | exposure | order-flow claims permitted |
|---|---|---|---|---|---|
| canonical 1m OHLCV | OHLC + total volume | **Tier 0** | 7.1 y (2019-07-04→2026-08-17) | fully exposed DEV | price action, total volume, bar volatility — **not order flow** |
| V4.1 volumetric capture | 1m **bar-aggregated** classified delta | Tier-1-derived aggregates (fails Tier 1 event-field requirements: no per-trade ticks, no contemporaneous BBO rows) | 381,982 rows, 313 DEV days (12.0 months) | fully exposed and spent (V4.1/OFH/MOFAD) | bar delta at 1m only; no event features |
| LTF 30s lineage | 30s observations, non-contiguous | Tier 0 (sub-minute) | rows, not full sessions | exposed | none beyond price/volume |
| ES pilot | 1m OHLCV | Tier 0 | 42 session days (1.86%) | exposed | none; too short regardless |
| MLES capture (`MLES-CAPTURE-1.0.0`) | trades w/ full BBO + QUOTE_TEST_v1, quote events, MBP depth, quality | **Tier 2 by design, Tier 3 (MBP) when depth present** | **0 days — recorder never attached** | n/a | none until data exists |
| quotes/depth/tick history (historical) | — | absent | none | — | none |

Presumption of §1 verified line-by-line: TRUE in every respect.
Retrospective order-flow fields can never make the exposed 2019–2026
price path pristine; all future historical discovery on it stays
`EXPLORATORY DEV EVIDENCE`.

## C. Recorder disposition: REUSE the authoritative MLES recorder

Audit of `src/MlesV1CaptureHost.cs` (Freeze A
`c40f39a18a3741836b7849d0e2ab3c758c0e67e5`) against MROF §3:

| MROF §3 requirement | MLES status |
|---|---|
| immutable append-only raw streams (trades/quotes/depth/quality) | PRESENT |
| four clocks per row; later-availability causal rule | PRESENT (tExch/tCb/tRecv/tMono) |
| full BBO on every quote row | PRESENT |
| aggressor provenance: raw field never overwritten; versioned inference | PRESENT (aggrRaw empty by feed; QUOTE_TEST_v1 + confidence) |
| depth with action/level/side | PRESENT (MBP; queue/order-identity claims prohibited and documented) |
| system-integrity events (connect/gap/reversal/reset/heartbeat) | PRESENT (quality stream, 8 kinds) |
| atomic manifests + SHA-256 per file | PRESENT |
| session roll 18:00 ET; research-folder write guard; no order APIs | PRESENT (grep-tested) |
| provider/exchange sequence numbers | **FEED LIMITATION** — NT8 supplies none; per-stream arrival counter recorded, limitation documented, never disguised |
| exchange clock-offset measurement | **FEED LIMITATION** — no reference clock in NT8; TS_REVERSAL + heartbeat telemetry recorded instead |
| roll-overlap capture | **OPERATIONAL** — run recorder instances on both contracts across roll week; contract is stamped on every row and the MROF parser refuses silent mixing |

Disposition: **no competing capture system is created and no frozen
artifact is modified.** The recorder is reused as-is; the two gaps are
feed limitations no NT8 recorder can close (they are recorded
honestly), and the roll requirement is operational. Tick Replay /
Playback are NOT capture substitutes (inside-quote/last-event replay
is not historical depth) and are prohibited as data sources.

## D. Multi-resolution feature engine (delivered, State-A-legal)

`analysis/mrof/mrof_engine.py` + `tests_mrof.py` (**42/42**, all
fixtures hand-computed; synthetic events are software fixtures only):

- Parser for the frozen `MLES-CAPTURE-1.0.0` schema with an integrity
  pass (schema check, per-stream duplicates/gaps, tRecv reversals,
  flags census, **hard refusal of silent contract mixing**); raw rows
  are never modified or dropped.
- Causal aggregation at 30s/1m/3m/5m/10m/15m/60m/4h/session —
  close-stamped, **complete-only with completion proof** (a bar exists
  only when a later event or session-end proves the interval ended);
  `features_at(t)` leakage guard.
- Tier-limited feature library: trade sign (honest 0 for
  unclassifiable; aggrRaw never used), TD/NTD/count-imbalance/
  cumulative session delta with frozen reset; Cont-Kukanov-Stoikov
  best-level OFI (all nine price-change cases fixture-tested);
  depth imbalance DI_K with zero-depth guard; microprice/spread with
  locked/crossed/invalid states; trade intensity; best-level
  depletion/replenishment primitives that **never label cancel vs
  execution** (MBP cannot distinguish).
- Parent-event declustering (a burst seen at several resolutions is
  one causal event).
- Non-colocated execution model: decision clock → latency → **first
  strictly-later VALID quote**; long at ask / short at bid; stressed
  slippage; passive fills prohibited (no queue model is possible from
  MBP). Costs per house convention.
- **No outcome computation exists in the module** (tested), and
  `research_unlocked()` is hard-locked until a committed State-C
  readiness freeze writes `MROF_V1_STATE_C_AUTHORIZED.json` — which
  does not exist.

## E. Frozen State-C entry requirements (future, binding)

Outcome research on capture data may begin only after a readiness
commit proves ALL of: ≥20 complete sessions parsed for pipeline
verification (no outcome reads); ≥60 complete sessions for the
descriptive engineering audit (no promotion); the MLES readiness
floors (12 months / 200 eligible days / 1,000 raw triggers / 500
effective events, per `MLES_V1_READINESS_STATUS.json`); coverage ≥95%
and parse ≥99.9%; a pre-outcome power/effective-event analysis; frozen
costs/latency grid/decluster rules; and a bounded hypothesis matrix
drawn from MROF §7 designs that passes the spent-registry screen
(Design J must prove material novelty vs the spent
DURATION_HAZARD_RENEWAL class; Design B/F vs spent OF_* classes at
event granularity — bar-level variants of the spent OF classes are
prohibited). Shorter history yields `PROVISIONAL EXPLORATORY` at
best; five genuine years remain required for full durability
promotion. Candidates reaching State D route into untouched
validation/shadow execution and are never re-mined.

## Continuation rule

On any later MROF invocation: resume from this checkpoint; while
capture is insufficient, continue capture/engineering only; never
spam outcome searches against a short capture. Next physical step:
the user attaches the MLES recorder in NinjaTrader
(`analysis/mles/MLES_V1_NINJATRADER_SETUP.md`, package
`MLES_V1_Capture.zip` already delivered) and capture days begin to
accumulate; `mles_integrity.py` scores each session outcome-blind.
