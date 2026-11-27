# MROF_YT_WAVE31_SIZING_REGISTRATION.md — how far, used for size: RVMR and ATR on A and B

**Status: FROZEN on 2026-11-27, before the tool was written, before
RVMR's or ATR's state was computed on any trade of A or B, and before
any ES or RTY bar, or any NQ bar after 2026-06-11, was read by
anything.** What had been seen beforehand is listed in §0.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on historical bars. No order is placed.

---

## 0. Where this comes from, and what was already seen

The operator asked, on 2026-11-27, whether a forecast of how far the
market will move can make A and B steadier. On NQ's ten years, the
prop account of wave twenty-six blew six accounts and fell as much as
$11,000 at its first budgets.

Two forecasts of how far the market will move are at hand.

- **RVMR** (`docs/RVMR_V1_SPEC.md`, frozen in August): a minute's range
  over its mean over the 1,440 bars before it; HIGH above 2.335. On
  five earlier years the next 5 to 60 minutes moved more after HIGH than
  after MEDIUM, and more after MEDIUM than after LOW, in 70 of 70 checks;
  it held on ES unchanged. It is **certified for use as a registered
  context variable** in later research, and its own file says sizing
  is not yet authorised: this file is that registration.
- **ATR**: the mean true range of the last 20 minutes. Earlier work
  found it the stronger predictor of the two; RVMR adds a quarter to a
  third beyond it.

This file asks one thing: **used only to make a position smaller when
the market is wild, does either forecast give A or B a better result
per unit of risk, on markets these rules were not picked on?** A rule
that does not beat the plain ATR does not earn RVMR a place.

**Seen beforehand:** everything in the reports of waves twenty-four and
twenty-six on NQ's ten years, including the prop account (six failures,
the daily stop met on ten days and preventing none of them); RVMR's
five-year replication and its strategy studies on other rules (RVMR ×
ten earlier strategies: nothing survived; avoiding HIGH: favourable and
adverse moves grew together); MEMORY-PRED (the last minute tends to
continue in HIGH states).

**Not seen:** RVMR's or ATR's state at any decision of A or B on any
bar; any ES or RTY bar; any NQ bar after 2026-06-11.

## 1. Common to all

Wave twenty-four's bars, trading days, front contract, P(m), VWAP, the
daily chain, A and B; wave twenty-five's markets (NQ, ES, RTY), their
costs, halves and the reader's refusals, all unchanged. A is wave
twenty-four's trade, sized as its source (leverage = min(1 % ÷ (R ÷
entry), 4)); B is wave twenty-four's rule, sized as its source
(leverage = min(2 % ÷ s, 4)).

## 2. The decisions

- **A** decides at 09:35.
- **B** decides at each of its half-hour times at which it changes its
  position; the flat at 16:00 is a close, not a decision.

At a decision at minute m, a measure is read on **the last completed
one-minute bar ending at or before m** of the session's front contract.

## 3. The two measures

- **RVMR:** RANGE-REGIME-V1 exactly as `analysis/rvmr/rvmr_spec.py`
  computes it (sha256 beginning `e348f035a9209540`, imported, not
  copied; the tool stops if the file has changed): the bar's high minus
  low over the mean of the 1,440 bars before it, over the front
  contracts' bars of the trading days in time order, overnight
  included. **HIGH** when the score is above 2.335. Unavailable (fewer
  than 1,440 bars before it) counts as not HIGH.
- **ATR:** `rvmr_spec.atr20` over the same bars: the mean true range of
  the 20 bars ending at the decision bar. Its usual level is the mean
  of the same figure at the same minute on the 14 previous eligible
  sessions. **HIGH** when it is at least **1.5 times** its usual
  level. Unavailable (fewer than 14 sessions) counts as not HIGH.

## 4. The rule

Under a measure, a position decided in a HIGH state is taken at **half
size**; otherwise at full size. For A: its whole trade. For B: the
position taken at that change, held until B's next change; trading
from one position to another pays B's cost on the size bought or sold.
Nothing else changes: not the entries, the exits, the stops or the
sizing formulas.

Three versions of each rule are compared on the same sessions:
**UNCHANGED**, **ATR** and **RVMR**.

## 5. The numbers

A session's result x is the rule's net basis points of capital in its
source's sizing (0 on a session without a trade). A is judged on its
eligible sessions, B on those on which it has its bounds and its
volatility.

- **Sharpe:** the mean of x over its standard deviation.
- **Fall:** the largest drop of the running sum of x from its highest
  point; the **fall ratio** is the fall over the mean of x, a fall
  measured in average sessions (none when the mean is not above 0).

## 6. The verdict

For each of A and B and each measure, the measure is **BETTER** when,
on **each of ES and RTY**:

- its Sharpe is **at least 5 % higher** than UNCHANGED's; and
- its fall ratio is lower than UNCHANGED's.

Then:

- If RVMR is BETTER and its Sharpe is at least ATR's on both ES and
  RTY, **RVMR** goes on for that rule.
- Otherwise, if ATR is BETTER, **ATR** goes on: the simpler tool wins
  a tie or a loss.
- Otherwise **neither** goes on, and the rule keeps its size.

A measure can go on for a rule **only if that rule itself passes wave
twenty-five**. NQ's ten years are reported, never judged: the account
plan was fitted to them. Halving a position cannot create an edge, so
a false pass here would cost less than a false pass of a rule; with
no effect, both markets improve together by chance about one time in
four or five. A pass is followed on the shadow step, not acted on.

Reported beside, never judged: the share of decisions that are HIGH
under each measure; A's mean result on HIGH and on other sessions,
before halving; the halves; A and B together.

## 7. Reads

- NQ's ten years (already read), ES and RTY (wave twenty-five's 2a
  exports), each read by this wave's own command **once**, recorded
  before any result is shown. They can be made in the same sitting as
  waves twenty-five, twenty-six and thirty.
- Sessions from 2026-07-01 are never read by it.

## Explicitly NOT registered

- other factors than one half; other thresholds, windows or minutes;
  the volume regime; sizing up in quiet states; skipping trades
- a measure inside the day for exits or stops; any change to A or B
- the prop account in micros: reported by a later file, because with
  one or two micros a trade a half size often cannot be taken
- markets other than NQ, ES and RTY
- live, paper or simulated order placement

## Expected beforehand (written 2026-11-27, before anything was computed)

Little. A already risks a fixed share of capital on each trade, so a
wild day does not make its loss larger. B is already sized by its own
14-day volatility. RVMR's window includes the quiet night, so at 09:35
its state is likely HIGH on most days: for A it mostly halves
everything, which changes neither its Sharpe nor its fall ratio. And
the account's big drops came from runs of ordinary losses, not from
single wild days. **ATR better for B:** about one chance in four; for
A about one in six. **RVMR better for B:** about one in five; for A
about one in ten. **RVMR beating ATR where both are better:** about one
in four. The most likely outcome: neither goes on, and the drops are a
matter for the sizing of the account, not of the trade.
