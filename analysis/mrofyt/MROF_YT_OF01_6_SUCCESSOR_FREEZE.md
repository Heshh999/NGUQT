# MROF_YT_OF01_6_SUCCESSOR_FREEZE.md — causal swing successor

Additive. `MROF_YT_OF01_5_SUCCESSOR_FREEZE.md` and every earlier freeze
stay unchanged and hash-pinned. **This project does not authorize live
trading.**

**Classification: `IMPLEMENTATION_COMPLETE` / `INSUFFICIENT_DATA`.**
The machinery and its tests exist. No swing outcome research was run,
and none may run until the inherited readiness gates pass on genuine
audited data.

## 1. Identifier selection

`v01_1 … v01_5` are used (`MROF_YT_OF01_1..5_SUCCESSOR_FREEZE.md`,
`mrofyt_engine_v014.py`, `mrofyt_engine_v015.py`). The next unused
successor identifier is **v01.6**, taken by this swing wave. The exit
experiment of Appendix C therefore took **v01.7**.

## 2. Artifacts and hashes

```
cb1ac7fa10b59955a467d140e7c17b9318eea525adb29b42c07cb15f64de1057  mrofyt_swings_v016.py
001d80630f0561749899f2ea46707bc339dd91435e082bad6da963c394d8b9de  mrofyt_engine_v016.py
84a0ca89b93eea041a82da37e5afb87c91072d3c8ed75ff77ced17706126b963  tests_mrofyt_v01_6.py
```

Predecessors reverified by the v01.6 suite (test B19), **unmodified**:

```
74ff9a99e468e22326dad9e01e4ee4dc7ab90c8da7e330a6b5f9e70e9eecb91b  MROF_YT_OF01_FINAL_SOURCE_PROMPT.md
b753a09cc077267a935df37f9b531f2179d920b8f76dc6ee5788628c264f7194  MROF_YT_OF01_5_SUCCESSOR_FREEZE.md
e3da36cd63a18a22935124e852ce8f8b785e96df136d98944f7e88654b1c6847  mrofyt_engine_v015.py
```

All three match the values pinned in the source prompt exactly.

## 3. Frozen swing construction

Five consecutive completed bars `j-2 … j+2` per timeframe.

```
swing high at j:   H[j] >= H[j-1],  H[j] >= H[j-2],  H[j] > H[j+1],  H[j] > H[j+2]
swing low  at j:   L[j] <= L[j-1],  L[j] <= L[j-2],  L[j] < L[j+1],  L[j] < L[j+2]
```

The asymmetric tie rule (`>=` left, `>` right) assigns an equal-price
plateau to its **last** occurrence before price departs, producing one
deterministic swing instead of one per plateau bar.

Price comes from centre bar `j`; **causal availability is the close of
`j+2`**. Nothing before that timestamp may use the swing for any
purpose — signal, feature, grade, stop, target or chart label.

### Roles

| TF | Frozen role |
| --- | --- |
| `1m` | Diagnostic/context only. Cannot create eligibility, change grade, or move a stop or target. |
| `5m` | Active experimental entry location and target-space input. |
| `15m` | Active experimental structural entry location and target-space input. |
| `60m` | HTF context and active experimental entry location inside the unchanged proximity window. |

No 3m, 10m, 30m, 4h or daily variant exists in this wave. That bounds
multiplicity; it does not assert those timeframes are useless.

### Bar aggregation

Exchange-calendar aligned on Eastern minute-of-day. A higher-timeframe
bar forms **only** when every constituent minute is present, complete,
contiguous and shares one instrument, contract, session and run. A
missing minute, an uncertain minute, a maintenance break, a
holiday-misaligned interval, a mixed run or a contract roll voids the
bucket entirely — it never yields a bar built from whatever arrived.

### Identity and family voting

```
SWING_{5M,15M,60M}_{HIGH,LOW}|contract|center_t|price_tick
```

All active swing IDs map to exactly one clustering family,
`CAUSAL_SWING`. A coincident 5m + 15m + 60m swing contributes **one**
family vote, not three, while every timeframe-specific level ID is
retained for diagnostics.

Same-side swings within `max(4 ticks, 0.20 × ATR20-1m)` merge into one
physical cluster. The anchor is the earliest causally available member;
ties break by timeframe order `60m, 15m, 5m` then lexically by
`swing_id`. **The anchor never moves to a later price.** Opposite-side
swings keep their side labels and are never silently cancelled.

## 4. Frozen lifecycle

`CONFIRMED_UNTOUCHED` → `ACTIVE_TESTED` → `BROKEN_PENDING_ACCEPTANCE` →
`RECLAIMED_BEFORE_ACCEPTANCE` | `ACCEPTED_BROKEN`; `ROLLED_OFF` on a
contract change or certification failure.

Acceptance requires **two consecutive completed closes of the swing's
own timeframe** at least one tick beyond it. A reclaim before the second
such close gives `RECLAIMED_BEFORE_ACCEPTANCE`, which may condition A4
only when every inherited A4 order-flow requirement is also satisfied.

`ACCEPTED_BROKEN` retires the level from new entry eligibility. **It
does not flip polarity into support/resistance** — that would be a
separate hypothesis. Retired levels stay in the ledger for audit and
target-path reconstruction.

No optimized age cutoff is imposed. Eligibility is bounded naturally by
the unchanged proximity window; age and freshness are reported so a
later preregistered wave can test decay without picking a favourable
cutoff here.

## 5. Toggles

| Toggle | Behaviour |
| --- | --- |
| `SWINGS_OFF_PARENT` | The v01.5 executable path, unchanged. |
| `SWINGS_ONLY` | Requires an eligible active swing; takes no credit from another key-level family. |
| `PARENT_PLUS_SWINGS` | Admits either the unchanged parent pool or an active swing. |
| `PARENT_AND_SWING_OVERLAP` | Separately reported confluence branch requiring a parent family **and** `CAUSAL_SWING` in the same frozen proximity cluster. |

The complete set of available level IDs and families is logged at
`FIRST_PROXIMITY`, `SIGNAL_COMPLETION`, `ENTRY_RELEASE`, `FILL`,
`EARLY_EXIT` and `TERMINAL_EXIT`, so no branch can choose a favourable
label after the trade.

### `SWINGS_OFF_PARENT` parity — by construction, not by resemblance

In that mode `ResearchEngineV016.__init__` constructs a genuine,
unmodified `mrofyt_engine_v015.ResearchEngineV015` and forwards every
call to it. There is no mirrored copy of the v01.5 path inside v01.6
that could drift. Test **B17** proves byte-identical ledger and log
output on a shared fixture, and additionally asserts
`type(engine.co) is CoordinatorV015`. B17b proves the other three
toggles genuinely differ, so "identical" is a real constraint rather
than a vacuous one.

### Available-R

```
Available_R = distance to next opposing eligible structural level
            / distance to frozen structural stop
```

Thresholds unchanged: reject below `0.70R`, A+ at `>= 2.0R`. A nearer
opposing swing can **reduce** available space. A same-direction
supporting swing is location context only and can never expand space by
ignoring a closer opposing non-swing level — `available_r()` therefore
takes opposing levels alone.

## 6. Test results (actual output)

```
cd analysis/mrofyt && python3 tests_mrofyt_v01_6.py     # 21/21
```

Full battery, every suite re-run at this freeze:

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
| `tests_mrofyt_v01_6.py` | **21/21** |
| `tests_mrofyt_v01_7.py` | 15/15 |
| **total** | **370/370** |

**Synthetic tests prove implementation behaviour only.** None of this is
evidence of profitability, prediction accuracy or positive EV.

## 7. Traceability

| § | Requirement | Code | Test |
| --- | --- | --- | --- |
| 10.1 | availability only at `j+2` close | `detect_swings`, `Swing.available_at` | B1 |
| 10.2 | arrival order changes no identity | `CoordinatorV016.on_group` (inherits v01.5 ordering) | B2 |
| 10.3 | plateau → one deterministic swing | `is_swing_high/low` | B3 |
| 10.4 | partial/mixed bars form no swing | `detect_swings`, `BarAggregator._close` | B4 |
| 10.5 | calendar-aligned, no roll crossing | `bucket_start`, `BarAggregator` | B5 |
| 10.6 | 1m stays diagnostic | `ACTIVE_TF`, `Swing.eligible_tf` | B6 |
| 10.7 | eligibility only after availability | `Swing.eligible`, `SwingLifecycle.levels` | B7 |
| 10.8 | one `CAUSAL_SWING` vote | `cluster_swings` | B8 |
| 10.9 | later swing cannot reset an approach | `CoordinatorV016.on_price` | B9 |
| 10.10 | two closes → accepted; reclaim → reclaimed | `SwingLifecycle.on_tf_close` | B10 |
| 10.11 | no silent polarity flip | `RETIRED_STATES` | B11 |
| 10.12 | roll retires prior-contract swings | `on_contract_roll` | B12 |
| 10.13 | no duplicate episodes | inherited v01.5 callback set | B13 |
| 10.14 | opposing signals → zero fill | inherited v01.5 F6 | B14 |
| 10.15 | complete ledger records | `_ledger`, `observe` | B15 |
| 10.16 | four re-armed setups, no cap | inherited re-arm | B16 |
| 10.17 | `SWINGS_OFF_PARENT` bit-identical | delegation to v01.5 | B17, B17b |
| 10.18 | no live order submission | — | B18 |
| 10.19 | full inherited + v01.6 suite | — | B19, battery above |

## 8. Blocked, user-side

Unchanged from the v1.2 recorder freeze and **not** performed here:
real NinjaTrader F5 compilation, Market Replay or live smoke testing.
This environment has no NT8, Windows or live feed. A stub compile is not
an API validation, and nothing in this wave should be read as one.

## 9. What swing levels can and cannot do — plainly

A confirmed swing high or low marks a price where the market has already
turned, confirmed only after two more bars close. That is useful for one
reason: it says **where** other traders' stops and resting orders are
likely to sit, so it is a sensible place to *look* at the tape and the
book.

It does **not** tell you which way price will go. It is not a signal, it
has no direction, and it carries no expected value on its own. Two bars
of confirmation lag is a real cost: by the time a swing is usable, price
has already moved away from it. Everything about whether tape and depth
behave differently at a swing than anywhere else is an open question
that needs genuine recorded data to answer — and that data does not yet
exist in sufficient quantity.

## 10. Readiness

Genuine captured sessions with complete bulk CSVs: **one date**
(2026-09-01), covering 162.3 s of NQ and 344.5 s of MNQ with **zero
seconds of simultaneous coverage** — see
`MROF_YT_PILOT_DIAGNOSTIC_FINDINGS.md`. Fourteen further runs exist as
manifests only.

That is far below every readiness gate. Classification stands at
**`INSUFFICIENT_DATA`**.
