# Frozen Prospective Registry

**Frozen:** 2026-08-21, before any 2026-09+ data existed.
**Data freeze line:** last spent bar `2026-08-19`. Anything at or before
that date is historical and SPENT. Only `day > 2026-08-19` is scored
prospectively.
**Modules:** `analysis/v41/cand_spec.py` (definitions),
`cand_audit.py` (audit), `cand_mgmt.py` (management), `prospective.py`
(scorer). Source hashes in `analysis/v41/FROZEN_HASHES.txt`; the scorer
aborts if any frozen source changes.

| source | sha256[:16] |
|---|---|
| cand_spec.py | `9bea8f1cafc2b6ea` |
| ofh6_spec.py | `e8145b7c493029de` |
| ofht_spec.py | `272d7bca6402b6d2` |
| ofht_cache.py | `376ce829086b5224` |

---

## 1. Exact frozen definitions (transcribed from source)

Shared: cost **0.87 pt** RT; MNQ **$2/pt**; measurement/exit horizon
**60 min**; OFH6 context life **30 min**; per-candidate chronological
cooldown **30 min** (G1/G3 are per-signal and exempt); entry at a
COMPLETED 1m close unless stated. `TICK = 0.25`.

**OFH6 context** (`ofh6_spec.py`, unmodified): `dsum15` = sum of
`ofBarDelta` over 15 consecutive completed 1m bars; signal when
`|dsum15| >= 3380.0`; direction = sign; cooldown 30 min; signal gate
requires RTH, `minutesFromRthOpen >= 30`, `minutesToRthClose >= 90`, and
90 consecutive forward minutes.

**OFH13** — FVG mitigation + opposing order-flow failure.
Parent: OFH6 signal. Walk forward ≤30 min from the signal for the FIRST
bar carrying a displacement-qualified FVG in the signal direction
(FVG: `c1.high < c3.low` bullish / `c1.low > c3.high` bearish; zone
`[c1.high, c3.low]`; displacement on `c2`: `range >= 1.00*ATR`,
`body/range >= 0.50`, close-location `>= 0.70` / `<= 0.30`, and
`c3.close > c1.open` / `<`). Then mitigate: first touch of the zone,
then the first completed close beyond the zone midpoint — expiring at
**signal time + 30 min**. Requires `flow` (≥1 mitigation bar with
`|barDelta| >= 511` opposing the trade) **and** `depth < 1.0` (FVG not
fully filled). Invalidation while waiting: a completed close beyond the
far zone boundary. R = entry − (far boundary − 1 tick). **First-FVG rule:
only the first qualifying FVG per signal is ever used.**

**OFH14** — identical to OFH13 without the `flow`/`depth` requirement.

**G4** — opposing-delta attack that fails.
Trend `t` = sign of `disp5` where `|disp5| >= 0.50*ATR`. Attack bar:
`barDelta` opposing `t` with `|barDelta| >= 511`. OFH6 context must be
active for `t` at that bar (≤30 min, no opposing signal). Then within
**3 bars**: if the trend-side extreme of the attack bar breaks first →
enter at that bar's close; if the adverse side breaks first → dead.
R = entry − (attack-bar adverse extreme ∓ 1 tick).

**G3** — delayed entry if still discounted.
At exactly **signal bar + 20 min** (consecutive minutes required, no
opposing signal): if the close is on the adverse side of the signal
close, enter at that close. R = **1.0 × ATR** of the entry bar.

**G1** — execution overlay (not a standalone edge).
Resting limit at `signal close − d × 0.50 × ATR(signal bar)`, valid 30
min from the signal, filled on first touch, no chase. R = ATR of the
**signal** bar.

## 2. Written spec ≠ implemented spec (documented, NOT corrected)

| id | discrepancy |
|---|---|
| **D1** | `ofht_spec.entry_ok` — used by every historical run — does **not** enforce ">=30 min after RTH open" despite its header and several run headers saying so. Only the OFH6 *signal* gate enforces it. `cand_spec.entry_ok` reproduces the implemented behaviour exactly. |
| **D2** | `offvg_run.py` header claims OFH13/OFH14 use ">=30 min after open"; only the ">=60 min to close" half is enforced. |
| **D3** | OFH13/OFH14 mitigation expiry is **signal time + 30 min**, not FVG time + 30 min. An FVG forming at minute 29 gets one minute. |
| **D4** | G4 passes `B[k]['close']` as entry price — identical to the close, so it is a market entry. |
| **D5** | G1's R is the ATR of the **signal** bar, not the fill bar. |
| **D6** | G3's R is 1.0 × ATR, so its "structural" and "1.0 ATR" stops are the same object. |
| **D7** | G1 historical fills assumed TOUCH. Fill realism measured separately; not part of the frozen rule. |
| **D8** | The frozen `tmin` index (`cand_spec.py` line 130) treats every month as 44,640 min (31 days) but a year as 527,040 min (366 days), so it is **non-monotonic across the year boundary**: Jan 1–5 of a new year index *below* late December of the old year (Jan 6 00:00 == Dec 31 00:00). Consequence: the OFH6 30-min cooldown after a late-December signal suppresses all early-January signals. Verified: 2025-12-30 10:59 suppresses five would-be signals on 2026-01-02/05 (diffs −4379…−14 min). Discovered during NT8 parity (a true-minute clock fired exactly those 5); the NT8 engine replicates the frozen arithmetic verbatim (`V41InBar.TminOf`). See docs/NT8_PROSPECTIVE_ENGINE.md. |

**Enforcing any of these creates a NEW VERSION that cannot inherit the
existing validation evidence.**

## 3. Reproducibility audit — PASS

| candidate | canonical U/D/I | historical U/D/I | |
|---|---|---|---|
| OFH13 | 16 / 57 / 60 | 16 / 57 / 60 | EXACT |
| G4 | 36 / 79 / 103 | 36 / 79 / 103 | EXACT |
| G3 | 82 / 194 / 201 | 82 / 194 / 201 | EXACT |
| OFH14 | 70 / 177 / 215 | 70 / 177 / 215 | EXACT |
| G1 | 150 / 326 / 369 | 150 / 326 / 369 | EXACT |

Integrity: no duplicate event IDs, no causality violations (every
referenced parent bar precedes its entry), no cooldown violations, all
R > 0, no entry outside its bar's range. 355,455 bars, 952 OFH6 signals.

## 4. Candidate character (60m frozen entry, no stop)

| | n | mean | median | MFE/MAE | ff@1ATR | UNSEEN / DEV / IR | type |
|---|---|---|---|---|---|---|---|
| OFH13 | 133 | +21.04 | +12.13 | 1.376 | 49.6 | +37.5 / +31.9 / +6.4 | **positive-skew drift, small-n** |
| G4 | 218 | +13.65 | +13.88 | 1.181 | 43.8 | +13.1 / +20.7 / +8.4 | **directional drift, runner-dependent** |
| G3 | 477 | +5.17 | +3.38 | 1.135 | 47.7 | +12.6 / +8.1 / **−0.7** | **unstable** |
| OFH14 | 462 | +8.61 | +6.13 | 1.101 | 50.0 | +13.8 / +6.8 / +8.4 | **directional drift, most consistent** |

No candidate has entry asymmetry: every ff@1ATR is ~44–50%, i.e. at or
below a coin flip. All four are **drift** candidates. Concentration is
heavy everywhere (top-5% ≥ 66% of total for OFH13, >100% for the others).
p95 MAE runs 178–210 pt ($356–420/contract).

## 5–6. Management — one genuine plateau, three failures

Fixed-R maps were negative in nearly every cell for all four candidates
(full-history R/trade: OFH13 −0.26…+0.06, G4 −0.10…+0.01, G3 −0.63…−0.36,
OFH14 −0.28…−0.20). **There is no fixed-R payoff plateau anywhere.** G3's
map was additionally unusable on its tightest stop (89.9% hit rate,
22–44% intrabar ambiguity) and was remapped on its correct 1.0-ATR stop.

Stop + time exit (no target) is the surviving question, and one candidate
answers it:

**OFH13 is positive in all 36 cells** (3 stops × 4 exits × 3 partitions).

| stop | UNSEEN 60m | DEV 60m | IR 60m | full mean | win% | PF | maxDD |
|---|---|---|---|---|---|---|---|
| STRUCT | +6.22 | +13.09 | +9.92 | +10.83 | 20.3 | 1.80 | 444 pt |
| ATR1.0 | +35.38 | +17.78 | +0.91 | +12.29 | 24.1 | 1.67 | 348 pt |
| **ATR1.5** | +41.15 | +18.47 | +9.74 | **+17.26** | **36.1** | **1.80** | **333 pt** |

The others fail: **G4** is negative on UNSEEN under every stop (its
unseen edge requires no stop at all); **G3** is negative on IR under
every stop; **OFH14** is broadly positive but thin (+1.75 pt/trade
against a 992 pt drawdown, PF 1.13).

## 7–9. G1 overlay — measured, and NOT adopted

Matched A/B on identical parent events. On the events it fills, the
B-arm looks far better — but that comparison is a trap:

| | fill | improvement | per-PARENT-EVENT EV (no-fill = 0) |
|---|---|---|---|
| OFH13 | 83% | +11.94 pt | **B +11.81 vs A +21.04** |
| G4 | 90% | +12.20 pt | **B +11.25 vs A +13.65** |
| OFH14 | 87% | +10.72 pt | **B +6.94 vs A +8.61** |

**The events G1 fails to fill are the explosive ones.** For OFH13 the 23
unfilled events averaged roughly +107 pt each; waiting for a half-ATR
discount forfeits them. The selection cost exceeds the price improvement
on all three lineages, so **G1 is not adopted anywhere**.

Fill realism barely matters: TOUCH / 1-tick-through / 2-ticks-through
give 110 / 109 / 109 fills for OFH13 and nearly identical results. The
problem is selection, not optimism about queue position.

This also explains why G1 *did* help OFH6 standalone: OFH6 had no drift
to forfeit. **G1 helps signals with no edge and hurts signals with one.**

**G3 × G1 is not run** — G3 entries are already ≥0.5 ATR discounted in
**86%** of cases (median discount 1.77 ATR). Stacking would double-count
the same mechanism.

## 10. Frozen prospective versions

| version | lineage | role | stop | target | exit |
|---|---|---|---|---|---|
| **OFH13_PROSPECTIVE_V1** | OFH13 | **PRIMARY** | ATR1.5 | none | 60m |
| OFH14_PROSPECTIVE_V1 | OFH14 | secondary | STRUCT | none | 60m |
| G4_PROSPECTIVE_V1 | G4 | secondary | **none — SIGNAL-ONLY** | none | 60m |
| G3_PROSPECTIVE_V1 | G3 | secondary | **none — SIGNAL-ONLY** | none | 60m |

OFH13's ATR1.5 was chosen on **risk and stability, not return**: lowest
maxDD of its family, highest win rate (least runner-dependent), flattest
IR profile, and volatility-adaptive so it does not depend on FVG geometry
being re-identified identically in future data. That all three stops work
*is* the plateau. G4 and G3 get no management version, as instructed —
neither has one that survives its own partitions.

## 11. Ranking (changed from the working priority — explained)

1. **OFH13** — unchanged at #1. Only candidate with a genuine management
   plateau. Caveat that dominates everything: n=133, and its headline
   unseen result is **n=16**. Do not extrapolate +38 pt/trade.
2. **OFH14** — **promoted from 4th to 2nd.** The only other candidate
   positive in all three partitions, with the largest sample (462) and a
   broad if thin positive management region.
3. **G4** — **demoted from 2nd to 3rd.** Good median and drift, but
   negative on UNSEEN under every declared stop, and ff@1ATR 43.8.
4. **G3** — **demoted from 3rd to 4th.** IR partition is negative
   (−0.65) and it is the least stable across partitions.

## 12. Future-data rules

1. New captures go in `<scratch>/ofprospective/`. Run
   `python3 analysis/v41/prospective.py`.
2. Only `day > 2026-08-19` is scored. Earlier data is spent.
3. The scorer has **no optimiser and no free parameters**. It aborts if
   any frozen source hash changes.
4. Prospective results are appended to `docs/prospective_ledger.csv` and
   never overwrite history.
5. No rule may change because of a prospective outcome. A changed rule is
   a new version starting from zero evidence.
6. Both G1 arms are recorded per parent event; the A-arm is primary.

## 13. Checkpoints and pre-declared failure conditions

Report at **20 / 50 / 100** trades (reporting points, not significance
thresholds). Failure conditions declared now, before any data:

- mean expectancy persistently negative past the 50-trade checkpoint
- median materially negative **and** mean carried by <5% of trades
- medMFE/medMAE collapsing toward 1.00
- favourable-first collapsing toward 50% with negative expectancy
- both directions failing simultaneously
- one trade producing >50% of cumulative P&L at 50 trades
- management cells flipping negative (plateau disappearing)
- drawdown exceeding historical maxDD by more than 50%

**Multiple-candidate accounting, declared in advance:** four versions are
being scored, so raw per-candidate p-values are not family-aware. OFH13
is the **declared primary**; G4/G3/OFH14 are secondaries; G1 is an
execution overlay only. Any future claim must state which of the four it
came from and apply an M=4 correction.

*THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.*
