# ANOMALY-CONFIRM-V1 — PREREGISTRATION (frozen BEFORE any holdout statistic exists)

**Status: PREREGISTRATION ONLY.** No holdout outcome has been computed.
This document is written, hashed, committed and pushed *first*; only a
later directive may execute it. Nothing here creates a trading rule.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**

---

## 0. RESULT-BLINDNESS DECLARATION AND CONTAMINATION DISCLOSURE

### 0.1 What has NOT been computed

No candidate outcome on the holdout window (≥ 2024-01-01) exists. As of
this freeze, for AC-FLIP, MONDAY, MONDAY-RTH, SHOCK-CONT-MEDIUM or any
other ANOMALY-SCAN-V1 statistic, **nothing** has been calculated on
2024–2026: no autocorrelation, no variance ratio, no entropy, no mean
return, no Monday return, no hit rate, no p-value, no confidence
interval, no year slice, no month slice, no RVMR slice, no 1m result,
no 15m result. No "quick sanity check" was run.

This is enforced structurally, not by memory: both scan engines
hard-restrict every statistic to `day[i] <= DISC_END` with
`DISC_END = '2023-12-31'` (`analysis/anomaly/scan_run.py:22,67`;
`analysis/anomaly/scan2_run.py:19,63`), and every downstream index set
derives from that `idx` list.

### 0.2 What WAS computed on the holdout before this freeze — full disclosure

The holdout is **not pristine in the absolute sense**, and this was
recorded in the scan protocol at its own freeze
(`docs/ANOMALY_SCAN_V1_PROTOCOL.md`, lines 25–30) before any scan
statistic existed. Restated here in full:

- Prior, *separate* studies computed on 2024–2026: XMARKET-V1,
  RVMR-VALIDATION-V1, RVMR-BANDS-V1, NQ-DIRECTION-V1, 4H-DVT-V1.
- Those studies estimated entirely different objects (cross-market
  breakout confirmation, quantile band calibration, directional entry
  edges, a 4H/15m/1m entry construction). **None** of them computed
  serial correlation by RVMR state, weekday accrual, variance ratios,
  block entropy, or any statistic in the ANOMALY-SCAN-V1 menu.
- What the holdout is therefore protected against is **this family's
  selection process**: the two candidates below were selected using
  discovery-window data only.

**Honest limitation, stated before the test:** a confirmed result here
is HISTORICAL evidence from a window that has been touched by unrelated
studies. It is not a prospective out-of-sample result. Prospective
shadow validation would remain a separate, later, and unfunded step.

### 0.3 What was permitted and done before this freeze

Only: source and code inspection; file availability; timestamp/date
coverage; row counts for feasibility; schema inspection. The coverage
counts in §2.2 were produced by a script that reads **only the `et`
timestamp column** — it never touches open, high, low, close or volume,
so it cannot expose any candidate outcome.

---

## 1. CANDIDATE SELECTION — A CONFLICT, SURFACED AND RESOLVED ON THE RECORD

### 1.1 The conflict

The directive commissioning this study names the two candidates:

> "ANOMALY-SCAN-V1 found at most two candidates eligible for
> confirmation: 1. AC-FLIP — RVMR-CONDITIONAL RETURN-MEMORY /
> AUTOCORRELATION STRUCTURE  2. MONDAY — POSITIVE MONDAY RETURN EFFECT"

and simultaneously instructs:

> "Do NOT reconstruct AC-FLIP or MONDAY from this prompt. The scan
> source is authoritative."

The frozen scan source, however, does not end on those two names. Its
Wave-2 section (`docs/ANOMALY_SCAN_V1_FINDINGS.md`, lines 170–186)
declares:

> "1. **SHOCK-CONT-MEDIUM** … *Declared non-promotable secondaries
> inside the same study:* the 1m AC-FLIP, the CLV flip, and the leverage
> V-curve — reported, never promoted.  2. **MONDAY-RTH** …
> This supersedes the Wave-1 pick of raw AC-FLIP as primary (it becomes
> a secondary), declared here while the holdout remains untouched, as
> the frozen protocol permits."

So the directive funds {AC-FLIP, MONDAY}; the authoritative source's
last word funds {SHOCK-CONT-MEDIUM, MONDAY-RTH}. Both cannot be run:
the frozen two-candidate cap (protocol lines 80–83) is binding, and
running all four would silently inflate the family from 2 to 4.

### 1.2 The resolution rule adopted (frozen)

> **The principal's directive governs WHICH hypotheses are funded.
> The frozen source governs HOW each funded hypothesis is DEFINED.**

Rationale: "the scan source is authoritative" is an instruction about
*definition* — it exists so I cannot rewrite a hypothesis from memory
into an easier form. It is not a licence for me to overrule the
principal on *which* hypotheses get tested. The Wave-2 supersession was
**my own declaration**, not the user's, and I am not entitled to spend
the user's two-candidate budget on candidates the user did not name.

Therefore:

**M = 2, and the family is exactly {AC-FLIP, MONDAY}.**

Every numeric definition below is read out of the frozen source files
(cited by file and line), never reconstructed from the directive's prose.

### 1.3 Consequences, declared now so no family game is possible

1. **The Wave-2 supersession is WITHDRAWN**, on the record, before any
   holdout contact. AC-FLIP is restored to PRIMARY status per the
   Wave-1 recommendation (`ANOMALY_SCAN_V1_FINDINGS.md:91–94`).
2. **SHOCK-CONT-MEDIUM IS NOT TESTED IN THIS STUDY.** It remains an
   unconfirmed discovery-window finding. It may not be quietly added
   later if AC-FLIP fails.
3. **Cumulative-family clause (binding on all future directives):** if
   SHOCK-CONT-MEDIUM is ever tested on this same holdout, it enters a
   **cumulative family of M_cum = 3** and its multiplicity correction
   must be computed against M_cum = 3, not M = 1. The same applies to
   the leverage V-curve, the CLV flip, the half-hour-mark drift, and
   every other Wave-1/Wave-2 finding: each additional holdout test
   increments M_cum by one, permanently. **The family may grow with
   each new test; it may never shrink.**
4. **MONDAY-RTH is not discarded.** The source's Wave-2 S22
   decomposition sharpened MONDAY, so MONDAY-RTH is carried as a
   **pre-declared secondary inside the MONDAY candidate** (§5.4). A
   secondary can corroborate; it can never promote on its own, and it
   does not add to M.

---

## 2. PROVENANCE AND THE DISCOVERY / HOLDOUT BOUNDARY

### 2.1 Authoritative sources (paths, hashes, commits at this freeze)

| artifact | sha256 | last commit touching it |
|---|---|---|
| `docs/ANOMALY_SCAN_V1_PROTOCOL.md` | `edd1f1baae50619a689da15b2ffedfb9c5865e698304c45588b4dbb2ab19255f` | `c4c4d8202e0f9562f659f3f9a659b53da842b067` |
| `docs/ANOMALY_SCAN_V1_FINDINGS.md` | `79e0355cdc996f5bf7a278c3265140c05ae5997727fd5d7b336890ccd1d0ef22` | `70c373568e636a911f6a5f43693263a058053f82` |
| `analysis/anomaly/scan_run.py` (Wave 1) | `03d65b1dd6f5fb8995373d188ea2576c9956fa20ab8928d0e5171548a2c92e89` | `03f0e985505a06c4808bf94b34e4d241b57e6a33` |
| `analysis/anomaly/scan2_run.py` (Wave 2) | `6c52693ff4a44fcd7090e9bfd82869196572822ef137547b4e42b9a47f9fd747` | `70c373568e636a911f6a5f43693263a058053f82` |
| `analysis/rvmr/rvmr_spec.py` (frozen RVMR-V1) | `e348f035a920954054a2b3e76ac0f0363b5502ccb2c872a2276d6236a152cd62` | `84933d28c71c07e149e7728a96b4af7d30ea1685` |
| `analysis/rvmr/rvmr_run.py` (canonical loader) | `8743161d6fb5b04e8092f4ea571e86bb09bedd9db161dc6d31b364a0b868bd8c` | `9d14dfaa9be90b5a3ee407690b543dcedbb27bc0` |

Protocol freeze order for the record: Wave-1 protocol `9f71b24`
(sha256 `179af253…47ea67`) → Wave-1 scan `03f0e98` → Wave-2 menu
`c4c4d82` → Wave-2 scan + findings `70c3735` → **this preregistration**.

Data: `…/scratchpad/rvmr_1m/rvmr_1m_{2019..2026}.csv`, eight files,
loaded by `rvmr_run.load_bars()` with `STAMP_SHIFT = 0`
(`scan_run.py:63`, `scan2_run.py:58`) — close-stamped ET wall clock.

### 2.2 Separation proof — coverage only, no outcomes

Timestamp-column-only census of the full data set (2,503,622 rows):

| window | rule | rows | exchange days | span |
|---|---|---|---|---|
| DISCOVERY | `day <= 2023-12-31` | 1,577,173 | — | 2019-01-02 … 2023-12-29 |
| **HOLDOUT** | `day >= 2024-01-01` | **926,449** | **820** | 2024-01-01 18:01 … 2026-08-17 15:16 |

Holdout structure (feasibility only):

- Contiguous 1m pairs available (timestamp arithmetic only): **925,748**
- RTH-stamped bars (minute-of-day 570…960): **259,372**
- Exchange days by year: 2024 → 313, 2025 → 311, 2026 → 196
- Distinct months: **32** (2024-01 … 2026-08)
- Day-of-week counts: Mon **138**, Tue 137, Wed 137, Thu 137, Fri 134,
  Sun 137, Sat 0
- Monday RTH-stamped bars: **51,541**
- Bars available strictly before the holdout for the RVMR 1440-bar
  warmup: **1,577,173** (warmup is fully satisfied from discovery data)

The two windows are disjoint by construction: `1,577,173 + 926,449 =
2,503,622`, the full row count, with no row in both.

**Deliberately NOT computed:** holdout RVMR bucket occupancy. Counting
LOW/MEDIUM/HIGH bars requires reading high−low, which is one step from a
conditional result. The minimum-n gates in §4.6 are therefore derived
from **discovery-window proportions scaled by the holdout row count**,
not from any holdout measurement.

---

## 3. SHARED MACHINERY (frozen)

### 3.1 Loader and universe

`rvmr_run.load_bars()` verbatim, `STAMP_SHIFT = 0`. Parallel arrays
`et, day, mod, em, o, h, l, c, v`. `day` = calendar date of the ET
close stamp; `mod` = hour*60 + minute; `em` = integer minutes since
2019-01-01 (the contiguity clock).

### 3.2 Return definition

`analysis/anomaly/scan_run.py:80–86`, verbatim:

```python
for i in idx:
    if i == 0 or em[i] - em[i-1] != 1 or day[i] > <WINDOW END>:
        continue
    if c[i-1] <= 0:
        continue
    r = math.log(c[i] / c[i-1])
```

Log return of close-to-close on **strictly minute-contiguous** bars.
Gaps are skipped, never bridged, never interpolated. No 1m bar is ever
split into a lower timeframe. For the holdout run the window test
becomes `day[i] < '2024-01-01'` → skip, i.e. `idx` is the holdout index
set and the first holdout bar has no predecessor pair only if its
preceding minute is absent.

**One boundary decision, frozen now:** the return spanning
2023-12-29 → 2024-01-01 (across the year boundary) is **excluded** —
`em` differs by far more than 1, so the contiguity test already rejects
it. No special-casing is needed or permitted.

### 3.3 RVMR state (frozen, unmodified)

`rvmr_spec.trailing_ratio(high − low, W=1440)` then
`rvmr_spec.bucket()`: LOW < 1.270 ≤ MEDIUM ≤ 2.335 < HIGH. The window
is **1440 bars** ending at `i−1`, **excluding the current bar**.

Computed on the **full 2019–2026 series** exactly as the scan does
(`scan_run.py:75–76`), then read only at holdout indices. This is
causal — the normaliser for a holdout bar uses only bars strictly before
it — and it is the only way the holdout's first 1440 bars can be scored
at all. **The RVMR-V1 spec files are not modified. No recalibration.**

### 3.4 15m aggregation (for the AC-FLIP secondary)

`scan_run.py:220–230`, verbatim: within each exchange day, walk the
day's contiguous-return list; take blocks of 15 whose first and last
indices differ by exactly 14 (i.e. a genuinely unbroken 15 minutes);
non-overlapping (`k += 15` on success, `k += 1` on failure). The block's
return is the sum of its 15 log returns. The block's RVMR state is the
state of its **first** bar (`RB[block[0][0]]`).

### 3.5 Inference

- **Cluster unit: the exchange day.** A minute is never treated as an
  independent trial.
- **Day-clustered bootstrap**, resampling whole days with replacement,
  **20,000 iterations**, **seed 20260825**, percentile CI at **95%**
  (2.5% / 97.5%).
- **Bootstrap p-value:** `p = 2 × min(#{b ≤ 0}, #{b ≥ 0}) / B`, floored
  at `1/(B+1)`.
- **Day-level permutation** as an independent null (per candidate, §4.8
  and §5.6), 20,000 iterations, same seed.
- **Multiplicity: M = 2**, Benjamini–Hochberg on the two *primary*
  p-values, target **q ≤ 0.05**. Secondaries are excluded from BH and
  can never promote.
- **No ML. No parameter sweeps. No retuning. One run.**

### 3.6 Cost treatment — declared, and what it forbids

**No transaction cost is applied to either candidate, because neither
is a P&L claim.** Both primaries are structural statistics on log
returns. Consequently:

> **No gate in this document may be read as economic viability.**
> Discovery already showed the 1m predictable component at ≈ 0.2 NQ
> points against a 0.87-point round-turn cost — roughly 4× underwater.
> Confirmation would mean the *structure* is real, not that it is
> tradeable.

---

## 4. CANDIDATE 1 — AC-FLIP

### 4.1 Source of the claim (verbatim)

`docs/ANOMALY_SCAN_V1_FINDINGS.md:91–93`:

> "**AC-FLIP:** AC1(1m | LOW) < 0 < AC1(1m | HIGH), and secondarily
> AC1(15m | HIGH) < 0, using the frozen RVMR states unchanged."

### 4.2 The estimator (verbatim, including its known artifact)

`scan_run.py:201–208`:

```python
def ac(rs, lag):
    n = len(rs)
    if n < lag + 100: return float('nan')
    m = sum(rs) / n
    num = sum((rs[i]-m)*(rs[i-lag]-m) for i in range(lag, n))
    den = sum((x-m)**2 for x in rs)
    return num/den if den > 0 else float('nan')
```

applied to `rs = [r for i, r in rets if RB[i] == st]` (`scan_run.py:217`).

**KNOWN ESTIMATOR ARTIFACT, declared before the test.** This pairs
consecutive members of the *state-filtered* sequence. Two such members
are adjacent minutes only while the state persists; at a state change
the estimator pairs across a gap. RVMR states flicker (S19 dwell median
1–2 min), so a non-trivial share of pairs are non-adjacent. This is a
defect in the discovery statistic — **and it is exactly why it must be
replicated verbatim.** A confirmation test must re-measure the thing
that was found, not a cleaner thing that was not. The clean version is
frozen as a pre-declared robustness secondary in §4.5.

### 4.3 Primary endpoint (frozen)

> **AC1(1m | RANGE-LOW) < 0 AND AC1(1m | RANGE-HIGH) > 0**, with the
> **gap** `G = AC1(HIGH) − AC1(LOW)` as the single scalar carried into
> inference and multiplicity.

MEDIUM is reported but is **not** part of the primary (discovery
MEDIUM +0.0166 sits between the two poles; requiring monotonicity would
be a post-hoc tightening).

### 4.4 Discovery baselines (the retention anchors — frozen numbers)

| slice | n (1m returns) | AC1(1m) | AC1(15m) |
|---|---|---|---|
| RANGE **LOW** | 1,187,450 | **−0.0280** | +0.0023 |
| RANGE MEDIUM | 288,214 | +0.0166 | −0.0050 |
| RANGE **HIGH** | 95,744 | **+0.0239** | **−0.0321** (n 5,326) |
| pooled | 1,572,786 | +0.0085 | +0.0219 |

Discovery gap **G_disc = +0.0239 − (−0.0280) = 0.0519**.

Corroborating discovery statistics (secondaries only): VR(15) LOW
0.9779 / MED 0.9924 / HIGH 1.0053; 5-bit entropy deficit LOW 0.0056 /
MED 0.0008 / HIGH 0.0073; corr(CLV, r₊₁) LOW −0.0070 / MED +0.0088 /
HIGH +0.0141.

### 4.5 Primary vs secondary — declared from source, not chosen later

**PRIMARY (one endpoint):** the 1m sign flip, scalar `G`.

**SECONDARIES (reported, never promoting, excluded from BH):**

- **S-a** AC1(15m | HIGH) < 0 — the source's own "and secondarily".
- **S-b** VR(15) gradient: VR(15|LOW) < VR(15|HIGH).
- **S-c** 5-bit block-entropy deficit: LOW and HIGH both exceed MEDIUM.
- **S-d** CLV flip: corr(CLV, r₊₁) negative in LOW, positive in HIGH.
- **S-e** *Adjacency-restricted robustness:* the same AC1 by state,
  computed only over pairs where the two minutes are genuinely adjacent
  (`em` differs by 1) **and both** carry the same state. Reported
  alongside the primary. It may **not** rescue a failed primary and may
  **not** overturn a passed one; it exists to tell the reader whether a
  confirmed flip is market structure or the filtering artifact of §4.2.

### 4.6 Scale requirement — decided BEFORE the holdout

The 1m scale is **primary**; the 15m scale is **secondary**.

Reason, fixed now and not after seeing anything: the 1m result rests on
1.57M discovery observations, the 15m HIGH cell on 5,326 blocks — a
~300× difference in information. Requiring both to confirm would let the
weakest cell veto the strongest evidence; requiring either would be a
free extra ticket. So: **AC-FLIP confirms on the 1m flip alone; the 15m
reversion is corroboration whose failure is reported and costs nothing.**

### 4.7 Effect-retention gates (numeric, frozen)

Half of the discovery effect must survive:

- `AC1(1m|LOW) ≤ −0.0140` (50% of |−0.0280|)
- `AC1(1m|HIGH) ≥ +0.0120` (50% of +0.0239)
- `G ≥ +0.0260` (50% of G_disc = 0.0519)

Minimum-n floors, derived from discovery proportions (LOW 75.5%,
MEDIUM 18.3%, HIGH 6.1%) × 926,449 holdout rows, then discounted 40%:

- LOW ≥ **420,000**, MEDIUM ≥ **100,000**, HIGH ≥ **33,000** filtered
  1m returns.

### 4.8 Inference for AC-FLIP (frozen)

`ac()` is a ratio of sums, so the bootstrap uses **per-(day, state)
sufficient statistics** — `n`, `Σr`, `Σr²`, and `Σ r_k·r_{k−1}` over
pairs **within that day** — accumulated across resampled days. This is
the same estimator computed day-blocked: it drops the (days − 1)
cross-day boundary pairs out of ~700k, and it is the *only* form that
makes a day-clustered resample well defined. Both numbers are reported:

- **Replication estimate** = verbatim `ac()` on the pooled filtered list
  (scan-identical). **This is the number compared against §4.7.**
- **Inference estimate** = day-blocked, used for the CI and p-value.

Gates: the day-clustered 95% CI on `G` must exclude 0 (20,000 iters,
seed 20260825).

**Permutation null (independent of the bootstrap):** within each
exchange day, randomly permute the order of that day's 1m returns while
leaving the state labels attached to their positions. This destroys
serial dependence, preserves each day's return distribution and the
holdout's exact state composition. 20,000 iterations, seed 20260825.
Two-sided p on `G`.

### 4.9 Stability gate

- Sign of the flip (LOW < 0 < HIGH) correct in **≥ 2 of 3** calendar
  years {2024, 2025, 2026-partial}.
- Sign of the flip correct in **≥ 20 of 32** months.

### 4.10 Tail destruction

AC1 is outlier-dominated. Recompute the primary after **symmetric
winsorization of the 1m return series at the holdout's own 0.5% /
99.5% quantiles of `r`**, and again at **2.5% / 97.5%**. Gate: both
signs (LOW negative, HIGH positive) must survive **both** winsorization
levels. Magnitudes will shrink; only the signs are gated.

### 4.11 THE TEN CONFIRMATION CONDITIONS FOR AC-FLIP

| # | condition | threshold |
|---|---|---|
| A1 | Data integrity | ≥ 900,000 holdout bars, ≥ 750 exchange days, 0 duplicate stamps, 0 OHLC violations (`h ≥ max(o,c)`, `l ≤ min(o,c)`, `h ≥ l`) |
| A2 | Warmup / state availability | RVMR RANGE state non-None for ≥ 95% of holdout bars; every scored bar has 1440 strictly-prior bars |
| A3 | Minimum n | LOW ≥ 420,000; MEDIUM ≥ 100,000; HIGH ≥ 33,000 filtered 1m returns |
| A4 | LOW sign | `AC1(1m\|LOW) < 0` |
| A5 | HIGH sign | `AC1(1m\|HIGH) > 0` |
| A6 | Magnitude retention | `AC1(1m\|LOW) ≤ −0.0140` **and** `AC1(1m\|HIGH) ≥ +0.0120` |
| A7 | Gap retention | `G = AC1(HIGH) − AC1(LOW) ≥ +0.0260` |
| A8 | Dependence-aware CI | day-clustered 95% CI on `G` excludes 0 (20,000 iters, seed 20260825) |
| A9 | Multiplicity + permutation | BH-adjusted `q ≤ 0.05` at M = 2 **and** within-day-shuffle permutation `p ≤ 0.05` |
| A10 | Stability + tails | sign correct in ≥ 2 of 3 years **and** ≥ 20 of 32 months **and** both signs survive 0.5%/99.5% **and** 2.5%/97.5% winsorization |

---

## 5. CANDIDATE 2 — MONDAY

### 5.1 Source of the claim (verbatim)

`docs/ANOMALY_SCAN_V1_FINDINGS.md:93–94`:

> "**MONDAY:** mean Monday exchange-day return > 0 with day-clustered CI
> excluding 0."

### 5.2 The estimator (verbatim), and every convention it carries

`scan_run.py:295–310`:

```python
dayret = collections.defaultdict(float)
for i, r in rets:
    dayret[day[i]] += r
w = dt.datetime.strptime(dd, '%Y-%m-%d').weekday()      # Mon == 0
```

Definitions this fixes, each stated so none can drift at execution time:

- **Return window** = sum of *all* contiguous 1m log returns whose bar
  carries that calendar date. Not open-to-close, not settlement-to-
  settlement. A simple additive accrual.
- **Session window** = the whole calendar date, 00:00–23:59 ET,
  including the 18:00–24:00 evening block.
- **Monday classification** = `weekday() == 0` on the **calendar date of
  the ET close stamp**.
- **Timezone** = ET wall clock as stamped by the loader (`STAMP_SHIFT =
  0`). DST shifts are inherited, not corrected — minute-of-day is a
  wall-clock coordinate, as in discovery.
- **Sunday / overnight handling — the important quirk, preserved
  verbatim:** Sunday-dated bars (Sunday 18:00 ET onward, the true start
  of Monday's session) form their **own** exchange day and are **NOT**
  part of the Monday figure. Monday-dated bars **DO** include Monday
  18:00–24:00, which is the start of *Tuesday's* session. The Monday
  cell is therefore a calendar-date accrual, not a session accrual.
  This is a real definitional oddity in the discovery statistic; it is
  reproduced exactly, because that is what was found.
- **Holidays** = Mondays with no bars simply do not appear; n falls.
  No imputation, no forward-fill, no manufactured bars.
- **Early closes** = included as-is, unadjusted, as in discovery.
- **Cost** = none (§3.6). This is an accrual statistic, not a strategy.
- **Cluster unit** = the exchange day, which here is also the
  observation — so the day-clustered bootstrap reduces to an ordinary
  bootstrap over the 138 Monday day-totals.

### 5.3 Primary claim, control and null (frozen)

**PRIMARY:** mean Monday exchange-day return > 0, day-clustered 95% CI
excluding 0.

**CONTROL (gate M7):** Monday must be *distinguished*, not merely a
by-product of a rising market. Frozen contrast:

> `Δ = mean(Monday) − mean(all non-Monday exchange days)` must be `> 0`
> with its own day-clustered 95% CI excluding 0.

The comparison pool is every non-Monday exchange day in the holdout
(Tue/Wed/Thu/Fri/Sun as the loader dates them), using the identical
`dayret` construction. Discovery reference: Tue–Sun spanned −2.9 to
+4.3 bp, all CIs including 0.

**NULL:** returns are exchangeable across weekdays; Monday carries no
special accrual.

### 5.4 Secondary — MONDAY-RTH (declared, non-promoting)

From `scan2_run.py:357–377` (S22): segment accruals per session,

- `SUN 18:00-24:00` — Sunday-dated bars with `mod ≥ 1081`
- `MON 00:00-09:29` — Monday-dated bars with `mod ≤ 569`
- `MON RTH` — Monday-dated bars with `570 ≤ mod ≤ 960`

Discovery: **MON RTH +16.63 bp, CI [+5.82, +27.21]**; the other two
segments null. Secondary gate (reported, cannot promote): MON RTH mean
> 0 with CI excluding 0 and mean ≥ **+8.32 bp** (50% retention).

If the exchange-day primary fails but MONDAY-RTH passes, the verdict is
**NOT CONFIRMED** with the RTH result reported as a note. A secondary
never rescues a primary.

### 5.5 Materiality-retention rule (numeric, frozen)

Discovery: **+22.08 bp**, CI [+7.52, +35.73], n = 234.

> Holdout mean Monday exchange-day return must be **≥ +11.04 bp**
> (50% of the discovery point estimate).

Rationale for stating it now: a statistically significant +2 bp Monday
would be a confirmed *sign* and a destroyed *effect*. Both matter, and
the threshold has to exist before the number does.

### 5.6 Inference for MONDAY (frozen)

- Bootstrap over the 138 Monday day-totals, 20,000 iterations, seed
  20260825, percentile 95% CI; p as in §3.5.
- **Day-level sign-flip permutation:** multiply each Monday's day-total
  by ±1 with probability ½ (independently per day), recompute the mean,
  20,000 iterations, seed 20260825; two-sided p.
- BH at M = 2 alongside AC-FLIP's primary p.

### 5.7 Tail destruction

- Remove the single largest-|value| Monday (≈ top 1% of 138): mean must
  remain > 0.
- Remove the top 5% by |value| (7 Mondays): mean must remain > 0.
- Both trimmed means are reported with their CIs; only the **sign** is
  gated, since trimming mechanically shrinks magnitude.

### 5.8 THE NINE CONFIRMATION CONDITIONS FOR MONDAY

| # | condition | threshold |
|---|---|---|
| M1 | Data integrity | identical to A1 |
| M2 | Minimum n | ≥ 120 Monday exchange-days (coverage shows 138) |
| M3 | Sign | mean Monday exchange-day return > 0 |
| M4 | Materiality retention | mean ≥ **+11.04 bp** |
| M5 | Dependence-aware CI | day-clustered 95% CI excludes 0 (20,000 iters, seed 20260825) |
| M6 | Multiplicity + permutation | BH `q ≤ 0.05` at M = 2 **and** sign-flip permutation `p ≤ 0.05` |
| M7 | Control | `mean(Mon) − mean(non-Mon) > 0` with its own 95% CI excluding 0 |
| M8 | Stability | mean Monday return > 0 in ≥ 2 of 3 years **and** in ≥ 18 of 32 months |
| M9 | Tail destruction | mean remains > 0 after dropping top 1% **and** after dropping top 5% by \|value\| |

---

## 6. ALLOWED VERDICTS (exhaustive; one per candidate)

| verdict | precise meaning |
|---|---|
| **CONFIRMED** | **every** condition passes (A1–A10, or M1–M9). |
| **PARTIALLY CONFIRMED — DIRECTIONAL ONLY, NOT PROMOTABLE** | all *sign*, *CI*, *multiplicity* and *permutation* conditions pass (A4/A5/A8/A9, or M3/M5/M6/M7), but ≥ 1 retention, stability or tail condition fails. The direction replicated; the effect did not survive intact. **Confers no promotion and no certificate change.** |
| **NOT CONFIRMED** | any sign, CI, multiplicity or permutation condition fails. |
| **VOID — SPECIFICATION ERROR** | the test could not be executed as written because of a defect in *this* document (e.g. an impossible envelope, an undefined cell, an infeasible n). Requires an explicit written diagnosis. **A VOID may not be retuned into a passing test, does not reduce M, and its slot in the family is spent.** |
| **VOID — INSUFFICIENT DATA** | a data-availability gate (A1/A2/A3, or M1/M2) fails for reasons outside the hypothesis. Same non-retuning rule. |

A failed candidate is **destroyed, not retuned**. No threshold in this
document may be relaxed after any holdout number is seen. No hypothesis
may be re-run under a new name. M stays at 2 regardless of outcome.

---

## 7. RVMR CERTIFICATE IMPACT CLAUSE (binding, and deliberately narrow)

**If AC-FLIP is CONFIRMED:**

1. RVMR-V1's certificate is amended in **documentation only**, from
   *"certified magnitude context"* to *"certified magnitude context,
   with HISTORICAL evidence that it also modulates short-horizon return
   memory."*
2. `analysis/rvmr/rvmr_spec.py`, `rvmr_run.py`, the RVMR forward logger,
   the prospective ledgers, OFH13/OFH14, and every NinjaTrader host
   remain **byte-for-byte unmodified**. Confirmation changes a sentence
   in a document, not a line of frozen code.
3. It authorizes **no** directional use of RVMR, **no** entry rule,
   **no** filter, **no** sizing, **no** strategy, and **no** live
   trading. Per §3.6, the 1m predictable component was ≈ 4× below cost
   in discovery; confirming its existence does not move it above cost.
4. The evidence stays **HISTORICAL**. Prospective shadow validation on
   genuinely future data remains a separate, unfunded step.

**If AC-FLIP is PARTIALLY CONFIRMED or worse:** the certificate is
unchanged, and the finding is recorded as a discovery-window structure
that did not survive holdout confirmation.

**If MONDAY is CONFIRMED:** it is recorded as a confirmed calendar
anomaly in NQ over 2024–2026. It touches nothing in RVMR and authorizes
no trading. Calendar effects are notoriously fragile; a confirmed
Monday effect would still require prospective validation.

---

## 8. DEFECT AND CAUSALITY AUDIT (performed BEFORE freezing)

| # | failure mode | AC-FLIP | MONDAY |
|---|---|---|---|
| D1 | **Impossible envelope** (a reference window containing its own decision bar — the XMARKET-H8 / RVMR-STRAT-B6 defect class) | **Clear.** `trailing_ratio` averages bars `i−1440 … i−1`, strictly excluding bar `i` (`rvmr_spec.py:82–91`). No decision bar enters its own normaliser. | **Clear.** No envelope; a day-total is a sum, not a conditional window. |
| D2 | **Look-ahead in state assignment** | **Clear.** States are computed on the full series but every state at index `i` depends only on bars `< i`. Reading them at holdout indices imports no future information. | n/a — no state used. |
| D3 | **Look-ahead in the outcome** | **Clear.** AC1 is a descriptive statistic of a realised series, not a forecast; no bar is scored against information after it. | **Clear.** |
| D4 | **Overlapping windows treated as independent** | **Addressed.** 1m returns overlap not at all; the 15m secondary uses strictly non-overlapping blocks; day-clustered resampling handles within-day dependence. | **Addressed.** Day-totals are disjoint by construction. |
| D5 | **Selection on the tested data** | **Clear for this family.** Both candidates were selected on ≤ 2023-12-31 only. Non-pristine caveat fully disclosed in §0.2. | Same. |
| D6 | **Multiple testing** | M = 2, BH, plus the cumulative-family clause §1.3.3 that forbids shrinking the family later. | Same. |
| D7 | **Estimator artifact** | **Disclosed, not hidden** (§4.2): state-filtered pairing. Robustness secondary S-e frozen to measure it. | **Disclosed** (§5.2): calendar-date accrual, not session accrual; Monday includes Monday-evening bars that belong to Tuesday's session. |
| D8 | **Survivorship / data conditioning** | None: the series is a single continuous contract; no instrument is selected on outcome. | Same. |
| D9 | **Roll contamination** | **Declared, not corrected.** The anomaly scan applied **no** roll quarantine (unlike XMARKET-V1, which quarantined ±2 days around three anchors). The confirmation applies **the same absence** of quarantine, so discovery and holdout are treated identically. Roll days may inject artificial 1m moves; this is a known, symmetric limitation of both windows and is reported, not patched mid-study. | Same. Roll Thursdays/Fridays are not Mondays, so the Monday cell is the least roll-exposed weekday — a point in its favour, not a fix. |
| D10 | **Timezone / DST** | Wall-clock ET stamps; DST shifts inherited verbatim from discovery. | Same; weekday is taken from the ET calendar date. |
| D11 | **Cost / economic misreading** | Blocked by §3.6 and §7.3. | Blocked by §3.6. |
| D12 | **Fabricated data** | None. Only genuine 1m OHLCV bars are read. No MBO, DOM, tick, iceberg or footprint data is used or inferred. No bar is interpolated, forward-filled, split into 5s/15s, or manufactured. Gaps are skipped. | Same. |

---

## 9. EXECUTION RULES (binding on the later execution directive)

1. **One run.** The engine executes once. No re-run after seeing output,
   except to fix a crash — and any crash fix must be disclosed with its
   diff and must not touch a threshold.
2. **No retuning of anything in §§3–5** after any holdout number exists.
3. **No new hypotheses.** No statistic outside this document may be
   computed on the holdout in this study.
4. **Report every gate**, passed and failed, with its number.
5. **Report the honest verdict**, including "the strongest finding in
   ~120 studies did not replicate" if that is what the data says.
6. The engine **submits no orders** and modifies nothing frozen.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
