# NVQ-V1 — STREAK3DN PROSPECTIVE FREEZE

Frozen 2026-08-28, **before any VALIDATION data (2026-09-01+) exists or
is opened**. This freeze is immutable: no threshold, definition,
direction, cost, or floor may change after scoring begins. It stands
alone and does not modify the hash-protected
`docs/PROSPECTIVE_REGISTRY.md`.
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

## Frozen signal (exact)

Daily RTH series from the canonical grid convention: RTH = close-stamps
571–960 ET; daily close = last RTH close; a day requires ≥300 RTH bars.
Let `c[t]` be the daily RTH close.

**STREAK3DN fires at the close of day t iff:**
`c[t] < c[t-1] < c[t-2] < c[t-3]` **and** `c[t-3] ≥ c[t-4]`
(exactly three consecutive down closes; the day before the streak not
down).

## Frozen measured object (primary)

Long, close-to-close: score `ret = ln(c[t+1]/c[t])`, reported in bp and
in MNQ points at `c[t]`. Cost model for the economic view: 1.740 pt RT
(overnight stressed); 0.87 pt base also reported. One MNQ contract,
non-compounded.

## Frozen secondary (the pre-frozen DEV translation, for comparison)

Long next session open → next session close (RTH only, no overnight):
points at 0.87 / 1.305 pt RT.

## Frozen anchors (DEV, exposed, for retention scoring)

n 84 · c2c +44.8 bp (~+84 pt) · overnight +30.7 / intraday +14.1 ·
win 63% · median +32.6 bp · positive 8/8 years · translation +22.8 pt
stressed, PF 1.328.

## Frozen verdict rule

Score after **24 prospective events** (≈ 2 years) or 2028-09-01,
whichever first:
- **CONFIRMS** if prospective c2c mean > 0 with ≥ 55% wins AND retention
  ≥ ⅓ of the +44.8 bp anchor.
- **FAILS** if prospective mean ≤ 0 or retention < ⅓.
- Fewer than 12 events by 2028-09-01 → INSUFFICIENT, extend, no verdict.
No interim peeking gates: interim counts may be reported, means may not
be examined before event 12.

## Protections

`DAY_TYPE_TAXONOMY` becomes a protected class while this runs:
no streak-length variants, no threshold variants, no filter overlays,
no direction inversion, no management additions may be tested on any
data until this freeze resolves. VALIDATION/OOS/LOCKBOX remain governed
by their existing boundaries; this freeze reads nothing before its
scoring dates arrive.
