# MROF_YT_WAVE2_REGISTRATION.md — second-wave hypotheses, registered blind

**Status: DRAFT — PENDING OPERATOR SIGN-OFF.** Items marked `[SIGN-OFF]`
need the operator's number or approval. On sign-off this file is
hash-pinned and becomes immutable; any later change is a new wave.

**Registered:** 2026-09-18. **Informed by:** sessions 2026-09-01 →
2026-09-18 only (all labelled `EXPOSED_PILOT_DEV`). **Judged on:**
sessions from 2026-09-21 onward, which nobody has examined.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Every test below is
read-only shadow research on recorded tape. No order is placed.

---

## 0. What this document is and is not

Wave one (A1–A6 as frozen in `mrofyt_signals.py`, session/VWAP/pivot
levels from `mrofyt_levels.py`) **continues unchanged**. It runs blind
to the December checkpoint and is reported exactly as it is. Nothing in
this file modifies a wave-one threshold, level, window, feature, baseline
or exit. Wave-two code, when written, lives in new modules; the frozen
detectors are never edited.

This file exists because a hypothesis registered *after* its outcome is
known is not a hypothesis. Nine exposed sessions were enough to show
which wave-one families are *structurally* unable to produce evidence.
Those are facts about definitions, not about outcomes, and they are the
only thing this design uses.

## 1. Wave-two families

| family | status | reason |
| --- | --- | --- |
| **W2-A1** absorption | kept, one input redefined | mechanism sound; wave-one input `replenish_z` observed only at executions, 171 of 44,628 windows |
| **W2-A4r** failed break, *as it ran* | kept, registered honestly | 65 events; `resid_tail_5pct` unwired, so `response_failed` was `progress_ticks <= 1` alone. This IS the hypothesis that has evidence |
| **W2-A4f** failed break, *full* | registered, pending wiring | the residual model of the original A4, as a separate named variant so the two are compared, never conflated |
| **W2-A4-OPEN** | new | see §2 |
| A2 wall | **dropped** | qualifying wall in 2.1% of windows; `exec_vs_displayed` median 0.0. The premise does not occur at this instrument and size. Wall state survives as a *label* (§5) |
| A3 vacuum | **dropped** | 3 evaluable checks in 9 sessions; cannot accumulate a population |
| A5 trend-adverse | **dropped** | 4 of 5 inputs hardcoded `None`; wiring it is its own future wave |
| A6 open control | **folded into W2-A4-OPEN** | blocked on the same `rr` laggard as A1 |

### 1.1 W2-A1 replenishment redefinition

Wave one: `rr = adds_at_level / executions_at_level`, observed only when
`exec_at > 0`. Wave two:

```
repl10 = sum(ADD size, top-3 levels, approached side, last 10 s)
         / (sum(executions at those levels, last 10 s) + 1)
```

observed on **every** 10 s grid tick like `delta10`, z-scored against the
same `(feature, 5-minute-of-day)` robust baseline with the same 5-prior
floor. Every other W2-A1 condition and threshold is identical to A1.
This is a new feature, not a retune.

## 2. W2-A4-OPEN — where the mechanism is forced

29 of 65 wave-one events sat at `CASH_OPEN_0930`, nearly all inside the
first 30 minutes, HIGH/HIGH regime. Overnight positioning must resolve at
the open: that is forced flow with a structural reason.

- conditions: identical to W2-A4r
- levels: `CASH_OPEN_0930`, `OVERNIGHT_HIGH`, `OVERNIGHT_LOW` only
- window: 09:30:00 – 10:30:00 ET only
- everything else frozen as wave one

## 3. Threshold variant — the legitimate use of the funnel

The wave-one funnel shows `aggr_z >= 2.0` removed 1,400 of A4's 2,385
input-complete windows. That is information about where the threshold
sits relative to what occurs. Wave one is **not** retuned. Instead:

- **W2-A4r-z15**: W2-A4r with `aggr_z >= 1.5`, all else identical.

Reported beside W2-A4r, never in place of it. Its verdict comes from
validation sessions only.

## 4. The three comparison arms

### 4.1 Arm B — candle-only trigger on the same approaches `[SIGN-OFF]`

Same approaches, same levels, same decision instant; the flow features
are replaced by a bar-only rule. Evaluated on the 1-minute bar that
contains the approach, at that bar's close.

- **B1 rejection wick:** the bar's wick beyond the level is `>= 50%` of
  the bar's range **and** the close is back on the approach side.
  Direction: away from the wick.
- **B2 engulfing reclaim:** the bar closes through the level and the
  *next* 1-minute bar closes back on the original side. Direction: back
  toward the original side. (Decision instant is the second bar's close.)

Two rules, both frozen here. Adding a third later is a new wave.

### 4.2 Arm C — placebo levels (matched control)

For every validation session, the full wave-two pipeline is re-run with
the level set replaced by **placebo levels**: each real level shifted by
a per-session random offset, drawn once per session with a fixed seed
(`seed = int(session)`), constrained so every placebo price is
`>= 3 x proximity radius` from every real active level. Same detectors,
same thresholds, same baselines, same de-duplication.

Arm C answers: does flow at *levels* predict, or does flow predict
*everywhere* and the levels are decoration? Without it a positive result
is uninterpretable.

### 4.3 Level-set comparison — `CAUSAL_SWING` vs session/VWAP/pivot

The v01.6 engine (`mrofyt_swings_v016.py`, frozen, 21/21) supplies the
level set; the detectors are W2-A1 and W2-A4r unchanged.

- timeframes: `ACTIVE_TF` = 5m, 15m, 60m (1m diagnostic only)
- availability: causal, close of bar `j+2`
- eligibility: `CONFIRMED_UNTOUCHED`, `ACTIVE_TESTED`,
  `BROKEN_PENDING_ACCEPTANCE`, `RECLAIMED_BEFORE_ACCEPTANCE`
- acceptance: 2 consecutive own-timeframe closes beyond

Paired with the session/VWAP/pivot run on the same sessions. The
question is whether uncrowded, causal structure behaves differently from
the levels every desk watches — not which "makes more money".

## 5. Conditioning labels (stratification, not new families)

Each wave-two event carries these labels at fire time. They split an
existing population; they never create one.

| label | definition |
| --- | --- |
| `asia_inside` | fire price within [Asia low, Asia high]; Asia window = 18:00:00 → 02:59:59 ET (Globex open → London open) |
| `asia_ranged` | Asia range `<= 0.75 x ATR20` (ATR20 in points as of 18:00 ET from the prior completed session) `[SIGN-OFF: 0.75]` |
| `wall_state` | wave-one wall overlay at fire (`NO_QUALIFYING_WALL`, `WALL_OBSERVED`, …) |
| `regime` | wave-one range/volume regime at fire |
| `aggr_conf_high_only` | see §6 |

Asia is tested as: median primary metric, `asia_inside` vs not, paired
by session. Nothing else. "Track Asia structure and look" is explicitly
not registered.

## 6. Measure the feed's weakness instead of assuming it away

`aggr_z` rests on an *inferred* aggressor side (`aggressorSource:
ABSENT-feed; inferred QUOTE_TEST_v1`). The recorder writes `aggrConf`
per trade.

- Report the HIGH / LOW confidence split per session.
- **W2-A4r-HC**: W2-A4r computed on `aggrConf == HIGH` trades only.

If the signal survives, the inference is not driving it. If it collapses,
the feed cannot support the hypothesis — a real answer, not a failure.

## 7. Primary metric, friction, kill criteria

**Primary metric (one number, decided now):**
median signed mid markout at **300 s**, NQ signal-source events only,
de-duplicated at 60 s (`mrofyt_pilot.dedup_fires`), **minus** the arm-C
placebo median, paired by session. Secondary: 600 s, 1800 s, and
`frac_positive`.

**Friction F** (from the operator's account report, limit-in /
limit-out, no spread crossed) `[SIGN-OFF — confirm from the Fills tab]`:

```
NQ   ~0.09 points round trip
MNQ  ~0.91 points round trip
```

**Reading rule per family, at the December checkpoint (2026-12-01):**

| NQ events (dedup) | paired primary metric | verdict |
| --- | ---: | --- |
| `< 30` | — | **NOT TESTED** (not "failed"; keep recording) |
| `>= 30` | 95% interval includes 0 | no signal |
| `>= 30` | positive, but `< F` | signal real, friction eats it — execution problem |
| `>= 30` | positive, `>= F`, interval excludes 0 | promising; proceed to sizing study, still no live orders |

**Hard kill:** at **200** NQ events for a family, if the paired 95%
interval includes zero, that family is dead and is not re-cut, re-tuned
or re-windowed. `[SIGN-OFF: 200]`

**Family minimum:** a family with `< 30` NQ events by 2026-12-31 is
reported as untested and carried forward without modification.

## 8. Exposure and hold-out

- **DEV (exposed):** every session `<= 20260918`. May inform design.
  Already labelled `EXPOSED_PILOT_DEV`.
- **Validation (untouched):** every session `>= 20260921`. No wave-two
  number is read from these until the checkpoint. Any session examined
  early is moved to DEV and labelled, permanently.
- Wave one keeps its own exposure ledger; the two are never merged.

## 9. Explicitly NOT registered

So that a later "we should also…" is recognised as a new wave with its
own budget:

- any threshold other than those named above
- any level not named above
- any horizon other than 300 / 600 / 1800 s
- machine-learned models of any kind
- additional instruments
- any exit study (E0/E1/E2 remain locked behind State-C)
- live, paper or simulated order placement

## 10. Sign-off

| item | value | operator initials |
| --- | --- | --- |
| F (NQ / MNQ, points) | 0.09 / 0.91 | |
| Asia ranged threshold | 0.75 x ATR20 | |
| Hard kill N | 200 | |
| Arm B rules B1 + B2 | as §4.1 | |
| Validation start | 20260921 | |

On sign-off: hash this file, pin it in `REVIEW_PACKAGE_MANIFEST_v01_6_7.md`
and in the test suite, and stop editing it.
