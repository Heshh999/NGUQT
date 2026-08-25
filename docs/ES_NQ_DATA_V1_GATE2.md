# ES-NQ-DATA-V1 — GATE 2: EMPIRICAL ES/NQ ROLL PARITY

**Verdict: `ES-NQ-DATA-V1 PASS — READY FOR XMARKET-V1 EXECUTION`**

Gate 1 (synchronization) passed earlier. This document closes Gate 2,
the last data gate, using the actual seven-year history rather than the
CME convention the quarantine was originally built from. Raw output:
`scratchpad/roll_parity*.py` transcripts.

Nothing frozen was modified. No hypothesis, threshold, window, control
or normalization was changed. The only change is a **subtractive**
widening of the roll quarantine in `analysis/xmarket/es_nq_data_spec.py`.

---

## 1. Method

Candidate discontinuities were selected **without any reference to a
roll calendar**, independently in each market:

- every session boundary ranked by `|last close of day D -> first close
  of day D+1| / ATR20`
- maximum intraday normalized 1-minute move per day
- daily volume
- `|REL_STRENGTH|` extremes surviving the quarantine

Only afterwards was each candidate labelled INSIDE / OUTSIDE quarantine.

## 2. Session-boundary shifts

| | NQ | ES |
|---|---|---|
| boundaries tested | 2,217 | 2,245 |
| largest normalized shift | 98.18 ATR (2022-02-27, −363.25 pt) | 120.00 ATR (2022-02-27, −114.00 pt) |
| top-100 inside quarantine | 0 | 0 |
| top-100 outside quarantine | 100 | 100 |

100% outside — and every one of them is a **weekend re-open gap**, not a
contract transition:

- **97 of the top 100 fall on a Sunday, 3 on a Monday, 0 on a Thursday.**
  A quarterly roll is a Thursday event.
- **84–88%** of each market's largest shifts occur on the *same dates* as
  the other market's.
- Of boundaries with z ≥ 5 in either market (n = 275), **96.7% share the
  same sign**. A contract transition moves one market; a news gap moves
  both.
- `corr(NQ normalized boundary gap, ES normalized boundary gap) =
  **+0.9368**` (n = 2,216).

The largest are 2022-02-27 (Ukraine escalation), 2020-03-08 (oil-price
war), 2025-04-06 — real, shared, simultaneous.

## 3. What roll days actually look like

| | NQ median / max z | ES median / max z |
|---|---|---|
| roll-window Thursdays | 0.260 / **4.64** | 0.460 / **4.00** |
| all non-roll days | 0.456 / **98.18** | 0.563 / **120.00** |

Roll boundaries are the **calmest in the dataset**. Max intraday
normalized 1-minute move tells the same story:

| day class | NQ max | ES max |
|---|---|---|
| all days | 60.00 | 105.00 |
| 2nd Thursday | 12.55 | 11.20 |
| expiry − 8 (true CME roll) | 12.55 | 11.20 |
| expiry (3rd Friday) | 21.56 | 22.86 |

**No roll or expiry day contains an outlier as large as ordinary days
routinely produce, in either market.** A raw-stitched series would put
its single largest move exactly there.

## 4. DEFECT FOUND AND FIXED — quarantine calendar

The original `roll_days()` anchored only on the **2nd Thursday** of the
quarter month. The CME equity-index roll is defined against **expiry**
(3rd Friday) at 8 days prior; the two anchors coincide only when the
month's weekday alignment happens to make them coincide.

Across 2019–2026 they diverge by 7 days in **4 of 32 quarters** —
2019-03-07, 2023-09-07, 2023-12-07, 2024-03-07 — which the ±2 pad could
not bridge. On those four days the true roll fell **outside** the
quarantine.

Empirically those days are inert:

| missed roll day | NQ boundary gap | ES boundary gap |
|---|---|---|
| 2019-03-07 | (pre-history) | (pre-history) |
| 2023-09-07 | −0.25 | −0.25 |
| 2023-12-07 | −1.50 | +0.00 |
| 2024-03-07 | −0.75 | −0.25 |

Sub-tick to 1.5 points, against a `|REL_STRENGTH|` p99.9 of 3.32 ATR.
Nothing was contaminated.

**The quarantine was widened anyway** to cover all three anchors — 2nd
Thursday, expiry−8, and expiry itself — each ±2 days. Quarantining only
removes data, so this can only make the study more conservative.

## 5. Historical construction — empirical, not assumed

Both series sit far above the levels actually traded:

| | our low | traded ≈ | offset |
|---|---|---|---|
| NQ 2020-03-23 | 9,987.75 | 6,628 | **+3,359.75** |
| ES 2020-03-23 | 2,926.50 | 2,174 | **+752.50** |
| NQ 2019-08-05 | 10,583.75 | 7,327 | +3,256.75 |
| ES 2019-08-05 | 3,521.00 | 2,775 | +746.00 |
| NQ 2022-10-13 | 13,755.75 | 10,440 | +3,315.75 |
| ES 2022-10-13 | 4,306.50 | 3,502 | +804.50 |

Both markets are **additively back-adjusted**, in the same direction, on
the same calendar. This is not a caveat — it is the construction the
study requires. The frozen normalization

```
Z_X(t,w) = (close_X(t) - close_X(t-w)) / ATR_X(t)
```

is a **ratio of differences**, and an additive shift cancels in both the
numerator and the denominator. Combined with the total absence of a jump
at any roll anchor (§3), roll construction cannot reach the normalized
fields at all.

## 6. Volume and outlier clustering

Daily volume on roll days is 1.105× (NQ) and 1.091× (ES) the median —
mild, and consistent with genuine quarterly expiry activity rather than
a stitch. Normalized-return outliers are mildly enriched on roll days
(NQ 8.4%, ES 9.1% of the top 1,000 vs a 5.0/5.2% base rate), which is
quad-witching volatility; those bars are quarantined regardless.

## 7. Data holes — reported, never filled

- **ES**: one ~10.5-hour hole (2022-11-06 19:00 → 2022-11-07 05:34) plus
  a handful of late Sunday opens (2021-10-03 19:51, 2025-07-13 20:10).
- **NQ**: exactly **one** missing day in seven years — 2025-08-29. Every
  other ES-only day is the pre-NQ-history month of June 2019.
- **Zero days exist in NQ but not in ES.**

Nothing is forward-filled or interpolated. `Z` requires exactly
consecutive minutes, so a hole **voids** the field rather than bridging
it, and the unmatched minute is dropped by the synchronization table.

## 8. THE GATE 2 CRITICAL QUESTION

> Could an unquarantined contract transition create a fake NQ/ES
> divergence, relative-strength extreme, lead/lag event, or cross-market
> disagreement?

### **NO.**

1. Rolls produce no level shift in either market — both back-adjusted,
   and roll boundaries are the calmest in the data.
2. The four formerly-unquarantined roll anchors carry gaps ≤ 1.50 NQ
   points; `|REL_STRENGTH|` p99.9 is 3.32 ATR.
3. Large boundary shifts are Sunday gaps **shared** by both markets
   (+0.9368 correlation, 96.7% sign agreement, 0 Thursdays).
4. Of the 20 most extreme post-quarantine divergences, **none** fall on
   a quarantined day; 4 sit near one and are all COVID-era limit moves;
   the rest cluster at 09:31–09:36 — the cash open, a genuine
   microstructure effect the pre-registration explicitly tests for.

## 9. Pass conditions

| # | condition | result |
|---|---|---|
| 1 | no material unexplained roll discontinuity outside quarantine | **PASS** |
| 2 | cross-market normalized returns uncontaminated by roll construction | **PASS** |
| 3 | relative-strength fields undistorted by unhandled transitions | **PASS** |
| 4 | NQ/ES historical construction sufficiently compatible | **PASS** |

## 10. Final synchronized universe

| | corrected quarantine | original quarantine |
|---|---|---|
| **MATCHED** | **2,243,394** | 2,361,754 |
| ROLL_QUARANTINED | 258,873 | 140,513 |
| NQ_ONLY | 1,355 | 1,355 |
| ES_ONLY | 40,157 | 40,157 |

118,360 additional bars quarantined by the fix. Of NQ minutes where an
ES bar exists at all, **99.94%** still match on the exact close-stamped
ET minute, with a maximum clock discrepancy of **0**.

---

```
ES-NQ-DATA-V1 PASS
READY FOR XMARKET-V1 EXECUTION
```

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
