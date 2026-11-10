# MROF_YT_WAVE20_PROFILELEVELS_REGISTRATION.md — levels like the value area

**Status: FROZEN on 2026-11-10, before any result from a validation
session (on or after 2026-09-21) or a replay holdout session existed.**

What is disclosed about the held-out sessions at this date:

- Two one-read checkpoint runs with `--unblind` were started (7 and
  8 November) and stopped before they finished. They wrote no report and
  no ledger entry, and no outcome from them was seen by anyone.
- The operator watches the market every day, and a chart of the first
  week of November was looked at while the Traders Reality Psy levels
  were matched (Amendment 45). No rule below was chosen from it.

On DEV, wave thirteen's return into yesterday's value area was the
cleanest small result (7 trades, 7 won, three sessions; seen, far too
few to judge). The operator asked which other levels of the same kind
belong beside it. This wave registers five, all built from where volume
traded or from yesterday's range. None of them was computed on any
session, DEV included, before this file was frozen.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.** Everything below is
read-only research on recorded tape. No order is placed.

---

## 1. The levels

Per instrument, NQ and MNQ separately, from the trades the runner hands
to wave thirteen's profile (the same trade stream, 1-point bins) and
from the runner's own levels. The value area is the context study's
`value_area` throughout (POC the fullest bin's centre, grown to 70 % of
the volume; VAH its top, VAL its bottom), as in wave thirteen §1.

| group | levels | built from | known |
| --- | --- | --- | --- |
| **ONVA** | `ON_POC`, `ON_VAH`, `ON_VAL` | the session's **overnight** trades, 18:00:00–09:29:59 ET | 09:30:00 ET to 17:00:00 ET that session |
| **WKVA** | `LW_POC`, `LW_VAH`, `LW_VAL` | the summed cash-session profiles of the **previous ISO week** | the whole session |
| **CLOSE** | `YDAY_CLOSE` | yesterday's last cash-session trade | the whole session |
| **MID** | `YDAY_MID` | halfway between the runner's `YDAY_HIGH` and `YDAY_LOW` | the whole session |

### 1.1 Completeness

- **Overnight:** the first overnight trade at or before 18:30 ET and the
  last at or after 09:00 ET; otherwise that session has no ONVA.
- **Last week:** the cash-session profiles (09:30:00–15:59:59 ET) of the
  sessions of the ISO week before the session's ISO week that are
  complete by wave thirteen's rule (first cash trade at or before
  10:00, last at or after 15:30); at least **3** of them; otherwise no
  WKVA.
- **Yesterday's close:** the price of the last cash-session trade of the
  latest earlier recorded session that has one **at or after
  15:59:00 ET**, that session being no more than **4 calendar days**
  before; otherwise no CLOSE.
- **Yesterday's midpoint:** `(YDAY_HIGH + YDAY_LOW) / 2` from wave
  eleven's copy of the runner's levels on the grid, not rounded; a
  session without both has no MID.

The runner does not follow contracts, so across a contract roll these
levels inherit its treatment of the instrument, as the main levels do.

## 2. The first signal at each level (four tests)

Wave fifteen §2, unchanged, at these levels only:

- **Signal:** wave eleven's WICK entry: a 10 s grid close a tick or more
  beyond the level, the last close not at it having been on the other
  side; entry at the first 10 s tick within 300 s where the mid is back
  a tick through and that tick's aggression is against the break
  (`z_delta_s >= 1.0`). The trade fades the break.
- **Taken:** only the first signal at each level per CME session.
- **Trade:** target 100 ticks (25 points), stop 60 ticks (15 points),
  1 800 s, mid-to-mid (wave six's `path_exit`), `mrofyt_costs`' round
  trip; one position at a time within each group and instrument.

| id | group |
| --- | --- |
| **ONVA** | the overnight value area |
| **WKVA** | last week's value area |
| **CLOSE** | yesterday's close |
| **MID** | yesterday's midpoint |

## 3. Back into the value area with speed (two tests)

Wave thirteen §2's event, unchanged, against the two new value areas in
place of yesterday's: out by at least 2 points beyond VAH or VAL; back
inside by a tick; at that tick at least 4 points back toward value over
the last 30 s and aggression into value with `z_delta_s >= 2.0`; entries
09:30–15:30 ET; the trade goes into value.

| id | value area | the event starts |
| --- | --- | --- |
| **RE-ON** | the overnight value area | at 09:30 ET, when it is known |
| **RE-WK** | last week's value area | with the session |

The fixed trade of §2 (25 / 15 / 1 800 s), one position at a time.

## 4. An untested POC as the target (two tests)

- **Untested POC:** the POC (wave thirteen §1) of each of the **5
  recorded sessions** before the trade's session, for as long as no
  recorded mid, from the first record of the following session on, has
  been at it or on both sides of it. A touch during time that was not
  recorded cannot be seen; a move through it is.
- **Target:** among the untested POCs at the entry, the nearest one
  **ahead of the entry by at least 40 ticks (10 points)**; the target is
  **2 ticks short of it** (wave nine's NEXT LEVEL rule); stop 60 ticks,
  1 800 s, no cap.
- **Trades:** wave eight's L2 events. `NP-ALL` every L2 event;
  `NP-FIRST` wave fourteen's first signals. Only trades that have such a
  POC are compared; the others are counted beside.
- **Statistic:** per trade, net with the POC target minus net with the
  fixed 100 ticks, same entry and stop, session-clustered (wave nine's
  `paired_stats`).

## 5. Verdicts (NQ; MNQ described beside, never tested)

- **§2 and §3:** wave fourteen's verdict on each test's own trades: 30
  or more trades; mean net per trade above 0 with its session-clustered
  95 % interval above 0; still above 0 without the session of the
  largest total. **Holm** over the four tests of §2, and separately over
  the two of §3, at 0.05.
- **§4:** 30 or more compared trades; the mean difference above 0 with
  its 95 % interval above 0; still above 0 without the session of the
  largest total difference; **Holm** over the two at 0.05.
- **PASS**, or **NOT PROVEN** with the reason; under 30, **NOT ENOUGH
  TRADES**.

Beside, not tested: every signal of each group (not only the first), the
counts of levels built, and the L2 trades with no untested POC ahead.

## 6. Withholding and where it is judged

- A held-out read shows the count only for any test with fewer than 30
  NQ trades.
- **DEV:** describes. **Validation** (`--unblind`): **secondary** tests,
  part of the one-read checkpoint from V46 on. **Replay holdout:**
  separately.
- Wave fourteen stays the headline. Eight tests are added to a read that
  already holds about fifty-four; a pass here is a lead.

## 7. What a verdict leads to

A PASS admits that level group (or that target) to a later registration
judged on sessions read by nothing before it; it changes no other
wave's rule and nothing in wave seventeen's confluence families.

## Explicitly NOT registered

- the developing (today's) value area, intraday volume nodes, monthly
  or composite profiles, single prints
- the overnight value area before 09:30; the full-session (not cash)
  weekly profile; other shares than 70 %, other bin sizes
- the EARLY or CLOSE entries at these levels; a second signal at a level
- POC, far-edge or scaled targets for §3; any other target, stop or hold
  limit in §2 and §3
- an untested POC older than 5 sessions, or as an entry level; untested
  VAH or VAL
- the Traders Reality Psy levels (their window is not yet matched to the
  chart, Amendment 45)
- machine-learned models of any kind
- live, paper or simulated order placement

## Implementation record — 2026-11-10

`mrofyt_profilelevels.py`, `tests_mrofyt_profilelevels.py`. Written
against this file before any held-out result existed; verified on
hand-built trades, grids and paths and on synthetic recorder-format
runs, never on market evidence.

| registered | implemented as | precision |
| --- | --- | --- |
| §1 | `ProfileLevelsRunner` (wave thirteen's runner, hooks only), `on_values`, `week_values`, `prev_close`, `yday_mids`, `levels_by_instrument` | the 09:30 of a session is the last overnight trade's time plus the rest of the overnight window |
| §2 | `OL.wick_events`, `OL.first_signals`, `OL.score`, `V.one_at_a_time` | wave fifteen's code, these levels only |
| §3 | `reentry_events` | wave thirteen's `va_events` with the value area supplied; the suite shows it gives wave thirteen's own events when handed yesterday's value |
| §4 | `naked_pocs`, `naked_target`, `score_naked`, `paired_verdict` | "at or on both sides" is the range of the mids since the following session's first record containing the POC |
| §5 | `FS.verdict`, `apply_holm` | none |
| §6 | `run`, `text`, the ledgers | none |
